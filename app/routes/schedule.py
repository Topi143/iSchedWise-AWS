"""
Schedule routes for managing class schedules
Supports multi-user concurrent scheduling with optimistic locking
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, case
from sqlalchemy.orm import joinedload
from datetime import datetime, time, timedelta
from app.services.export_service import (
    generate_class_schedule_excel,
    generate_faculty_schedule_excel,
    generate_room_schedule_excel,
    generate_class_schedule_excel_for_posting,
    generate_class_schedule_pdf,
    generate_faculty_schedule_pdf,
    generate_room_schedule_pdf
)
import os

import json

from app.extensions import db, csrf
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.schedule_snapshot import ScheduleSnapshot
from app.models.program import Program
from app.models.department import Department
from app.models.section import Section
from app.models.curriculum import Subject, Curriculum
from app.models.faculty import Faculty, FacultySubjectAssignment, FacultyAvailability
from app.models.building import Room
from app.models.settings import AcademicSettings
from app.models.activity_log import UserActivityLog
from app.decorators import role_required
from app.routes.socket_events import broadcast_schedule_change, broadcast_conflict_alert

# Day-of-week ordering: Monday=0 … Sunday=6 for natural sort
_DAY_ORDER = case(
    {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
     'Friday': 4, 'Saturday': 5, 'Sunday': 6},
    value=Schedule.day_of_week,
    else_=7,
)

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')


@schedule_bp.route('/')
@login_required
def index():
    """Redirect to appropriate schedule view based on query params (backward compat)"""
    if request.args.get('faculty_id'):
        return redirect(url_for('schedule.faculty_view', **request.args))
    elif request.args.get('room_id'):
        return redirect(url_for('schedule.room_view', **request.args))
    elif request.args.get('exam_section_id'):
        args = request.args.to_dict()
        section_id = args.pop('exam_section_id', None)
        if section_id:
            args['section_id'] = section_id
        return redirect(url_for('schedule.exam_view', **args))
    return redirect(url_for('schedule.class_view', **request.args))


# ============================================================================
# HELPER: Common data loading functions
# ============================================================================

def _get_departments_for_user():
    """Get programs based on current user's access level."""
    user_program_ids = current_user.get_program_ids()
    if user_program_ids is None:
        return Program.query.filter_by(is_active=True).order_by(Program.program_code).all()
    else:
        return Program.query.filter(
            Program.is_active == True,
            Program.id.in_(user_program_ids)
        ).order_by(Program.program_code).all()


def _get_sections_for_user(department_filter=None):
    """Get sections based on current user's program access."""
    user_program_ids = current_user.get_program_ids()
    sections_query = Section.query
    if user_program_ids is not None:
        sections_query = sections_query.filter(Section.program_id.in_(user_program_ids))
    if department_filter:
        sections_query = sections_query.filter_by(program_id=department_filter)
    return sections_query.order_by(Section.section_name).all()


def _build_faculty_available_days_map(faculty_ids):
    """Return a map of faculty_id -> ordered available day names."""
    if not faculty_ids:
        return {}

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    records = FacultyAvailability.query.filter(
        FacultyAvailability.faculty_id.in_(faculty_ids),
        FacultyAvailability.is_active == True,
        FacultyAvailability.day_of_week.isnot(None)
    ).all()

    days_by_faculty = {faculty_id: set() for faculty_id in faculty_ids}
    for record in records:
        days_by_faculty.setdefault(record.faculty_id, set()).add(record.day_of_week)

    return {
        faculty_id: [day for day in day_order if day in days_by_faculty.get(faculty_id, set())]
        for faculty_id in faculty_ids
    }


def _attach_faculty_available_days(faculties):
    """Attach an `available_days` attribute to faculty model instances for template rendering."""
    if not faculties:
        return faculties

    days_map = _build_faculty_available_days_map([faculty.id for faculty in faculties])
    for faculty in faculties:
        faculty.available_days = days_map.get(faculty.id, [])
    return faculties


def _get_schedule_counts(items, model_class, id_field, current_settings, extra_filters=None):
    """Calculate schedule counts for a list of items using a single grouped query."""
    if not items:
        return {}

    item_ids = [item.id for item in items]
    col = getattr(model_class, id_field)

    q = db.session.query(
        col, func.count(model_class.id)
    ).filter(
        col.in_(item_ids),
        model_class.is_active == True
    )
    if current_settings:
        q = q.filter(
            model_class.academic_year == current_settings.academic_year,
            model_class.semester == current_settings.semester
        )
    rows = q.group_by(col).all()

    counts = {item_id: 0 for item_id in item_ids}
    for item_id, count in rows:
        counts[item_id] = count
    return counts


def _coerce_setting_time(value, fallback_hour):
    """Normalize settings values that may be stored as time, int hour, or HH:MM string."""
    if isinstance(value, time):
        return value
    if isinstance(value, int):
        return time(value, 0)
    if isinstance(value, str):
        try:
            parts = value.split(':')
            return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except Exception:
            pass
    return time(fallback_hour, 0)


def _minutes_of(t):
    return t.hour * 60 + t.minute


def _fmt_setting_time(t):
    return t.strftime('%I:%M %p').lstrip('0')


def _get_time_settings(current_settings):
    """Get schedule time range from settings."""
    start_time = _coerce_setting_time(
        getattr(current_settings, 'schedule_start_time', None) if current_settings else None,
        7
    )
    end_time = _coerce_setting_time(
        getattr(current_settings, 'schedule_end_time', None) if current_settings else None,
        20
    )
    return {
        'schedule_start_hour': start_time.hour,
        'schedule_end_hour': end_time.hour,
        'schedule_end_minute': end_time.minute,
        'schedule_start_time': start_time.strftime('%H:%M'),
        'schedule_end_time': end_time.strftime('%H:%M'),
    }


def _get_exam_time_settings(current_settings):
    """Get exam-specific time settings."""
    exam_start_time = _coerce_setting_time(
        getattr(current_settings, 'exam_start_time', None) if current_settings else None,
        7
    )
    exam_end_time = _coerce_setting_time(
        getattr(current_settings, 'exam_end_time', None) if current_settings else None,
        17
    )
    settings = {
        'exam_start_hour': exam_start_time.hour,
        'exam_end_hour': exam_end_time.hour,
        'exam_end_minute': exam_end_time.minute,
        'exam_start_time': exam_start_time.strftime('%H:%M'),
        'exam_end_time': exam_end_time.strftime('%H:%M'),
        'exam_lunch_start': '12:00',
        'exam_lunch_end': '13:00',
        'exam_slot_duration': current_settings.exam_slot_duration if current_settings else 30,
        'exam_duration_limit': current_settings.exam_duration_limit if current_settings else 120,
        'exam_period_start': None,
        'exam_period_end': None,
    }
    if current_settings:
        if current_settings.exam_lunch_start:
            settings['exam_lunch_start'] = current_settings.exam_lunch_start.strftime('%H:%M')
        if current_settings.exam_lunch_end:
            settings['exam_lunch_end'] = current_settings.exam_lunch_end.strftime('%H:%M')
        if hasattr(current_settings, 'exam_period_start') and current_settings.exam_period_start:
            settings['exam_period_start'] = current_settings.exam_period_start.strftime('%Y-%m-%d')
        if hasattr(current_settings, 'exam_period_end') and current_settings.exam_period_end:
            settings['exam_period_end'] = current_settings.exam_period_end.strftime('%Y-%m-%d')
    return settings


# ============================================================================
# BADGE STATUS HELPERS - Color-coded faculty/room badges
# ============================================================================

def _get_faculty_load_status(faculties, current_settings):
    """
    Compute load status for each faculty member.
    Returns dict {faculty_id: {'status': str, 'current': float, 'max': float, 'pct': float}}.
    """
    result = {}
    ay = current_settings.academic_year if current_settings else None
    sem = current_settings.semester if current_settings else None
    for fac in faculties:
        current_load, max_units, pct, status = fac.get_load_status(ay, sem)
        result[fac.id] = {
            'status': status,     # 'normal', 'warning', 'exceeded'
            'current': current_load,
            'max': max_units,
            'pct': round(pct)
        }
    return result


# ============================================================================
# VIEW ROUTES - Separate pages for each schedule type
# ============================================================================

@schedule_bp.route('/class')
@login_required
def class_view():
    """Class schedule view page - master-detail layout with sections"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    programs = _get_departments_for_user()

    department_filter = request.args.get('program_id', type=int)
    if department_filter is None and len(programs) == 1:
        department_filter = programs[0].id

    sections = _get_sections_for_user(department_filter)
    section_schedule_counts = _get_schedule_counts(sections, Schedule, 'section_id', current_settings)

    # Get selected section
    selected_section_id = request.args.get('section_id', type=int)
    selected_section = None
    schedules = []

    if selected_section_id:
        selected_section = Section.query.get(selected_section_id)
        if selected_section:
            schedules_query = Schedule.query.options(
                joinedload(Schedule.section),
                joinedload(Schedule.subject),
                joinedload(Schedule.faculty),
                joinedload(Schedule.room)
            ).filter_by(section_id=selected_section_id, is_active=True)
            if current_settings:
                schedules_query = schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            schedules = schedules_query.order_by(_DAY_ORDER, Schedule.start_time).all()

    time_settings = _get_time_settings(current_settings)

    return render_template(
        'schedule_class.html',
        sections=sections,
        selected_section=selected_section,
        schedules=schedules,
        programs=programs,
        department_filter=department_filter,
        current_settings=current_settings,
        section_schedule_counts=section_schedule_counts,
        **time_settings
    )


@schedule_bp.route('/faculty')
@login_required
def faculty_view():
    """Faculty schedule view page - master-detail layout with faculty members"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    programs = _get_departments_for_user()

    # Derive unique departments from user's programs for the faculty filter
    # Faculty belongs to departments (not programs), so we need department IDs
    user_program_ids = current_user.get_program_ids()
    if user_program_ids is None:
        # Admin: show all active departments
        faculty_departments = Department.query.filter_by(is_active=True).order_by(Department.department_code).all()
    else:
        # Dean: show only departments that contain their programs
        dept_ids = list({p.department_id for p in programs if p.department_id})
        faculty_departments = Department.query.filter(
            Department.id.in_(dept_ids),
            Department.is_active == True
        ).order_by(Department.department_code).all() if dept_ids else []

    faculty_department_filter = request.args.get('faculty_department_id', type=int)

    if faculty_department_filter:
        from app.models.program import Program
        from sqlalchemy import or_
        
        progs_in_dept = Program.query.filter_by(department_id=faculty_department_filter, is_active=True).all()
        prog_ids = [p.id for p in progs_in_dept]
        
        _teaching_fac_q = db.session.query(Schedule.faculty_id).join(Section).filter(
            Schedule.faculty_id.isnot(None),
            Schedule.is_active == True,
            Section.program_id.in_(prog_ids)
        )
        if current_settings:
            _teaching_fac_q = _teaching_fac_q.filter(
                Schedule.academic_year == current_settings.academic_year,
                Schedule.semester == current_settings.semester
            )
        _teaching_fac_ids = [r[0] for r in _teaching_fac_q.distinct().all()]

        if _teaching_fac_ids:
            faculties_query = Faculty.query.filter(
                Faculty.is_active == True,
                or_(
                    Faculty.department_id == faculty_department_filter,
                    Faculty.id.in_(_teaching_fac_ids)
                )
            )
        else:
            faculties_query = Faculty.query.filter(
                Faculty.is_active == True,
                Faculty.department_id == faculty_department_filter
            )
    else:
        faculties_query = Faculty.query.filter_by(is_active=True)

    faculties_list = faculties_query.order_by(Faculty.last_name, Faculty.first_name).all()
    faculty_schedule_counts = _get_schedule_counts(faculties_list, Schedule, 'faculty_id', current_settings)

    # Get selected faculty
    selected_faculty_id = request.args.get('faculty_id', type=int)
    selected_faculty = None
    faculty_schedules = []

    if selected_faculty_id:
        selected_faculty = Faculty.query.get(selected_faculty_id)
        if selected_faculty:
            faculty_schedules_query = Schedule.query.options(
                joinedload(Schedule.section),
                joinedload(Schedule.subject),
                joinedload(Schedule.faculty),
                joinedload(Schedule.room)
            ).filter_by(faculty_id=selected_faculty_id, is_active=True)
            if current_settings:
                faculty_schedules_query = faculty_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            faculty_schedules = faculty_schedules_query.order_by(
                _DAY_ORDER, Schedule.start_time
            ).all()

    time_settings = _get_time_settings(current_settings)

    # Faculty load status for color-coded badges
    faculty_load_status = _get_faculty_load_status(faculties_list, current_settings)

    return render_template(
        'schedule_faculty.html',
        faculties=faculties_list,
        selected_faculty=selected_faculty,
        faculty_schedules=faculty_schedules,
        programs=programs,
        faculty_departments=faculty_departments,
        faculty_department_filter=faculty_department_filter,
        current_settings=current_settings,
        faculty_schedule_counts=faculty_schedule_counts,
        faculty_load_status=faculty_load_status,
        **time_settings
    )


@schedule_bp.route('/room')
@login_required
def room_view():
    """Room schedule view page - master-detail layout with rooms"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()

    from app.models.building import Building
    buildings = Building.query.filter_by(is_active=True).order_by(Building.building_name).all()

    rooms_query = Room.query.filter_by(is_available=True)
    rooms_list = rooms_query.order_by(Room.room_number).all()
    room_schedule_counts = _get_schedule_counts(rooms_list, Schedule, 'room_id', current_settings)

    # Get selected room
    selected_room_id = request.args.get('room_id', type=int)
    selected_room = None
    room_schedules = []

    if selected_room_id:
        selected_room = Room.query.get(selected_room_id)
        if selected_room:
            room_schedules_query = Schedule.query.options(
                joinedload(Schedule.section),
                joinedload(Schedule.subject),
                joinedload(Schedule.faculty),
                joinedload(Schedule.room)
            ).filter_by(room_id=selected_room_id, is_active=True)
            if current_settings:
                room_schedules_query = room_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            room_schedules = room_schedules_query.order_by(
                _DAY_ORDER, Schedule.start_time
            ).all()

    time_settings = _get_time_settings(current_settings)

    return render_template(
        'schedule_room.html',
        rooms=rooms_list,
        selected_room=selected_room,
        room_schedules=room_schedules,
        current_settings=current_settings,
        room_schedule_counts=room_schedule_counts,
        buildings=buildings,
        **time_settings
    )


@schedule_bp.route('/exam')
@login_required
def exam_view():
    """Exam schedule view page - master-detail layout with sections"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    programs = _get_departments_for_user()

    exam_department_filter = request.args.get('exam_department_id', type=int)
    if exam_department_filter is None and len(programs) == 1:
        exam_department_filter = programs[0].id

    exam_sections = _get_sections_for_user(exam_department_filter)
    exam_section_schedule_counts = _get_schedule_counts(
        exam_sections, ExamSchedule, 'section_id', current_settings
    )

    # Get selected section for exam
    selected_exam_section_id = request.args.get('section_id', type=int)
    selected_exam_section = None
    exam_schedules = []

    if selected_exam_section_id:
        selected_exam_section = Section.query.get(selected_exam_section_id)
        if selected_exam_section:
            exam_schedules_query = ExamSchedule.query.filter_by(
                section_id=selected_exam_section_id, is_active=True
            )
            if current_settings:
                exam_schedules_query = exam_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            exam_schedules = exam_schedules_query.order_by(
                ExamSchedule.exam_date, ExamSchedule.start_time
            ).all()

    # Get all faculties and rooms for exam modals
    all_faculties = Faculty.query.filter_by(is_active=True).order_by(Faculty.last_name, Faculty.first_name).all()
    _attach_faculty_available_days(all_faculties)
    all_rooms = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()

    from app.models.building import Building
    buildings = Building.query.filter_by(is_active=True).order_by(Building.building_name).all()

    time_settings = _get_time_settings(current_settings)
    exam_time_settings = _get_exam_time_settings(current_settings)

    return render_template(
        'schedule_exam.html',
        exam_sections=exam_sections,
        selected_exam_section=selected_exam_section,
        exam_schedules=exam_schedules,
        programs=programs,
        exam_department_filter=exam_department_filter,
        current_settings=current_settings,
        exam_section_schedule_counts=exam_section_schedule_counts,
        all_faculties=all_faculties,
        all_rooms=all_rooms,
        buildings=buildings,
        **time_settings,
        **exam_time_settings
    )


