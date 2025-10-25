"""
Reports Routes
Handles report generation and statistics
"""
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, and_, or_
from datetime import datetime, time, timedelta
from app.extensions import db
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.faculty import Faculty, FacultySubjectAssignment
from app.models.curriculum import Subject
from app.models.building import Room, Building
from app.models.department import Department, Section
from app.models.settings import AcademicSettings
from app.models.activity_log import UserActivityLog
from app.models.user import User
from app.decorators import role_required
from app.ai_scheduler import ai_scheduler
import io

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    """Display reports dashboard with statistics"""
    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    if current_settings:
        academic_year = current_settings.academic_year
        semester = current_settings.semester
        exam_period = current_settings.exam_period
    else:
        academic_year = None
        semester = None
        exam_period = None
    
    # Get user's department access
    user_department_ids = current_user.get_department_ids()
    
    # Get filter parameters from request
    filter_department = request.args.get('department', type=int)
    
    # Calculate statistics with filters
    stats = calculate_statistics(
        academic_year, 
        semester, 
        user_department_ids,
        filter_department
    )
    
    # Get departments for filter
    if user_department_ids is None:
        departments = Department.query.filter_by(is_active=True).order_by(Department.department_code).all()
    else:
        departments = Department.query.filter(
            Department.is_active == True,
            Department.id.in_(user_department_ids)
        ).order_by(Department.department_code).all()
    
    return render_template(
        'reports.html',
        stats=stats,
        academic_year=academic_year,
        semester=semester,
        exam_period=exam_period,
        departments=departments,
        filter_department=filter_department
    )


@reports_bp.route('/api/filtered-data')
@login_required
def get_filtered_data():
    """Get filtered statistics data as JSON for AJAX updates"""
    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    if current_settings:
        academic_year = current_settings.academic_year
        semester = current_settings.semester
    else:
        academic_year = None
        semester = None
    
    # Get user's department access
    user_department_ids = current_user.get_department_ids()
    
    # Get filter parameters from request
    filter_department = request.args.get('department', type=int)
    
    # Calculate statistics with filters
    stats = calculate_statistics(
        academic_year, 
        semester, 
        user_department_ids,
        filter_department
    )
    
    return jsonify({'stats': stats})


@reports_bp.route('/api/ai-summary')
@login_required
def get_ai_summary():
    """Generate AI summary of current report statistics"""
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if current_settings:
            academic_year = current_settings.academic_year
            semester = current_settings.semester
        else:
            academic_year = None
            semester = None
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Get filter parameters from request
        filter_department = request.args.get('department', type=int)
        
        # Calculate statistics with filters
        stats = calculate_statistics(
            academic_year, 
            semester, 
            user_department_ids,
            filter_department
        )
        
        # Generate AI summary
        ai_summary = ai_scheduler.generate_report_summary(
            stats, 
            academic_year, 
            semester
        )
        
        return jsonify(ai_summary)
        
    except Exception as e:
        print(f"Error generating AI summary: {str(e)}")
        return jsonify({
            'ai_enabled': False,
            'error': str(e),
            'summary': 'Unable to generate AI summary at this time.',
            'insights': [],
            'recommendations': []
        }), 500


