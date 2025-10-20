"""
Main routes (index, dashboard, about)
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from app.extensions import db
from app.models.curriculum import Curriculum, Subject
from app.models.department import Department, Section
from app.models.faculty import Faculty
from app.models.building import Building, Room
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.settings import AcademicSettings
from app.models.archive import Archive

main_bp = Blueprint('main', __name__)


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
    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    # Get user's department access
    user_department_ids = current_user.get_department_ids()
    
    # Build department filter query
    if user_department_ids is None:
        # Admin - see all departments
        dept_query = Department.query.filter_by(is_active=True)
        curriculum_query = Curriculum.query.filter_by(is_active=True)
        section_query = Section.query.filter_by(is_active=True)
        faculty_query = Faculty.query.filter_by(is_active=True)
    else:
        # Dean - filter by assigned departments
        dept_query = Department.query.filter(
            Department.is_active == True,
            Department.id.in_(user_department_ids)
        )
        curriculum_query = Curriculum.query.filter(
            Curriculum.is_active == True,
            Curriculum.department_id.in_(user_department_ids)
        )
        section_query = Section.query.filter(
            Section.is_active == True,
            Section.department_id.in_(user_department_ids)
        )
        faculty_query = Faculty.query.filter(
            Faculty.is_active == True,
            Faculty.department_id.in_(user_department_ids)
        )
    
    # Get counts for dashboard stats
    curriculum_count = curriculum_query.count()
    department_count = dept_query.count()
    faculty_count = faculty_query.count()
    building_count = Building.query.filter_by(is_active=True).count()
    
    # Additional statistics
    section_count = section_query.count()
    room_count = Room.query.filter_by(is_available=True).count()
    
    # Subject count - handle filtering differently
    if user_department_ids is None:
        subject_count = Subject.query.count()
    else:
        from app.models.curriculum import Semester, YearLevel
        subject_count = db.session.query(Subject).join(Semester).join(YearLevel).join(Curriculum)\
            .filter(Curriculum.department_id.in_(user_department_ids))\
            .count()
    
    # Schedule statistics (for current academic year/semester if available)
    schedule_query = Schedule.query.filter_by(is_active=True)\
        .join(Schedule.section)
    
    if user_department_ids:
        schedule_query = schedule_query.filter(Section.department_id.in_(user_department_ids))
    
    if current_settings:
        schedule_query = schedule_query.filter(
            Schedule.academic_year == current_settings.academic_year,
            Schedule.semester == current_settings.semester
        )
    
    schedule_count = schedule_query.count()
    
    # Exam schedule statistics
    exam_query = ExamSchedule.query.filter_by(is_active=True)\
        .join(ExamSchedule.section)
    
    if user_department_ids:
        exam_query = exam_query.filter(Section.department_id.in_(user_department_ids))
    
    if current_settings:
        exam_query = exam_query.filter(
            ExamSchedule.academic_year == current_settings.academic_year,
            ExamSchedule.semester == current_settings.semester
        )
    
    exam_schedule_count = exam_query.count()
    
    # Recent activity - get last 5 schedules created
    recent_query = Schedule.query.filter_by(is_active=True)\
        .join(Schedule.section)
    
    if user_department_ids:
        recent_query = recent_query.filter(Section.department_id.in_(user_department_ids))
    
    recent_schedules = recent_query.order_by(desc(Schedule.created_at)).limit(5).all()
    
    # Get departments with their curriculum count for quick overview
    departments_overview = []
    departments = dept_query.order_by(Department.department_name).all()
    for dept in departments:
        dept_curriculum_count = Curriculum.query.filter_by(department_id=dept.id, is_active=True).count()
        dept_section_count = Section.query.filter_by(department_id=dept.id, is_active=True).count()
        dept_faculty_count = Faculty.query.filter_by(department_id=dept.id, is_active=True).count()
        
        departments_overview.append({
            'name': dept.department_name,
            'code': dept.department_code,
            'curriculum_count': dept_curriculum_count,
            'section_count': dept_section_count,
            'faculty_count': dept_faculty_count
        })
    
    # Faculty workload overview (top 5 with most schedules)
    faculties = faculty_query.all()
    
    faculty_workload_list = []
    for faculty in faculties:
        schedules = Schedule.query.filter_by(
            faculty_id=faculty.id, 
            is_active=True
        ).all()
        
        if schedules:  # Only include faculty with schedules
            schedule_count = len(schedules)
            total_units = sum([schedule.subject.total_units for schedule in schedules if schedule.subject])
            
            faculty_workload_list.append({
                'full_name': faculty.full_name,
                'department_name': faculty.department.department_name if faculty.department else None,
                'schedule_count': schedule_count,
                'total_units': total_units
            })
    
    # Sort by schedule count and limit to top 5
    faculty_workload = sorted(faculty_workload_list, key=lambda x: x['schedule_count'], reverse=True)[:5]
    
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
                         recent_schedules=recent_schedules,
                         departments_overview=departments_overview,
                         faculty_workload=faculty_workload,
                         current_settings=current_settings)


@main_bp.route('/about')
def about():
    """About page"""
    return '<h1>About iSchedWise V4</h1><p>This is a Flask web application for scheduling management.</p>'