def _get_unified_form_context(current_settings, selected_section, mode='add',
                               schedule=None, exam_schedule=None, active_tab='class'):
    """Build the full template context dict for the unified schedule_form.html."""
    from app.ai_scheduler import ai_scheduler

    time_settings = _get_time_settings(current_settings)
    exam_time_settings = _get_exam_time_settings(current_settings)
    sections = _get_sections_for_user()
    all_faculties = Faculty.query.filter_by(is_active=True).order_by(Faculty.last_name, Faculty.first_name).all()
    _attach_faculty_available_days(all_faculties)
    all_rooms = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()

    ctx = dict(
        mode=mode,
        active_tab=active_tab,
        unified_page=True,
        selected_section=selected_section,
        current_settings=current_settings,
        schedule=schedule,
        exam_schedule=exam_schedule,
        sections=sections,
        exam_sections=sections,          # same queryset, both need all user sections
        all_faculties=all_faculties,
        all_rooms=all_rooms,
        ai_enabled=ai_scheduler.enabled,
        operation_days=current_settings.get_operation_days_list() if current_settings else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
    )
    ctx.update(time_settings)
    ctx.update(exam_time_settings)
    return ctx


@schedule_bp.route('/create')
@login_required
def create_page():
    """Unified page for creating class or exam schedules."""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    section_id = request.args.get('section_id', type=int)
    selected_section = Section.query.get(section_id) if section_id else None
    active_tab = request.args.get('type', 'class')
    if active_tab not in ('class', 'exam'):
        active_tab = 'class'

    ctx = _get_unified_form_context(
        current_settings, selected_section,
        mode='add', active_tab=active_tab
    )
    return render_template('schedule_form.html', **ctx)


# Keep legacy add routes as redirects so old bookmarks / links still work
@schedule_bp.route('/class/add')
@login_required
def class_add_page():
    """Redirect to unified create page (class tab)."""
    section_id = request.args.get('section_id', '')
    url = url_for('schedule.create_page', type='class')
    if section_id:
        url += f'&section_id={section_id}' if '?' in url else f'?section_id={section_id}'
    return redirect(url)


@schedule_bp.route('/exam/add')
@login_required
def exam_add_page():
    """Redirect to unified create page (exam tab)."""
    section_id = request.args.get('section_id', '')
    url = url_for('schedule.create_page', type='exam')
    if section_id:
        url += f'&section_id={section_id}' if '?' in url else f'?section_id={section_id}'
    return redirect(url)


@schedule_bp.route('/class/edit/<int:schedule_id>')
@login_required
def class_edit_page(schedule_id):
    """Edit class schedule using the unified form page."""
    schedule = Schedule.query.options(
        joinedload(Schedule.section),
        joinedload(Schedule.subject),
        joinedload(Schedule.faculty),
        joinedload(Schedule.room)
    ).get_or_404(schedule_id)

    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    ctx = _get_unified_form_context(
        current_settings, schedule.section,
        mode='edit', schedule=schedule, active_tab='class'
    )
    return render_template('schedule_form.html', **ctx)


@schedule_bp.route('/exam/edit/<int:exam_id>')
@login_required
def exam_edit_page(exam_id):
    """Edit exam schedule using the unified form page."""
    exam_schedule = ExamSchedule.query.get_or_404(exam_id)
    selected_section = Section.query.get(exam_schedule.section_id)

    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    ctx = _get_unified_form_context(
        current_settings, selected_section,
        mode='edit', exam_schedule=exam_schedule, active_tab='exam'
    )
    return render_template('schedule_form.html', **ctx)



