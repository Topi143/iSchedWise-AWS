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
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, PieChart, Reference
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas as pdf_canvas
import io
import os

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
    
    # Auto-set filter for single-department users (non-admin)
    if not filter_department and user_department_ids is not None and len(user_department_ids) == 1:
        filter_department = user_department_ids[0]
    
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
        
        # Get department name for AI context
        department_name = None
        if filter_department:
            department = Department.query.get(filter_department)
            if department:
                department_name = f"{department.department_name} ({department.department_code})"
        
        # Generate AI summary with department context
        ai_summary = ai_scheduler.generate_report_summary(
            stats, 
            academic_year, 
            semester,
            department_name
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
    
    # Active sections - apply both user department access AND filter_department
    section_query = Section.query.filter_by(is_active=True)
    if filter_department:
        section_query = section_query.filter(Section.department_id == filter_department)
    elif user_department_ids is not None:
        section_query = section_query.filter(Section.department_id.in_(user_department_ids))
    stats['total_sections'] = section_query.count()
    
    # Active faculty - apply both user department access AND filter_department
    faculty_query = Faculty.query.filter_by(is_active=True, is_archived=False)
    if filter_department:
        faculty_query = faculty_query.filter(Faculty.department_id == filter_department)
    elif user_department_ids is not None:
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


# ============================================================================
# EXCEL EXPORT WITH ISO 25010 COMPLIANCE
# ============================================================================

@reports_bp.route('/export/excel')
@login_required
def export_excel():
    """Export reports to Excel with ISO 25010 compliant formatting"""
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if current_settings:
            academic_year = current_settings.academic_year
            semester = current_settings.semester
            exam_period = current_settings.exam_period
        else:
            academic_year = "N/A"
            semester = "N/A"
            exam_period = "N/A"
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Get filter parameters
        filter_department = request.args.get('department', type=int)
        
        # Calculate statistics
        stats = calculate_statistics(
            academic_year if academic_year != "N/A" else None,
            semester if semester != "N/A" else None,
            user_department_ids,
            filter_department
        )
        
        # Get department name for header
        department_name = "All Departments"
        if filter_department:
            department = Department.query.get(filter_department)
            if department:
                department_name = f"{department.department_name} ({department.department_code})"
        
        # Create workbook
        wb = Workbook()
        
        # Create Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        create_summary_sheet(ws_summary, stats, academic_year, semester, exam_period, department_name)
        
        # Create Faculty Workload Sheet
        ws_faculty = wb.create_sheet("Faculty Workload")
        create_faculty_workload_sheet(ws_faculty, stats, academic_year, semester, department_name)
        
        # Create Room Utilization Sheet
        ws_rooms = wb.create_sheet("Room Utilization")
        create_room_utilization_sheet(ws_rooms, stats, academic_year, semester, department_name)
        
        # Create Weekly Distribution Sheet
        ws_weekly = wb.create_sheet("Weekly Distribution")
        create_weekly_distribution_sheet(ws_weekly, stats, academic_year, semester, department_name)
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Generate filename
        filename = f"Reports_{academic_year}_{semester}"
        if filter_department:
            dept = Department.query.get(filter_department)
            if dept:
                filename += f"_{dept.department_code}"
        filename += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error exporting Excel: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def create_summary_sheet(ws, stats, academic_year, semester, exam_period, department_name):
    """Create summary sheet with overview statistics and charts"""
    # Set column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 15
    
    # Header styles
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1F4788', end_color='1F4788', fill_type='solid')
    title_font = Font(name='Arial', size=14, bold=True, color='1F4788')
    subtitle_font = Font(name='Arial', size=10, color='666666')
    
    # Simple header matching PDF style
    ws['A1'] = 'Republic of the Philippines'
    ws['A1'].font = Font(name='Arial', size=10, bold=True)
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A1:D1')
    
    ws['A2'] = 'Municipality of Norzagaray'
    ws['A2'].font = Font(name='Arial', size=9)
    ws['A2'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A2:D2')
    
    ws['A3'] = 'NORZAGARAY COLLEGE'
    ws['A3'].font = title_font
    ws['A3'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A3:D3')
    ws.row_dimensions[3].height = 25
    
    ws['A4'] = 'COMPUTER STUDIES'
    ws['A4'].font = Font(name='Arial', size=11, bold=True)
    ws['A4'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A4:D4')
    
    # Period Info
    ws['A5'] = f'AY {academic_year} - {semester}'
    ws['A5'].font = subtitle_font
    ws['A5'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A5:D5')
    
    ws['A6'] = f'Department: {department_name}'
    ws['A6'].font = subtitle_font
    ws['A6'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A6:D6')
    
    ws['A7'] = f'Generated: {datetime.now().strftime("%B %d, %Y")}'
    ws['A7'].font = Font(name='Arial', size=9, italic=True, color='999999')
    ws['A7'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A7:D7')
    
    # Add spacing
    ws.row_dimensions[8].height = 5
    
    # Overview Statistics Header
    current_row = 9
    ws[f'A{current_row}'] = 'OVERVIEW STATISTICS'
    ws[f'A{current_row}'].font = header_font
    ws[f'A{current_row}'].fill = header_fill
    ws[f'A{current_row}'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells(f'A{current_row}:D{current_row}')
    ws.row_dimensions[current_row].height = 25
    
    # Data styles
    label_font = Font(name='Arial', size=10, bold=True)
    value_font = Font(name='Arial', size=11)
    border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    # Statistics data with better organization
    current_row += 1
    stats_data = [
        ('Class Schedules', stats.get('total_schedules', 0)),
        ('Exam Schedules', stats.get('total_exam_schedules', 0)),
        ('Active Faculty', stats.get('total_faculty', 0)),
        ('Active Sections', stats.get('total_sections', 0)),
        ('Total Rooms', stats.get('total_rooms', 0)),
        ('Rooms in Use', stats.get('rooms_in_use', 0)),
        ('Faculty with Schedules', stats.get('faculty_with_schedules', 0)),
        ('Lecture Classes', stats.get('lecture_count', 0)),
        ('Lab Classes', stats.get('lab_count', 0)),
    ]
    
    for i, (label, value) in enumerate(stats_data):
        row = current_row + i
        col_offset = 0 if i % 2 == 0 else 2
        
        ws[f'{get_column_letter(col_offset + 1)}{row}'] = label
        ws[f'{get_column_letter(col_offset + 1)}{row}'].font = label_font
        ws[f'{get_column_letter(col_offset + 1)}{row}'].border = border
        ws[f'{get_column_letter(col_offset + 1)}{row}'].alignment = Alignment(horizontal='left', vertical='center')
        
        ws[f'{get_column_letter(col_offset + 2)}{row}'] = value
        ws[f'{get_column_letter(col_offset + 2)}{row}'].font = value_font
        ws[f'{get_column_letter(col_offset + 2)}{row}'].border = border
        ws[f'{get_column_letter(col_offset + 2)}{row}'].alignment = Alignment(horizontal='center', vertical='center')
        
        # Alternate row colors
        if i % 2 == 0:
            ws[f'{get_column_letter(col_offset + 1)}{row}'].fill = PatternFill(start_color='F8F9FA', end_color='F8F9FA', fill_type='solid')
            ws[f'{get_column_letter(col_offset + 2)}{row}'].fill = PatternFill(start_color='F8F9FA', end_color='F8F9FA', fill_type='solid')
        
        if i % 2 == 1:
            current_row += 1
    
    if len(stats_data) % 2 == 1:
        current_row += 1


def create_faculty_workload_sheet(ws, stats, academic_year, semester, department_name):
    """Create faculty workload details sheet"""
    # Set column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 35
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 12
    
    # Simple header matching PDF style
    ws['A1'] = 'NORZAGARAY COLLEGE'
    ws['A1'].font = Font(name='Arial', size=12, bold=True, color='1F4788')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A1:G1')
    
    ws['A2'] = 'FACULTY WORKLOAD REPORT'
    ws['A2'].font = Font(name='Arial', size=14, bold=True)
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A2:G2')
    
    ws['A3'] = f'AY {academic_year} - {semester} | {department_name}'
    ws['A3'].font = Font(name='Arial', size=10, italic=True, color='666666')
    ws['A3'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A3:G3')
    
    ws['A4'] = f'Generated: {datetime.now().strftime("%B %d, %Y")}'
    ws['A4'].font = Font(name='Arial', size=9, italic=True, color='999999')
    ws['A4'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A4:G4')
    
    # Column headers with better styling
    current_row = 6
    headers = ['#', 'Faculty Name', 'Department', 'Schedules', 'Lec Units', 'Lab Units', 'Total Units']
    header_font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1F4788', end_color='1F4788', fill_type='solid')
    
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=current_row, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
    
    # Data rows with improved styling
    faculty_workloads = stats.get('faculty_workloads', [])
    current_row += 1
    
    # Define colors for top performers
    gold_fill = PatternFill(start_color='FFD700', end_color='FFD700', fill_type='solid')
    silver_fill = PatternFill(start_color='C0C0C0', end_color='C0C0C0', fill_type='solid')
    bronze_fill = PatternFill(start_color='CD7F32', end_color='CD7F32', fill_type='solid')
    
    for idx, faculty in enumerate(faculty_workloads, start=1):
        ws.cell(row=current_row, column=1, value=idx)
        ws.cell(row=current_row, column=2, value=faculty['name'])
        ws.cell(row=current_row, column=3, value=faculty['department'])
        ws.cell(row=current_row, column=4, value=faculty['schedules'])
        ws.cell(row=current_row, column=5, value=faculty['lec_units'])
        ws.cell(row=current_row, column=6, value=faculty['lab_units'])
        ws.cell(row=current_row, column=7, value=faculty['total_units'])
        
        # Apply styles
        for col_idx in range(1, 8):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.alignment = Alignment(horizontal='center' if col_idx != 2 else 'left', vertical='center')
            cell.border = Border(
                left=Side(style='thin', color='CCCCCC'),
                right=Side(style='thin', color='CCCCCC'),
                top=Side(style='thin', color='CCCCCC'),
                bottom=Side(style='thin', color='CCCCCC')
            )
            
            # Highlight top 3 performers
            if idx == 1:
                cell.fill = gold_fill
                cell.font = Font(name='Arial', size=10, bold=True)
            elif idx == 2:
                cell.fill = silver_fill
                cell.font = Font(name='Arial', size=10, bold=True)
            elif idx == 3:
                cell.fill = bronze_fill
                cell.font = Font(name='Arial', size=10, bold=True)
            elif idx % 2 == 0:
                cell.fill = PatternFill(start_color='F8F9FA', end_color='F8F9FA', fill_type='solid')
        
        ws.row_dimensions[current_row].height = 22
        current_row += 1
    
    # Add chart if data exists
    if len(faculty_workloads) > 0:
        # Create bar chart for top 15 faculty
        chart = BarChart()
        chart.title = "Top 15 Faculty by Total Units"
        chart.type = "bar"  # Horizontal bars
        chart.style = 10
        chart.x_axis.title = 'Total Units'
        chart.y_axis.title = 'Faculty'
        
        # Limit to top 15 for chart readability
        chart_data_rows = min(15, len(faculty_workloads))
        data_ref = Reference(ws, min_col=7, min_row=6, max_row=6 + chart_data_rows)
        cats_ref = Reference(ws, min_col=2, min_row=7, max_row=6 + chart_data_rows)
        
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.height = 12
        chart.width = 20
        
        ws.add_chart(chart, f'A{current_row + 2}')


def create_room_utilization_sheet(ws, stats, academic_year, semester, department_name):
    """Create room utilization details sheet"""
    # Set column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 15
    
    # Simple header matching PDF style
    ws['A1'] = 'NORZAGARAY COLLEGE'
    ws['A1'].font = Font(name='Arial', size=12, bold=True, color='1F4788')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A1:G1')
    
    ws['A2'] = 'ROOM UTILIZATION REPORT'
    ws['A2'].font = Font(name='Arial', size=14, bold=True)
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A2:G2')
    
    ws['A3'] = f'AY {academic_year} - {semester} | {department_name}'
    ws['A3'].font = Font(name='Arial', size=10, italic=True, color='666666')
    ws['A3'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A3:G3')
    
    ws['A4'] = f'Generated: {datetime.now().strftime("%B %d, %Y")}'
    ws['A4'].font = Font(name='Arial', size=9, italic=True, color='999999')
    ws['A4'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A4:G4')
    
    # Column headers with better styling
    current_row = 6
    headers = ['#', 'Room', 'Building', 'Classes', 'Exams', 'Total Usage', 'Status']
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1F4788', end_color='1F4788', fill_type='solid')
    
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=current_row, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
    
    ws.row_dimensions[current_row].height = 30
    
    # Data rows with improved styling
    room_utilizations = stats.get('room_utilizations', [])
    current_row += 1
    
    # Define status colors
    high_usage_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')  # Light green
    medium_usage_fill = PatternFill(start_color='FFE5B4', end_color='FFE5B4', fill_type='solid')  # Peach
    low_usage_fill = PatternFill(start_color='FFB6C1', end_color='FFB6C1', fill_type='solid')  # Light pink
    
    for idx, room in enumerate(room_utilizations, start=1):
        ws.cell(row=current_row, column=1, value=idx)
        ws.cell(row=current_row, column=2, value=room['room'])
        ws.cell(row=current_row, column=3, value=room['building'])
        ws.cell(row=current_row, column=4, value=room['schedules'])
        ws.cell(row=current_row, column=5, value=room['exams'])
        ws.cell(row=current_row, column=6, value=room['total_usage'])
        
        # Determine status and color
        total_usage = room['total_usage']
        if total_usage >= 10:
            status = 'High Use'
            status_fill = high_usage_fill
        elif total_usage >= 5:
            status = 'Medium Use'
            status_fill = medium_usage_fill
        elif total_usage > 0:
            status = 'Low Use'
            status_fill = low_usage_fill
        else:
            status = 'Unused'
            status_fill = PatternFill(start_color='E8E8E8', end_color='E8E8E8', fill_type='solid')
        
        ws.cell(row=current_row, column=7, value=status)
        
        # Apply styles
        for col_idx in range(1, 8):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = Border(
                left=Side(style='thin', color='CCCCCC'),
                right=Side(style='thin', color='CCCCCC'),
                top=Side(style='thin', color='CCCCCC'),
                bottom=Side(style='thin', color='CCCCCC')
            )
            
            # Color code the status column
            if col_idx == 7:
                cell.fill = status_fill
                cell.font = Font(name='Arial', size=10, bold=True)
            elif idx % 2 == 0:
                cell.fill = PatternFill(start_color='F8F9FA', end_color='F8F9FA', fill_type='solid')
        
        ws.row_dimensions[current_row].height = 22
        current_row += 1
    
    # Add chart if data exists
    if len(room_utilizations) > 0:
        # Create bar chart for top 15 rooms
        chart = BarChart()
        chart.title = "Top 15 Rooms by Usage"
        chart.type = "bar"  # Horizontal bars
        chart.style = 10
        chart.x_axis.title = 'Total Usage'
        chart.y_axis.title = 'Room'
        
        # Limit to top 15
        chart_data_rows = min(15, len(room_utilizations))
        data_ref = Reference(ws, min_col=6, min_row=6, max_row=6 + chart_data_rows)
        cats_ref = Reference(ws, min_col=2, min_row=7, max_row=6 + chart_data_rows)
        
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.height = 12
        chart.width = 20
        
        ws.add_chart(chart, f'A{current_row + 2}')


def create_weekly_distribution_sheet(ws, stats, academic_year, semester, department_name):
    """Create weekly schedule distribution sheet"""
    # Set column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 5  # Spacing
    ws.column_dimensions['D'].width = 18
    
    # Simple header matching PDF style
    ws['A1'] = 'NORZAGARAY COLLEGE'
    ws['A1'].font = Font(name='Arial', size=12, bold=True, color='1F4788')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A1:D1')
    
    ws['A2'] = 'WEEKLY SCHEDULE DISTRIBUTION'
    ws['A2'].font = Font(name='Arial', size=14, bold=True)
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A2:D2')
    
    ws['A3'] = f'AY {academic_year} - {semester} | {department_name}'
    ws['A3'].font = Font(name='Arial', size=10, italic=True, color='666666')
    ws['A3'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A3:D3')
    
    ws['A4'] = f'Generated: {datetime.now().strftime("%B %d, %Y")}'
    ws['A4'].font = Font(name='Arial', size=9, italic=True, color='999999')
    ws['A4'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A4:D4')
    
    # Column headers with better styling
    current_row = 6
    headers = ['Day', 'Schedule Count']
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1F4788', end_color='1F4788', fill_type='solid')
    
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=current_row, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
    
    ws.row_dimensions[current_row].height = 30
    
    # Data rows with improved styling
    schedule_by_day = stats.get('schedule_by_day', {})
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    current_row += 1
    
    # Define day colors (different shade for each day)
    day_colors = {
        'Monday': 'E3F2FD',     # Light blue
        'Tuesday': 'F3E5F5',    # Light purple
        'Wednesday': 'E8F5E9',  # Light green
        'Thursday': 'FFF3E0',   # Light orange
        'Friday': 'FCE4EC',     # Light pink
        'Saturday': 'F5F5F5'    # Light gray
    }
    
    total_schedules = sum(schedule_by_day.values())
    
    for idx, day in enumerate(day_order, start=1):
        count = schedule_by_day.get(day, 0)
        percentage = (count / total_schedules * 100) if total_schedules > 0 else 0
        
        ws.cell(row=current_row, column=1, value=day)
        ws.cell(row=current_row, column=2, value=count)
        
        # Add percentage in column D
        ws.cell(row=current_row, column=4, value=f'{percentage:.1f}%')
        ws.cell(row=current_row, column=4).alignment = Alignment(horizontal='center')
        ws.cell(row=current_row, column=4).font = Font(name='Arial', size=10, italic=True, color='666666')
        
        # Apply styles
        for col_idx in [1, 2]:
            cell = ws.cell(row=current_row, column=col_idx)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = Border(
                left=Side(style='thin', color='CCCCCC'),
                right=Side(style='thin', color='CCCCCC'),
                top=Side(style='thin', color='CCCCCC'),
                bottom=Side(style='thin', color='CCCCCC')
            )
            cell.fill = PatternFill(start_color=day_colors[day], end_color=day_colors[day], fill_type='solid')
            cell.font = Font(name='Arial', size=11, bold=True if col_idx == 2 else False)
        
        ws.row_dimensions[current_row].height = 25
        current_row += 1


# ============================================================================
# PDF EXPORT WITH ISO 25010 COMPLIANCE
# ============================================================================

def create_pdf_header(academic_year, semester, program_name):
    """Create PDF header with logos and institution info matching the image format"""
    
    # Get paths to logos
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    images_dir = os.path.join(base_dir, 'static', 'images')
    
    logo_left_path = os.path.join(images_dir, 'norzagaray-college-logo.png')
    logo_right_path = os.path.join(images_dir, 'bagong-pilipinas.png')
    
    # Create header data with 3 columns: [Left Logo | Center Text | Right Logo]
    header_data = []
    
    # First row: Logos and institution info
    left_logo = None
    right_logo = None
    
    try:
        if os.path.exists(logo_left_path):
            left_logo = RLImage(logo_left_path, width=0.8*inch, height=0.8*inch)
    except:
        pass
    
    try:
        if os.path.exists(logo_right_path):
            right_logo = RLImage(logo_right_path, width=0.8*inch, height=0.8*inch)
    except:
        pass
    
    # Center text with institution info
    center_text = Paragraph(
        '<para align="center">'
        '<font size="10"><b>Republic of the Philippines</b></font><br/>'
        '<font size="9">Municipality of Norzagaray</font><br/>'
        '<font size="11"><b>NORZAGARAY COLLEGE</b></font><br/>'
        '<font size="10"><b>{}</b></font>'
        '</para>'.format(program_name),
        ParagraphStyle(
            'HeaderCenter',
            alignment=TA_CENTER,
            fontSize=10,
            leading=12
        )
    )
    
    # Build header row
    if left_logo and right_logo:
        header_data.append([left_logo, center_text, right_logo])
    elif left_logo:
        header_data.append([left_logo, center_text, ''])
    elif right_logo:
        header_data.append(['', center_text, right_logo])
    else:
        header_data.append(['', center_text, ''])
    
    # Create table
    header_table = Table(header_data, colWidths=[1*inch, 6*inch, 1*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -1), 1, rl_colors.black),
    ]))
    
    return header_table


@reports_bp.route('/export/pdf')
@login_required
def export_pdf():
    """Export reports to PDF with ISO 25010 compliant formatting"""
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if current_settings:
            academic_year = current_settings.academic_year
            semester = current_settings.semester
            exam_period = current_settings.exam_period
        else:
            academic_year = "N/A"
            semester = "N/A"
            exam_period = "N/A"
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Get filter parameters
        filter_department = request.args.get('department', type=int)
        
        # Calculate statistics
        stats = calculate_statistics(
            academic_year if academic_year != "N/A" else None,
            semester if semester != "N/A" else None,
            user_department_ids,
            filter_department
        )
        
        # Get department name and program
        department_name = "All Departments"
        program_name = "COMPUTER STUDIES"
        if filter_department:
            department = Department.query.get(filter_department)
            if department:
                department_name = f"{department.department_name} ({department.department_code})"
                program_name = department.department_name.upper()
        
        # Create PDF with A4 size in portrait
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1.2*inch,  # More space for header with logos
            bottomMargin=0.5*inch
        )
        
        # Build PDF content
        elements = []
        
        # Add header with logos
        header_table = create_pdf_header(academic_year, semester, program_name)
        elements.append(header_table)
        
        styles = getSampleStyleSheet()
        
        # Custom styles - ISO 25010: Usability (clear typography)
        report_title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=rl_colors.black,
            spaceAfter=8,
            spaceBefore=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=rl_colors.HexColor('#333333'),
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=rl_colors.HexColor('#1F4788'),
            spaceAfter=6,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        )
        
        # Report title and period info
        elements.append(Paragraph('REPORTS & ANALYTICS', report_title_style))
        elements.append(Paragraph(
            f'{semester.upper()}, AY {academic_year}',
            subtitle_style
        ))
        if department_name != "All Departments":
            elements.append(Paragraph(f'{department_name}', subtitle_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Overview Statistics - adjusted for A4 portrait
        elements.append(Paragraph('OVERVIEW STATISTICS', heading_style))
        
        # Calculate available width for A4 portrait (210mm - margins = ~7.27 inches usable)
        available_width = 7.27*inch
        col_width = available_width / 4  # 4 columns
        
        stats_data = [
            ['Metric', 'Value', 'Metric', 'Value'],
            ['Class Schedules', str(stats.get('total_schedules', 0)), 
             'Exam Schedules', str(stats.get('total_exam_schedules', 0))],
            ['Active Faculty', str(stats.get('total_faculty', 0)), 
             'Active Sections', str(stats.get('total_sections', 0))],
            ['Total Rooms', str(stats.get('total_rooms', 0)), 
             'Rooms in Use', str(stats.get('rooms_in_use', 0))],
            ['Faculty with Schedules', str(stats.get('faculty_with_schedules', 0)), 
             'Lecture Classes', str(stats.get('lecture_count', 0))],
            ['Lab Classes', str(stats.get('lab_count', 0)), '', ''],
        ]
        
        stats_table = Table(stats_data, colWidths=[col_width*1.3, col_width*0.7, col_width*1.3, col_width*0.7])
        stats_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1F4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), rl_colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F8F9FA')]),
        ]))
        
        elements.append(stats_table)
        elements.append(Spacer(1, 0.1*inch))
        
        # Faculty Workload (Top 15) - adjusted for A4 portrait
        elements.append(Paragraph('FACULTY WORKLOAD', heading_style))
        
        faculty_data = [['#', 'Faculty Name', 'Department', 'Schedules', 'Lec', 'Lab', 'Total']]
        faculty_workloads = stats.get('faculty_workloads', [])  # Show all faculty
        
        for idx, faculty in enumerate(faculty_workloads, start=1):
            # Truncate long names to fit table
            faculty_name = faculty['name'][:28] if len(faculty['name']) > 28 else faculty['name']
            dept_code = faculty['department'][:8] if len(faculty['department']) > 8 else faculty['department']
            
            faculty_data.append([
                str(idx),
                faculty_name,
                dept_code,
                str(faculty['schedules']),
                f"{faculty['lec_units']:.1f}",
                f"{faculty['lab_units']:.1f}",
                f"{faculty['total_units']:.1f}"
            ])
        
        if len(faculty_workloads) > 0:
            # Calculate column widths for A4 portrait (~7.27 inches usable)
            faculty_table = Table(faculty_data, colWidths=[0.3*inch, 2.8*inch, 1*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.7*inch])
            faculty_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1F4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                
                ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.black),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F8F9FA')]),
            ]))
            elements.append(faculty_table)
        else:
            elements.append(Paragraph('No faculty workload data available.', styles['Normal']))
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Room Utilization (Top 15) - adjusted for A4 portrait
        elements.append(Paragraph('ROOM UTILIZATION', heading_style))
        
        room_data = [['#', 'Room', 'Building', 'Classes', 'Exams', 'Total', 'Status']]
        room_utilizations = stats.get('room_utilizations', [])  # Show all rooms
        
        for idx, room in enumerate(room_utilizations, start=1):
            building_name = room['building'][:15] if len(room['building']) > 15 else room['building']
            room_data.append([
                str(idx),
                room['room'],
                building_name,
                str(room['schedules']),
                str(room['exams']),
                str(room['total_usage']),
                'In Use' if room['total_usage'] > 0 else 'Available'
            ])
        
        if len(room_utilizations) > 0:
            # Calculate column widths for A4 portrait - total ~7.27 inches
            room_table = Table(room_data, colWidths=[0.3*inch, 0.9*inch, 1.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.9*inch])
            room_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1F4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                
                ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F8F9FA')]),
            ]))
            elements.append(room_table)
        else:
            elements.append(Paragraph('No room utilization data available.', styles['Normal']))
        
        elements.append(Spacer(1, 0.1*inch))
        
        # Weekly Distribution - adjusted for A4 portrait
        elements.append(Paragraph('WEEKLY SCHEDULE DISTRIBUTION', heading_style))
        
        schedule_by_day = stats.get('schedule_by_day', {})
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        weekly_data = [['Day', 'Schedule Count']]
        for day in day_order:
            count = schedule_by_day.get(day, 0)
            weekly_data.append([day, str(count)])
        
        if len(schedule_by_day) > 0:
            # Center the table on page with balanced column widths for portrait
            weekly_table = Table(weekly_data, colWidths=[2*inch, 1.5*inch])
            weekly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1F4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F8F9FA')]),
            ]))
            elements.append(weekly_table)
        else:
            elements.append(Paragraph('No weekly distribution data available.', styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        buffer.seek(0)
        
        # Generate filename
        filename = f"Reports_{academic_year}_{semester}"
        if filter_department:
            dept = Department.query.get(filter_department)
            if dept:
                filename += f"_{dept.department_code}"
        filename += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error exporting PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
