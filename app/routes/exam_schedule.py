"""
Exam Schedule routes for managing exam schedules
"""
from flask import Blueprint, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from datetime import datetime
from app.extensions import db, csrf
from app.models.exam_schedule import ExamSchedule
from app.models.department import Department, Section
from app.models.curriculum import Subject
from app.models.faculty import Faculty
from app.models.building import Room
from app.models.settings import AcademicSettings
from app.decorators import role_required
from app.utils.activity_logger import log_create, log_edit, log_delete

exam_schedule_bp = Blueprint('exam_schedule', __name__, url_prefix='/exam-schedule')


@exam_schedule_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new exam schedule"""
    try:
        section_id = request.form.get('section_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int) or None
        room_id = request.form.get('room_id', type=int) or None
        exam_date_str = request.form.get('exam_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        # Get current academic settings (including exam_period)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            flash('No active academic settings found. Please configure academic settings first.', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        academic_year = current_settings.academic_year
        semester = current_settings.semester
        exam_period = current_settings.exam_period
        
        # Validation
        if not all([section_id, subject_id, exam_date_str, start_time_str, end_time_str]):
            flash('All required fields must be filled', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Convert date and time strings
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Check for conflicts - same section, date, and overlapping time
        conflict_query = ExamSchedule.query.filter(
            ExamSchedule.section_id == section_id,
            ExamSchedule.exam_date == exam_date,
            ExamSchedule.is_active == True,
            or_(
                and_(ExamSchedule.start_time <= start_time, ExamSchedule.end_time > start_time),
                and_(ExamSchedule.start_time < end_time, ExamSchedule.end_time >= end_time),
                and_(ExamSchedule.start_time >= start_time, ExamSchedule.end_time <= end_time)
            )
        )
        
        if academic_year and semester:
            conflict_query = conflict_query.filter(
                ExamSchedule.academic_year == academic_year,
                ExamSchedule.semester == semester
            )
        
        if conflict_query.first():
            flash('Exam schedule conflict: This section already has an exam scheduled at this time', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Check for faculty conflicts if faculty assigned
        if faculty_id:
            faculty_conflict = ExamSchedule.query.filter(
                ExamSchedule.faculty_id == faculty_id,
                ExamSchedule.exam_date == exam_date,
                ExamSchedule.is_active == True,
                or_(
                    and_(ExamSchedule.start_time <= start_time, ExamSchedule.end_time > start_time),
                    and_(ExamSchedule.start_time < end_time, ExamSchedule.end_time >= end_time),
                    and_(ExamSchedule.start_time >= start_time, ExamSchedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                faculty_conflict = faculty_conflict.filter(
                    ExamSchedule.academic_year == academic_year,
                    ExamSchedule.semester == semester
                )
            
            if faculty_conflict.first():
                flash('Faculty conflict: This faculty member is already assigned to another exam at this time', 'danger')
                return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Check for room conflicts if room assigned
        if room_id:
            room_conflict = ExamSchedule.query.filter(
                ExamSchedule.room_id == room_id,
                ExamSchedule.exam_date == exam_date,
                ExamSchedule.is_active == True,
                or_(
                    and_(ExamSchedule.start_time <= start_time, ExamSchedule.end_time > start_time),
                    and_(ExamSchedule.start_time < end_time, ExamSchedule.end_time >= end_time),
                    and_(ExamSchedule.start_time >= start_time, ExamSchedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                room_conflict = room_conflict.filter(
                    ExamSchedule.academic_year == academic_year,
                    ExamSchedule.semester == semester
                )
            
            if room_conflict.first():
                flash('Room conflict: This room is already assigned to another exam at this time', 'danger')
                return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Create new exam schedule
        exam_schedule = ExamSchedule(
            section_id=section_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            room_id=room_id,
            exam_date=exam_date,
            start_time=start_time,
            end_time=end_time,
            semester=semester,
            academic_year=academic_year,
            exam_period=exam_period,
            is_active=True
        )
        
        db.session.add(exam_schedule)
        db.session.flush()
        
        # Log activity
        log_create('exam_schedule', exam_schedule.id, f'{exam_schedule.subject.subject_code} - {exam_schedule.section.section_name}', {
            'exam_date': str(exam_date),
            'exam_period': exam_period
        })
        
        db.session.commit()
        
        flash('Exam schedule added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding exam schedule: {str(e)}', 'danger')
    
    return redirect(url_for('schedule.index', exam_section_id=section_id))


@exam_schedule_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing exam schedule"""
    section_id = None  # Initialize to prevent UnboundLocalError
    try:
        # Frontend sends 'exam_schedule_id', not 'schedule_id'
        schedule_id = request.form.get('exam_schedule_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int) or None
        room_id = request.form.get('room_id', type=int) or None
        exam_date_str = request.form.get('exam_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        # Get existing schedule
        exam_schedule = ExamSchedule.query.get(schedule_id)
        if not exam_schedule:
            flash('Exam schedule not found', 'danger')
            return redirect(url_for('schedule.index'))
        
        section_id = exam_schedule.section_id
        
        # Get current academic settings (including exam_period)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            flash('No active academic settings found. Please configure academic settings first.', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        academic_year = current_settings.academic_year
        semester = current_settings.semester
        exam_period = current_settings.exam_period
        
        # Validation
        if not all([subject_id, exam_date_str, start_time_str, end_time_str]):
            flash('All required fields must be filled', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Convert date and time strings
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Check for conflicts - same section, date, and overlapping time (excluding current schedule)
        conflict_query = ExamSchedule.query.filter(
            ExamSchedule.id != schedule_id,
            ExamSchedule.section_id == section_id,
            ExamSchedule.exam_date == exam_date,
            ExamSchedule.is_active == True,
            or_(
                and_(ExamSchedule.start_time <= start_time, ExamSchedule.end_time > start_time),
                and_(ExamSchedule.start_time < end_time, ExamSchedule.end_time >= end_time),
                and_(ExamSchedule.start_time >= start_time, ExamSchedule.end_time <= end_time)
            )
        )
        
        if academic_year and semester:
            conflict_query = conflict_query.filter(
                ExamSchedule.academic_year == academic_year,
                ExamSchedule.semester == semester
            )
        
        if conflict_query.first():
            flash('Exam schedule conflict: This section already has an exam scheduled at this time', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Check for faculty conflicts if faculty assigned
        if faculty_id:
            faculty_conflict = ExamSchedule.query.filter(
                ExamSchedule.id != schedule_id,
                ExamSchedule.faculty_id == faculty_id,
                ExamSchedule.exam_date == exam_date,
                ExamSchedule.is_active == True,
                or_(
                    and_(ExamSchedule.start_time <= start_time, ExamSchedule.end_time > start_time),
                    and_(ExamSchedule.start_time < end_time, ExamSchedule.end_time >= end_time),
                    and_(ExamSchedule.start_time >= start_time, ExamSchedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                faculty_conflict = faculty_conflict.filter(
                    ExamSchedule.academic_year == academic_year,
                    ExamSchedule.semester == semester
                )
            
            if faculty_conflict.first():
                flash('Faculty conflict: This faculty member is already assigned to another exam at this time', 'danger')
                return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Check for room conflicts if room assigned
        if room_id:
            room_conflict = ExamSchedule.query.filter(
                ExamSchedule.id != schedule_id,
                ExamSchedule.room_id == room_id,
                ExamSchedule.exam_date == exam_date,
                ExamSchedule.is_active == True,
                or_(
                    and_(ExamSchedule.start_time <= start_time, ExamSchedule.end_time > start_time),
                    and_(ExamSchedule.start_time < end_time, ExamSchedule.end_time >= end_time),
                    and_(ExamSchedule.start_time >= start_time, ExamSchedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                room_conflict = room_conflict.filter(
                    ExamSchedule.academic_year == academic_year,
                    ExamSchedule.semester == semester
                )
            
            if room_conflict.first():
                flash('Room conflict: This room is already assigned to another exam at this time', 'danger')
                return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Track changes
        changes = {}
        if exam_schedule.subject_id != subject_id:
            old_subject = Subject.query.get(exam_schedule.subject_id)
            new_subject = Subject.query.get(subject_id)
            changes['subject'] = f'{old_subject.subject_code if old_subject else "N/A"} → {new_subject.subject_code if new_subject else "N/A"}'
        
        if exam_schedule.faculty_id != faculty_id:
            old_faculty = Faculty.query.get(exam_schedule.faculty_id) if exam_schedule.faculty_id else None
            new_faculty = Faculty.query.get(faculty_id) if faculty_id else None
            changes['faculty'] = f'{old_faculty.full_name if old_faculty else "None"} → {new_faculty.full_name if new_faculty else "None"}'
        
        if exam_schedule.room_id != room_id:
            old_room = Room.query.get(exam_schedule.room_id) if exam_schedule.room_id else None
            new_room = Room.query.get(room_id) if room_id else None
            changes['room'] = f'{old_room.room_number if old_room else "None"} → {new_room.room_number if new_room else "None"}'
        
        if exam_schedule.exam_date != exam_date:
            changes['date'] = f'{exam_schedule.exam_date} → {exam_date}'
        
        if exam_schedule.start_time != start_time or exam_schedule.end_time != end_time:
            changes['time'] = f'{exam_schedule.start_time}-{exam_schedule.end_time} → {start_time}-{end_time}'
        
        if exam_schedule.exam_period != exam_period:
            changes['exam_period'] = f'{exam_schedule.exam_period} → {exam_period}'
        
        if exam_schedule.semester != semester:
            changes['semester'] = f'{exam_schedule.semester} → {semester}'
        
        if exam_schedule.academic_year != academic_year:
            changes['academic_year'] = f'{exam_schedule.academic_year} → {academic_year}'
        
        # Update exam schedule
        exam_schedule.subject_id = subject_id
        exam_schedule.faculty_id = faculty_id
        exam_schedule.room_id = room_id
        exam_schedule.exam_date = exam_date
        exam_schedule.start_time = start_time
        exam_schedule.end_time = end_time
        exam_schedule.exam_period = exam_period
        exam_schedule.semester = semester
        exam_schedule.academic_year = academic_year
        exam_schedule.updated_at = datetime.utcnow()
        
        # Log activity with changes
        log_edit('exam_schedule', exam_schedule.id, f'{exam_schedule.subject.subject_code} - {exam_schedule.section.section_name}', changes if changes else None)
        
        db.session.commit()
        
        flash('Exam schedule updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating exam schedule: {str(e)}', 'danger')
    
    # Use section_id if available, otherwise redirect without it
    if section_id:
        return redirect(url_for('schedule.index', exam_section_id=section_id))
    else:
        return redirect(url_for('schedule.index'))


@exam_schedule_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete an exam schedule"""
    section_id = None  # Initialize to prevent UnboundLocalError
    try:
        # Frontend sends 'exam_schedule_id', not 'schedule_id'
        schedule_id = request.form.get('exam_schedule_id', type=int)
        exam_schedule = ExamSchedule.query.get(schedule_id)
        if not exam_schedule:
            flash('Exam schedule not found', 'danger')
            return redirect(url_for('schedule.index'))
        
        section_id = exam_schedule.section_id
        exam_info = f'{exam_schedule.subject.subject_code} - {exam_schedule.section.section_name}'
        
        # Log activity before deletion
        log_delete('exam_schedule', exam_schedule.id, exam_info, {'exam_date': str(exam_schedule.exam_date)})
        
        db.session.delete(exam_schedule)
        db.session.commit()
        
        flash('Exam schedule deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting exam schedule: {str(e)}', 'danger')
    
    # Use section_id if available, otherwise redirect without it
    if section_id:
        return redirect(url_for('schedule.index', exam_section_id=section_id))
    else:
        return redirect(url_for('schedule.index'))