@schedule_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new schedule"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    ajax_warnings = []
    try:
        section_id = request.form.get('section_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int)
        room_id = request.form.get('room_id', type=int)
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        schedule_type = request.form.get('schedule_type', 'lecture')
        
        # Validation - faculty and room are now required
        if not all([section_id, subject_id, faculty_id, room_id, day_of_week, start_time_str, end_time_str]):
            msg = 'All required fields must be filled (including faculty and room).'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('schedule.create_page', type='class', section_id=section_id))
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        academic_year = current_settings.academic_year if current_settings else None
        semester = current_settings.semester if current_settings else None
        
        # Convert time strings to time objects
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            msg = 'End time must be after start time.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('schedule.create_page', type='class', section_id=section_id))
        
        # Validate schedule times are within configured hours
        if current_settings:
            schedule_start_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_start_time', None), current_settings.schedule_start_hour or 7)
            schedule_end_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_end_time', None), current_settings.schedule_end_hour or 20)

            if _minutes_of(start_time) < _minutes_of(schedule_start_cfg):
                msg = f'Start time must be at or after {_fmt_setting_time(schedule_start_cfg)}'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('schedule.create_page', type='class', section_id=section_id))
            
            if _minutes_of(end_time) > _minutes_of(schedule_end_cfg):
                msg = f'End time must be at or before {_fmt_setting_time(schedule_end_cfg)}'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('schedule.create_page', type='class', section_id=section_id))
        
        # Check for conflicts - same section, day, and overlapping time
        # Use pessimistic locking to prevent race conditions when multiple users add schedules
        conflict_query = Schedule.query.filter(
            Schedule.section_id == section_id,
            Schedule.day_of_week == day_of_week,
            Schedule.is_active == True,
            or_(
                and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
            )
        )
        
        if academic_year and semester:
            conflict_query = conflict_query.filter(
                Schedule.academic_year == academic_year,
                Schedule.semester == semester
            )
        
        # Pessimistic lock to prevent concurrent inserts for same slot
        conflict_query = conflict_query.with_for_update(nowait=True)
        
        if conflict_query.first():
            msg = 'Schedule conflict: This section already has a class at this time.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 409
            flash(msg, 'error')
            return redirect(url_for('schedule.create_page', type='class', section_id=section_id))
        
        # Check for faculty conflicts if faculty assigned
        if faculty_id:
            faculty_conflict = Schedule.query.filter(
                Schedule.faculty_id == faculty_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                faculty_conflict = faculty_conflict.filter(
                    Schedule.academic_year == academic_year,
                    Schedule.semester == semester
                )
            
            # Pessimistic lock to prevent concurrent faculty double-booking
            faculty_conflict = faculty_conflict.with_for_update(nowait=True)
            
            if faculty_conflict.first():
                msg = 'Faculty conflict: This faculty member is already assigned to another class at this time.'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 409
                flash(msg, 'error')
                return redirect(url_for('schedule.create_page', type='class', section_id=section_id))
        
        # Check for room conflicts if room assigned
        if room_id:
            room_conflict = Schedule.query.filter(
                Schedule.room_id == room_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                room_conflict = room_conflict.filter(
                    Schedule.academic_year == academic_year,
                    Schedule.semester == semester
                )
            
            # Use pessimistic locking to prevent race conditions
            room_conflict = room_conflict.with_for_update(nowait=True)
            
            if room_conflict.first():
                msg = 'Room conflict: This room is already booked at this time.'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 409
                flash(msg, 'error')
                return redirect(url_for('schedule.create_page', type='class', section_id=section_id))
        
        # Check faculty availability (warning only, not blocking)
        if faculty_id:
            faculty = Faculty.query.get(faculty_id)
            availability_result = FacultyAvailability.check_faculty_available_by_day(
                faculty_id, day_of_week, start_time, end_time
            )
            
            if availability_result['status'] == 'not_in_schedule':
                # Faculty has defined availability but not for this day/time - show warning
                warn_msg = f'Warning: {faculty.full_name if faculty else "Faculty"} is not marked as available on {day_of_week} at this time. Schedule created anyway.'
                if is_ajax:
                    ajax_warnings.append(warn_msg)
                else:
                    flash(warn_msg, 'warning')
        
        # Check for soft-deleted schedule in the same slot (uk_section_slot)
        existing_inactive = Schedule.query.filter_by(
            section_id=section_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            academic_year=academic_year,
            semester=semester,
            is_active=False
        ).first()

        if existing_inactive:
            # Reactivate and update the soft-deleted schedule
            existing_inactive.subject_id = subject_id
            existing_inactive.faculty_id = faculty_id
            existing_inactive.room_id = room_id
            existing_inactive.schedule_type = schedule_type
            existing_inactive.is_active = True
            existing_inactive.version = (existing_inactive.version or 1) + 1
            existing_inactive.updated_at = datetime.utcnow()
            db.session.flush()
            new_schedule = existing_inactive
        else:
            # Create new schedule
            new_schedule = Schedule(
                section_id=section_id,
                subject_id=subject_id,
                faculty_id=faculty_id,
                room_id=room_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                schedule_type=schedule_type,
                academic_year=academic_year,
                semester=semester,
                is_active=True
            )
            db.session.add(new_schedule)
            db.session.flush()  # Get the schedule ID
        
        # Auto-create FacultySubjectAssignment if it doesn't exist
        # This ensures workload tracking works automatically when scheduling
        if faculty_id and subject_id and academic_year and semester:
            existing_assignment = FacultySubjectAssignment.query.filter_by(
                faculty_id=faculty_id,
                subject_id=subject_id,
                academic_year=academic_year,
                semester=semester
            ).first()
            
            if not existing_assignment:
                new_assignment = FacultySubjectAssignment(
                    faculty_id=faculty_id,
                    subject_id=subject_id,
                    academic_year=academic_year,
                    semester=semester,
                    is_active=True,
                    is_archived=False
                )
                db.session.add(new_assignment)
        
        # Log the action
        subject = Subject.query.get(subject_id)
        section = Section.query.get(section_id)
        entity_name = f"{subject.subject_code if subject else 'N/A'} - {section.full_section_name if section else 'N/A'}"
        
        UserActivityLog.log_action(
            user_id=current_user.id,
            action='created',
            entity_type='schedule',
            entity_id=new_schedule.id,
            entity_name=entity_name,
            details=f'Created schedule for {day_of_week} {start_time}-{end_time}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Broadcast schedule creation to all connected users
        broadcast_schedule_change(new_schedule, 'created', 'class')
        
        # Broadcast conflict alert to users who might be editing overlapping slots
        # This enables real-time conflict awareness for multi-user scheduling
        schedule_data = {
            'section_id': section_id,
            'faculty_id': faculty_id,
            'room_id': room_id,
            'day_of_week': day_of_week,
            'start_time': str(start_time),
            'end_time': str(end_time)
        }
        broadcast_conflict_alert(schedule_data, [], academic_year, semester, 'class')
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'Schedule added successfully!',
                'warnings': ajax_warnings,
                'section_id': section_id,
                'schedule_id': new_schedule.id
            })
        flash('Schedule added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'error': f'Error adding schedule: {str(e)}'}), 500
        flash(f'Error adding schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.create_page', type='class', section_id=section_id))


@schedule_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing schedule with optimistic locking"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    ajax_warnings = []
    try:
        schedule_id = request.form.get('schedule_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int)
        room_id = request.form.get('room_id', type=int)
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        schedule_type = request.form.get('schedule_type', 'lecture')
        submitted_version = request.form.get('version', type=int)
        
        # Get schedule with pessimistic lock to prevent concurrent modification
        schedule = Schedule.query.filter_by(id=schedule_id).with_for_update().first_or_404()
        section_id = schedule.section_id
        
        # Optimistic locking: Check if version matches
        if submitted_version is not None and schedule.version != submitted_version:
            msg = 'This schedule was modified by another user. Please refresh and try again.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 409
            flash(msg, 'error')
            return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Check if locked by another user
        if schedule.is_locked_by_other(current_user.id):
            lock_info = schedule.get_lock_info()
            msg = f'This schedule is being edited by {lock_info["locked_by_name"]}. Please try again later.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 409
            flash(msg, 'error')
            return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Validation - faculty and room are now required
        if not all([subject_id, faculty_id, room_id, day_of_week, start_time_str, end_time_str]):
            msg = 'All required fields must be filled (including faculty and room).'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Convert time strings to time objects
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            msg = 'End time must be after start time.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Get current settings for schedule hours validation
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Validate schedule times are within configured hours
        if current_settings:
            schedule_start_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_start_time', None), current_settings.schedule_start_hour or 7)
            schedule_end_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_end_time', None), current_settings.schedule_end_hour or 20)

            if _minutes_of(start_time) < _minutes_of(schedule_start_cfg):
                msg = f'Start time must be at or after {_fmt_setting_time(schedule_start_cfg)}'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
            
            if _minutes_of(end_time) > _minutes_of(schedule_end_cfg):
                msg = f'End time must be at or before {_fmt_setting_time(schedule_end_cfg)}'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Check for conflicts (excluding current schedule)
        conflict_query = Schedule.query.filter(
            Schedule.id != schedule_id,
            Schedule.section_id == schedule.section_id,
            Schedule.day_of_week == day_of_week,
            Schedule.is_active == True,
            or_(
                and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
            )
        )
        
        if schedule.academic_year and schedule.semester:
            conflict_query = conflict_query.filter(
                Schedule.academic_year == schedule.academic_year,
                Schedule.semester == schedule.semester
            )
        
        if conflict_query.first():
            msg = 'Schedule conflict: This section already has a class at this time.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 409
            flash(msg, 'error')
            return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Check for faculty conflicts if faculty assigned
        if faculty_id:
            faculty_conflict = Schedule.query.filter(
                Schedule.id != schedule_id,
                Schedule.faculty_id == faculty_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if schedule.academic_year and schedule.semester:
                faculty_conflict = faculty_conflict.filter(
                    Schedule.academic_year == schedule.academic_year,
                    Schedule.semester == schedule.semester
                )
            
            if faculty_conflict.first():
                msg = 'Faculty conflict: This faculty member is already assigned to another class at this time.'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 409
                flash(msg, 'error')
                return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Check for room conflicts if room assigned
        if room_id:
            room_conflict = Schedule.query.filter(
                Schedule.id != schedule_id,
                Schedule.room_id == room_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if schedule.academic_year and schedule.semester:
                room_conflict = room_conflict.filter(
                    Schedule.academic_year == schedule.academic_year,
                    Schedule.semester == schedule.semester
                )
            
            if room_conflict.first():
                msg = 'Room conflict: This room is already booked at this time.'
                if is_ajax:
                    return jsonify({'success': False, 'error': msg}), 409
                flash(msg, 'error')
                return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))
        
        # Check faculty availability (warning only)
        if faculty_id:
            faculty = Faculty.query.get(faculty_id)
            availability_result = FacultyAvailability.check_faculty_available_by_day(
                faculty_id, day_of_week, start_time, end_time
            )
            
            if availability_result['status'] == 'not_in_schedule':
                # Faculty has defined availability but not for this day/time - show warning
                warn_msg = f'Warning: {faculty.full_name if faculty else "Faculty"} is not marked as available on {day_of_week} at this time. Schedule updated anyway.'
                if is_ajax:
                    ajax_warnings.append(warn_msg)
                else:
                    flash(warn_msg, 'warning')
        
        # Update schedule
        schedule.subject_id = subject_id
        schedule.faculty_id = faculty_id
        schedule.room_id = room_id
        schedule.day_of_week = day_of_week
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.schedule_type = schedule_type
        schedule.updated_at = datetime.utcnow()
        
        # Increment version for optimistic locking
        schedule.version = (schedule.version or 1) + 1
        
        # Release the edit lock
        schedule.release_lock(current_user.id)
        
        # Auto-create FacultySubjectAssignment if it doesn't exist
        # This ensures workload tracking when changing faculty during edit
        if faculty_id and subject_id and schedule.academic_year and schedule.semester:
            existing_assignment = FacultySubjectAssignment.query.filter_by(
                faculty_id=faculty_id,
                subject_id=subject_id,
                academic_year=schedule.academic_year,
                semester=schedule.semester
            ).first()
            
            if not existing_assignment:
                new_assignment = FacultySubjectAssignment(
                    faculty_id=faculty_id,
                    subject_id=subject_id,
                    academic_year=schedule.academic_year,
                    semester=schedule.semester,
                    is_active=True,
                    is_archived=False
                )
                db.session.add(new_assignment)
        
        # Log the action
        subject = Subject.query.get(subject_id)
        section = Section.query.get(schedule.section_id)
        entity_name = f"{subject.subject_code if subject else 'N/A'} - {section.full_section_name if section else 'N/A'}"
        
        UserActivityLog.log_action(
            user_id=current_user.id,
            action='edited',
            entity_type='schedule',
            entity_id=schedule.id,
            entity_name=entity_name,
            details=f'Updated schedule for {day_of_week} {start_time}-{end_time}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Broadcast schedule update to all connected users
        broadcast_schedule_change(schedule, 'updated', 'class')
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'Schedule updated successfully!',
                'warnings': ajax_warnings,
                'section_id': section_id,
                'schedule_id': schedule.id
            })
        flash('Schedule updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'error': f'Error updating schedule: {str(e)}'}), 500
        flash(f'Error updating schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.class_edit_page', schedule_id=schedule_id))


@schedule_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a schedule"""
    try:
        schedule_id = request.form.get('schedule_id', type=int)
        
        schedule = Schedule.query.filter_by(id=schedule_id).with_for_update().first_or_404()
        section_id = schedule.section_id
        
        # Check if locked by another user
        if schedule.is_locked_by_other(current_user.id):
            lock_info = schedule.get_lock_info()
            flash(f'This schedule is being edited by {lock_info["locked_by_name"]}. Please try again later.', 'error')
            return redirect(url_for('schedule.class_view', section_id=section_id))
        
        # Store schedule data before deletion for broadcast
        schedule_data = schedule.to_dict()
        
        # Soft delete (set is_active to False)
        schedule.is_active = False
        schedule.updated_at = datetime.utcnow()
        schedule.version = (schedule.version or 1) + 1
        
        # Log the action
        entity_name = f"{schedule.subject.subject_code if schedule.subject else 'N/A'} - {schedule.section.full_section_name if schedule.section else 'N/A'}"
        
        UserActivityLog.log_action(
            user_id=current_user.id,
            action='deleted',
            entity_type='schedule',
            entity_id=schedule.id,
            entity_name=entity_name,
            details=f'Deleted schedule for {schedule.day_of_week} {schedule.start_time}-{schedule.end_time}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Broadcast schedule deletion to all connected users
        broadcast_schedule_change(schedule, 'deleted', 'class')
        
        flash('Schedule deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.class_view', section_id=section_id))


@schedule_bp.route('/delete-ajax', methods=['POST'])
@login_required
@csrf.exempt
def delete_ajax():
    """Delete a schedule via AJAX and return JSON response."""
    try:
        data = request.get_json()
        schedule_id = data.get('schedule_id')
        
        if not schedule_id:
            return jsonify({'success': False, 'error': 'Schedule ID is required'}), 400
        
        schedule = Schedule.query.filter_by(id=schedule_id).with_for_update().first_or_404()
        section_id = schedule.section_id
        
        # Check if locked by another user
        if schedule.is_locked_by_other(current_user.id):
            lock_info = schedule.get_lock_info()
            return jsonify({
                'success': False,
                'error': f'This schedule is being edited by {lock_info["locked_by_name"]}. Please try again later.'
            }), 409
        
        # Store schedule data before deletion for broadcast
        schedule_data = schedule.to_dict()
        
        # Soft delete (set is_active to False)
        schedule.is_active = False
        schedule.updated_at = datetime.utcnow()
        schedule.version = (schedule.version or 1) + 1
        
        # Log the action
        entity_name = f"{schedule.subject.subject_code if schedule.subject else 'N/A'} - {schedule.section.full_section_name if schedule.section else 'N/A'}"
        
        UserActivityLog.log_action(
            user_id=current_user.id,
            action='deleted',
            entity_type='schedule',
            entity_id=schedule.id,
            entity_name=entity_name,
            details=f'Deleted schedule for {schedule.day_of_week} {schedule.start_time}-{schedule.end_time}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Broadcast schedule deletion to all connected users
        broadcast_schedule_change(schedule, 'deleted', 'class')
        
        return jsonify({
            'success': True,
            'message': 'Schedule deleted successfully',
            'section_id': section_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/batch-delete', methods=['POST'])
@login_required
@csrf.exempt
def batch_delete():
    """Delete multiple class schedules at once via AJAX."""
    try:
        data = request.get_json()
        schedule_ids = data.get('schedule_ids', [])

        if not schedule_ids or not isinstance(schedule_ids, list):
            return jsonify({'success': False, 'error': 'No schedules selected'}), 400

        if len(schedule_ids) > 100:
            return jsonify({'success': False, 'error': 'Cannot delete more than 100 schedules at once'}), 400

        schedules = Schedule.query.filter(
            Schedule.id.in_(schedule_ids),
            Schedule.is_active == True
        ).all()

        if not schedules:
            return jsonify({'success': False, 'error': 'No active schedules found for the given IDs'}), 404

        # Program access control for deans
        user_program_ids = current_user.get_program_ids()
        if user_program_ids is not None:
            schedules = [s for s in schedules if s.section and s.section.program_id in user_program_ids]

        # Check locks
        locked = [s for s in schedules if s.is_locked_by_other(current_user.id)]
        if locked:
            return jsonify({
                'success': False,
                'error': f'{len(locked)} schedule(s) are locked by other users. Please try again later.'
            }), 409

        deleted_count = 0
        section_id = schedules[0].section_id if schedules else None
        for schedule in schedules:
            schedule.is_active = False
            schedule.updated_at = datetime.utcnow()
            schedule.version = (schedule.version or 1) + 1
            deleted_count += 1

        # Log batch action
        entity_names = ', '.join(
            f"{s.subject.subject_code if s.subject else 'N/A'}" for s in schedules[:5]
        )
        if len(schedules) > 5:
            entity_names += f' (+{len(schedules) - 5} more)'

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='batch_deleted',
            entity_type='schedule',
            entity_id=None,
            entity_name=entity_names,
            details=f'Batch deleted {deleted_count} class schedule(s)',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        db.session.commit()

        # Broadcast deletions
        for schedule in schedules:
            broadcast_schedule_change(schedule, 'deleted', 'class')

        return jsonify({
            'success': True,
            'message': f'Successfully deleted {deleted_count} schedule(s)',
            'deleted_count': deleted_count,
            'section_id': section_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CONCURRENCY CONTROL ENDPOINTS
# ============================================================================

@schedule_bp.route('/lock/<int:schedule_id>', methods=['POST'])
@login_required
def acquire_lock(schedule_id):
    """Acquire edit lock on a schedule via REST API"""
    try:
        schedule = Schedule.query.filter_by(id=schedule_id).with_for_update(nowait=True).first()
        
        if not schedule:
            return jsonify({'success': False, 'error': 'Schedule not found'}), 404
        
        if schedule.is_locked_by_other(current_user.id):
            lock_info = schedule.get_lock_info()
            return jsonify({
                'success': False,
                'error': 'locked',
                'locked_by': lock_info['locked_by_name'],
                'locked_at': lock_info['locked_at'],
                'expires_at': lock_info['expires_at']
            }), 409
        
        if schedule.acquire_lock(current_user.id):
            db.session.commit()
            
            # Broadcast lock to other users
            broadcast_schedule_change(schedule, 'locked', 'class')
            
            return jsonify({
                'success': True,
                'schedule_id': schedule_id,
                'version': schedule.version
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to acquire lock'}), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/unlock/<int:schedule_id>', methods=['POST'])
@login_required
def release_lock(schedule_id):
    """Release edit lock on a schedule via REST API"""
    try:
        schedule = Schedule.query.get(schedule_id)
        
        if not schedule:
            return jsonify({'success': False, 'error': 'Schedule not found'}), 404
        
        if schedule.release_lock(current_user.id):
            db.session.commit()
            
            # Broadcast unlock to other users
            broadcast_schedule_change(schedule, 'unlocked', 'class')
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Not lock owner'}), 403
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/active-users')
@login_required
def get_active_users():
    """Get list of users currently viewing the schedule page"""
    from app.routes.socket_events import get_active_users_in_room
    
    academic_year = request.args.get('academic_year', '')
    semester = request.args.get('semester', '')
    
    users = get_active_users_in_room(academic_year, semester)
    
    return jsonify({
        'success': True,
        'users': list(users.values()),
        'count': len(users)
    })


@schedule_bp.route('/check-version/<int:schedule_id>')
@login_required
def check_version(schedule_id):
    """Check current version of a schedule for optimistic locking"""
    schedule = Schedule.query.get(schedule_id)
    
    if not schedule:
        return jsonify({'success': False, 'error': 'Schedule not found'}), 404
    
    return jsonify({
        'success': True,
        'schedule_id': schedule_id,
        'version': schedule.version,
        'lock_info': schedule.get_lock_info()
    })


@schedule_bp.route('/api/section-schedules/<int:section_id>')
@login_required
def get_section_schedules_json(section_id):
    """Get schedules for a section as JSON for modal calendar view"""
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Build query for schedules
        query = Schedule.query.options(
            joinedload(Schedule.subject),
            joinedload(Schedule.faculty),
            joinedload(Schedule.room)
        ).filter_by(
            section_id=section_id,
            is_active=True
        )
        
        # Filter by current academic settings if available
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        # Format schedules for JSON response
        schedules_data = []
        for schedule in schedules:
            start_time = schedule.start_time
            end_time = schedule.end_time
            
            # Convert time to minutes from midnight for positioning
            start_minutes = start_time.hour * 60 + start_time.minute if start_time else 0
            end_minutes = end_time.hour * 60 + end_time.minute if end_time else start_minutes + 60
            duration = end_minutes - start_minutes
            
            # Get curriculum_id through subject -> semester -> year_level -> curriculum_id
            curriculum_id = None
            if schedule.subject and schedule.subject.semester and schedule.subject.semester.year_level:
                curriculum_id = schedule.subject.semester.year_level.curriculum_id
            
            schedules_data.append({
                'id': schedule.id,
                'section_id': schedule.section_id,
                'curriculum_id': curriculum_id,
                'subject_id': schedule.subject_id,
                'subject_code': schedule.subject.subject_code if schedule.subject else 'N/A',
                'subject_name': schedule.subject.course_description if schedule.subject else 'N/A',
                'faculty_id': schedule.faculty_id,
                'faculty_name': schedule.faculty.full_name if schedule.faculty else 'TBA',
                'room_id': schedule.room_id,
                'room_number': schedule.room.room_number if schedule.room else 'TBA',
                'building_name': schedule.room.building.building_name if schedule.room and schedule.room.building else 'TBA',
                'day_of_week': schedule.day_of_week,
                'start_time': start_time.strftime('%H:%M') if start_time else '',
                'end_time': end_time.strftime('%H:%M') if end_time else '',
                'start_time_display': start_time.strftime('%I:%M %p') if start_time else '',
                'end_time_display': end_time.strftime('%I:%M %p') if end_time else '',
                'schedule_type': schedule.schedule_type or 'lecture',
                'start_minutes': start_minutes,
                'duration': duration,
                'version': schedule.version
            })
        
        # Get schedule hour settings
        start_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_start_time', None) if current_settings else None, 7)
        end_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_end_time', None) if current_settings else None, 20)
        start_hour = start_cfg.hour
        end_hour = end_cfg.hour
        
        return jsonify({
            'success': True,
            'schedules': schedules_data,
            'settings': {
                'start_hour': start_hour,
                'end_hour': end_hour
            }
        })
        
    except Exception as e:
        print(f"[SECTION SCHEDULES ERROR] {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/get-curricula/<int:section_id>')
@login_required
def get_curricula_for_section(section_id):
    """Get available curricula for a section's program ONLY"""
    try:
        # Get the section and keep API responses JSON-only (no HTML error pages).
        section = Section.query.filter_by(id=section_id).first()
        if not section:
            return jsonify({
                'curricula': [],
                'error': 'Section not found'
            }), 404

        # Dean access control: users can only query sections under allowed programs.
        user_program_ids = current_user.get_program_ids()
        if user_program_ids is not None and section.program_id not in user_program_ids:
            return jsonify({
                'curricula': [],
                'error': 'Access denied'
            }), 403
        
        # Ensure section has a program
        if not section.program_id:
            return jsonify({
                'curricula': [],
                'error': 'Section has no program assigned'
            }), 400
        
        # Get ONLY active curricula for THIS SPECIFIC program
        curricula = Curriculum.query.filter_by(
            program_id=section.program_id,
            is_active=True,
            is_archived=False
        ).order_by(Curriculum.curriculum_code).all()
        
        # Debug logging
        print(f"[CURRICULA] Section {section_id} ({section.section_name}) - Program ID: {section.program_id}")
        print(f"[CURRICULA] Found {len(curricula)} curricula for program {section.program_id}")
        
        # Format curricula for JSON response
        curricula_data = [
            {
                'id': curriculum.id,
                'curriculum_code': curriculum.curriculum_code,
                'degree_program': curriculum.degree_program,
                'program_id': curriculum.program_id,  # Include for verification
                'display': f"{curriculum.curriculum_code}"
            }
            for curriculum in curricula
        ]
        
        return jsonify({'curricula': curricula_data})
        
    except Exception:
        current_app.logger.exception('Failed to load curricula for section_id=%s', section_id)
        return jsonify({
            'curricula': [],
            'error': 'Failed to load curricula'
        }), 500


@schedule_bp.route('/get-subjects/<int:section_id>')
@login_required
def get_subjects_for_section(section_id):
    """Get subjects for a specific section based on curriculum, year level, and semester"""
    from flask import jsonify
    from app.models.curriculum import Curriculum, YearLevel, Semester
    
    try:
        # Get the section
        section = Section.query.get_or_404(section_id)
        
        # Get curriculum_id from query parameter (optional)
        curriculum_id = request.args.get('curriculum_id', type=int)
        
        # Get current academic settings to determine the semester
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if not current_settings:
            return jsonify({'subjects': []})
        
        # Determine semester number from semester name
        semester_mapping = {
            '1st Semester': 1,
            '2nd Semester': 2
        }
        semester_number = semester_mapping.get(current_settings.semester, 1)
        
        # Find curriculum
        if curriculum_id:
            # Use specified curriculum
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or curriculum.program_id != section.program_id:
                return jsonify({'subjects': [], 'error': 'Invalid curriculum for this section'})
        else:
            # Default to first active curriculum for this program
            curriculum = Curriculum.query.filter_by(
                program_id=section.program_id,
                is_active=True,
                is_archived=False
            ).first()
        
        if not curriculum:
            return jsonify({'subjects': []})
        
        # Find the year level
        year_level = YearLevel.query.filter_by(
            curriculum_id=curriculum.id,
            year_number=section.year_level
        ).first()
        
        if not year_level:
            return jsonify({'subjects': []})
        
        # Find the semester within that year level
        semester = Semester.query.filter_by(
            year_level_id=year_level.id,
            semester_number=semester_number
        ).first()
        
        if not semester:
            return jsonify({'subjects': []})
        
        # Get all subjects for this semester
        subjects = Subject.query.filter_by(semester_id=semester.id).order_by(Subject.subject_code).all()
        
        # Format subjects for JSON response with unit information
        def format_units(u):
            return f"{float(u):g}" if u is not None else "0"

        subjects_data = [
            {
                'id': subject.id,
                'subject_code': subject.subject_code,
                'course_description': subject.course_description,
                'lec_units': float(subject.lec_units),
                'lab_units': float(subject.lab_units),
                'total_units': subject.total_units,
                'display': f"{subject.subject_code} - {subject.course_description} ({format_units(subject.total_units)} units)"
            }
            for subject in subjects
        ]
        
        return jsonify({'subjects': subjects_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-subject-details/<int:subject_id>')
@login_required
def get_subject_details(subject_id):
    """Get detailed information about a subject including its curriculum"""
    from flask import jsonify
    import traceback
    
    try:
        print(f'[SUBJECT DETAILS] Fetching subject {subject_id}')
        subject = Subject.query.get(subject_id)
        
        if not subject:
            print(f'[SUBJECT DETAILS] Subject {subject_id} not found')
            return jsonify({'error': 'Subject not found'}), 404
        
        print(f'[SUBJECT DETAILS] Subject found: {subject.subject_code}')
        print(f'[SUBJECT DETAILS] Semester ID: {subject.semester_id}')
        
        # Get curriculum through relationships
        semester = subject.semester
        if not semester:
            print(f'[SUBJECT DETAILS] Subject {subject_id} has no semester')
            return jsonify({'error': 'Subject has no semester'}), 404
        
        print(f'[SUBJECT DETAILS] Semester found: {semester.semester_name}')
        print(f'[SUBJECT DETAILS] Year level ID: {semester.year_level_id}')
        
        year_level = semester.year_level
        if not year_level:
            print(f'[SUBJECT DETAILS] Semester {semester.id} has no year level')
            return jsonify({'error': 'Semester has no year level'}), 404
        
        print(f'[SUBJECT DETAILS] Year level found: {year_level.year_name}')
        print(f'[SUBJECT DETAILS] Curriculum ID: {year_level.curriculum_id}')
        
        curriculum = year_level.curriculum
        if not curriculum:
            print(f'[SUBJECT DETAILS] Year level {year_level.id} has no curriculum')
            return jsonify({'error': 'Year level has no curriculum'}), 404
        
        print(f'[SUBJECT DETAILS] Curriculum found: {curriculum.curriculum_code}')
        
        return jsonify({
            'id': subject.id,
            'subject_code': subject.subject_code,
            'course_description': subject.course_description,
            'curriculum_id': curriculum.id,
            'curriculum_code': curriculum.curriculum_code,
            'curriculum_name': curriculum.degree_program
        })
        
    except Exception as e:
        print(f'[SUBJECT DETAILS] ERROR: {str(e)}')
        print(f'[SUBJECT DETAILS] Traceback: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-subjects-by-curriculum/<int:curriculum_id>')
@login_required
def get_subjects_by_curriculum(curriculum_id):
    """Get all subjects for a specific curriculum"""
    from flask import jsonify
    from app.models.curriculum import Curriculum, YearLevel, Semester
    
    try:
        print(f'[SUBJECTS BY CURRICULUM] Fetching subjects for curriculum {curriculum_id}')
        
        # Get the curriculum
        curriculum = Curriculum.query.get(curriculum_id)
        if not curriculum:
            print(f'[SUBJECTS BY CURRICULUM] Curriculum {curriculum_id} not found')
            return jsonify({'subjects': []})
        
        print(f'[SUBJECTS BY CURRICULUM] Curriculum found: {curriculum.curriculum_code}')
        
        # Format subjects
        def format_units(u):
            return f"{float(u):g}" if u is not None else "0"

        # Get all subjects for this curriculum through year levels and semesters
        subjects = []
        for year_level in curriculum.year_levels:
            for semester in year_level.semesters:
                for subject in semester.subjects:
                    subjects.append({
                        'id': subject.id,
                        'subject_code': subject.subject_code,
                        'course_description': subject.course_description,
                        'lec_units': float(subject.lec_units),
                        'lab_units': float(subject.lab_units),
                        'total_units': subject.total_units,
                        'year_level': year_level.year_name,
                        'semester': semester.semester_name,
                        'display': f"{subject.subject_code} - {subject.course_description} ({format_units(subject.total_units)} units)"
                    })
        
        print(f'[SUBJECTS BY CURRICULUM] Found {len(subjects)} subjects')
        
        # Sort by year level number, semester number, then subject code
        subjects.sort(key=lambda x: (x['year_level'], x['semester'], x['subject_code']))
        
        return jsonify({'subjects': subjects})
        
    except Exception as e:
        print(f'[SUBJECTS BY CURRICULUM] ERROR: {str(e)}')
        import traceback
        print(f'[SUBJECTS BY CURRICULUM] Traceback: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-program-subjects/<int:section_id>')
@login_required
def get_program_subjects(section_id):
    """Get subjects from ALL active curricula under the same program.

    This is an optional, rarely-used feature that allows users to pick
    subjects from other year levels / semesters within the same program
    (e.g. retake subjects, cross-year electives).

    Returns subjects grouped by curriculum → year level → semester
    for <optgroup> rendering on the frontend.
    """
    from app.models.curriculum import Curriculum, YearLevel, Semester

    try:
        section = Section.query.get_or_404(section_id)

        # Dean access control
        user_program_ids = current_user.get_program_ids()
        if user_program_ids is not None and section.program_id not in user_program_ids:
            return jsonify({'subjects': [], 'error': 'Access denied'}), 403

        curricula = Curriculum.query.filter_by(
            program_id=section.program_id,
            is_active=True,
            is_archived=False
        ).order_by(Curriculum.curriculum_code).all()

        subjects = []
        for curriculum in curricula:
            for year_level in sorted(curriculum.year_levels, key=lambda yl: yl.year_number):
                for semester in sorted(year_level.semesters, key=lambda s: s.semester_number):
                    group_label = f"{curriculum.curriculum_code} › {year_level.year_name} › {semester.semester_name}"
                    for subject in sorted(semester.subjects, key=lambda s: s.subject_code):
                        subjects.append({
                            'id': subject.id,
                            'subject_code': subject.subject_code,
                            'course_description': subject.course_description,
                            'lec_units': float(subject.lec_units),
                            'lab_units': float(subject.lab_units),
                            'total_units': subject.total_units,
                            'curriculum_code': curriculum.curriculum_code,
                            'year_level_name': year_level.year_name,
                            'semester_name': semester.semester_name,
                            'group_label': group_label,
                            'display': f"{subject.subject_code} - {subject.course_description} ({subject.total_units} units)"
                        })

        return jsonify({'subjects': subjects})

    except Exception as e:
        import traceback
        print(f'[PROGRAM SUBJECTS] ERROR: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/batch-all-program-subjects/<int:section_id>')
@login_required
def batch_all_program_subjects(section_id):
    """Get subjects from ALL active curricula under the same program for batch builders.

    Returns in the same format as batch-unscheduled-subjects but includes
    subjects from other year levels/semesters.  Already-scheduled subjects
    for this section (active in the current academic term) are excluded.
    """
    from app.models.curriculum import Curriculum, YearLevel, Semester

    try:
        section = Section.query.get_or_404(section_id)

        # Dean access control
        user_program_ids = current_user.get_program_ids()
        if user_program_ids is not None and section.program_id not in user_program_ids:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        current_settings = AcademicSettings.query.filter_by(is_active=True).first()

        # Collect already-scheduled subject+type combos for this section
        scheduled_keys = set()
        if current_settings:
            existing = Schedule.query.filter_by(
                section_id=section_id,
                is_active=True,
                semester=current_settings.semester,
                academic_year=current_settings.academic_year
            ).all()
            for s in existing:
                scheduled_keys.add(f"{s.subject_id}_{s.schedule_type or 'lecture'}")

        curricula = Curriculum.query.filter_by(
            program_id=section.program_id,
            is_active=True,
            is_archived=False
        ).order_by(Curriculum.curriculum_code).all()

        subjects = []
        for curriculum in curricula:
            for year_level in sorted(curriculum.year_levels, key=lambda yl: yl.year_number):
                for semester in sorted(year_level.semesters, key=lambda s: s.semester_number):
                    group_label = f"{curriculum.curriculum_code} › {year_level.year_name} › {semester.semester_name}"
                    for subject in sorted(semester.subjects, key=lambda s: s.subject_code):
                        lec = float(subject.lec_units)
                        lab = float(subject.lab_units)
                        entries = []
                        if lec > 0:
                            entries.append(('lecture', lec))
                        if lab > 0:
                            entries.append(('lab', lab))
                        if not entries:
                            entries.append(('lecture', 0))

                        for stype, units in entries:
                            key = f"{subject.id}_{stype}"
                            if key in scheduled_keys:
                                continue
                            duration = int(units * 60) if units else 60
                            subjects.append({
                                'subject_id': subject.id,
                                'subject_code': subject.subject_code,
                                'course_description': subject.course_description,
                                'schedule_type': stype,
                                'lec_units': lec,
                                'lab_units': lab,
                                'total_units': subject.total_units,
                                'duration_minutes': duration,
                                'curriculum_code': curriculum.curriculum_code,
                                'year_level_name': year_level.year_name,
                                'semester_name': semester.semester_name,
                                'group_label': group_label,
                            })

        return jsonify({'success': True, 'subjects': subjects})

    except Exception as e:
        import traceback
        print(f'[BATCH PROGRAM SUBJECTS] ERROR: {traceback.format_exc()}')
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/get-faculty/<int:subject_id>')
@login_required
def get_faculty_for_subject(subject_id):
    """Get all active faculty members with workload info for better UX
    
    Returns faculty with:
    - Current weekly hours/units taught
    - Availability status
    - Program info
    - Assignment status for this subject
    """
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Get ALL active faculty
        faculties = Faculty.query.filter(
            Faculty.is_active == True,
            Faculty.is_archived == False
        ).order_by(Faculty.last_name, Faculty.first_name).all()
        
        available_days_map = _build_faculty_available_days_map([faculty.id for faculty in faculties])

        # Get existing assignments to show which faculty are already assigned
        assigned_faculty_ids = set()
        if current_settings:
            assignments = FacultySubjectAssignment.query.filter_by(
                subject_id=subject_id,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester,
                is_active=True,
                is_archived=False
            ).all()
            assigned_faculty_ids = set([a.faculty_id for a in assignments])
        
        # Calculate workload for each faculty
        faculty_workloads = {}
        if current_settings:
            # Get all schedules for current period grouped by faculty
            schedules = Schedule.query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester,
                is_active=True
            ).all()
            
            for schedule in schedules:
                if schedule.faculty_id:
                    if schedule.faculty_id not in faculty_workloads:
                        faculty_workloads[schedule.faculty_id] = {
                            'weekly_hours': 0,
                            'weekly_units': 0,
                            'schedule_count': 0
                        }
                    
                    # Calculate hours for this schedule
                    if schedule.start_time and schedule.end_time:
                        from datetime import datetime, timedelta
                        start = datetime.combine(datetime.today(), schedule.start_time)
                        end = datetime.combine(datetime.today(), schedule.end_time)
                        hours = (end - start).seconds / 3600
                        faculty_workloads[schedule.faculty_id]['weekly_hours'] += hours
                    
                    # Add units from subject
                    if schedule.subject:
                        units = schedule.subject.lec_units + schedule.subject.lab_units
                        faculty_workloads[schedule.faculty_id]['weekly_units'] += units
                    
                    faculty_workloads[schedule.faculty_id]['schedule_count'] += 1
        
        # Format faculty for JSON response with enhanced data
        faculty_data = []
        for faculty in faculties:
            workload = faculty_workloads.get(faculty.id, {
                'weekly_hours': 0,
                'weekly_units': 0,
                'schedule_count': 0
            })
            
            # Get max units from faculty model (respects individual & system limits)
            max_units = faculty.get_max_units()
            current_units = workload['weekly_units']
            
            # Determine availability status based on actual max_units
            availability = 'available'
            if current_units >= max_units:
                availability = 'overloaded'
            elif current_units >= max_units * 0.8:
                availability = 'high_load'
            elif current_units >= max_units * 0.5:
                availability = 'moderate'
            
            # Calculate utilization percentage
            utilization_pct = round((current_units / max_units) * 100, 1) if max_units > 0 else 0
            
            faculty_data.append({
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_code': faculty.department.department_code if faculty.department else '',
                'department_name': faculty.department.department_name if faculty.department else '',
                'display': f"{faculty.full_name}" + (f" - {faculty.department.department_code}" if faculty.department else ""),
                'is_assigned': faculty.id in assigned_faculty_ids,
                'weekly_hours': round(workload['weekly_hours'], 1),
                'weekly_units': current_units,
                'max_units': max_units,
                'utilization_pct': utilization_pct,
                'schedule_count': workload['schedule_count'],
                'availability': availability,
                'initials': ((faculty.first_name[0] if faculty.first_name else '') + (faculty.last_name[0] if faculty.last_name else '')).upper(),
                'available_days': available_days_map.get(faculty.id, [])
            })
        
        # Sort: assigned first, then by availability, then by name
        availability_order = {'available': 0, 'moderate': 1, 'high_load': 2, 'overloaded': 3}
        faculty_data.sort(key=lambda f: (
            0 if f['is_assigned'] else 1,
            availability_order.get(f['availability'], 4),
            f['full_name']
        ))
        
        return jsonify({'faculty': faculty_data})
        
    except Exception as e:
        import traceback
        print(f"[GET FACULTY] Error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-all-faculty')
@login_required
def get_all_faculty():
    """Get all active faculty members for exam schedule modals"""
    try:
        # Get all active faculty
        faculties = Faculty.query.filter_by(
            is_active=True,
            is_archived=False
        ).order_by(Faculty.last_name, Faculty.first_name).all()
        
        available_days_map = _build_faculty_available_days_map([faculty.id for faculty in faculties])

        # Format faculty for JSON response
        faculty_data = [
            {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_code': faculty.department.department_code if faculty.department else '',
                'display': f"{faculty.full_name}" + (f" - {faculty.department.department_code}" if faculty.department else ""),
                'available_days': available_days_map.get(faculty.id, [])
            }
            for faculty in faculties
        ]
        
        return jsonify({'faculty': faculty_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-all-rooms')
@login_required
def get_all_rooms():
    """Get all available rooms for exam schedule modals"""
    try:
        # Get all available rooms
        rooms = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()
        
        # Format rooms for JSON response
        room_data = [
            {
                'id': room.id,
                'room_number': room.room_number,
                'room_type': room.room_type or 'Lecture',
                'building_name': room.building.building_name if room.building else '',
                'display': f"{room.room_number}" + (f" - {room.building.building_name}" if room.building else "")
            }
            for room in rooms
        ]
        
        return jsonify({'rooms': room_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-all-faculties')
@login_required
def get_all_faculties():
    """Get all active faculty members"""
    try:
        # Get all active faculty
        faculties = Faculty.query.filter(
            Faculty.is_active == True,
            Faculty.is_archived == False
        ).order_by(Faculty.last_name, Faculty.first_name).all()
        
        available_days_map = _build_faculty_available_days_map([faculty.id for faculty in faculties])

        # Format faculty for JSON response
        faculty_data = [
            {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_code': faculty.department.department_code if faculty.department else '',
                'display': f"{faculty.full_name}" + (f" - {faculty.department.department_code}" if faculty.department else ""),
                'available_days': available_days_map.get(faculty.id, [])
            }
            for faculty in faculties
        ]
        
        return jsonify({'faculties': faculty_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/ai-check-conflicts', methods=['POST'])
@login_required
@csrf.exempt  # Exempt CSRF for AJAX endpoints
def ai_check_conflicts():
    """
    AI-powered conflict detection and recommendations
    
    Uses new service layer architecture:
    - ConflictDetector: Fast pure Python conflict checking
    - RecommendationEngine: Workload-aware suggestions
    - AISchedulerAssistant: Gemini AI explanations
    """
    from app.ai_scheduler import ai_scheduler
    from datetime import datetime as dt
    
    try:
        data = request.get_json()
        
        # Debug logging
        print(f"[AI CHECK] Received data: {data}")
        
        if not data:
            return jsonify({'error': 'No data received', 'ai_enabled': False}), 400
        
        # Parse schedule data
        section_id = data.get('section_id')
        subject_id = data.get('subject_id')
        faculty_id = data.get('faculty_id')
        room_id = data.get('room_id')
        day_of_week = data.get('day_of_week')
        schedule_type = data.get('schedule_type', 'lecture')  # Default to lecture
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        schedule_id = data.get('schedule_id')  # For edit mode
        
        # Debug logging
        print(f"[AI CHECK] Parsed - section:{section_id} day:{day_of_week} type:{schedule_type} time:{start_time_str}-{end_time_str}")
        
        if not all([section_id, day_of_week, start_time_str, end_time_str]):
            missing = []
            if not section_id: missing.append('section_id')
            if not day_of_week: missing.append('day_of_week')
            if not start_time_str: missing.append('start_time')
            if not end_time_str: missing.append('end_time')
            error_msg = f'Missing required fields: {", ".join(missing)}'
            print(f"[AI CHECK] Validation failed: {error_msg}")
            return jsonify({'error': error_msg, 'ai_enabled': False}), 400
        
        # Convert times
        start_time = dt.strptime(start_time_str, '%H:%M').time()
        end_time = dt.strptime(end_time_str, '%H:%M').time()
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Check if schedule times are outside configured hours (non-blocking warning)
        schedule_hours_warning = None
        if current_settings:
            schedule_start_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_start_time', None), current_settings.schedule_start_hour or 7)
            schedule_end_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_end_time', None), current_settings.schedule_end_hour or 20)

            if _minutes_of(start_time) < _minutes_of(schedule_start_cfg):
                schedule_hours_warning = f'Start time is before configured schedule hours ({_fmt_setting_time(schedule_start_cfg)})'

            elif _minutes_of(end_time) > _minutes_of(schedule_end_cfg):
                schedule_hours_warning = f'End time is after configured schedule hours ({_fmt_setting_time(schedule_end_cfg)})'
        
        # Get existing schedules for the same academic period (load all, let service filter)
        existing_query = Schedule.query.filter_by(is_active=True)
        
        if current_settings:
            existing_query = existing_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        existing_schedules = existing_query.all()
        
        # Prepare schedule data for analysis
        schedule_data = {
            'section_id': section_id,
            'subject_id': subject_id,
            'faculty_id': faculty_id,
            'room_id': room_id,
            'day_of_week': day_of_week,
            'schedule_type': schedule_type,
            'start_time': start_time,
            'end_time': end_time
        }
        
        # Check if client wants full AI or offline-only conflict detection
        use_ai = data.get('use_ai', True)
        
        if use_ai:
            # Full AI analysis (conflict detection + recommendations + Gemini explanation)
            analysis = ai_scheduler.analyze_schedule_conflicts(
                schedule_data, 
                existing_schedules,
                exclude_schedule_id=int(schedule_id) if schedule_id else None
            )
        else:
            # Basic mode: rule-based conflict detection + recommendations (no Gemini AI)
            from app.services.conflict_detector import conflict_detector
            from app.services.recommendation_engine import recommendation_engine
            conflicts = conflict_detector.detect_class_conflicts(
                schedule_data,
                existing_schedules,
                int(schedule_id) if schedule_id else None
            )
            recommendations = []
            offline_explanation = ''
            if conflicts:
                subject = None
                if subject_id:
                    from app.models.curriculum import Subject
                    subject = Subject.query.get(subject_id)
                recommendations = recommendation_engine.generate_class_recommendations(
                    schedule_data,
                    conflicts,
                    existing_schedules,
                    subject,
                    exclude_schedule_id=int(schedule_id) if schedule_id else None
                )
                offline_explanation = ai_scheduler._get_offline_explanation(conflicts, recommendations)
            analysis = {
                'has_conflicts': len(conflicts) > 0,
                'conflicts': [c.to_dict() for c in conflicts],
                'recommendations': [r.to_dict() for r in recommendations],
                'ai_explanation': offline_explanation,
                'ai_enabled': False,
                'ai_fallback': False,
                'ai_fallback_reason': None
            }
        
        # Check faculty availability (warning, not a hard conflict)
        faculty_availability_warning = None
        if faculty_id:
            availability_result = FacultyAvailability.check_faculty_available_by_day(
                faculty_id, day_of_week, start_time, end_time
            )
            
            faculty = Faculty.query.get(faculty_id)
            faculty_name = faculty.full_name if faculty else 'Selected faculty'
            
            if availability_result['status'] == 'not_in_schedule':
                # Soft warning - faculty has defined availability but not for this slot
                faculty_availability_warning = {
                    'type': 'warning',
                    'message': f'{faculty_name} is not marked as available on {day_of_week} at this time.',
                    'faculty_name': faculty_name,
                    'status': 'not_in_schedule'
                }
            elif availability_result['status'] == 'available':
                # Positive confirmation - faculty is available for this slot
                faculty_availability_warning = {
                    'type': 'success',
                    'message': f'{faculty_name} is available on {day_of_week} at this time.',
                    'faculty_name': faculty_name,
                    'status': 'available'
                }
        
        # Build workload summary for AI-Powered mode
        workload_summary = None
        if use_ai and faculty_id:
            try:
                from app.services.recommendation_engine import recommendation_engine
                from datetime import datetime as dt_util
                faculty_obj = Faculty.query.get(faculty_id)
                if faculty_obj:
                    # Calculate weekly hours from existing schedules
                    weekly_hours = 0
                    day_hours = {}
                    for s in existing_schedules:
                        if s.faculty_id == faculty_id:
                            s_start = dt_util.combine(dt_util.today(), s.start_time)
                            s_end = dt_util.combine(dt_util.today(), s.end_time)
                            hrs = (s_end - s_start).total_seconds() / 3600
                            weekly_hours += hrs
                            d = s.day_of_week
                            day_hours[d] = day_hours.get(d, 0) + hrs
                    max_weekly = recommendation_engine.MAX_FACULTY_WEEKLY_UNITS
                    status = 'balanced'
                    if weekly_hours >= max_weekly:
                        status = 'at_limit'
                    elif weekly_hours > max_weekly * 0.8:
                        status = 'heavy'
                    workload_summary = {
                        'faculty_name': faculty_obj.full_name,
                        'weekly_hours': round(weekly_hours, 1),
                        'max_weekly': max_weekly,
                        'day_distribution': {d: round(h, 1) for d, h in day_hours.items()},
                        'status': status
                    }
            except Exception:
                pass  # Non-critical, skip on error
        
        # Response already formatted by service layer
        response = {
            'ai_enabled': analysis.get('ai_enabled', False),
            'ai_fallback': analysis.get('ai_fallback', False),
            'ai_fallback_reason': analysis.get('ai_fallback_reason'),
            'ai_fallback_message': analysis.get('ai_fallback_reason') if analysis.get('ai_fallback', False) else '',
            'has_conflicts': analysis.get('has_conflicts', False),
            'conflicts': analysis.get('conflicts', []),
            'recommendations': analysis.get('recommendations', []),
            'ai_explanation': analysis.get('ai_explanation', ''),
            'faculty_availability_warning': faculty_availability_warning,
            'schedule_hours_warning': schedule_hours_warning,
            'workload_summary': workload_summary
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"AI check conflicts error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'ai_enabled': False}), 500


@schedule_bp.route('/resolve-conflicts', methods=['POST'])
@login_required
@csrf.exempt
def resolve_conflicts():
    """
    Generate a resolution plan for detected schedule conflicts.
    
    Uses ConflictResolver to find optimal form field changes that
    eliminate all conflicts. Returns a plan for user confirmation.
    """
    from app.services.conflict_resolver import conflict_resolver
    from datetime import datetime as dt

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400

        # Parse the current schedule form data
        section_id = data.get('section_id')
        subject_id = data.get('subject_id')
        faculty_id = data.get('faculty_id')
        room_id = data.get('room_id')
        day_of_week = data.get('day_of_week')
        schedule_type = data.get('schedule_type', 'lecture')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        schedule_id = data.get('schedule_id')  # For edit mode
        conflicts = data.get('conflicts', [])

        if not all([section_id, day_of_week, start_time_str, end_time_str]):
            return jsonify({'error': 'Missing required schedule fields'}), 400

        if not conflicts:
            return jsonify({'error': 'No conflicts to resolve'}), 400

        start_time = dt.strptime(start_time_str, '%H:%M').time()
        end_time = dt.strptime(end_time_str, '%H:%M').time()

        # Get existing schedules for the current academic period
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        existing_query = Schedule.query.filter_by(is_active=True)
        if current_settings:
            existing_query = existing_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        existing_schedules = existing_query.all()

        # Get subject object if available
        subject_obj = None
        if subject_id:
            subject_obj = Subject.query.get(subject_id)

        schedule_data = {
            'section_id': section_id,
            'subject_id': subject_id,
            'faculty_id': faculty_id,
            'room_id': room_id,
            'day_of_week': day_of_week,
            'schedule_type': schedule_type,
            'start_time': start_time,
            'end_time': end_time
        }

        exclude_id = int(schedule_id) if schedule_id else None

        plan = conflict_resolver.generate_resolution_plan(
            schedule_data=schedule_data,
            conflicts=conflicts,
            existing_schedules=existing_schedules,
            subject=subject_obj,
            exclude_schedule_id=exclude_id
        )

        return jsonify(plan)

    except Exception as e:
        print(f"Resolve conflicts error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/apply-resolution', methods=['POST'])
@login_required
@csrf.exempt
def apply_resolution():
    """
    Apply a confirmed resolution plan to an existing schedule (edit mode).
    Modifies database fields in a single transaction.
    """
    from app.services.conflict_resolver import ResolutionApplier

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400

        plan = data.get('plan', {})
        schedule_id = data.get('schedule_id')

        if not schedule_id:
            return jsonify({'error': 'schedule_id is required'}), 400

        result = ResolutionApplier.apply_plan(
            resolution_plan=plan,
            schedule_id=int(schedule_id),
            user_id=current_user.id
        )

        return jsonify(result)

    except Exception as e:
        print(f"Apply resolution error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/preview-conflicts', methods=['POST'])
@login_required
@csrf.exempt
def preview_conflicts():
    """
    Lightweight conflict preview for hover tooltips
    No AI API calls - pure Python detection for instant response
    """
    from app.services.conflict_detector import conflict_detector
    from datetime import datetime as dt
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        section_id = data.get('section_id')
        faculty_id = data.get('faculty_id')
        room_id = data.get('room_id')
        day_of_week = data.get('day_of_week')
        time_slots = data.get('time_slots', [])  # List of {start: 'HH:MM', end: 'HH:MM'}
        
        if not section_id or not day_of_week:
            return jsonify({'error': 'Section and day are required'}), 400
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Get existing schedules
        existing_query = Schedule.query.filter_by(is_active=True)
        if current_settings:
            existing_query = existing_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        existing_schedules = existing_query.all()
        
        # Parse time slots
        parsed_slots = []
        for slot in time_slots:
            try:
                start = dt.strptime(slot['start'], '%H:%M').time()
                end = dt.strptime(slot['end'], '%H:%M').time()
                parsed_slots.append((start, end))
            except (ValueError, KeyError):
                continue
        
        # Get quick conflict preview
        preview = conflict_detector.preview_slot_conflicts(
            section_id=section_id,
            faculty_id=faculty_id,
            room_id=room_id,
            day_of_week=day_of_week,
            time_slots=parsed_slots,
            existing_schedules=existing_schedules
        )
        
        return jsonify({'preview': preview})
        
    except Exception as e:
        print(f"Preview conflicts error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/ai-suggest-schedule', methods=['POST'])
@login_required
@csrf.exempt  # Exempt CSRF for AJAX endpoints
def ai_suggest_schedule():
    """Get AI suggestions for optimal scheduling"""
    from flask import jsonify
    from app.ai_scheduler import ai_scheduler
    
    try:
        data = request.get_json()
        
        section_id = data.get('section_id')
        subject_id = data.get('subject_id')
        faculty_id = data.get('faculty_id')
        
        if not section_id or not subject_id:
            return jsonify({'error': 'Section and subject are required'}), 400
        
        # Get models
        section = Section.query.get_or_404(section_id)
        subject = Subject.query.get_or_404(subject_id)
        faculty = Faculty.query.get(faculty_id) if faculty_id else None
        
        # Get AI suggestions
        result = ai_scheduler.suggest_optimal_schedule(section, subject, faculty)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"AI suggest schedule error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'ai_enabled': False}), 500


@schedule_bp.route('/export/class/<int:section_id>')
@login_required
def export_class_schedule(section_id):
    """Export class schedule to Excel - weekly grid format matching template"""
    try:
        section = Section.query.get_or_404(section_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules
        query = Schedule.query.filter_by(section_id=section_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        output, filename = generate_class_schedule_excel(section, schedules, current_settings, current_user)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.class_view', section_id=section_id))


@schedule_bp.route('/export/faculty/<int:faculty_id>')
@login_required
def export_faculty_schedule(faculty_id):
    """Export faculty schedule to Excel - weekly grid format matching template"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules
        query = Schedule.query.filter_by(faculty_id=faculty_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        output, filename = generate_faculty_schedule_excel(faculty, schedules, current_settings, current_user)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.faculty_view', faculty_id=faculty_id))


@schedule_bp.route('/export/room/<int:room_id>')
@login_required
def export_room_schedule(room_id):
    """Export room schedule to Excel - weekly grid format matching template"""
    try:
        room = Room.query.get_or_404(room_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules
        query = Schedule.query.filter_by(room_id=room_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        output, filename = generate_room_schedule_excel(room, schedules, current_settings, current_user)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.room_view', room_id=room_id))




# ============================================================================
# Export for Posting Routes (Simplified, print-friendly versions)
# ============================================================================

@schedule_bp.route('/export/class/<int:section_id>/posting')
@login_required
def export_class_schedule_for_posting(section_id):
    """Export class schedule for posting - table format with subject details"""
    try:
        section = Section.query.get_or_404(section_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules
        query = Schedule.query.filter_by(section_id=section_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        output, filename = generate_class_schedule_excel_for_posting(section, schedules, current_settings, current_user)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.class_view', section_id=section_id))


# ============================================================================
# PDF EXPORT ROUTES
# ============================================================================

@schedule_bp.route('/export/class/<int:section_id>/pdf')
@login_required
def export_class_schedule_pdf(section_id):
    """Export class schedule to PDF - weekly grid format matching Excel template"""
    try:
        section = Section.query.get_or_404(section_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules
        query = Schedule.query.filter_by(section_id=section_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        output, filename = generate_class_schedule_pdf(section, schedules, current_settings, current_user)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting PDF schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.class_view', section_id=section_id))


@schedule_bp.route('/export/faculty/<int:faculty_id>/pdf')
@login_required
def export_faculty_schedule_pdf(faculty_id):
    """Export faculty schedule to PDF - weekly grid format"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules
        query = Schedule.query.filter_by(faculty_id=faculty_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        output, filename = generate_faculty_schedule_pdf(faculty, schedules, current_settings, current_user)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting faculty PDF schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.faculty_view', faculty_id=faculty_id))


@schedule_bp.route('/export/room/<int:room_id>/pdf')
@login_required
def export_room_schedule_pdf(room_id):
    """Export room schedule to PDF - weekly grid format"""
    try:
        room = Room.query.get_or_404(room_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules
        query = Schedule.query.filter_by(room_id=room_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(_DAY_ORDER, Schedule.start_time).all()
        
        output, filename = generate_room_schedule_pdf(room, schedules, current_settings, current_user)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting room PDF schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.room_view', room_id=room_id))




# ============================================================================


@schedule_bp.route('/suggest-rooms', methods=['POST'])
@login_required
def suggest_rooms():
    """Suggest rooms based on subject and time"""
    from app.ai_scheduler import ai_scheduler
    
    data = request.get_json()
    subject_id = data.get('subject_id')
    day = data.get('day')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    schedule_id = data.get('schedule_id')
    
    if not all([subject_id, day, start_time_str, end_time_str]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()

        suggestions = ai_scheduler.suggest_rooms(
            subject_id,
            day,
            start_time,
            end_time,
            exclude_schedule_id=int(schedule_id) if schedule_id else None
        )
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/cleanup-archived', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def cleanup_archived():
    """Delete class schedules that have archived sections, programs, faculty, or rooms"""
    try:
        # Get all active schedules
        all_schedules = Schedule.query.filter_by(is_active=True).all()
        
        deleted_count = 0
        deleted_details = []
        
        for schedule in all_schedules:
            if schedule.has_archived_relationships():
                # Build detail string for logging
                reason_parts = []
                if schedule.section and schedule.section.program and schedule.section.program.is_archived:
                    reason_parts.append(f"archived program: {schedule.section.program.program_name}")
                if schedule.faculty and schedule.faculty.is_archived:
                    reason_parts.append(f"archived faculty: {schedule.faculty.full_name}")
                if schedule.room and not schedule.room.is_available:
                    reason_parts.append(f"unavailable room: {schedule.room.room_number}")
                if schedule.room and schedule.room.building and schedule.room.building.is_archived:
                    reason_parts.append(f"archived building: {schedule.room.building.building_name}")
                
                detail = f"{schedule.subject.subject_code if schedule.subject else 'N/A'} - {', '.join(reason_parts)}"
                deleted_details.append(detail)
                
                # Log deletion
                from app.utils.activity_logger import log_delete
                log_delete('schedule', schedule.id, f'{schedule.subject.subject_code} - {schedule.section.full_section_name}', {
                    'reason': 'Cleanup: ' + ', '.join(reason_parts),
                    'day_of_week': schedule.day_of_week
                })
                
                db.session.delete(schedule)
                deleted_count += 1
        
        db.session.commit()
        
        if deleted_count > 0:
            flash(f'Successfully deleted {deleted_count} class schedule(s) with archived relationships.', 'success')
            # Optionally log details
            print(f"[CLEANUP] Deleted class schedules:\n" + "\n".join(deleted_details))
        else:
            flash('No class schedules with archived relationships found.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cleaning up archived class schedules: {str(e)}', 'danger')
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('schedule.class_view'))


# ============================================================================
# BATCH SCHEDULE BUILDER ROUTES
# ============================================================================


@schedule_bp.route('/batch-check-conflicts', methods=['POST'])
@login_required
@csrf.exempt
def batch_check_conflicts():
    """
    Check conflicts for ALL batch rows in a single request.
    Returns per-row conflict results including intra-batch detection.
    """
    from app.services.conflict_detector import conflict_detector
    from datetime import datetime as dt

    try:
        data = request.get_json()
        section_id = data.get('section_id')
        rows = data.get('rows', [])

        if not section_id or not rows:
            return jsonify({'success': False, 'error': 'section_id and rows required'}), 400

        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        schedule_start_cfg = time(7, 0)
        schedule_end_cfg = time(20, 0)
        if current_settings:
            schedule_start_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_start_time', None), current_settings.schedule_start_hour or 7)
            schedule_end_cfg = _coerce_setting_time(getattr(current_settings, 'schedule_end_time', None), current_settings.schedule_end_hour or 20)

        # Load existing schedules for conflict detection
        existing_query = Schedule.query.filter_by(is_active=True)
        if current_settings:
            existing_query = existing_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        existing_schedules = existing_query.all()

        # Pre-load faculty availability for all faculty in batch (performance optimisation)
        batch_faculty_ids = set()
        for r in rows:
            if r.get('faculty_id'):
                try:
                    batch_faculty_ids.add(int(r['faculty_id']))
                except (ValueError, TypeError):
                    pass
        faculty_avail_map = {}  # faculty_id -> list of availability records
        faculty_name_map = {}   # faculty_id -> full_name
        if batch_faculty_ids:
            avail_records = FacultyAvailability.query.filter(
                FacultyAvailability.faculty_id.in_(batch_faculty_ids),
                FacultyAvailability.is_active == True,
                FacultyAvailability.day_of_week.isnot(None)
            ).all()
            for rec in avail_records:
                faculty_avail_map.setdefault(rec.faculty_id, []).append(rec)
            # Pre-load names
            faculty_objs = Faculty.query.filter(Faculty.id.in_(batch_faculty_ids)).all()
            for f in faculty_objs:
                faculty_name_map[f.id] = f.full_name
            # Track which faculty have ANY active records (for not_in_schedule detection)
            faculty_has_availability = set()
            all_avail_recs = FacultyAvailability.query.filter(
                FacultyAvailability.faculty_id.in_(batch_faculty_ids),
                FacultyAvailability.is_active == True
            ).with_entities(FacultyAvailability.faculty_id).distinct().all()
            for row_tuple in all_avail_recs:
                faculty_has_availability.add(row_tuple[0])

        # Build Mock objects for intra-batch detection (same pattern as confirm_schedule)
        class _Mock:
            pass

        parsed_rows = []
        for i, row in enumerate(rows):
            start_str = row.get('start_time', '')
            end_str = row.get('end_time', '')
            if not start_str or not end_str:
                parsed_rows.append(None)
                continue
            try:
                st = dt.strptime(start_str, '%H:%M').time()
                et = dt.strptime(end_str, '%H:%M').time()
            except ValueError:
                parsed_rows.append(None)
                continue

            parsed_rows.append({
                'index': i,
                'section_id': section_id,
                'subject_id': row.get('subject_id'),
                'faculty_id': int(row['faculty_id']) if row.get('faculty_id') else None,
                'room_id': int(row['room_id']) if row.get('room_id') else None,
                'day_of_week': row.get('day_of_week', ''),
                'start_time': st,
                'end_time': et,
                'schedule_type': row.get('schedule_type', 'lecture'),
                'subject_code': row.get('subject_code', f'Row {i+1}'),
                'schedule_id': int(row['schedule_id']) if row.get('schedule_id') else None,
            })

        results = []
        ok_count = 0
        conflict_count = 0
        warning_count = 0

        for i, parsed in enumerate(parsed_rows):
            if parsed is None:
                results.append({
                    'index': i,
                    'status': 'warning',
                    'conflicts': [{'type': 'time_invalid', 'severity': 'critical',
                                   'message': 'Missing or invalid time values'}]
                })
                warning_count += 1
                continue

            row_conflicts = []

            # 1) Check against existing DB schedules using ConflictDetector
            schedule_data = {
                'section_id': section_id,
                'faculty_id': parsed['faculty_id'],
                'room_id': parsed['room_id'],
                'day_of_week': parsed['day_of_week'],
                'start_time': parsed['start_time'],
                'end_time': parsed['end_time'],
            }
            db_conflicts = conflict_detector.detect_class_conflicts(
                schedule_data, existing_schedules,
                exclude_schedule_id=parsed.get('schedule_id')
            )
            for c in db_conflicts:
                row_conflicts.append(c.to_dict())

            # 2) Intra-batch: check this row against all OTHER rows
            for j, other in enumerate(parsed_rows):
                if j == i or other is None:
                    continue
                if parsed['day_of_week'] != other['day_of_week']:
                    continue
                # Check time overlap
                if parsed['start_time'] >= other['end_time'] or parsed['end_time'] <= other['start_time']:
                    continue
                # Overlapping — check section, faculty, room
                time_disp = f"{other['start_time'].strftime('%I:%M %p')}-{other['end_time'].strftime('%I:%M %p')}"

                # Section conflict (same section = always conflict)
                row_conflicts.append({
                    'type': 'section_batch',
                    'severity': 'critical',
                    'message': f"Overlaps with Row {j+1} ({other['subject_code']}) on {other['day_of_week']} {time_disp}",
                    'details': {'other_row': j+1, 'subject_code': other['subject_code']}
                })

                # Faculty conflict
                if parsed['faculty_id'] and other['faculty_id'] and parsed['faculty_id'] == other['faculty_id']:
                    row_conflicts.append({
                        'type': 'faculty_batch',
                        'severity': 'high',
                        'message': f"Same faculty assigned in Row {j+1} ({other['subject_code']}) at {time_disp}",
                        'details': {'other_row': j+1, 'faculty_id': parsed['faculty_id']}
                    })

                # Room conflict
                if parsed['room_id'] and other['room_id'] and parsed['room_id'] == other['room_id']:
                    row_conflicts.append({
                        'type': 'room_batch',
                        'severity': 'high',
                        'message': f"Same room used in Row {j+1} ({other['subject_code']}) at {time_disp}",
                        'details': {'other_row': j+1, 'room_id': parsed['room_id']}
                    })

            # 3) Schedule hours check
            if _minutes_of(parsed['start_time']) < _minutes_of(schedule_start_cfg):
                row_conflicts.append({
                    'type': 'schedule_hours',
                    'severity': 'medium',
                    'message': f"Start time is before schedule hours ({schedule_start_cfg.strftime('%I:%M %p').lstrip('0')})",
                    'details': {}
                })
            if _minutes_of(parsed['end_time']) > _minutes_of(schedule_end_cfg):
                row_conflicts.append({
                    'type': 'schedule_hours',
                    'severity': 'medium',
                    'message': f"End time is after schedule hours ({schedule_end_cfg.strftime('%I:%M %p').lstrip('0')})",
                    'details': {}
                })

            # 4) Faculty availability check (uses pre-loaded data for performance)
            if parsed['faculty_id'] and parsed['day_of_week']:
                fid = parsed['faculty_id']
                day = parsed['day_of_week']
                fname = faculty_name_map.get(fid, 'Faculty')
                avail_recs = faculty_avail_map.get(fid, [])
                
                # Filter records for this day
                day_records = [r for r in avail_recs if r.day_of_week == day]
                
                is_explicitly_available = False
                
                for rec in day_records:
                    # Check time overlap — any active record covering this time = available
                    if rec.start_time < parsed['end_time'] and parsed['start_time'] < rec.end_time:
                        is_explicitly_available = True
                        break
                
                if not is_explicitly_available and fid in faculty_has_availability:
                    # Faculty has defined availability but not for this day/time
                    row_conflicts.append({
                        'type': 'faculty_availability',
                        'severity': 'medium',
                        'message': f"{fname} is not marked as available on {day} at this time",
                        'details': {'faculty_id': fid, 'status': 'not_in_schedule'}
                    })

            # Determine row status
            has_critical = any(c['severity'] in ('critical', 'high') for c in row_conflicts)
            has_warning = any(c['severity'] in ('medium', 'low') for c in row_conflicts)

            if has_critical:
                status = 'conflict'
                conflict_count += 1
            elif has_warning:
                status = 'warning'
                warning_count += 1
            else:
                status = 'ok'
                ok_count += 1

            results.append({
                'index': i,
                'status': status,
                'conflicts': row_conflicts
            })

        return jsonify({
            'success': True,
            'rows': results,
            'summary': {
                'total': len(rows),
                'ok': ok_count,
                'conflicts': conflict_count,
                'warnings': warning_count
            }
        })

    except Exception as e:
        print(f"Batch check conflicts error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/auto-generate', methods=['POST'])
@schedule_bp.route('/batch-generate', methods=['POST'])
@login_required
@csrf.exempt
def batch_generate_schedule():
    """Generate a batch schedule preview — auto-assigns day/time/room, faculty left blank."""
    from app.services.auto_scheduler import AutoScheduler

    try:
        data = request.get_json()
        section_id = data.get('section_id')

        if not section_id:
            return jsonify({'success': False, 'error': 'Section ID is required'}), 400

        # Verify access
        section = Section.query.get_or_404(section_id)
        user_program_ids = current_user.get_program_ids()
        if user_program_ids is not None and section.program_id not in user_program_ids:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        scheduler = AutoScheduler()
        curriculum_id = data.get('curriculum_id')
        try:
            preferred_building_id = int(data.get('preferred_building_id')) if data.get('preferred_building_id') else None
        except (ValueError, TypeError):
            preferred_building_id = None

        mode = (data.get('mode') or 'auto').lower()

        if mode == 'smart':
            from app.services.smart_scheduler import SmartScheduler
            active_settings = AcademicSettings.query.filter_by(is_active=True).first()
            smart = SmartScheduler(scheduler, settings=active_settings)
            result = smart.generate_smart_preview(
                section_id, curriculum_id=curriculum_id,
                preferred_building_id=preferred_building_id
            )
        elif mode == 'quick':
            result = scheduler.generate_batch_preview(
                section_id, curriculum_id=curriculum_id,
                preferred_building_id=preferred_building_id
            )
            if isinstance(result, dict):
                result['mode'] = 'quick'
        else:
            # Auto mode: run quick first; fall back to smart only when needed.
            quick_result = scheduler.generate_batch_preview(
                section_id, curriculum_id=curriculum_id,
                preferred_building_id=preferred_building_id
            )

            if not quick_result.get('success'):
                result = quick_result
            else:
                quick_unplaceable = len(quick_result.get('unplaceable') or [])

                if quick_unplaceable == 0:
                    quick_result['mode'] = 'quick'
                    result = quick_result
                else:
                    from app.services.smart_scheduler import SmartScheduler
                    active_settings = AcademicSettings.query.filter_by(is_active=True).first()
                    smart = SmartScheduler(scheduler, settings=active_settings)
                    smart_result = smart.generate_smart_preview(
                        section_id, curriculum_id=curriculum_id,
                        preferred_building_id=preferred_building_id
                    )

                    if not smart_result.get('success'):
                        quick_result['mode'] = 'quick'
                        result = quick_result
                    else:
                        smart_unplaceable = len(smart_result.get('unplaceable') or [])
                        quick_scheduled = len(quick_result.get('proposed') or [])
                        smart_scheduled = len(smart_result.get('proposed') or [])

                        use_smart = (
                            smart_unplaceable < quick_unplaceable or
                            (smart_unplaceable == quick_unplaceable and smart_scheduled > quick_scheduled)
                        )

                        if use_smart:
                            result = smart_result
                        else:
                            quick_result['mode'] = 'quick'
                            result = quick_result

        return jsonify(result)

    except Exception as e:
        print(f"Batch generate schedule error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/auto-generate/confirm', methods=['POST'])
@schedule_bp.route('/batch-confirm', methods=['POST'])
@login_required
@csrf.exempt
def batch_confirm_schedule():
    """Validate and save batch schedule rows with full conflict checking."""
    from app.services.auto_scheduler import AutoScheduler
    from app.routes.socket_events import broadcast_schedule_change

    try:
        data = request.get_json()
        section_id = data.get('section_id')
        proposed_items = data.get('proposed', [])

        if not section_id or not proposed_items:
            return jsonify({'success': False, 'error': 'Section ID and proposed items required'}), 400

        # Verify access
        section = Section.query.get_or_404(section_id)
        user_program_ids = current_user.get_program_ids()
        if user_program_ids is not None and section.program_id not in user_program_ids:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        scheduler = AutoScheduler()
        result = scheduler.confirm_schedule(section_id, proposed_items, user_id=current_user.id)

        if result.get('success'):
            # Broadcast real-time update
            try:
                broadcast_schedule_change({
                    'action': 'batch_created',
                    'section_id': section_id,
                    'count': result.get('created', 0),
                    'user': current_user.full_name if hasattr(current_user, 'full_name') else current_user.username
                })
            except Exception:
                pass

        return jsonify(result)

    except Exception as e:
        print(f"Batch confirm error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/get-buildings')
@login_required
def get_buildings():
    """Get all active, non-archived buildings for batch builder building preference."""
    from app.models.building import Building
    try:
        buildings = Building.query.filter_by(
            is_active=True,
            is_archived=False
        ).order_by(Building.building_name).all()

        return jsonify({
            'buildings': [
                {'id': b.id, 'building_name': b.building_name}
                for b in buildings
            ]
        })
    except Exception as e:
        return jsonify({'buildings': [], 'error': str(e)}), 500


@schedule_bp.route('/batch-available-rooms')
@login_required
def batch_available_rooms():
    """Get rooms available (no conflicts) at a specific day/time/type.
    
    Optional params:
        subject_id: enables PE-aware room filtering (Lecture + Court/Gym for PE subjects)
        building_id: soft preference — rooms from this building are listed first
    """
    from app.services.auto_scheduler import AutoScheduler

    try:
        day = request.args.get('day')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        schedule_type = request.args.get('schedule_type', 'lecture')
        subject_id = request.args.get('subject_id', type=int)
        building_id = request.args.get('building_id', type=int)
        schedule_id = request.args.get('schedule_id', type=int)

        if not all([day, start_time, end_time]):
            return jsonify({'rooms': [], 'error': 'day, start_time, end_time required'}), 400

        scheduler = AutoScheduler()
        rooms = scheduler.get_available_rooms(
            day, start_time, end_time, schedule_type,
            subject_id=subject_id,
            preferred_building_id=building_id,
            exclude_schedule_id=schedule_id
        )

        return jsonify({'rooms': rooms})

    except Exception as e:
        print(f"Batch available rooms error: {str(e)}")
        return jsonify({'rooms': [], 'error': str(e)}), 500


# ============================================================================
# SNAPSHOT & CLEAR ROUTES
# ============================================================================

def _get_accessible_section_ids_for_current_user():
    """Return section IDs current user can manage; None means unrestricted (admin)."""
    user_program_ids = current_user.get_program_ids()
    if user_program_ids is None:
        return None
    if not user_program_ids:
        return []
    sections = Section.query.filter(Section.program_id.in_(user_program_ids)).with_entities(Section.id).all()
    return [s.id for s in sections]


def _validate_snapshot_access_for_current_user(snapshot, accessible_section_ids):
    """Return (allowed, message, status) for snapshot restore/delete access."""
    if accessible_section_ids is None:
        return True, None, None

    # Semester-wide snapshots are admin-only.
    if snapshot.section_id is None:
        return False, 'Only admins can manage semester-wide snapshots', 403

    if snapshot.section_id not in accessible_section_ids:
        return False, 'You do not have access to this snapshot', 403

    return True, None, None

@schedule_bp.route('/snapshot/create', methods=['POST'])
@login_required
@csrf.exempt
def create_snapshot():
    """Create a snapshot of current schedules for the active semester."""
    try:
        data = request.get_json()
        snapshot_name = data.get('snapshot_name', '').strip()
        snapshot_scope = data.get('snapshot_scope', 'class')  # 'class' or 'exam'
        section_id = data.get('section_id')  # None = all sections

        if not snapshot_name:
            return jsonify({'success': False, 'error': 'Snapshot name is required'}), 400
        if len(snapshot_name) > 100:
            return jsonify({'success': False, 'error': 'Snapshot name must be 100 characters or less'}), 400
        if snapshot_scope not in ('class', 'exam'):
            return jsonify({'success': False, 'error': 'Invalid snapshot scope'}), 400

        accessible_section_ids = _get_accessible_section_ids_for_current_user()

        if accessible_section_ids is not None:
            if not section_id:
                return jsonify({'success': False, 'error': 'Only admins can create semester-wide snapshots'}), 403
            if int(section_id) not in accessible_section_ids:
                return jsonify({'success': False, 'error': 'You do not have access to this section'}), 403

        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return jsonify({'success': False, 'error': 'No active academic settings found'}), 400

        # Build query based on scope
        if snapshot_scope == 'class':
            query = Schedule.query.filter_by(
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        else:
            query = ExamSchedule.query.filter_by(
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )

        # Filter by section if specified
        if section_id:
            section = Section.query.get(section_id)
            if not section:
                return jsonify({'success': False, 'error': 'Section not found'}), 404
            query = query.filter_by(section_id=section_id)

        # Program-scoped access control for non-admin users.
        if accessible_section_ids is not None:
            if snapshot_scope == 'class':
                query = query.filter(Schedule.section_id.in_(accessible_section_ids))
            else:
                query = query.filter(ExamSchedule.section_id.in_(accessible_section_ids))

        schedules = query.all()
        schedule_dicts = [s.to_dict() for s in schedules]

        snapshot = ScheduleSnapshot(
            snapshot_name=snapshot_name,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            snapshot_scope=snapshot_scope,
            section_id=int(section_id) if section_id else None,
            schedule_data=json.dumps(schedule_dicts),
            schedule_count=len(schedule_dicts),
            snapshot_type='manual',
            created_by=current_user.id,
        )
        db.session.add(snapshot)

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='created',
            entity_type='schedule_snapshot',
            entity_id=None,
            entity_name=snapshot_name,
            details=f'Created {snapshot_scope} snapshot with {len(schedule_dicts)} schedule(s)',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Snapshot "{snapshot_name}" created with {len(schedule_dicts)} schedule(s)',
            'snapshot': snapshot.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        print(f"Create snapshot error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/snapshots', methods=['GET'])
@login_required
def list_snapshots():
    """List snapshots for current academic year/semester."""
    try:
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return jsonify({'success': True, 'snapshots': []})

        snapshot_scope = request.args.get('scope', 'class')
        section_id = request.args.get('section_id', type=int)

        query = ScheduleSnapshot.query.filter_by(
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            snapshot_scope=snapshot_scope
        )

        accessible_section_ids = _get_accessible_section_ids_for_current_user()

        if accessible_section_ids is not None:
            if section_id and section_id not in accessible_section_ids:
                return jsonify({'success': False, 'error': 'You do not have access to this section'}), 403

            if not accessible_section_ids:
                return jsonify({'success': True, 'snapshots': []})

            # Non-admin users can only see section-specific snapshots in their scope.
            query = query.filter(ScheduleSnapshot.section_id.in_(accessible_section_ids))

        if section_id:
            if accessible_section_ids is None:
                # Admin view: show section-specific + semester-wide snapshots.
                query = query.filter(
                    or_(ScheduleSnapshot.section_id == section_id, ScheduleSnapshot.section_id.is_(None))
                )
            else:
                query = query.filter(ScheduleSnapshot.section_id == section_id)

        snapshots = query.order_by(ScheduleSnapshot.created_at.desc()).all()
        return jsonify({
            'success': True,
            'snapshots': [s.to_dict() for s in snapshots]
        })

    except Exception as e:
        print(f"List snapshots error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/snapshot/<int:snapshot_id>/restore', methods=['POST'])
@login_required
@csrf.exempt
def restore_snapshot(snapshot_id):
    """Restore schedules from a snapshot. Auto-creates a backup snapshot first."""
    try:
        snapshot = ScheduleSnapshot.query.get(snapshot_id)
        if not snapshot:
            return jsonify({'success': False, 'error': 'Snapshot not found'}), 404

        accessible_section_ids = _get_accessible_section_ids_for_current_user()
        allowed, message, status = _validate_snapshot_access_for_current_user(snapshot, accessible_section_ids)
        if not allowed:
            return jsonify({'success': False, 'error': message}), status

        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return jsonify({'success': False, 'error': 'No active academic settings found'}), 400

        snapshot_data = snapshot.get_schedule_data()
        scope = snapshot.snapshot_scope

        # Determine which schedules to replace
        if scope == 'class':
            Model = Schedule
        else:
            Model = ExamSchedule

        existing_query = Model.query.filter_by(
            is_active=True,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester
        )

        if snapshot.section_id:
            existing_query = existing_query.filter_by(section_id=snapshot.section_id)

        # Program-scoped access control for non-admin users.
        if accessible_section_ids is not None:
            existing_query = existing_query.filter(Model.section_id.in_(accessible_section_ids))

        existing_schedules = existing_query.all()

        # Auto-create backup snapshot before restore
        backup_dicts = [s.to_dict() for s in existing_schedules]
        if backup_dicts:
            backup_snapshot = ScheduleSnapshot(
                snapshot_name=f'Auto backup before restore "{snapshot.snapshot_name}"',
                academic_year=current_settings.academic_year,
                semester=current_settings.semester,
                snapshot_scope=scope,
                section_id=snapshot.section_id,
                schedule_data=json.dumps(backup_dicts),
                schedule_count=len(backup_dicts),
                snapshot_type='auto_pre_restore',
                created_by=current_user.id,
            )
            db.session.add(backup_snapshot)

        # Soft-delete existing schedules
        for s in existing_schedules:
            s.is_active = False
            s.updated_at = datetime.utcnow()
            if hasattr(s, 'version'):
                s.version = (s.version or 1) + 1

        # Re-create schedules from snapshot data
        # Reuse soft-deleted rows in the same slot to avoid uk_section_slot / uk_exam_section_slot violations
        restored_count = 0
        for item in snapshot_data:
            if accessible_section_ids is not None and item.get('section_id') not in accessible_section_ids:
                continue

            start_time = datetime.strptime(item['start_time'], '%H:%M').time() if item.get('start_time') else None
            end_time = datetime.strptime(item['end_time'], '%H:%M').time() if item.get('end_time') else None

            if scope == 'class':
                # Check for soft-deleted schedule in the same slot (uk_section_slot)
                existing_inactive = Schedule.query.filter_by(
                    section_id=item.get('section_id'),
                    day_of_week=item.get('day_of_week'),
                    start_time=start_time,
                    end_time=end_time,
                    academic_year=item.get('academic_year'),
                    semester=item.get('semester'),
                    is_active=False
                ).first()

                if existing_inactive:
                    existing_inactive.subject_id = item.get('subject_id')
                    existing_inactive.faculty_id = item.get('faculty_id')
                    existing_inactive.room_id = item.get('room_id')
                    existing_inactive.schedule_type = item.get('schedule_type', 'lecture')
                    existing_inactive.is_active = True
                    existing_inactive.version = (existing_inactive.version or 1) + 1
                    existing_inactive.updated_at = datetime.utcnow()
                else:
                    new_schedule = Schedule(
                        section_id=item.get('section_id'),
                        subject_id=item.get('subject_id'),
                        faculty_id=item.get('faculty_id'),
                        room_id=item.get('room_id'),
                        day_of_week=item.get('day_of_week'),
                        start_time=start_time,
                        end_time=end_time,
                        semester=item.get('semester'),
                        academic_year=item.get('academic_year'),
                        schedule_type=item.get('schedule_type', 'lecture'),
                        is_active=True,
                        version=1,
                    )
                    db.session.add(new_schedule)
            else:
                exam_date = None
                if item.get('exam_date'):
                    exam_date = datetime.strptime(item['exam_date'], '%Y-%m-%d').date()

                # Check for soft-deleted exam schedule in the same slot (uk_exam_section_slot)
                existing_inactive = ExamSchedule.query.filter_by(
                    section_id=item.get('section_id'),
                    exam_date=exam_date,
                    start_time=start_time,
                    end_time=end_time,
                    academic_year=item.get('academic_year'),
                    semester=item.get('semester'),
                    exam_period=item.get('exam_period'),
                    is_active=False
                ).first()

                if existing_inactive:
                    existing_inactive.subject_id = item.get('subject_id')
                    existing_inactive.faculty_id = item.get('faculty_id')
                    existing_inactive.room_id = item.get('room_id')
                    existing_inactive.schedule_type = item.get('schedule_type', 'lecture')
                    existing_inactive.is_active = True
                    existing_inactive.version = (existing_inactive.version or 1) + 1
                    existing_inactive.updated_at = datetime.utcnow()
                else:
                    new_schedule = ExamSchedule(
                        section_id=item.get('section_id'),
                        subject_id=item.get('subject_id'),
                        faculty_id=item.get('faculty_id'),
                        room_id=item.get('room_id'),
                        exam_date=exam_date,
                        start_time=start_time,
                        end_time=end_time,
                        semester=item.get('semester'),
                        academic_year=item.get('academic_year'),
                        exam_period=item.get('exam_period'),
                        schedule_type=item.get('schedule_type', 'lecture'),
                        is_active=True,
                        version=1,
                    )
                    db.session.add(new_schedule)

            restored_count += 1

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='restored',
            entity_type='schedule_snapshot',
            entity_id=snapshot_id,
            entity_name=snapshot.snapshot_name,
            details=f'Restored {restored_count} {scope} schedule(s) from snapshot (replaced {len(existing_schedules)})',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Restored {restored_count} schedule(s) from "{snapshot.snapshot_name}"',
            'restored_count': restored_count,
            'replaced_count': len(existing_schedules)
        })

    except Exception as e:
        db.session.rollback()
        print(f"Restore snapshot error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/snapshot/<int:snapshot_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_snapshot(snapshot_id):
    """Delete a snapshot. Only the creator or an Admin can delete."""
    try:
        snapshot = ScheduleSnapshot.query.get(snapshot_id)
        if not snapshot:
            return jsonify({'success': False, 'error': 'Snapshot not found'}), 404

        if snapshot.created_by != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'You do not have permission to delete this snapshot'}), 403

        accessible_section_ids = _get_accessible_section_ids_for_current_user()
        allowed, message, status = _validate_snapshot_access_for_current_user(snapshot, accessible_section_ids)
        if not allowed:
            return jsonify({'success': False, 'error': message}), status

        snapshot_name = snapshot.snapshot_name

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='deleted',
            entity_type='schedule_snapshot',
            entity_id=snapshot_id,
            entity_name=snapshot_name,
            details=f'Deleted {snapshot.snapshot_scope} snapshot with {snapshot.schedule_count} schedule(s)',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        db.session.delete(snapshot)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Snapshot "{snapshot_name}" deleted'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Delete snapshot error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/clear', methods=['POST'])
@login_required
@csrf.exempt
def clear_schedules():
    """Clear schedules for a section or entire semester. Auto-creates a backup snapshot first."""
    try:
        data = request.get_json()
        scope = data.get('scope', 'class')  # 'class' or 'exam'
        section_id = data.get('section_id')  # None = all sections (semester-wide)
        section_id_int = None

        if scope not in ('class', 'exam'):
            return jsonify({'success': False, 'error': 'Invalid scope'}), 400

        if section_id is not None:
            try:
                section_id_int = int(section_id)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'Invalid section ID'}), 400

        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return jsonify({'success': False, 'error': 'No active academic settings found'}), 400

        accessible_section_ids = _get_accessible_section_ids_for_current_user()
        if accessible_section_ids is not None:
            if section_id_int is None:
                return jsonify({'success': False, 'error': 'Only admins can clear semester-wide schedules'}), 403
            if section_id_int not in accessible_section_ids:
                return jsonify({'success': False, 'error': 'You do not have access to this section'}), 403

        if scope == 'class':
            Model = Schedule
        else:
            Model = ExamSchedule

        query = Model.query.filter_by(
            is_active=True,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester
        )

        if section_id_int is not None:
            section = Section.query.get(section_id_int)
            if not section:
                return jsonify({'success': False, 'error': 'Section not found'}), 404
            query = query.filter_by(section_id=section_id_int)

        if accessible_section_ids is not None:
            query = query.filter(Model.section_id.in_(accessible_section_ids))

        schedules = query.all()

        if not schedules:
            return jsonify({'success': True, 'message': 'No active schedules to clear', 'cleared_count': 0})

        # Auto-create backup snapshot before clearing
        schedule_dicts = [s.to_dict() for s in schedules]
        section_name = ''
        if section_id_int is not None:
            sec = Section.query.get(section_id_int)
            section_name = f' for {sec.full_section_name}' if sec else ''

        backup_snapshot = ScheduleSnapshot(
            snapshot_name=f'Auto backup before clear{section_name}',
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            snapshot_scope=scope,
            section_id=section_id_int,
            schedule_data=json.dumps(schedule_dicts),
            schedule_count=len(schedule_dicts),
            snapshot_type='auto_pre_clear',
            created_by=current_user.id,
        )
        db.session.add(backup_snapshot)

        # Soft-delete all matching schedules
        cleared_count = 0
        for s in schedules:
            s.is_active = False
            s.updated_at = datetime.utcnow()
            if hasattr(s, 'version'):
                s.version = (s.version or 1) + 1
            cleared_count += 1

        scope_label = 'class' if scope == 'class' else 'exam'
        details = f'Cleared {cleared_count} {scope_label} schedule(s)'
        if section_id_int is not None:
            details += f' for section {section_name.strip()}'
        else:
            details += f' for entire semester ({current_settings.semester} {current_settings.academic_year})'

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='cleared',
            entity_type='schedule',
            entity_id=None,
            entity_name=f'{scope_label}_schedules',
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Cleared {cleared_count} {scope_label} schedule(s). Auto backup snapshot created.',
            'cleared_count': cleared_count
        })

    except Exception as e:
        db.session.rollback()
        print(f"Clear schedules error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/batch-unscheduled-subjects/<int:section_id>')
@login_required
def batch_unscheduled_subjects(section_id):
    """Get unscheduled subjects for a section — used to add rows in batch builder."""
    from app.services.auto_scheduler import AutoScheduler

    try:
        section = Section.query.get_or_404(section_id)
        user_program_ids = current_user.get_program_ids()
        if user_program_ids is not None and section.program_id not in user_program_ids:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        scheduler = AutoScheduler()
        curriculum_id = request.args.get('curriculum_id', type=int)
        include_all = request.args.get('include_all', '').lower() in ('1', 'true')
        result = scheduler.get_unscheduled_subjects(section_id, curriculum_id=curriculum_id,
                                                     include_all=include_all)

        return jsonify(result)

    except Exception as e:
        print(f"Batch unscheduled subjects error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@schedule_bp.route('/ai-suggest-slot', methods=['POST'])
@login_required
@csrf.exempt
def ai_suggest_slot():
    """Suggest the optimal complete schedule assignment for a subject.

    Leverages the existing RecommendationEngine to pick the best faculty,
    day, room and time slot in a single request so the user can auto-fill the
    entire form with one click.
    """
    from app.services.recommendation_engine import RecommendationEngine

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON body'}), 400

    section_id = data.get('section_id')
    subject_id = data.get('subject_id')
    if not section_id or not subject_id:
        return jsonify({'success': False, 'error': 'section_id and subject_id are required'}), 400

    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({'success': False, 'error': 'Subject not found'}), 404

    # Determine schedule type from forced value or subject units
    forced_type = data.get('schedule_type')  # 'lecture' or 'lab' from user
    if forced_type == 'lab' and float(subject.lab_units or 0) > 0:
        schedule_type_label = 'Laboratory'
        units = float(subject.lab_units)
    elif forced_type == 'lecture' and float(subject.lec_units or 0) > 0:
        schedule_type_label = 'Lecture'
        units = float(subject.lec_units)
    else:
        # Auto-detect: prefer lecture if available
        if float(subject.lec_units or 0) > 0:
            schedule_type_label = 'Lecture'
            units = float(subject.lec_units)
        elif float(subject.lab_units or 0) > 0:
            schedule_type_label = 'Laboratory'
            units = float(subject.lab_units)
        else:
            schedule_type_label = 'Lecture'
            units = 1  # Fallback

    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    academic_year = data.get('academic_year') or (current_settings.academic_year if current_settings else None)
    semester = data.get('semester') or (current_settings.semester if current_settings else None)

    # Build filters for existing schedules
    sched_query = Schedule.query.filter_by(is_archived=False)
    if academic_year:
        sched_query = sched_query.filter_by(academic_year=academic_year)
    if semester:
        sched_query = sched_query.filter_by(semester=semester)

    # If editing, exclude self
    schedule_id = data.get('schedule_id')
    if schedule_id:
        sched_query = sched_query.filter(Schedule.id != int(schedule_id))

    all_schedules = sched_query.all()

    engine = RecommendationEngine()
    reasons = []
    overall_confidence_parts = []

    # ── 1. Best Faculty ──────────────────────────────────────────
    faculty_data = {
        'subject_id': subject_id,
        'section_id': section_id,
        'day_of_week': 'Monday',   # placeholder, not used for faculty
        'start_time': '08:00',
        'end_time': '09:00',
    }
    faculty_options = engine._find_alternative_faculty(faculty_data, all_schedules)
    best_faculty = None
    if faculty_options:
        best_faculty = Faculty.query.get(faculty_options[0]['faculty_id'])
        conf = faculty_options[0].get('confidence', 70)
        overall_confidence_parts.append(conf)
        reasons.append(f"Faculty: {best_faculty.full_name} ({faculty_options[0].get('reason', '')})")

    # ── 2. Best Day ──────────────────────────────────────────────
    duration_minutes = int(units * 60)
    day_data = {
        'faculty_id': best_faculty.id if best_faculty else None,
        'section_id': section_id,
        'room_id': None,
        'day_of_week': None,
        'start_time': datetime.strptime('08:00', '%H:%M').time(),
        'end_time': (datetime.strptime('08:00', '%H:%M') + timedelta(minutes=duration_minutes)).time(),
    }
    day_options = engine._find_alternative_days(day_data, all_schedules)
    best_day = day_options[0]['day'] if day_options else 'Monday'
    if day_options:
        overall_confidence_parts.append(day_options[0].get('confidence', 60))
        reasons.append(f"Day: {best_day} ({day_options[0].get('reason', '')})")

    # ── 3. Best Room ─────────────────────────────────────────────
    room_type = 'Laboratory' if schedule_type_label == 'Laboratory' else 'Lecture'
    if subject and any(kw in (subject.subject_code or '').lower() for kw in ['pe', 'pathfit', 'p.e.']):
        room_type = 'Court/Gym'

    room_data = {
        'day_of_week': best_day,
        'start_time': datetime.strptime('08:00', '%H:%M').time(),
        'end_time': (datetime.strptime('08:00', '%H:%M') + timedelta(minutes=duration_minutes)).time(),
        'room_id': None,
        'section_id': section_id,
        'faculty_id': best_faculty.id if best_faculty else None,
        'subject_id': subject_id,
    }
    room_options = engine._find_alternative_rooms(room_data, all_schedules, subject)
    best_room = None
    if room_options:
        best_room = Room.query.get(room_options[0]['room_id'])
        overall_confidence_parts.append(room_options[0].get('confidence', 60))

    # ── 4. Best Time ─────────────────────────────────────────────
    # Pass dummy start/end reflecting subject duration so engine calculates correct slot length
    dummy_start = datetime.strptime('08:00', '%H:%M').time()
    dummy_end = (datetime.strptime('08:00', '%H:%M') + timedelta(minutes=duration_minutes)).time()
    time_data = {
        'section_id': section_id,
        'faculty_id': best_faculty.id if best_faculty else None,
        'room_id': best_room.id if best_room else None,
        'day_of_week': best_day,
        'start_time': dummy_start,
        'end_time': dummy_end,
    }
    time_options = engine._find_alternative_times(time_data, all_schedules, subject)
    best_time = None
    if time_options:
        best_time = time_options[0]
        overall_confidence_parts.append(best_time.get('confidence', 60))
        reasons.append(f"Time: {best_time['display']} ({best_time.get('reason', '')})")

    # Check we found everything
    if not all([best_faculty, best_day, best_room, best_time]):
        missing = []
        if not best_faculty:
            missing.append('faculty')
        if not best_room:
            missing.append('room')
        if not best_time:
            missing.append('time slot')

        partial = {}
        if best_faculty:
            partial['faculty_id'] = best_faculty.id
            partial['faculty_name'] = best_faculty.full_name
        if best_day:
            partial['day_of_week'] = best_day
        if best_room:
            partial['room_id'] = best_room.id
            partial['room_name'] = f"{best_room.room_number} ({best_room.building.building_name})" if best_room.building else best_room.room_number
        if best_time:
            partial['start_time'] = best_time['start_time']
            partial['end_time'] = best_time['end_time']

        return jsonify({
            'success': False,
            'fallback_message': f"Could not find conflict-free {', '.join(missing)}. Try manual assignment.",
            'partial': partial,
            'schedule_type': 'lecture' if schedule_type_label == 'Lecture' else 'lab',
        })

    # Overall confidence = average of parts
    overall_confidence = round(sum(overall_confidence_parts) / len(overall_confidence_parts)) if overall_confidence_parts else 50

    return jsonify({
        'success': True,
        'suggestion': {
            'schedule_type': 'lecture' if schedule_type_label == 'Lecture' else 'lab',
            'faculty_id': best_faculty.id,
            'faculty_name': best_faculty.full_name,
            'day_of_week': best_day,
            'room_id': best_room.id,
            'room_name': f"{best_room.room_number} ({best_room.building.building_name})" if best_room.building else best_room.room_number,
            'start_time': best_time['start_time'],
            'end_time': best_time['end_time'],
            'confidence': overall_confidence,
            'reasons': reasons,
        }
    })


@schedule_bp.route('/field-context')
@login_required
def get_field_context():
    """Return lightweight contextual information for a single field change.
    
    Used by the Smart Status Line (B2) to give real-time feedback as the user
    fills each form field, without triggering a full conflict check.
    
    Query params:
        field: 'faculty' | 'day'
        faculty_id: int (for faculty/day context)
        day_of_week: str (for day context)
        academic_year: str (optional)
        semester: str (optional)
        exclude_schedule_id: int (optional, for edit mode)
    """
    field = request.args.get('field')

    if field == 'faculty':
        faculty_id = request.args.get('faculty_id', type=int)
        if not faculty_id:
            return jsonify({'error': 'faculty_id required'}), 400
        faculty = Faculty.query.get(faculty_id)
        if not faculty:
            return jsonify({'error': 'Faculty not found'}), 404

        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        ay = request.args.get('academic_year') or (current_settings.academic_year if current_settings else None)
        sem = request.args.get('semester') or (current_settings.semester if current_settings else None)

        load_info = faculty.get_load_status(ay, sem)
        return jsonify({
            'name': faculty.full_name,
            'current_units': load_info[0],
            'max_units': load_info[1],
            'utilization_pct': round(load_info[2], 1),
            'status': load_info[3]  # 'normal', 'warning', 'exceeded'
        })

    elif field == 'day':
        faculty_id = request.args.get('faculty_id', type=int)
        day = request.args.get('day_of_week')
        if not faculty_id or not day:
            return jsonify({'error': 'faculty_id and day_of_week required'}), 400

        faculty = Faculty.query.get(faculty_id)
        if not faculty:
            return jsonify({'error': 'Faculty not found'}), 404

        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        ay = request.args.get('academic_year') or (current_settings.academic_year if current_settings else None)
        sem = request.args.get('semester') or (current_settings.semester if current_settings else None)

        query = Schedule.query.filter_by(
            faculty_id=faculty_id,
            day_of_week=day,
            is_active=True
        ).filter(Schedule.is_archived == False)
        if ay:
            query = query.filter_by(academic_year=ay)
        if sem:
            query = query.filter_by(semester=sem)

        exclude_id = request.args.get('exclude_schedule_id', type=int)
        if exclude_id:
            query = query.filter(Schedule.id != exclude_id)

        schedules = query.all()

        total_hours = 0
        for s in schedules:
            if s.start_time and s.end_time:
                start = datetime.combine(datetime.today(), s.start_time)
                end = datetime.combine(datetime.today(), s.end_time)
                total_hours += (end - start).seconds / 3600

        return jsonify({
            'faculty_name': faculty.full_name,
            'schedule_count': len(schedules),
            'total_hours': round(total_hours, 1),
            'max_daily_hours': 6
        })

    return jsonify({'error': 'Unknown field type. Use field=faculty or field=day'}), 400


# ============================================================================
# END OF SCHEDULE ROUTES
# ============================================================================