def calculate_statistics(academic_year=None, semester=None, user_department_ids=None, 
                        filter_department=None):
    """Calculate various statistics for the dashboard"""
    stats = {}
    
    # Build base queries
    schedule_query = Schedule.query.filter_by(is_active=True)
    exam_query = ExamSchedule.query.filter_by(is_active=True)
    
    if academic_year:
        schedule_query = schedule_query.filter_by(academic_year=academic_year)
        exam_query = exam_query.filter_by(academic_year=academic_year)
    
    if semester:
        schedule_query = schedule_query.filter_by(semester=semester)
        exam_query = exam_query.filter_by(semester=semester)
    
    # Track if we've already joined Section
    schedule_has_section_join = False
    exam_has_section_join = False
    
    # Filter by user department access
    if user_department_ids is not None:
        schedule_query = schedule_query.join(Section)
        exam_query = exam_query.join(Section)
        schedule_query = schedule_query.filter(Section.department_id.in_(user_department_ids))
        exam_query = exam_query.filter(Section.department_id.in_(user_department_ids))
        schedule_has_section_join = True
        exam_has_section_join = True
    
    # Apply additional filters
    if filter_department:
        if not schedule_has_section_join:
            schedule_query = schedule_query.join(Section)
            schedule_has_section_join = True
        schedule_query = schedule_query.filter(Section.department_id == filter_department)
        
        if not exam_has_section_join:
            exam_query = exam_query.join(Section)
            exam_has_section_join = True
        exam_query = exam_query.filter(Section.department_id == filter_department)
    
    # Total schedules
    stats['total_schedules'] = schedule_query.count()
    stats['total_exam_schedules'] = exam_query.count()
    
    # Active sections
    section_query = Section.query.filter_by(is_active=True)
    if user_department_ids is not None:
        section_query = section_query.filter(Section.department_id.in_(user_department_ids))
    stats['total_sections'] = section_query.count()
    
    # Active faculty
    faculty_query = Faculty.query.filter_by(is_active=True, is_archived=False)
    if user_department_ids is not None:
        faculty_query = faculty_query.filter(Faculty.department_id.in_(user_department_ids))
    stats['total_faculty'] = faculty_query.count()
    
    # Available rooms
    stats['total_rooms'] = Room.query.filter_by(is_available=True).count()
    
    # Faculty with schedules
    faculty_with_schedules = schedule_query.filter(Schedule.faculty_id.isnot(None))\
        .with_entities(Schedule.faculty_id).distinct().count()
    stats['faculty_with_schedules'] = faculty_with_schedules
    
    # Rooms being used
    rooms_in_use = schedule_query.filter(Schedule.room_id.isnot(None))\
        .with_entities(Schedule.room_id).distinct().count()
    stats['rooms_in_use'] = rooms_in_use
    
    # Schedule type distribution
    lecture_count = schedule_query.filter(Schedule.schedule_type == 'lecture').count()
    lab_count = schedule_query.filter(Schedule.schedule_type == 'lab').count()
    stats['lecture_count'] = lecture_count
    stats['lab_count'] = lab_count
    
    # Day distribution
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    stats['schedule_by_day'] = {}
    for day in days:
        stats['schedule_by_day'][day] = schedule_query.filter(Schedule.day_of_week == day).count()
    
    # Faculty workload details - ALL faculty with schedules
    faculty_list = faculty_query.order_by(Faculty.full_name).all()
    faculty_workloads = []
    for faculty in faculty_list:
        # Build a fresh query for this faculty's schedules with same filters
        faculty_schedule_query = Schedule.query.filter_by(is_active=True, faculty_id=faculty.id)
        
        if academic_year:
            faculty_schedule_query = faculty_schedule_query.filter_by(academic_year=academic_year)
        if semester:
            faculty_schedule_query = faculty_schedule_query.filter_by(semester=semester)
        
        # Apply department filter if specified
        if filter_department or user_department_ids is not None:
            faculty_schedule_query = faculty_schedule_query.join(Section)
            if filter_department:
                faculty_schedule_query = faculty_schedule_query.filter(Section.department_id == filter_department)
            elif user_department_ids is not None:
                faculty_schedule_query = faculty_schedule_query.filter(Section.department_id.in_(user_department_ids))
        
        fac_schedules = faculty_schedule_query.all()
        # Include ALL faculty, even those with no schedules
        total_units = sum([s.subject.total_units if s.subject else 0 for s in fac_schedules])
        lec_units = sum([s.subject.lec_units if s.subject else 0 for s in fac_schedules])
        lab_units = sum([s.subject.lab_units if s.subject else 0 for s in fac_schedules])
        faculty_workloads.append({
            'name': faculty.full_name,
            'department': faculty.department.department_code if faculty.department else 'N/A',
            'schedules': len(fac_schedules),
            'lec_units': float(lec_units),
            'lab_units': float(lab_units),
            'total_units': float(total_units)
        })
    # Sort by total units descending - show ALL faculty (no limit)
    stats['faculty_workloads'] = sorted(faculty_workloads, key=lambda x: x['total_units'], reverse=True)
    
    # Room utilization details - ALL rooms
    rooms = Room.query.filter_by(is_available=True).all()
    room_utilizations = []
    for room in rooms:
        # Build fresh queries for this room's usage with same filters
        room_schedule_query = Schedule.query.filter_by(is_active=True, room_id=room.id)
        room_exam_query = ExamSchedule.query.filter_by(is_active=True, room_id=room.id)
        
        if academic_year:
            room_schedule_query = room_schedule_query.filter_by(academic_year=academic_year)
            room_exam_query = room_exam_query.filter_by(academic_year=academic_year)
        if semester:
            room_schedule_query = room_schedule_query.filter_by(semester=semester)
            room_exam_query = room_exam_query.filter_by(semester=semester)
        
        # Apply department filter if specified
        if filter_department or user_department_ids is not None:
            room_schedule_query = room_schedule_query.join(Section)
            room_exam_query = room_exam_query.join(Section)
            if filter_department:
                room_schedule_query = room_schedule_query.filter(Section.department_id == filter_department)
                room_exam_query = room_exam_query.filter(Section.department_id == filter_department)
            elif user_department_ids is not None:
                room_schedule_query = room_schedule_query.filter(Section.department_id.in_(user_department_ids))
                room_exam_query = room_exam_query.filter(Section.department_id.in_(user_department_ids))
        
        room_schedules = room_schedule_query.all()
        room_exams = room_exam_query.all()
        total_usage = len(room_schedules) + len(room_exams)
        # Include ALL rooms, even those with zero usage
        room_utilizations.append({
            'room': room.room_number,
            'building': room.building.building_name if room.building else 'N/A',
            'schedules': len(room_schedules),
            'exams': len(room_exams),
            'total_usage': total_usage,
            'is_available': room.is_available
        })
    # Sort by total usage descending - show ALL rooms (no limit)
    stats['room_utilizations'] = sorted(room_utilizations, key=lambda x: x['total_usage'], reverse=True)
    
    return stats


