"""
Main routes (index, dashboard, about)
"""
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from app.extensions import db
from app.models.curriculum import Curriculum, Subject
from app.models.program import Program
from app.models.section import Section
from app.models.faculty import Faculty
from app.models.building import Building, Room
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.settings import AcademicSettings
from app.models.archive import Archive
from app.models.activity_log import UserActivityLog
from app.models.user import User

main_bp = Blueprint('main', __name__)


def _calc_trend(current, previous):
    """Calculate trend direction and percentage change."""
    if previous == 0 and current == 0:
        return {'direction': 'same', 'pct': 0, 'previous': 0}
    if previous == 0:
        return {'direction': 'new', 'pct': 0, 'previous': 0}
    pct = round(((current - previous) / previous) * 100)
    if pct > 0:
        return {'direction': 'up', 'pct': pct, 'previous': previous}
    elif pct < 0:
        return {'direction': 'down', 'pct': abs(pct), 'previous': previous}
    else:
        return {'direction': 'same', 'pct': 0, 'previous': previous}


def get_stat_trends(current_year, current_semester, filter_program_ids=None):
    """Calculate trend data comparing current semester to previous semester."""
    if not current_year or not current_semester:
        return {}

    # Determine previous semester
    if current_semester == '2nd Semester':
        prev_semester = '1st Semester'
        prev_year = current_year
    elif current_semester == '1st Semester':
        prev_semester = '2nd Semester'
        years = current_year.split('-')
        if len(years) == 2:
            prev_year = f"{int(years[0])-1}-{int(years[1])-1}"
        else:
            return {}
    else:  # Summer
        prev_semester = '2nd Semester'
        prev_year = current_year

    # Previous schedule count
    prev_sched_q = Schedule.query.filter_by(
        academic_year=prev_year, semester=prev_semester, is_active=True
    ).join(Schedule.section)
    if filter_program_ids:
        prev_sched_q = prev_sched_q.filter(Section.program_id.in_(filter_program_ids))
    prev_schedules = prev_sched_q.count()

    # Previous exam count
    prev_exam_q = ExamSchedule.query.filter_by(
        academic_year=prev_year, semester=prev_semester, is_active=True
    ).join(ExamSchedule.section)
    if filter_program_ids:
        prev_exam_q = prev_exam_q.filter(Section.program_id.in_(filter_program_ids))
    prev_exams = prev_exam_q.count()

    # Previous faculty count (cross-semester, but we use active count; show vs previous count stored)
    # Faculty/section/room don't have semester — use current counts always
    # We only trend semester-bound metrics

    return {
        'prev_year': prev_year,
        'prev_semester': prev_semester,
        'schedule_trend': None,   # filled by caller with current counts
        'exam_trend': None,
        '_prev_schedules': prev_schedules,
        '_prev_exams': prev_exams,
    }


def get_weekly_activity(filter_program_ids=None):
    """Get schedule creation counts for the last 7 days."""
    today = datetime.utcnow().date()
    start_day = today - timedelta(days=6)
    start_dt = datetime.combine(start_day, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())

    q = db.session.query(
        func.date(Schedule.created_at).label('day'),
        func.count(Schedule.id).label('count')
    ).filter(
        Schedule.is_active == True,
        Schedule.created_at >= start_dt,
        Schedule.created_at < end_dt
    )

    if filter_program_ids:
        q = q.join(Schedule.section).filter(Section.program_id.in_(filter_program_ids))

    rows = q.group_by(func.date(Schedule.created_at)).all()
    counts_by_day = {str(row.day): row.count for row in rows}

    activity = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        key = day.isoformat()
        activity.append({
            'date': key,
            'count': counts_by_day.get(key, 0)
        })
    return activity


