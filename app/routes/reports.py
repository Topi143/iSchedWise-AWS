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


@reports_bp.route('/export/summary')
@login_required
def export_summary():
    """Export comprehensive report to Excel with multiple sheets"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, PieChart, Reference
    
    try:
        # Get current settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        user_department_ids = current_user.get_department_ids()
        
        # Get statistics
        stats = calculate_statistics(
            current_settings.academic_year if current_settings else None,
            current_settings.semester if current_settings else None,
            user_department_ids
        )
        
        # Create workbook
        wb = Workbook()
        
        # ===== SHEET 1: SUMMARY =====
        ws_summary = wb.active
        ws_summary.title = "Summary"
        
        # Title
        title = "iSchedWise - Comprehensive Report"
        if current_settings:
            title += f"\n{current_settings.academic_year} - {current_settings.semester}"
        
        ws_summary['A1'] = title
        ws_summary['A1'].font = Font(bold=True, size=18, color='FFFFFF')
        ws_summary['A1'].fill = PatternFill(start_color='7C3AED', end_color='7C3AED', fill_type='solid')
        ws_summary['A1'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws_summary.merge_cells('A1:D1')
        ws_summary.row_dimensions[1].height = 50
        
        # Generated timestamp
        ws_summary['A2'] = f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        ws_summary['A2'].font = Font(italic=True, size=10, color='666666')
        ws_summary['A2'].alignment = Alignment(horizontal='center')
        ws_summary.merge_cells('A2:D2')
        
        # Section headers style
        section_header_fill = PatternFill(start_color='9333EA', end_color='9333EA', fill_type='solid')
        section_header_font = Font(bold=True, color='FFFFFF', size=12)
        
        # Overview Statistics
        ws_summary['A4'] = 'OVERVIEW STATISTICS'
        ws_summary['A4'].fill = section_header_fill
        ws_summary['A4'].font = section_header_font
        ws_summary['A4'].alignment = Alignment(horizontal='center', vertical='center')
        ws_summary.merge_cells('A4:D4')
        ws_summary.row_dimensions[4].height = 25
        
        # Headers
        headers = ['Category', 'Count', 'Percentage', 'Status']
        for col, header in enumerate(headers, start=1):
            cell = ws_summary.cell(row=5, column=col)
            cell.value = header
            cell.fill = PatternFill(start_color='A855F7', end_color='A855F7', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data with alternating colors
        row = 6
        total_schedules = stats['total_schedules'] + stats['total_exam_schedules']
        
        overview_data = [
            ('Total Class Schedules', stats['total_schedules'], 
             f"{(stats['total_schedules']/total_schedules*100):.1f}%" if total_schedules > 0 else "0%", 
             '✓ Active'),
            ('Total Exam Schedules', stats['total_exam_schedules'], 
             f"{(stats['total_exam_schedules']/total_schedules*100):.1f}%" if total_schedules > 0 else "0%", 
             '✓ Active'),
            ('Lecture Schedules', stats['lecture_count'], 
             f"{(stats['lecture_count']/stats['total_schedules']*100):.1f}%" if stats['total_schedules'] > 0 else "0%", 
             '✓ Active'),
            ('Laboratory Schedules', stats['lab_count'], 
             f"{(stats['lab_count']/stats['total_schedules']*100):.1f}%" if stats['total_schedules'] > 0 else "0%", 
             '✓ Active'),
            ('Active Sections', stats['total_sections'], '-', '✓ Active'),
            ('Active Faculty', stats['total_faculty'], '-', '✓ Active'),
            ('Faculty with Schedules', stats['faculty_with_schedules'], 
             f"{(stats['faculty_with_schedules']/stats['total_faculty']*100):.1f}%" if stats['total_faculty'] > 0 else "0%", 
             '✓ Engaged'),
            ('Available Rooms', stats['total_rooms'], '-', '✓ Available'),
            ('Rooms in Use', stats['rooms_in_use'], 
             f"{(stats['rooms_in_use']/stats['total_rooms']*100):.1f}%" if stats['total_rooms'] > 0 else "0%", 
             '✓ In Use'),
        ]
        
        for idx, (category, count, percentage, status) in enumerate(overview_data):
            ws_summary[f'A{row}'] = category
            ws_summary[f'B{row}'] = count
            ws_summary[f'C{row}'] = percentage
            ws_summary[f'D{row}'] = status
            
            # Alternating row colors
            fill_color = 'F3E8FF' if idx % 2 == 0 else 'FFFFFF'
            for col in range(1, 5):
                cell = ws_summary.cell(row=row, column=col)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='center' if col > 1 else 'left', vertical='center')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_summary.column_dimensions['A'].width = 30
        ws_summary.column_dimensions['B'].width = 15
        ws_summary.column_dimensions['C'].width = 15
        ws_summary.column_dimensions['D'].width = 15
        
        # ===== SHEET 2: FACULTY WORKLOAD =====
        ws_faculty = wb.create_sheet("Faculty Workload")
        
        # Title
        ws_faculty['A1'] = "Faculty Workload Report"
        ws_faculty['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws_faculty['A1'].fill = PatternFill(start_color='16A34A', end_color='16A34A', fill_type='solid')
        ws_faculty['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_faculty.merge_cells('A1:G1')
        ws_faculty.row_dimensions[1].height = 35
        
        # Headers
        faculty_headers = ['#', 'Faculty Name', 'Department', 'Schedules', 'Lec Units', 'Lab Units', 'Total Units']
        for col, header in enumerate(faculty_headers, start=1):
            cell = ws_faculty.cell(row=3, column=col)
            cell.value = header
            cell.fill = PatternFill(start_color='22C55E', end_color='22C55E', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data
        row = 4
        for idx, faculty in enumerate(stats['faculty_workloads'], start=1):
            ws_faculty[f'A{row}'] = idx
            ws_faculty[f'B{row}'] = faculty['name']
            ws_faculty[f'C{row}'] = faculty['department']
            ws_faculty[f'D{row}'] = faculty['schedules']
            ws_faculty[f'E{row}'] = faculty['lec_units']
            ws_faculty[f'F{row}'] = faculty['lab_units']
            ws_faculty[f'G{row}'] = faculty['total_units']
            
            # Conditional formatting - highlight high workload
            fill_color = 'FEF3C7' if faculty['total_units'] >= 18 else ('FFFFFF' if idx % 2 == 0 else 'F0FDF4')
            for col in range(1, 8):
                cell = ws_faculty.cell(row=row, column=col)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='center' if col != 2 else 'left', vertical='center')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_faculty.column_dimensions['A'].width = 8
        ws_faculty.column_dimensions['B'].width = 35
        ws_faculty.column_dimensions['C'].width = 15
        ws_faculty.column_dimensions['D'].width = 12
        ws_faculty.column_dimensions['E'].width = 12
        ws_faculty.column_dimensions['F'].width = 12
        ws_faculty.column_dimensions['G'].width = 12
        
        # ===== SHEET 3: ROOM UTILIZATION =====
        ws_rooms = wb.create_sheet("Room Utilization")
        
        # Title
        ws_rooms['A1'] = "Room Utilization Report"
        ws_rooms['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws_rooms['A1'].fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
        ws_rooms['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_rooms.merge_cells('A1:F1')
        ws_rooms.row_dimensions[1].height = 35
        
        # Headers
        room_headers = ['#', 'Room', 'Building', 'Class Schedules', 'Exam Schedules', 'Total Usage']
        for col, header in enumerate(room_headers, start=1):
            cell = ws_rooms.cell(row=3, column=col)
            cell.value = header
            cell.fill = PatternFill(start_color='3B82F6', end_color='3B82F6', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data
        row = 4
        for idx, room in enumerate(stats['room_utilizations'], start=1):
            ws_rooms[f'A{row}'] = idx
            ws_rooms[f'B{row}'] = room['room']
            ws_rooms[f'C{row}'] = room['building']
            ws_rooms[f'D{row}'] = room['schedules']
            ws_rooms[f'E{row}'] = room['exams']
            ws_rooms[f'F{row}'] = room['total_usage']
            
            # Conditional formatting - highlight heavily used rooms
            fill_color = 'FEF3C7' if room['total_usage'] >= 15 else ('FFFFFF' if idx % 2 == 0 else 'EFF6FF')
            for col in range(1, 7):
                cell = ws_rooms.cell(row=row, column=col)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='center' if col > 2 else 'left', vertical='center')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_rooms.column_dimensions['A'].width = 8
        ws_rooms.column_dimensions['B'].width = 20
        ws_rooms.column_dimensions['C'].width = 25
        ws_rooms.column_dimensions['D'].width = 18
        ws_rooms.column_dimensions['E'].width = 18
        ws_rooms.column_dimensions['F'].width = 15
        
        # ===== SHEET 4: WEEKLY DISTRIBUTION =====
        ws_weekly = wb.create_sheet("Weekly Distribution")
        
        # Title
        ws_weekly['A1'] = "Weekly Schedule Distribution"
        ws_weekly['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws_weekly['A1'].fill = PatternFill(start_color='DC2626', end_color='DC2626', fill_type='solid')
        ws_weekly['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_weekly.merge_cells('A1:C1')
        ws_weekly.row_dimensions[1].height = 35
        
        # Headers
        ws_weekly['A3'] = 'Day of Week'
        ws_weekly['B3'] = 'Schedules'
        ws_weekly['C3'] = 'Percentage'
        for col in range(1, 4):
            cell = ws_weekly.cell(row=3, column=col)
            cell.fill = PatternFill(start_color='EF4444', end_color='EF4444', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data
        row = 4
        for idx, (day, count) in enumerate(stats['schedule_by_day'].items()):
            ws_weekly[f'A{row}'] = day
            ws_weekly[f'B{row}'] = count
            ws_weekly[f'C{row}'] = f"{(count/stats['total_schedules']*100):.1f}%" if stats['total_schedules'] > 0 else "0%"
            
            fill_color = 'FFFFFF' if idx % 2 == 0 else 'FEE2E2'
            for col in range(1, 4):
                cell = ws_weekly.cell(row=row, column=col)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='center' if col > 1 else 'left', vertical='center')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_weekly.column_dimensions['A'].width = 20
        ws_weekly.column_dimensions['B'].width = 15
        ws_weekly.column_dimensions['C'].width = 15
        
        # ===== SHEET 5: DETAILED SCHEDULE BREAKDOWN =====
        ws_detailed = wb.create_sheet("Schedule Breakdown")
        
        # Title
        ws_detailed['A1'] = "Detailed Schedule Breakdown"
        ws_detailed['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws_detailed['A1'].fill = PatternFill(start_color='8B5CF6', end_color='8B5CF6', fill_type='solid')
        ws_detailed['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_detailed.merge_cells('A1:H1')
        ws_detailed.row_dimensions[1].height = 35
        
        # Get all schedules for detailed breakdown
        detailed_query = Schedule.query.filter_by(is_active=True)
        if current_settings:
            detailed_query = detailed_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        if user_department_ids is not None:
            detailed_query = detailed_query.join(Schedule.section).filter(Section.department_id.in_(user_department_ids))
        
        schedules = detailed_query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Headers
        schedule_headers = ['#', 'Section', 'Subject', 'Faculty', 'Room', 'Day', 'Time', 'Type']
        for col, header in enumerate(schedule_headers, start=1):
            cell = ws_detailed.cell(row=3, column=col)
            cell.value = header
            cell.fill = PatternFill(start_color='A78BFA', end_color='A78BFA', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data
        row = 4
        for idx, schedule in enumerate(schedules, start=1):
            ws_detailed[f'A{row}'] = idx
            ws_detailed[f'B{row}'] = schedule.section.section_name if schedule.section else 'N/A'
            ws_detailed[f'C{row}'] = f"{schedule.subject.subject_code} - {schedule.subject.course_description[:30]}..." if schedule.subject else 'N/A'
            ws_detailed[f'D{row}'] = schedule.faculty.full_name if schedule.faculty else 'TBA'
            ws_detailed[f'E{row}'] = f"{schedule.room.room_number}" if schedule.room else 'TBA'
            ws_detailed[f'F{row}'] = schedule.day_of_week
            ws_detailed[f'G{row}'] = f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}" if schedule.start_time and schedule.end_time else 'TBA'
            ws_detailed[f'H{row}'] = schedule.schedule_type.upper()
            
            # Alternating colors
            fill_color = 'FFFFFF' if idx % 2 == 0 else 'F3E8FF'
            for col in range(1, 9):
                cell = ws_detailed.cell(row=row, column=col)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='center' if col in [1, 6, 8] else 'left', vertical='center')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_detailed.column_dimensions['A'].width = 8
        ws_detailed.column_dimensions['B'].width = 20
        ws_detailed.column_dimensions['C'].width = 40
        ws_detailed.column_dimensions['D'].width = 25
        ws_detailed.column_dimensions['E'].width = 15
        ws_detailed.column_dimensions['F'].width = 12
        ws_detailed.column_dimensions['G'].width = 20
        ws_detailed.column_dimensions['H'].width = 12
        
        # ===== SHEET 6: EXAM SCHEDULES =====
        ws_exams = wb.create_sheet("Exam Schedules")
        
        # Title
        ws_exams['A1'] = "Examination Schedules"
        ws_exams['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws_exams['A1'].fill = PatternFill(start_color='F59E0B', end_color='F59E0B', fill_type='solid')
        ws_exams['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_exams.merge_cells('A1:G1')
        ws_exams.row_dimensions[1].height = 35
        
        # Get all exam schedules
        exam_query = ExamSchedule.query.filter_by(is_active=True)
        if current_settings:
            exam_query = exam_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        if user_department_ids is not None:
            exam_query = exam_query.join(ExamSchedule.section).filter(Section.department_id.in_(user_department_ids))
        
        exams = exam_query.order_by(ExamSchedule.exam_date, ExamSchedule.start_time).all()
        
        # Headers
        exam_headers = ['#', 'Section', 'Subject', 'Room', 'Date', 'Time', 'Period']
        for col, header in enumerate(exam_headers, start=1):
            cell = ws_exams.cell(row=3, column=col)
            cell.value = header
            cell.fill = PatternFill(start_color='FBBF24', end_color='FBBF24', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data
        row = 4
        for idx, exam in enumerate(exams, start=1):
            ws_exams[f'A{row}'] = idx
            ws_exams[f'B{row}'] = exam.section.section_name if exam.section else 'N/A'
            ws_exams[f'C{row}'] = f"{exam.subject.subject_code} - {exam.subject.course_description[:30]}..." if exam.subject else 'N/A'
            ws_exams[f'D{row}'] = f"{exam.room.room_number}" if exam.room else 'TBA'
            ws_exams[f'E{row}'] = exam.exam_date.strftime('%B %d, %Y') if exam.exam_date else 'TBA'
            ws_exams[f'F{row}'] = f"{exam.start_time.strftime('%I:%M %p')} - {exam.end_time.strftime('%I:%M %p')}" if exam.start_time and exam.end_time else 'TBA'
            ws_exams[f'G{row}'] = exam.exam_period if exam.exam_period else 'N/A'
            
            # Alternating colors
            fill_color = 'FFFFFF' if idx % 2 == 0 else 'FEF3C7'
            for col in range(1, 8):
                cell = ws_exams.cell(row=row, column=col)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='center' if col in [1, 5, 7] else 'left', vertical='center')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_exams.column_dimensions['A'].width = 8
        ws_exams.column_dimensions['B'].width = 20
        ws_exams.column_dimensions['C'].width = 40
        ws_exams.column_dimensions['D'].width = 15
        ws_exams.column_dimensions['E'].width = 18
        ws_exams.column_dimensions['F'].width = 20
        ws_exams.column_dimensions['G'].width = 12
        
        # ===== SHEET 7: DEPARTMENT ANALYSIS =====
        ws_dept = wb.create_sheet("Department Analysis")
        
        # Title
        ws_dept['A1'] = "Department-wise Analysis"
        ws_dept['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws_dept['A1'].fill = PatternFill(start_color='10B981', end_color='10B981', fill_type='solid')
        ws_dept['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_dept.merge_cells('A1:F1')
        ws_dept.row_dimensions[1].height = 35
        
        # Get department statistics
        dept_query = Department.query.filter_by(is_active=True)
        if user_department_ids is not None:
            dept_query = dept_query.filter(Department.id.in_(user_department_ids))
        departments = dept_query.order_by(Department.department_code).all()
        
        # Headers
        dept_headers = ['#', 'Department', 'Code', 'Sections', 'Faculty', 'Schedules']
        for col, header in enumerate(dept_headers, start=1):
            cell = ws_dept.cell(row=3, column=col)
            cell.value = header
            cell.fill = PatternFill(start_color='34D399', end_color='34D399', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data
        row = 4
        for idx, dept in enumerate(departments, start=1):
            # Count sections
            sections_count = Section.query.filter_by(department_id=dept.id, is_active=True).count()
            
            # Count faculty
            faculty_count = Faculty.query.filter_by(department_id=dept.id, is_active=True, is_archived=False).count()
            
            # Count schedules
            dept_schedules = Schedule.query.join(Schedule.section).filter(
                Section.department_id == dept.id,
                Schedule.is_active == True
            )
            if current_settings:
                dept_schedules = dept_schedules.filter(
                    Schedule.academic_year == current_settings.academic_year,
                    Schedule.semester == current_settings.semester
                )
            schedules_count = dept_schedules.count()
            
            ws_dept[f'A{row}'] = idx
            ws_dept[f'B{row}'] = dept.department_name
            ws_dept[f'C{row}'] = dept.department_code
            ws_dept[f'D{row}'] = sections_count
            ws_dept[f'E{row}'] = faculty_count
            ws_dept[f'F{row}'] = schedules_count
            
            # Alternating colors
            fill_color = 'FFFFFF' if idx % 2 == 0 else 'D1FAE5'
            for col in range(1, 7):
                cell = ws_dept.cell(row=row, column=col)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='center' if col in [1, 3, 4, 5, 6] else 'left', vertical='center')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_dept.column_dimensions['A'].width = 8
        ws_dept.column_dimensions['B'].width = 35
        ws_dept.column_dimensions['C'].width = 12
        ws_dept.column_dimensions['D'].width = 12
        ws_dept.column_dimensions['E'].width = 12
        ws_dept.column_dimensions['F'].width = 12
        
        # ===== SHEET 8: RESOURCE SUMMARY =====
        ws_resource = wb.create_sheet("Resource Summary")
        
        # Title
        ws_resource['A1'] = "Resource Utilization Summary"
        ws_resource['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws_resource['A1'].fill = PatternFill(start_color='EC4899', end_color='EC4899', fill_type='solid')
        ws_resource['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_resource.merge_cells('A1:D1')
        ws_resource.row_dimensions[1].height = 35
        
        # Section 1: Room Status
        ws_resource['A3'] = 'ROOM STATUS'
        ws_resource['A3'].fill = PatternFill(start_color='F472B6', end_color='F472B6', fill_type='solid')
        ws_resource['A3'].font = Font(bold=True, color='FFFFFF', size=12)
        ws_resource['A3'].alignment = Alignment(horizontal='center')
        ws_resource.merge_cells('A3:D3')
        
        ws_resource['A4'] = 'Category'
        ws_resource['B4'] = 'Count'
        ws_resource['C4'] = 'Percentage'
        ws_resource['D4'] = 'Status'
        for col in range(1, 5):
            cell = ws_resource.cell(row=4, column=col)
            cell.fill = PatternFill(start_color='FBCFE8', end_color='FBCFE8', fill_type='solid')
            cell.font = Font(bold=True, size=11)
            cell.alignment = Alignment(horizontal='center')
        
        room_data = [
            ('Total Rooms', stats['total_rooms'], '100%', '✓ Available'),
            ('Rooms in Use', stats['rooms_in_use'], 
             f"{(stats['rooms_in_use']/stats['total_rooms']*100):.1f}%" if stats['total_rooms'] > 0 else "0%", 
             '✓ Active'),
            ('Rooms Unused', stats['total_rooms'] - stats['rooms_in_use'], 
             f"{((stats['total_rooms']-stats['rooms_in_use'])/stats['total_rooms']*100):.1f}%" if stats['total_rooms'] > 0 else "0%", 
             '◯ Available'),
        ]
        
        row = 5
        for category, count, percentage, status in room_data:
            ws_resource[f'A{row}'] = category
            ws_resource[f'B{row}'] = count
            ws_resource[f'C{row}'] = percentage
            ws_resource[f'D{row}'] = status
            
            for col in range(1, 5):
                cell = ws_resource.cell(row=row, column=col)
                cell.alignment = Alignment(horizontal='center' if col > 1 else 'left')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Section 2: Faculty Engagement
        row += 1
        ws_resource[f'A{row}'] = 'FACULTY ENGAGEMENT'
        ws_resource[f'A{row}'].fill = PatternFill(start_color='F472B6', end_color='F472B6', fill_type='solid')
        ws_resource[f'A{row}'].font = Font(bold=True, color='FFFFFF', size=12)
        ws_resource[f'A{row}'].alignment = Alignment(horizontal='center')
        ws_resource.merge_cells(f'A{row}:D{row}')
        
        row += 1
        for col in range(1, 5):
            cell = ws_resource.cell(row=row, column=col)
            cell.value = ['Category', 'Count', 'Percentage', 'Status'][col-1]
            cell.fill = PatternFill(start_color='FBCFE8', end_color='FBCFE8', fill_type='solid')
            cell.font = Font(bold=True, size=11)
            cell.alignment = Alignment(horizontal='center')
        
        faculty_data = [
            ('Total Faculty', stats['total_faculty'], '100%', '✓ Active'),
            ('Faculty with Schedules', stats['faculty_with_schedules'], 
             f"{(stats['faculty_with_schedules']/stats['total_faculty']*100):.1f}%" if stats['total_faculty'] > 0 else "0%", 
             '✓ Engaged'),
            ('Faculty without Schedules', stats['total_faculty'] - stats['faculty_with_schedules'], 
             f"{((stats['total_faculty']-stats['faculty_with_schedules'])/stats['total_faculty']*100):.1f}%" if stats['total_faculty'] > 0 else "0%", 
             '◯ Available'),
        ]
        
        row += 1
        for category, count, percentage, status in faculty_data:
            ws_resource[f'A{row}'] = category
            ws_resource[f'B{row}'] = count
            ws_resource[f'C{row}'] = percentage
            ws_resource[f'D{row}'] = status
            
            for col in range(1, 5):
                cell = ws_resource.cell(row=row, column=col)
                cell.alignment = Alignment(horizontal='center' if col > 1 else 'left')
                cell.border = Border(
                    left=Side(style='thin', color='D1D5DB'),
                    right=Side(style='thin', color='D1D5DB'),
                    top=Side(style='thin', color='D1D5DB'),
                    bottom=Side(style='thin', color='D1D5DB')
                )
            row += 1
        
        # Column widths
        ws_resource.column_dimensions['A'].width = 30
        ws_resource.column_dimensions['B'].width = 15
        ws_resource.column_dimensions['C'].width = 15
        ws_resource.column_dimensions['D'].width = 15
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"iSchedWise_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        from flask import flash, redirect, url_for
        flash(f'Error exporting report: {str(e)}', 'error')
        return redirect(url_for('reports.index'))


@reports_bp.route('/export/faculty-workload')
@login_required
def export_faculty_workload():
    """Export faculty workload report to Excel"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    try:
        # Get current settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        user_department_ids = current_user.get_department_ids()
        
        # Get faculty with schedules
        faculty_query = Faculty.query.filter_by(is_active=True, is_archived=False)
        if user_department_ids is not None:
            faculty_query = faculty_query.filter(Faculty.department_id.in_(user_department_ids))
        
        faculty_list = faculty_query.order_by(Faculty.last_name, Faculty.first_name).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Faculty Workload"
        
        # Title
        title = "Faculty Workload Report"
        if current_settings:
            title += f" ({current_settings.academic_year} - {current_settings.semester})"
        
        ws['A1'] = title
        ws['A1'].font = Font(bold=True, size=16, color='FFFFFF')
        ws['A1'].fill = PatternFill(start_color='16A34A', end_color='16A34A', fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A1:F1')
        ws.row_dimensions[1].height = 35
        
        # Headers
        headers = ['Faculty Name', 'Department', 'Total Schedules', 'Lecture', 'Lab', 'Total Units']
        header_fill = PatternFill(start_color='22C55E', end_color='22C55E', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Data
        row = 4
        for faculty in faculty_list:
            # Get schedules for this faculty
            schedule_query = Schedule.query.filter_by(
                faculty_id=faculty.id,
                is_active=True
            )
            
            if current_settings:
                schedule_query = schedule_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            
            schedules = schedule_query.all()
            total_schedules = len(schedules)
            lecture_count = len([s for s in schedules if s.schedule_type == 'lecture'])
            lab_count = len([s for s in schedules if s.schedule_type == 'lab'])
            
            # Calculate total units
            total_units = sum([s.subject.units if s.subject else 0 for s in schedules])
            
            # Write data
            ws[f'A{row}'] = faculty.full_name
            ws[f'B{row}'] = faculty.department.department_code if faculty.department else 'N/A'
            ws[f'C{row}'] = total_schedules
            ws[f'D{row}'] = lecture_count
            ws[f'E{row}'] = lab_count
            ws[f'F{row}'] = total_units
            
            # Center align numeric columns
            for col in ['C', 'D', 'E', 'F']:
                ws[f'{col}{row}'].alignment = Alignment(horizontal='center')
            
            row += 1
        
        # Column widths
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 15
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Faculty_Workload_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        from flask import flash, redirect, url_for
        flash(f'Error exporting faculty workload: {str(e)}', 'error')
        return redirect(url_for('reports.index'))