@reports_bp.route('/api/user-activity')
@login_required
@role_required('admin')
def get_user_activity():
    """Get user activity logs (admin only)"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Get filter parameters - handle empty strings as None
        filter_user = request.args.get('user_id', type=int)
        filter_action = request.args.get('action', type=str)
        filter_entity = request.args.get('entity_type', type=str)
        
        # Convert empty strings to None
        if filter_action == '':
            filter_action = None
        if filter_entity == '':
            filter_entity = None
        
        # Build query
        query = UserActivityLog.query
        
        # Apply filters
        if filter_user:
            query = query.filter_by(user_id=filter_user)
        if filter_action:
            query = query.filter_by(action=filter_action)
        if filter_entity:
            query = query.filter_by(entity_type=filter_entity)
        
        # Order by most recent first
        query = query.order_by(UserActivityLog.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Convert to dict
        logs = [log.to_dict() for log in pagination.items]
        
        # Get unique users, actions, and entity types for filters
        all_users = User.query.order_by(User.full_name).all()
        all_actions = db.session.query(UserActivityLog.action).distinct().all()
        all_entities = db.session.query(UserActivityLog.entity_type).distinct().all()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            },
            'filters': {
                'users': [{'id': u.id, 'name': u.full_name, 'role': u.role} for u in all_users],
                'actions': [a[0] for a in all_actions],
                'entities': [e[0] for e in all_entities]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching user activity: {str(e)}'
        }), 500


@reports_bp.route('/api/user-activity/stats')
@login_required
@role_required('admin')
def get_user_activity_stats():
    """Get user activity statistics (admin only)"""
    try:
        # Total actions
        total_actions = UserActivityLog.query.count()
        
        # Actions by type
        actions_by_type = db.session.query(
            UserActivityLog.action,
            func.count(UserActivityLog.id)
        ).group_by(UserActivityLog.action).all()
        
        # Actions by entity type
        actions_by_entity = db.session.query(
            UserActivityLog.entity_type,
            func.count(UserActivityLog.id)
        ).group_by(UserActivityLog.entity_type).all()
        
        # Most active users (top 10)
        most_active_users = db.session.query(
            User.full_name,
            User.role,
            func.count(UserActivityLog.id).label('action_count')
        ).join(UserActivityLog, UserActivityLog.user_id == User.id)\
         .group_by(User.id)\
         .order_by(func.count(UserActivityLog.id).desc())\
         .limit(10).all()
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_actions = UserActivityLog.query.filter(
            UserActivityLog.created_at >= yesterday
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_actions': total_actions,
                'recent_actions_24h': recent_actions,
                'actions_by_type': [{'action': a[0], 'count': a[1]} for a in actions_by_type],
                'actions_by_entity': [{'entity': e[0], 'count': e[1]} for e in actions_by_entity],
                'most_active_users': [
                    {'name': u[0], 'role': u[1], 'actions': u[2]} 
                    for u in most_active_users
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching activity stats: {str(e)}'
        }), 500