def generate_smart_actions(schedule_completion_rate, overloaded_faculty_count,
                          warning_faculty_count, upcoming_exams,
                          unscheduled_sections=0):
    """
    Generate context-aware Quick Action buttons for the dashboard.
    
    Returns list of dicts with: label, url, icon, color_class, priority
    Maximum 3 actions returned, ordered by priority.
    """
    actions = []
    
    # --- Priority 1 (Highest): Overloaded Faculty ---
    if overloaded_faculty_count > 0:
        actions.append({
            'label': f'Review {overloaded_faculty_count} Overloaded Faculty',
            'url': url_for('reports.index'),
            'icon': 'alert-triangle',
            'color_class': 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800 dark:hover:bg-red-900/40',
            'priority': 1
        })
    
    # --- Priority 2: Incomplete Scheduling ---
    if schedule_completion_rate < 100 and unscheduled_sections > 0:
        actions.append({
            'label': f'Schedule {unscheduled_sections} Remaining Section{"s" if unscheduled_sections != 1 else ""}',
            'url': url_for('schedule.class_view'),
            'icon': 'clipboard-list',
            'color_class': 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800 dark:hover:bg-amber-900/40',
            'priority': 2
        })
    
    # --- Priority 3: Near-capacity Faculty ---
    if warning_faculty_count > 0:
        actions.append({
            'label': f'{warning_faculty_count} Faculty Near Capacity',
            'url': url_for('reports.index'),
            'icon': 'users',
            'color_class': 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100 border border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-800 dark:hover:bg-yellow-900/40',
            'priority': 3
        })

    # --- Priority 4: Upcoming Exams ---
    if upcoming_exams and len(upcoming_exams) > 0:
        actions.append({
            'label': f'{len(upcoming_exams)} Exam{"s" if len(upcoming_exams) != 1 else ""} This Week',
            'url': url_for('schedule.exam_view'),
            'icon': 'file-text',
            'color_class': 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-800 dark:hover:bg-purple-900/40',
            'priority': 4
        })
    
    # --- Fill remaining slots with defaults (up to 3 total) ---
    default_actions = [
        {
            'label': 'New Schedule',
            'url': url_for('schedule.class_view'),
            'icon': 'plus-circle',
            'color_class': 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800 dark:hover:bg-blue-900/40',
            'priority': 10
        },
        {
            'label': 'View Reports',
            'url': url_for('reports.index'),
            'icon': 'bar-chart',
            'color_class': 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800 dark:hover:bg-emerald-900/40',
            'priority': 11
        }
    ]
    
    for default in default_actions:
        if len(actions) >= 3:
            break
        actions.append(default)
    
    # Sort by priority and limit to 3
    actions.sort(key=lambda a: a['priority'])
    return actions[:3]


def _count_classes_smart(schedule_rows):
    """
    Count today's classes with smart lec+lab merging.
    
    A lecture and lab count as ONE class only if ALL of these are true:
      1. Same section_id and subject_id
      2. Chronologically adjacent (lecture end_time == lab start_time)
      3. Same faculty_id
    
    Returns (total_classes, remaining_classes) where remaining = classes
    whose earliest start_time is still in the future.
    """
    from collections import defaultdict
    from datetime import datetime as dt

    now_time = dt.now().time()

    # Group rows by (section_id, subject_id)
    groups = defaultdict(list)
    for s in schedule_rows:
        groups[(s.section_id, s.subject_id)].append(s)

    total = 0
    remaining = 0

    for _key, rows in groups.items():
        # Sort by start_time within each group
        rows.sort(key=lambda r: r.start_time)

        merged = set()  # indices that were merged into a previous class

        for i, row in enumerate(rows):
            if i in merged:
                continue

            # Try to merge with next row in the group
            class_merged = False
            if i + 1 < len(rows):
                nxt = rows[i + 1]
                is_adjacent = row.end_time == nxt.start_time
                same_faculty = row.faculty_id is not None and row.faculty_id == nxt.faculty_id
                diff_types = row.schedule_type != nxt.schedule_type

                if is_adjacent and same_faculty and diff_types:
                    # Merge: this pair counts as 1 class
                    merged.add(i + 1)
                    class_merged = True
                    # Use the earliest start_time of the pair for "remaining" check
                    earliest_start = row.start_time
                    total += 1
                    if earliest_start > now_time:
                        remaining += 1
                    continue

            if not class_merged:
                total += 1
                if row.start_time > now_time:
                    remaining += 1

    return total, remaining


@main_bp.route('/')
def index():
    """Home page - redirects to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page with statistics"""
    if current_user.is_super_admin:
        return redirect(url_for('admin_tools.superadmin_dashboard'))

    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    # Get user's program access
    user_program_ids = current_user.get_program_ids()
    
    # Get program filter from request
    selected_department_id = request.args.get('program_id', type=int)
    
    # Get all programs the user has access to
    if user_program_ids is None:
        # Admin - see all programs
        available_departments = Program.query.filter_by(is_active=True).order_by(Program.program_name).all()
    else:
        # Dean - filter by assigned programs
        available_departments = Program.query.filter(
            Program.is_active == True,
            Program.id.in_(user_program_ids)
        ).order_by(Program.program_name).all()

    # Enforce program access when a specific program is requested
    if selected_department_id and user_program_ids is not None and selected_department_id not in user_program_ids:
        selected_department_id = None
    
    # Determine which programs to show stats for
    if selected_department_id:
        # Specific program selected
        filter_program_ids = [selected_department_id]
    elif user_program_ids is None:
        # Admin with no filter - show all
        filter_program_ids = None
    else:
        # Dean with no filter - show all their programs
        filter_program_ids = user_program_ids

    # Explicit scope label used by KPI microcopy to avoid interpretation confusion.
    selected_program = next((p for p in available_departments if p.id == selected_department_id), None) if selected_department_id else None
    if selected_program:
        dashboard_scope_label = f"{selected_program.program_code}"
    elif user_program_ids is None:
        dashboard_scope_label = "All Programs"
    else:
        dashboard_scope_label = "My Programs"
    
    # Build program-scoped base queries
    if filter_program_ids is None:
        # Admin - see all programs
        curriculum_query = Curriculum.query.filter_by(is_active=True)
        section_query = Section.query
        faculty_query = Faculty.query.filter_by(is_active=True, is_archived=False)
    else:
        # Filtered view
        curriculum_query = Curriculum.query.filter(
            Curriculum.is_active == True,
            Curriculum.program_id.in_(filter_program_ids)
        )
        section_query = Section.query.filter(
            Section.program_id.in_(filter_program_ids)
        )
        # Derive department IDs from program filter for faculty filtering
        from app.models.program import Program as Dept
        from sqlalchemy import or_

        _department_ids = db.session.query(Dept.department_id).filter(
            Dept.id.in_(filter_program_ids),
            Dept.department_id.isnot(None)
        ).distinct().all()
        _department_id_list = [c[0] for c in _department_ids]
        
        # Also include faculty dynamically teaching in these programs
        _teaching_fac_q = db.session.query(Schedule.faculty_id).join(Section).filter(
            Schedule.faculty_id.isnot(None),
            Schedule.is_active == True,
            Section.program_id.in_(filter_program_ids)
        )
        if current_settings:
            _teaching_fac_q = _teaching_fac_q.filter(
                Schedule.academic_year == current_settings.academic_year,
                Schedule.semester == current_settings.semester
            )
        _teaching_fac_ids = [r[0] for r in _teaching_fac_q.distinct().all()]

        faculty_query = Faculty.query.filter(
            Faculty.is_active == True,
            Faculty.is_archived == False
        )
        
        if _department_id_list:
            if _teaching_fac_ids:
                faculty_query = faculty_query.filter(
                    or_(
                        Faculty.department_id.in_(_department_id_list),
                        Faculty.id.in_(_teaching_fac_ids)
                    )
                )
            else:
                faculty_query = faculty_query.filter(Faculty.department_id.in_(_department_id_list))
        elif _teaching_fac_ids:
            faculty_query = faculty_query.filter(Faculty.id.in_(_teaching_fac_ids))
        else:
            faculty_query = faculty_query.filter(False)
    
    # Get counts for dashboard stats
    curriculum_count = curriculum_query.count()
    department_count = 0
    faculty_count = 0
    building_count = Building.query.filter_by(is_active=True, is_archived=False).count()

    # System-wide totals for admin-only system overview card.
    system_program_count = Program.query.filter_by(is_active=True, is_archived=False).count()
    system_building_count = Building.query.filter_by(is_active=True, is_archived=False).count()
    system_room_count = Room.query.filter_by(is_available=True).count()
    
    # Additional statistics
    section_count = section_query.count()
    room_count = 0
    
    # Subject count - handle filtering differently
    if filter_program_ids is None:
        subject_count = Subject.query.count()
    else:
        from app.models.curriculum import Semester, YearLevel
        subject_count = db.session.query(func.count(Subject.id)).join(Semester).join(YearLevel).join(Curriculum)\
            .filter(Curriculum.program_id.in_(filter_program_ids))\
            .scalar() or 0
    
    # Schedule statistics (for current academic year/semester if available)
    schedule_query = Schedule.query.filter_by(is_active=True)\
        .join(Schedule.section)
    
    if filter_program_ids:
        schedule_query = schedule_query.filter(Section.program_id.in_(filter_program_ids))
    
    if current_settings:
        schedule_query = schedule_query.filter(
            Schedule.academic_year == current_settings.academic_year,
            Schedule.semester == current_settings.semester
        )
    
    schedule_count = schedule_query.count()

    # Rooms/Buildings are scoped by currently visible schedules to avoid misleading global counts.
    room_count = db.session.query(func.count(func.distinct(Schedule.room_id))).filter(
        Schedule.is_active == True,
        Schedule.room_id.isnot(None)
    )
    if current_settings:
        room_count = room_count.filter(
            Schedule.academic_year == current_settings.academic_year,
            Schedule.semester == current_settings.semester
        )
    if filter_program_ids:
        room_count = room_count.join(Schedule.section).filter(Section.program_id.in_(filter_program_ids))
    room_count = room_count.scalar() or 0

    building_count = db.session.query(func.count(func.distinct(Room.building_id))).join(
        Schedule, Schedule.room_id == Room.id
    ).join(
        Building, Building.id == Room.building_id
    ).filter(
        Schedule.is_active == True,
        Building.is_active == True,
        Building.is_archived == False
    )
    if current_settings:
        building_count = building_count.filter(
            Schedule.academic_year == current_settings.academic_year,
            Schedule.semester == current_settings.semester
        )
    if filter_program_ids:
        building_count = building_count.join(Schedule.section).filter(Section.program_id.in_(filter_program_ids))
    building_count = building_count.scalar() or 0
    
    # Exam schedule statistics
    exam_query = ExamSchedule.query.filter_by(is_active=True)\
        .join(ExamSchedule.section)
    
    if filter_program_ids:
        exam_query = exam_query.filter(Section.program_id.in_(filter_program_ids))
    
    if current_settings:
        exam_query = exam_query.filter(
            ExamSchedule.academic_year == current_settings.academic_year,
            ExamSchedule.semester == current_settings.semester,
            ExamSchedule.exam_period == current_settings.exam_period
        )
    
    exam_schedule_count = exam_query.count()
    
    # Get programs with their curriculum/section/faculty counts for quick overview
    departments_overview = []
    if selected_department_id:
        programs = [program for program in available_departments if program.id == selected_department_id]
    else:
        programs = available_departments
    department_count = len(programs)
    program_ids = [program.id for program in programs]
    department_ids = [program.department_id for program in programs if program.department_id is not None]

    curriculum_counts_by_program = {}
    section_counts_by_program = {}
    faculty_counts_by_department = {}

    if program_ids:
        curriculum_count_rows = db.session.query(
            Curriculum.program_id,
            func.count(Curriculum.id)
        ).filter(
            Curriculum.is_active == True,
            Curriculum.program_id.in_(program_ids)
        ).group_by(Curriculum.program_id).all()
        curriculum_counts_by_program = {program_id: count for program_id, count in curriculum_count_rows}

        section_count_rows = db.session.query(
            Section.program_id,
            func.count(Section.id)
        ).filter(
            Section.program_id.in_(program_ids)
        ).group_by(Section.program_id).all()
        section_counts_by_program = {program_id: count for program_id, count in section_count_rows}

    if department_ids:
        faculty_count_rows = db.session.query(
            Faculty.department_id,
            func.count(Faculty.id)
        ).filter(
            Faculty.is_active == True,
            Faculty.is_archived == False,
            Faculty.department_id.in_(department_ids)
        ).group_by(Faculty.department_id).all()
        faculty_counts_by_department = {department_id: count for department_id, count in faculty_count_rows}

    for dept in programs:
        dept_curriculum_count = curriculum_counts_by_program.get(dept.id, 0)
        dept_section_count = section_counts_by_program.get(dept.id, 0)
        dept_faculty_count = faculty_counts_by_department.get(dept.department_id, 0) if dept.department_id else 0
        
        departments_overview.append({
            'name': dept.program_name,
            'code': dept.program_code,
            'curriculum_count': dept_curriculum_count,
            'section_count': dept_section_count,
            'faculty_count': dept_faculty_count
        })
    
    # Faculty workload overview (top 5 with most schedules)
    faculties = faculty_query.options(joinedload(Faculty.department)).all()
    faculty_count = len(faculties)
    faculty_ids = [faculty.id for faculty in faculties]

    faculty_workload_map = {}
    if faculty_ids:
        faculty_workload_query = db.session.query(
            Schedule.faculty_id,
            func.count(Schedule.id).label('schedule_count'),
            func.coalesce(
                func.sum(
                    func.coalesce(Subject.lec_units, 0) + func.coalesce(Subject.lab_units, 0)
                ),
                0
            ).label('total_units')
        ).outerjoin(Subject, Subject.id == Schedule.subject_id).filter(
            Schedule.is_active == True,
            Schedule.faculty_id.in_(faculty_ids)
        )

        if current_settings:
            faculty_workload_query = faculty_workload_query.filter(
                Schedule.academic_year == current_settings.academic_year,
                Schedule.semester == current_settings.semester
            )

        if filter_program_ids:
            faculty_workload_query = faculty_workload_query.join(Schedule.section).filter(
                Section.program_id.in_(filter_program_ids)
            )

        faculty_workload_rows = faculty_workload_query.group_by(Schedule.faculty_id).all()
        faculty_workload_map = {
            row.faculty_id: {
                'schedule_count': int(row.schedule_count or 0),
                'total_units': float(row.total_units or 0)
            }
            for row in faculty_workload_rows
            if row.faculty_id is not None
        }
    
    faculty_workload_list = []
    for faculty in faculties:
        workload = faculty_workload_map.get(faculty.id)
        if workload and workload['schedule_count'] > 0:  # Only include faculty with schedules
            faculty_workload_list.append({
                'full_name': faculty.full_name,
                'department_name': faculty.department.department_name if faculty.department else None,
                'schedule_count': workload['schedule_count'],
                'total_units': workload['total_units']
            })
    
    # Sort by schedule count and limit to top 5
    faculty_workload = sorted(faculty_workload_list, key=lambda x: x['schedule_count'], reverse=True)[:5]
    
    # Get recent activity logs (template renders up to 8)
    recent_activities = UserActivityLog.query.order_by(desc(UserActivityLog.created_at)).limit(8).all() if current_user.is_admin else []
    
    # Get user count (Admin only)
    user_count = User.query.filter_by(is_active=True).count() if current_user.is_admin else 0
    
    # Calculate schedule completion rate (sections with schedules vs total sections)
    sections_with_schedules = 0
    total_sections = section_count
    if total_sections > 0:
        sections_query = db.session.query(func.count(func.distinct(Schedule.section_id)))\
            .join(Section, Schedule.section_id == Section.id)\
            .filter(Schedule.is_active == True)

        if current_settings:
            sections_query = sections_query.filter(
                Schedule.academic_year == current_settings.academic_year,
                Schedule.semester == current_settings.semester
            )
        
        # Apply program filter for Deans
        if filter_program_ids:
            sections_query = sections_query.filter(Section.program_id.in_(filter_program_ids))
        
        sections_with_schedules = sections_query.scalar() or 0
    
    # Cap at 100% to handle edge cases
    schedule_completion_rate = min(100, round((sections_with_schedules / total_sections * 100) if total_sections > 0 else 0))
    
    # Get today's schedules count
    # Smart counting: lec+lab counts as 1 class ONLY if they are
    # chronologically adjacent (lecture end_time == lab start_time) AND same faculty.
    # Otherwise they count as separate classes.
    today = datetime.now().strftime('%A')  # Get day name like 'Monday'
    todays_query = Schedule.query.join(Section, Schedule.section_id == Section.id).filter(
        Schedule.is_active == True,
        Schedule.day_of_week == today
    )
    if current_settings:
        todays_query = todays_query.filter(
            Schedule.academic_year == current_settings.academic_year,
            Schedule.semester == current_settings.semester
        )
    if filter_program_ids:
        todays_query = todays_query.filter(Section.program_id.in_(filter_program_ids))
    todays_rows = todays_query.options(
        joinedload(Schedule.subject),
        joinedload(Schedule.room),
        joinedload(Schedule.section),
        joinedload(Schedule.faculty)
    ).order_by(Schedule.start_time, Schedule.section_id, Schedule.subject_id).all()
    
    todays_schedules, todays_remaining = _count_classes_smart(todays_rows)
    todays_schedule_overview = todays_rows
    
    # Get upcoming exams (next 7 days)
    today_date = datetime.now().date()
    week_later = today_date + timedelta(days=7)
    upcoming_exams_query = ExamSchedule.query.filter(
        ExamSchedule.is_active == True,
        ExamSchedule.exam_date >= today_date,
        ExamSchedule.exam_date <= week_later
    ).options(
        joinedload(ExamSchedule.subject),
        joinedload(ExamSchedule.section)
    )
    if filter_program_ids:
        upcoming_exams_query = upcoming_exams_query.join(ExamSchedule.section).filter(
            Section.program_id.in_(filter_program_ids)
        )
    upcoming_exams = upcoming_exams_query.order_by(
        ExamSchedule.exam_date,
        ExamSchedule.start_time
    ).limit(5).all()
    
    activity_filter_program_ids = [selected_department_id] if selected_department_id else (
        list(user_program_ids) if user_program_ids is not None else None
    )
    
    # Extract overloaded/warning counts for smart actions using one aggregated load query
    system_max_units = AcademicSettings.get_default_faculty_max_units()
    overloaded_faculty_count = 0
    warning_faculty_count = 0

    faculty_load_map = {}
    if faculty_ids:
        faculty_load_query = db.session.query(
            Schedule.faculty_id,
            func.coalesce(
                func.sum(
                    func.coalesce(Subject.lec_units, 0) + func.coalesce(Subject.lab_units, 0)
                ),
                0
            ).label('total_units')
        ).outerjoin(Subject, Subject.id == Schedule.subject_id).filter(
            Schedule.is_active == True,
            Schedule.faculty_id.in_(faculty_ids)
        )
        if current_settings:
            faculty_load_query = faculty_load_query.filter(
                Schedule.academic_year == current_settings.academic_year,
                Schedule.semester == current_settings.semester
            )
        faculty_load_rows = faculty_load_query.group_by(Schedule.faculty_id).all()
        faculty_load_map = {
            row.faculty_id: float(row.total_units or 0)
            for row in faculty_load_rows
            if row.faculty_id is not None
        }

    for fac in faculties:
        current_load = faculty_load_map.get(fac.id, 0)
        max_units = fac.max_units if fac.max_units is not None else system_max_units
        utilization_pct = (current_load / max_units * 100) if max_units > 0 else 0
        if utilization_pct >= 100:
            overloaded_faculty_count += 1
        elif utilization_pct >= 80:
            warning_faculty_count += 1
    
    # ============================================================
    # TIER 2: Smart Quick Actions (context-aware, max 4, priority-ordered)
    # ============================================================
    unscheduled_sections = section_count - sections_with_schedules
    smart_actions = generate_smart_actions(
        schedule_completion_rate=schedule_completion_rate,
        overloaded_faculty_count=overloaded_faculty_count,
        warning_faculty_count=warning_faculty_count,
        upcoming_exams=upcoming_exams,
        unscheduled_sections=unscheduled_sections
    )
    
    # ============================================================
    # C1: Stat Card Trends & Weekly Activity
    # ============================================================
    stat_trends = {}
    weekly_activity = []
    if current_settings:
        trend_data = get_stat_trends(
            current_settings.academic_year,
            current_settings.semester,
            activity_filter_program_ids
        )
        if trend_data:
            trend_data['schedule_trend'] = _calc_trend(schedule_count, trend_data['_prev_schedules'])
            trend_data['exam_trend'] = _calc_trend(exam_schedule_count, trend_data['_prev_exams'])
            stat_trends = trend_data
        weekly_activity = get_weekly_activity(activity_filter_program_ids)

    # Get next class happening today (for Today's Snapshot) from already-loaded rows
    next_class = None
    now_time = datetime.now().time()
    next_rows = [row for row in todays_rows if row.start_time and row.start_time > now_time]
    if next_rows:
        s = next_rows[0]
        next_class = {
            'subject': s.subject.subject_code if s.subject else 'N/A',
            'start_time': s.start_time.strftime('%I:%M %p') if s.start_time else '',
            'room': s.room.room_number if s.room else 'TBA'
        }
    
    return render_template('dashboard.html', 
                         user=current_user,
                         curriculum_count=curriculum_count,
                         department_count=department_count,
                         faculty_count=faculty_count,
                         building_count=building_count,
                         section_count=section_count,
                         room_count=room_count,
                         subject_count=subject_count,
                         schedule_count=schedule_count,
                         exam_schedule_count=exam_schedule_count,
                         todays_schedule_overview=todays_schedule_overview,
                         departments_overview=departments_overview,
                         faculty_workload=faculty_workload,
                         current_settings=current_settings,
                         available_departments=available_departments,
                         dashboard_scope_label=dashboard_scope_label,
                         program_count=system_program_count,
                         system_building_count=system_building_count,
                         system_room_count=system_room_count,
                         selected_department_id=selected_department_id,
                         recent_activities=recent_activities,
                         user_count=user_count,
                         schedule_completion_rate=schedule_completion_rate,
                         todays_schedules=todays_schedules,
                         todays_remaining=todays_remaining,
                         current_day_name=today,
                         smart_actions=smart_actions,
                         next_class=next_class,
                         overloaded_faculty_count=overloaded_faculty_count,
                         warning_faculty_count=warning_faculty_count,
                         faculty_with_schedules_count=len(faculty_workload_list),
                         stat_trends=stat_trends,
                         weekly_activity=weekly_activity)


@main_bp.route('/about')
def about():
    """About page"""
    return '<h1>About iSchedWise V4</h1><p>This is a Flask web application for scheduling management.</p>'
