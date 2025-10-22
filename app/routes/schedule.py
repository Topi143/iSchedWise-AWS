"""
Schedule routes for managing class schedules
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from datetime import datetime, time, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io

from app.extensions import db, csrf
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.department import Department, Section
from app.models.curriculum import Subject
from app.models.faculty import Faculty, FacultySubjectAssignment
from app.models.building import Room
from app.models.settings import AcademicSettings
from app.models.user import User
from app.models.activity_log import UserActivityLog
from app.decorators import role_required

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')


# ============================================================================
# HELPER FUNCTIONS FOR EXCEL EXPORT
# ============================================================================

def add_institution_logos(ws):
    """Add institution logos to the worksheet if they exist"""
    try:
        from openpyxl.drawing.image import Image as ExcelImage
        import os
        from flask import current_app
        from PIL import Image, ImageDraw, ImageFont
        
        # Get absolute path to static/images directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        images_dir = os.path.join(base_dir, 'static', 'images')
        
        # Path to logos in static/images (use correct filenames)
        logo_left_path = os.path.join(images_dir, 'norzagaray-college-logo.png')
        logo_right_path = os.path.join(images_dir, 'bagong-pilipinas.png')
        
        # Debug: Print paths to verify
        print(f"[LOGO DEBUG] Left logo path: {logo_left_path}")
        print(f"[LOGO DEBUG] Left logo exists: {os.path.exists(logo_left_path)}")
        print(f"[LOGO DEBUG] Right logo path: {logo_right_path}")
        print(f"[LOGO DEBUG] Right logo exists: {os.path.exists(logo_right_path)}")
        
        # Add left logo (Norzagaray College) in cell A1
        if os.path.exists(logo_left_path):
            img_left = ExcelImage(logo_left_path)
            img_left.width = 100
            img_left.height = 100
            ws.add_image(img_left, 'A1')
            print(f"[LOGO DEBUG] Left logo added successfully")
        else:
            print(f"[LOGO DEBUG] Left logo file not found at: {logo_left_path}")
        
        # Add right logo (Bagong Pilipinas) in cell G1
        if os.path.exists(logo_right_path):
            img_right = ExcelImage(logo_right_path)
            img_right.width = 100
            img_right.height = 100
            ws.add_image(img_right, 'G1')
            print(f"[LOGO DEBUG] Right logo added successfully")
        else:
            # Create placeholder image for Bagong Pilipinas
            print(f"[LOGO DEBUG] Creating placeholder for Bagong Pilipinas logo")
            try:
                import io as img_io
                # Create a 100x100 placeholder image
                placeholder = Image.new('RGB', (100, 100), color='white')
                draw = ImageDraw.Draw(placeholder)
                
                # Draw a border
                draw.rectangle([(0, 0), (99, 99)], outline='#1e40af', width=2)
                
                # Add text
                try:
                    # Try to use a default font, fallback to basic if not available
                    font = ImageFont.truetype("arial.ttf", 10)
                except:
                    font = ImageFont.load_default()
                
                text = "Bagong\nPilipinas"
                draw.text((50, 50), text, fill='#1e40af', font=font, anchor='mm', align='center')
                
                # Save to BytesIO
                img_buffer = img_io.BytesIO()
                placeholder.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                # Add to worksheet
                img_right = ExcelImage(img_buffer)
                img_right.width = 100
                img_right.height = 100
                ws.add_image(img_right, 'G1')
                print(f"[LOGO DEBUG] Placeholder image created and added successfully")
            except Exception as placeholder_error:
                print(f"[LOGO DEBUG] Could not create placeholder: {str(placeholder_error)}")
            
    except Exception as e:
        # Log error for debugging
        print(f"[LOGO ERROR] Error adding logos: {str(e)}")
        import traceback
        traceback.print_exc()
        pass  # Continue without logos if not found


def add_institution_logos_for_posting(ws):
    """Add institution logos for posting exports - centered with table layout"""
    try:
        from openpyxl.drawing.image import Image as ExcelImage
        import os
        from PIL import Image, ImageDraw, ImageFont
        
        # Get absolute path to static/images directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        images_dir = os.path.join(base_dir, 'static', 'images')
        
        # Path to left logo
        logo_left_path = os.path.join(images_dir, 'norzagaray-college-logo.png')
        
        # Add left logo (Norzagaray College) in cell B1 - centered with table
        if os.path.exists(logo_left_path):
            img_left = ExcelImage(logo_left_path)
            img_left.width = 100
            img_left.height = 100
            ws.add_image(img_left, 'B1')
            print(f"[LOGO DEBUG] Left logo added for posting export (centered)")
        
        # Always create placeholder for right side (no Bagong Pilipinas logo)
        try:
            import io as img_io
            # Create a 100x100 placeholder image
            placeholder = Image.new('RGB', (100, 100), color='white')
            draw = ImageDraw.Draw(placeholder)
            
            # Draw a border
            draw.rectangle([(0, 0), (99, 99)], outline='#d1d5db', width=2)
            
            # Add text
            try:
                font = ImageFont.truetype("arial.ttf", 9)
            except:
                font = ImageFont.load_default()
            
            text = "Logo\nPlaceholder"
            draw.text((50, 50), text, fill='#9ca3af', font=font, anchor='mm', align='center')
            
            # Save to BytesIO
            img_buffer = img_io.BytesIO()
            placeholder.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Add to worksheet in column G - centered with table
            img_right = ExcelImage(img_buffer)
            img_right.width = 100
            img_right.height = 100
            ws.add_image(img_right, 'G1')
            print(f"[LOGO DEBUG] Placeholder added for posting export (centered)")
        except Exception as placeholder_error:
            print(f"[LOGO DEBUG] Could not create placeholder: {str(placeholder_error)}")
            
    except Exception as e:
        print(f"[LOGO ERROR] Error adding logos for posting: {str(e)}")
        import traceback
        traceback.print_exc()
        pass


def add_institution_header(ws, department_name):
    """Add institution header to the worksheet"""
    # Header - Institution Information (centered across columns C-E)
    ws['C1'] = 'Republic of the Philippines'
    ws['C1'].font = Font(bold=True, size=11)
    ws['C1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('C1:E1')
    
    ws['C2'] = 'Municipality of Norzagaray'
    ws['C2'].font = Font(size=10)
    ws['C2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('C2:E2')
    
    ws['C3'] = 'NORZAGARAY COLLEGE'
    ws['C3'].font = Font(bold=True, size=11)
    ws['C3'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('C3:E3')
    
    dept_name = department_name.upper() if department_name else 'COLLEGE'
    ws['C4'] = f'{dept_name}'
    ws['C4'].font = Font(bold=True, size=11)
    ws['C4'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('C4:E4')


def add_institution_header_for_posting(ws, department_name):
    """Add institution header for posting exports - centered across full table width (A-H)"""
    # Header - Institution Information (centered across columns A-H)
    ws['A1'] = 'Republic of the Philippines'
    ws['A1'].font = Font(bold=True, size=11)
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A1:H1')
    
    ws['A2'] = 'Municipality of Norzagaray'
    ws['A2'].font = Font(size=10)
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A2:H2')
    
    ws['A3'] = 'NORZAGARAY COLLEGE'
    ws['A3'].font = Font(bold=True, size=11)
    ws['A3'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A3:H3')
    
    dept_name = department_name.upper() if department_name else 'COLLEGE'
    ws['A4'] = f'{dept_name}'
    ws['A4'].font = Font(bold=True, size=11)
    ws['A4'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A4:H4')


def add_schedule_title(ws, title, semester_text, section_display):
    """Add schedule title and metadata"""
    # Title
    ws['A6'] = title
    ws['A6'].font = Font(bold=True, size=12)
    ws['A6'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A6:G6')
    
    # Semester and AY - BOLD
    ws['A7'] = semester_text
    ws['A7'].font = Font(bold=True, size=11)
    ws['A7'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A7:G7')
    
    # Section/Faculty/Room info
    ws['A8'] = section_display
    ws['A8'].font = Font(bold=True, size=11)
    ws['A8'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A8:G8')


def add_schedule_title_for_posting(ws, title, semester_text, section_display):
    """Add schedule title for posting exports - centered across full table width (A-H)"""
    # Title
    ws['A6'] = title
    ws['A6'].font = Font(bold=True, size=12)
    ws['A6'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A6:H6')
    
    # Semester and AY - BOLD
    ws['A7'] = semester_text
    ws['A7'].font = Font(bold=True, size=11)
    ws['A7'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A7:H7')
    
    # Section/Faculty/Room info
    ws['A8'] = section_display
    ws['A8'].font = Font(bold=True, size=11)
    ws['A8'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A8:H8')


def generate_time_slots(start_hour=7, end_hour=20):
    """Generate 30-minute time slots from start_hour to end_hour"""
    time_slots = []
    current_time = time(start_hour, 0)
    
    while current_time.hour < end_hour:
        next_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=30)).time()
        
        # Format time slots (7:00-7:30, 12:00-12:30, 1:00-1:30, etc.)
        start_str = current_time.strftime('%#I:%M').lstrip('0') if current_time.hour != 12 else current_time.strftime('12:%M')
        end_str = next_time.strftime('%#I:%M').lstrip('0') if next_time.hour != 12 else next_time.strftime('12:%M')
        
        time_slots.append(f"{start_str}-{end_str}")
        current_time = next_time
    
    return time_slots


def add_column_headers(ws):
    """Add day column headers to the worksheet"""
    headers = ['TIME', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']
    header_font = Font(bold=False, size=10)
    header_alignment = Alignment(horizontal='center', vertical='center')
    
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=10, column=col_idx, value=header)
        cell.font = header_font
        cell.alignment = header_alignment


def write_time_slots(ws, time_slots):
    """Write time slots to the worksheet"""
    for idx, time_slot in enumerate(time_slots, start=11):
        ws.cell(row=idx, column=1, value=time_slot)
        ws.cell(row=idx, column=1).alignment = Alignment(horizontal='left', vertical='center')
        ws.cell(row=idx, column=1).font = Font(size=10)


def get_day_column_mapping():
    """Get mapping of day names to column indices"""
    return {
        'Monday': 2,
        'Tuesday': 3,
        'Wednesday': 4,
        'Thursday': 5,
        'Friday': 6,
        'Saturday': 7
    }


def place_schedule_in_grid(ws, schedules, start_hour=7):
    """Place schedules in the weekly grid"""
    day_columns = get_day_column_mapping()
    
    for schedule in schedules:
        if schedule.day_of_week not in day_columns:
            continue
        
        col_idx = day_columns[schedule.day_of_week]
        
        # Calculate which 30-minute slot this starts in
        start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
        end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
        slot_start_minutes = start_hour * 60
        
        # Find start row (each row is 30 minutes, starting from row 11)
        start_row = 11 + ((start_minutes - slot_start_minutes) // 30)
        
        # Calculate how many rows to merge
        duration_minutes = end_minutes - start_minutes
        rows_to_merge = max(1, (duration_minutes + 29) // 30)
        
        # Build cell content
        subject_code = schedule.subject.subject_code if schedule.subject else 'TBA'
        room_display = schedule.room.room_number if schedule.room else 'TBA'
        faculty_name = schedule.faculty.full_name if schedule.faculty else 'TBA'
        
        cell_content = f"{subject_code}\n{room_display}\n{faculty_name}"
        
        # Write to cell
        cell = ws.cell(row=start_row, column=col_idx, value=cell_content)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.font = Font(size=10)
        
        # Merge cells if needed
        if rows_to_merge > 1:
            end_row = start_row + rows_to_merge - 1
            ws.merge_cells(start_row=start_row, start_column=col_idx, 
                         end_row=end_row, end_column=col_idx)


def apply_grid_borders(ws, last_row):
    """Apply borders to the schedule grid"""
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for row in range(10, last_row + 1):
        for col in range(1, 8):  # A to G
            ws.cell(row=row, column=col).border = thin_border


def add_signature_section(ws, sig_start_row, department_id, dept_name):
    """Add signature section with dean and college president"""
    # Prepared by section (column D)
    ws.cell(row=sig_start_row, column=4, value='Prepared by :')
    ws.cell(row=sig_start_row, column=4).font = Font(size=10)
    ws.cell(row=sig_start_row, column=4).alignment = Alignment(horizontal='left')
    
    # Noted section (column F)
    ws.cell(row=sig_start_row, column=6, value='Noted :')
    ws.cell(row=sig_start_row, column=6).font = Font(size=10)
    ws.cell(row=sig_start_row, column=6).alignment = Alignment(horizontal='left')
    
    # Name of the Dean label (column D) - BOLD
    ws.cell(row=sig_start_row + 2, column=4, value='Name of the Dean')
    ws.cell(row=sig_start_row + 2, column=4).font = Font(bold=True, size=10)
    ws.cell(row=sig_start_row + 2, column=4).alignment = Alignment(horizontal='left')
    
    # College President name (column F) - BOLD
    ws.cell(row=sig_start_row + 2, column=6, value='Ma. Liberty DG. Pascual, Ph.D')
    ws.cell(row=sig_start_row + 2, column=6).font = Font(bold=True, size=10)
    ws.cell(row=sig_start_row + 2, column=6).alignment = Alignment(horizontal='left')
    
    # Dean title (column D) - Directly under "Name of the Dean" - CENTERED
    dean_title = f"Dean, {dept_name}" if dept_name else "Dean"
    ws.cell(row=sig_start_row + 3, column=4, value=dean_title)
    ws.cell(row=sig_start_row + 3, column=4).font = Font(size=10)
    ws.cell(row=sig_start_row + 3, column=4).alignment = Alignment(horizontal='center')
    
    # College President title (column F)
    ws.cell(row=sig_start_row + 3, column=6, value='College President')
    ws.cell(row=sig_start_row + 3, column=6).font = Font(size=10)
    ws.cell(row=sig_start_row + 3, column=6).alignment = Alignment(horizontal='left')


def set_column_widths(ws):
    """Set standard column widths for schedule grid"""
    ws.column_dimensions['A'].width = 12.71
    for col in ['B', 'C', 'D', 'E', 'F', 'G']:
        ws.column_dimensions[col].width = 20.71


@schedule_bp.route('/')
@login_required
def index():
    """Schedule management page with two-panel layout"""
    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    # Get user's department access
    user_department_ids = current_user.get_department_ids()
    
    # Get departments based on user access
    if user_department_ids is None:
        # Admin - see all departments
        departments = Department.query.filter_by(is_active=True).order_by(Department.department_code).all()
    else:
        # Dean - only assigned departments
        departments = Department.query.filter(
            Department.is_active == True,
            Department.id.in_(user_department_ids)
        ).order_by(Department.department_code).all()
    
    # Get department filter from query params
    department_filter = request.args.get('department_id', type=int)
    
    # Get sections based on filter
    sections_query = Section.query.filter_by(is_active=True)
    
    # Filter by user's department access
    if user_department_ids is not None:
        sections_query = sections_query.filter(Section.department_id.in_(user_department_ids))
    
    # Apply additional department filter if specified
    if department_filter:
        sections_query = sections_query.filter_by(department_id=department_filter)
    
    sections = sections_query.order_by(Section.section_name).all()
    
    # Calculate schedule counts for current academic period
    # Initialize empty dict to prevent Jinja2 undefined errors
    section_schedule_counts = {}
    
    if current_settings:
        for section in sections:
            count = Schedule.query.filter_by(
                section_id=section.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            section_schedule_counts[section.id] = count
    else:
        # No active settings, count all active schedules
        for section in sections:
            count = Schedule.query.filter_by(
                section_id=section.id,
                is_active=True
            ).count()
            section_schedule_counts[section.id] = count
    
    # Get selected section for class tab
    selected_section_id = request.args.get('section_id', type=int)
    selected_section = None
    schedules = []
    
    if selected_section_id:
        selected_section = Section.query.get(selected_section_id)
        if selected_section:
            # Get schedules for selected section
            schedules_query = Schedule.query.filter_by(
                section_id=selected_section_id,
                is_active=True
            )
            
            # Filter by current academic settings if available
            if current_settings:
                schedules_query = schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            
            schedules = schedules_query.order_by(
                Schedule.day_of_week,
                Schedule.start_time
            ).all()
    
    # Get faculties for faculty tab
    faculties_query = Faculty.query.filter_by(is_active=True)
    if current_user.role == 'Dean' and current_user.department_id:
        faculties_query = faculties_query.filter_by(department_id=current_user.department_id)
    faculties_list = faculties_query.order_by(Faculty.full_name).all()
    
    # Calculate faculty schedule counts for current academic period
    faculty_schedule_counts = {}
    if current_settings:
        for faculty in faculties_list:
            count = Schedule.query.filter_by(
                faculty_id=faculty.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            faculty_schedule_counts[faculty.id] = count
    else:
        for faculty in faculties_list:
            count = Schedule.query.filter_by(
                faculty_id=faculty.id,
                is_active=True
            ).count()
            faculty_schedule_counts[faculty.id] = count
    
    # Get selected faculty
    selected_faculty_id = request.args.get('faculty_id', type=int)
    selected_faculty = None
    faculty_schedules = []
    
    if selected_faculty_id:
        selected_faculty = Faculty.query.get(selected_faculty_id)
        if selected_faculty:
            faculty_schedules_query = Schedule.query.filter_by(
                faculty_id=selected_faculty_id,
                is_active=True
            )
            if current_settings:
                faculty_schedules_query = faculty_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            faculty_schedules = faculty_schedules_query.order_by(
                Schedule.day_of_week,
                Schedule.start_time
            ).all()
    
    # Get rooms for room tab
    rooms_list = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()
    
    # Calculate room schedule counts for current academic period
    room_schedule_counts = {}
    if current_settings:
        for room in rooms_list:
            count = Schedule.query.filter_by(
                room_id=room.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            room_schedule_counts[room.id] = count
    else:
        for room in rooms_list:
            count = Schedule.query.filter_by(
                room_id=room.id,
                is_active=True
            ).count()
            room_schedule_counts[room.id] = count
    
    # Get selected room
    selected_room_id = request.args.get('room_id', type=int)
    selected_room = None
    room_schedules = []
    
    if selected_room_id:
        selected_room = Room.query.get(selected_room_id)
        if selected_room:
            room_schedules_query = Schedule.query.filter_by(
                room_id=selected_room_id,
                is_active=True
            )
            if current_settings:
                room_schedules_query = room_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            room_schedules = room_schedules_query.order_by(
                Schedule.day_of_week,
                Schedule.start_time
            ).all()
    
    # Get all subjects for modals
    subjects = Subject.query.order_by(Subject.subject_code).all()
    
    # Get exam schedule data
    # Get sections for exam tab (reuse the sections query)
    exam_sections = sections
    exam_department_filter = request.args.get('exam_department_id', type=int)
    
    # Calculate exam schedule counts for current academic period
    exam_section_schedule_counts = {}
    if current_settings:
        for section in exam_sections:
            count = ExamSchedule.query.filter_by(
                section_id=section.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            exam_section_schedule_counts[section.id] = count
    else:
        for section in exam_sections:
            count = ExamSchedule.query.filter_by(
                section_id=section.id,
                is_active=True
            ).count()
            exam_section_schedule_counts[section.id] = count
    
    # Get selected section for exam tab
    selected_exam_section_id = request.args.get('exam_section_id', type=int)
    selected_exam_section = None
    exam_schedules = []
    
    if selected_exam_section_id:
        selected_exam_section = Section.query.get(selected_exam_section_id)
        if selected_exam_section:
            exam_schedules_query = ExamSchedule.query.filter_by(
                section_id=selected_exam_section_id,
                is_active=True
            )
            if current_settings:
                exam_schedules_query = exam_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            exam_schedules = exam_schedules_query.order_by(
                ExamSchedule.exam_date,
                ExamSchedule.start_time
            ).all()
    
    # Get all faculties and rooms for exam modals
    all_faculties = Faculty.query.filter_by(is_active=True).order_by(Faculty.full_name).all()
    all_rooms = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()
    
    # Get all buildings for room filter
    from app.models.building import Building
    buildings = Building.query.filter_by(is_active=True).order_by(Building.building_name).all()
    
    return render_template(
        'schedule.html',
        sections=sections,
        selected_section=selected_section,
        schedules=schedules,
        departments=departments,
        department_filter=department_filter,
        subjects=subjects,
        faculties=faculties_list,
        selected_faculty=selected_faculty,
        faculty_schedules=faculty_schedules,
        rooms=rooms_list,
        selected_room=selected_room,
        room_schedules=room_schedules,
        current_settings=current_settings,
        section_schedule_counts=section_schedule_counts,
        faculty_schedule_counts=faculty_schedule_counts,
        room_schedule_counts=room_schedule_counts,
        # Exam schedule data
        exam_sections=exam_sections,
        selected_exam_section=selected_exam_section,
        exam_schedules=exam_schedules,
        exam_department_filter=exam_department_filter,
        exam_section_schedule_counts=exam_section_schedule_counts,
        all_faculties=all_faculties,
        all_rooms=all_rooms,
        buildings=buildings
    )


@schedule_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new schedule"""
    try:
        section_id = request.form.get('section_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int) or None
        room_id = request.form.get('room_id', type=int) or None
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        schedule_type = request.form.get('schedule_type', 'lecture')
        
        # Validation
        if not all([section_id, subject_id, day_of_week, start_time_str, end_time_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        academic_year = current_settings.academic_year if current_settings else None
        semester = current_settings.semester if current_settings else None
        
        # Convert time strings to time objects
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Check for conflicts - same section, day, and overlapping time
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
        
        if conflict_query.first():
            flash('Schedule conflict: This section already has a class at this time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
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
            
            if faculty_conflict.first():
                flash('Faculty conflict: This faculty member is already assigned to another class at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
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
            
            if room_conflict.first():
                flash('Room conflict: This room is already booked at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
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
        
        # Log the action
        subject = Subject.query.get(subject_id)
        section = Section.query.get(section_id)
        entity_name = f"{subject.subject_code if subject else 'N/A'} - {section.section_name if section else 'N/A'}"
        
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
        
        flash('Schedule added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing schedule"""
    try:
        schedule_id = request.form.get('schedule_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int) or None
        room_id = request.form.get('room_id', type=int) or None
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        schedule_type = request.form.get('schedule_type', 'lecture')
        
        # Get schedule
        schedule = Schedule.query.get_or_404(schedule_id)
        section_id = schedule.section_id
        
        # Validation
        if not all([subject_id, day_of_week, start_time_str, end_time_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Convert time strings to time objects
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
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
            flash('Schedule conflict: This section already has a class at this time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
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
                flash('Faculty conflict: This faculty member is already assigned to another class at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
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
                flash('Room conflict: This room is already booked at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
        # Update schedule
        schedule.subject_id = subject_id
        schedule.faculty_id = faculty_id
        schedule.room_id = room_id
        schedule.day_of_week = day_of_week
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.schedule_type = schedule_type
        schedule.updated_at = datetime.utcnow()
        
        # Log the action
        subject = Subject.query.get(subject_id)
        section = Section.query.get(schedule.section_id)
        entity_name = f"{subject.subject_code if subject else 'N/A'} - {section.section_name if section else 'N/A'}"
        
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
        
        flash('Schedule updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a schedule"""
    try:
        schedule_id = request.form.get('schedule_id', type=int)
        
        schedule = Schedule.query.get_or_404(schedule_id)
        section_id = schedule.section_id
        
        # Soft delete (set is_active to False)
        schedule.is_active = False
        schedule.updated_at = datetime.utcnow()
        
        # Log the action
        entity_name = f"{schedule.subject.subject_code if schedule.subject else 'N/A'} - {schedule.section.section_name if schedule.section else 'N/A'}"
        
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
        
        flash('Schedule deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/get-curricula/<int:section_id>')
@login_required
def get_curricula_for_section(section_id):
    """Get available curricula for a section's department ONLY"""
    from flask import jsonify
    from app.models.curriculum import Curriculum
    
    try:
        # Get the section
        section = Section.query.get_or_404(section_id)
        
        # Ensure section has a department
        if not section.department_id:
            return jsonify({
                'curricula': [],
                'error': 'Section has no department assigned'
            }), 400
        
        # Get ONLY active curricula for THIS SPECIFIC department
        curricula = Curriculum.query.filter_by(
            department_id=section.department_id,
            is_active=True,
            is_archived=False
        ).order_by(Curriculum.curriculum_code).all()
        
        # Debug logging
        print(f"[CURRICULA] Section {section_id} ({section.section_name}) - Department ID: {section.department_id}")
        print(f"[CURRICULA] Found {len(curricula)} curricula for department {section.department_id}")
        
        # Format curricula for JSON response
        curricula_data = [
            {
                'id': curriculum.id,
                'curriculum_code': curriculum.curriculum_code,
                'curriculum_name': curriculum.curriculum_name,
                'degree_program': curriculum.degree_program,
                'department_id': curriculum.department_id,  # Include for verification
                'display': f"{curriculum.curriculum_code} - {curriculum.curriculum_name}"
            }
            for curriculum in curricula
        ]
        
        return jsonify({'curricula': curricula_data})
        
    except Exception as e:
        print(f"[CURRICULA ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


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
            '2nd Semester': 2,
            'Summer': 3
        }
        semester_number = semester_mapping.get(current_settings.semester, 1)
        
        # Find curriculum
        if curriculum_id:
            # Use specified curriculum
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or curriculum.department_id != section.department_id:
                return jsonify({'subjects': [], 'error': 'Invalid curriculum for this section'})
        else:
            # Default to first active curriculum for this department
            curriculum = Curriculum.query.filter_by(
                department_id=section.department_id,
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
        subjects_data = [
            {
                'id': subject.id,
                'subject_code': subject.subject_code,
                'course_description': subject.course_description,
                'lec_units': float(subject.lec_units),
                'lab_units': float(subject.lab_units),
                'total_units': subject.total_units,
                'display': f"{subject.subject_code} - {subject.course_description} ({subject.total_units} units)"
            }
            for subject in subjects
        ]
        
        return jsonify({'subjects': subjects_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-faculty/<int:subject_id>')
@login_required
def get_faculty_for_subject(subject_id):
    """Get faculty members assigned to a specific subject"""
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if not current_settings:
            return jsonify({'faculty': []})
        
        # Get faculty assignments for this subject and current academic period
        assignments = FacultySubjectAssignment.query.filter_by(
            subject_id=subject_id,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            is_active=True,
            is_archived=False
        ).all()
        
        # Get unique faculty IDs
        faculty_ids = list(set([assignment.faculty_id for assignment in assignments]))
        
        # Get faculty details
        faculties = Faculty.query.filter(
            Faculty.id.in_(faculty_ids),
            Faculty.is_active == True,
            Faculty.is_archived == False
        ).order_by(Faculty.full_name).all()
        
        # Format faculty for JSON response
        faculty_data = [
            {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_code': faculty.department.department_code if faculty.department else '',
                'display': f"{faculty.full_name}" + (f" - {faculty.department.department_code}" if faculty.department else "")
            }
            for faculty in faculties
        ]
        
        return jsonify({'faculty': faculty_data})
        
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
        ).order_by(Faculty.full_name).all()
        
        # Format faculty for JSON response
        faculty_data = [
            {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_code': faculty.department.department_code if faculty.department else '',
                'display': f"{faculty.full_name}" + (f" - {faculty.department.department_code}" if faculty.department else "")
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
    """AI-powered conflict detection and recommendations"""
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
        
        # Get existing schedules for the same academic period
        existing_query = Schedule.query.filter_by(is_active=True)
        
        if current_settings:
            existing_query = existing_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        # Exclude current schedule if editing
        if schedule_id:
            existing_query = existing_query.filter(Schedule.id != schedule_id)
        
        existing_schedules = existing_query.all()
        
        # Prepare schedule data for AI analysis
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
        
        # Get AI analysis
        analysis = ai_scheduler.analyze_schedule_conflicts(schedule_data, existing_schedules)
        
        # Format response
        response = {
            'ai_enabled': analysis.get('ai_enabled', False),
            'has_conflicts': analysis.get('has_conflicts', False),
            'conflicts': [],
            'recommendations': analysis.get('recommendations', []),
            'ai_explanation': analysis.get('ai_explanation', '')
        }
        
        # Format conflicts for frontend
        for conflict in analysis.get('conflicts', []):
            schedule = conflict.get('schedule')
            response['conflicts'].append({
                'type': conflict['type'],
                'message': conflict['message'],
                'severity': conflict['severity'],
                'details': {
                    'subject': schedule.subject.subject_code if schedule and schedule.subject else 'Unknown',
                    'time': f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}" if schedule else '',
                    'day': schedule.day_of_week if schedule else ''
                }
            })
        
        return jsonify(response)
        
    except Exception as e:
        print(f"AI check conflicts error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'ai_enabled': False}), 500


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
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Schedule"
        
        # Add logos
        add_institution_logos(ws)
        
        # Add header
        dept_name = section.department.department_name if section.department else 'COLLEGE'
        add_institution_header(ws, dept_name)
        
        # Add title
        dept_code = section.department.department_code if section.department else ''
        semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year}" if current_settings else "CLASS SCHEDULE"
        section_display = f"{dept_code} {section.year_level}{section.section_name}"
        add_schedule_title(ws, 'CLASS SCHEDULE', semester_text, section_display)
        
        # Add column headers
        add_column_headers(ws)
        
        # Generate and write time slots
        time_slots = generate_time_slots()
        write_time_slots(ws, time_slots)
        
        # Place schedules in grid
        place_schedule_in_grid(ws, schedules)
        
        # Apply borders
        last_row = 11 + len(time_slots) - 1
        apply_grid_borders(ws, last_row)
        
        # Add signature section
        sig_start_row = last_row + 3
        add_signature_section(ws, sig_start_row, section.department_id, dept_name.upper())
        
        # Set column widths
        set_column_widths(ws)
        
        # Save and return
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{dept_code}_{section.year_level}{section.section_name}_Schedule.xlsx".replace(' ', '_')
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', section_id=section_id))
        section = Section.query.get_or_404(section_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules for this section
        query = Schedule.query.filter_by(section_id=section_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Class Schedule"
        
        # Title
        title = f"{section.section_name} - Class Schedule"
        if current_settings:
            title += f" ({current_settings.academic_year} - {current_settings.semester})"
        
        ws['A1'] = title
        ws['A1'].font = Font(bold=True, size=14, color='FFFFFF')
        ws['A1'].fill = PatternFill(start_color='7C3AED', end_color='7C3AED', fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A1:H1')
        ws.row_dimensions[1].height = 30
        
        # Headers
        headers = ['Day', 'Time', 'Subject Code', 'Subject Description', 'Type', 'Faculty', 'Room', 'Units']
        header_fill = PatternFill(start_color='9333EA', end_color='9333EA', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border_style = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
        
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = border_style
        
        ws.row_dimensions[3].height = 25
        
        # Data rows
        data_border = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )
        
        for row_idx, schedule in enumerate(schedules, start=4):
            time_str = f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}"
            faculty_name = schedule.faculty.full_name if schedule.faculty else 'TBA'
            room_display = ''
            if schedule.room:
                building_name = schedule.room.building.building_name if schedule.room.building else ''
                room_display = f"{building_name} {schedule.room.room_number}".strip()
            else:
                room_display = 'TBA'
            
            row_data = [
                schedule.day_of_week,
                time_str,
                schedule.subject.subject_code if schedule.subject else '',
                schedule.subject.course_description if schedule.subject else '',
                schedule.schedule_type.title(),
                faculty_name,
                room_display,
                float(schedule.subject.total_units) if schedule.subject else 0
            ]
            
            # Alternate row colors
            if row_idx % 2 == 0:
                fill = PatternFill(start_color='F9FAFB', end_color='F9FAFB', fill_type='solid')
            else:
                fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
            
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.fill = fill
                cell.border = data_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if col_idx in [1, 5, 8]:  # Day, Type, Units
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            ws.row_dimensions[row_idx].height = 20
        
        # Column widths
        ws.column_dimensions['A'].width = 12  # Day
        ws.column_dimensions['B'].width = 20  # Time
        ws.column_dimensions['C'].width = 15  # Subject Code
        ws.column_dimensions['D'].width = 40  # Description
        ws.column_dimensions['E'].width = 12  # Type
        ws.column_dimensions['F'].width = 25  # Faculty
        ws.column_dimensions['G'].width = 20  # Room
        ws.column_dimensions['H'].width = 10  # Units
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{section.section_name.replace(' ', '_')}_Schedule.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', section_id=section_id))


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
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Schedule"
        
        # Add logos
        add_institution_logos(ws)
        
        # Add header
        dept_name = faculty.department.department_name if faculty.department else 'COLLEGE'
        add_institution_header(ws, dept_name)
        
        # Add title
        semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year}" if current_settings else "FACULTY SCHEDULE"
        add_schedule_title(ws, 'FACULTY SCHEDULE', semester_text, faculty.full_name)
        
        # Add column headers
        add_column_headers(ws)
        
        # Generate and write time slots
        time_slots = generate_time_slots()
        write_time_slots(ws, time_slots)
        
        # Place schedules in grid
        place_schedule_in_grid(ws, schedules)
        
        # Apply borders
        last_row = 11 + len(time_slots) - 1
        apply_grid_borders(ws, last_row)
        
        # Add signature section
        sig_start_row = last_row + 3
        dept_id = faculty.department_id if faculty.department else None
        add_signature_section(ws, sig_start_row, dept_id, dept_name.upper())
        
        # Set column widths
        set_column_widths(ws)
        
        # Save and return
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{faculty.full_name.replace(' ', '_')}_Schedule.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', faculty_id=faculty_id))


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
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Schedule"
        
        # Add logos
        add_institution_logos(ws)
        
        # Add header
        building_display = room.building.building_name if room.building else 'BUILDING'
        add_institution_header(ws, building_display)
        
        # Add title
        semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year}" if current_settings else "ROOM SCHEDULE"
        add_schedule_title(ws, 'ROOM SCHEDULE', semester_text, room.room_number)
        
        # Add column headers
        add_column_headers(ws)
        
        # Generate and write time slots
        time_slots = generate_time_slots()
        write_time_slots(ws, time_slots)
        
        # Place schedules in grid
        place_schedule_in_grid(ws, schedules)
        
        # Apply borders
        last_row = 11 + len(time_slots) - 1
        apply_grid_borders(ws, last_row)
        
        # Add signature section
        sig_start_row = last_row + 3
        dept_name = building_display.upper()
        add_signature_section(ws, sig_start_row, None, dept_name)
        
        # Set column widths
        set_column_widths(ws)
        
        # Save and return
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        building_name = room.building.building_name if room.building else 'Building'
        filename = f"{building_name}_{room.room_number}_Schedule.xlsx".replace(' ', '_')
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', room_id=room_id))


@schedule_bp.route('/export/exam/<int:section_id>')
@login_required
def export_exam_schedule(section_id):
    """Export exam schedule to Excel - table format with subject details"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    import io
    
    try:
        section = Section.query.get_or_404(section_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query exam schedules for this section
        query = ExamSchedule.query.filter_by(section_id=section_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester,
                exam_period=current_settings.exam_period
            )
        
        exam_schedules = query.order_by(ExamSchedule.exam_date, ExamSchedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Exam Schedule"
        
        # Add logos (use posting-specific function with placeholder)
        add_institution_logos_for_posting(ws)
        
        # Add header (posting-specific, centered across A-H)
        dept_name = section.department.department_name.upper() if section.department else 'COLLEGE'
        add_institution_header_for_posting(ws, dept_name)
        
        # Add title (posting-specific, centered across A-H)
        if current_settings:
            semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year} - {current_settings.exam_period.upper()}"
        else:
            semester_text = "EXAM SCHEDULE"
        dept_code = section.department.department_code if section.department else ''
        section_display = f"{dept_code} {section.year_level}{section.section_name}"
        add_schedule_title_for_posting(ws, 'EXAMINATION SCHEDULE', semester_text, section_display)
        
        # Define border style
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Row 10: "Units" label merged across columns C and D
        ws['C10'] = 'Units'
        ws['C10'].font = Font(bold=True, size=11)
        ws['C10'].alignment = Alignment(horizontal='center', vertical='center')
        ws['C10'].border = thin_border
        ws.merge_cells('C10:D10')
        # Apply border to merged cells
        for col in range(3, 5):  # C and D
            ws.cell(row=10, column=col).border = thin_border
        
        # Row 11: Column Headers
        headers = ['Subject Code', 'Description', 'Lec', 'Lab', 'Date', 'Time', 'Room', 'Faculty']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=11, column=col_idx, value=header)
            cell.font = Font(bold=True, size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border
        
        # Data rows starting from row 12
        row = 12
        total_lec_units = 0
        
        for exam in exam_schedules:
            # Subject code
            subject_code = exam.subject.subject_code if exam.subject else 'TBA'
            cell = ws.cell(row=row, column=1, value=subject_code)
            cell.border = thin_border
            
            # Description
            description = exam.subject.course_description if exam.subject else ''
            cell = ws.cell(row=row, column=2, value=description)
            cell.border = thin_border
            
            # Lecture units
            lec_units = float(exam.subject.lec_units) if exam.subject else 0
            cell = ws.cell(row=row, column=3, value=str(int(lec_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            total_lec_units += lec_units
            
            # Lab units
            lab_units = float(exam.subject.lab_units) if exam.subject else 0
            cell = ws.cell(row=row, column=4, value=str(int(lab_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            
            # Exam Date
            date_str = exam.exam_date.strftime('%b %d, %Y')
            cell = ws.cell(row=row, column=5, value=date_str)
            cell.border = thin_border
            
            # Time
            time_str = f"{exam.start_time.strftime('%I:%M %p')}-{exam.end_time.strftime('%I:%M %p')}"
            cell = ws.cell(row=row, column=6, value=time_str)
            cell.border = thin_border
            
            # Room
            room_display = exam.room.room_number if exam.room else 'TBA'
            cell = ws.cell(row=row, column=7, value=room_display)
            cell.border = thin_border
            
            # Faculty
            faculty_name = exam.faculty.full_name if exam.faculty else 'TBA'
            cell = ws.cell(row=row, column=8, value=faculty_name)
            cell.border = thin_border
            
            row += 1
        
        # Add TOTAL row
        cell = ws.cell(row=row, column=1, value='TOTAL')
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='left')
        cell.border = thin_border
        
        # Empty cells in TOTAL row with borders
        for col in range(2, 3):  # Column B (Description)
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        cell = ws.cell(row=row, column=3, value=str(int(total_lec_units)))
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
        
        # Empty cells after total for proper borders
        for col in range(4, 9):  # Columns D through H
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        # Signature section (skip 3 rows after TOTAL)
        sig_start_row = row + 3
        
        # Prepared by: (column B)
        ws.cell(row=sig_start_row, column=2, value='Prepared by:')
        ws.cell(row=sig_start_row, column=2).font = Font(size=10)
        
        # Checked by: (column F)
        ws.cell(row=sig_start_row, column=6, value='Checked by:')
        ws.cell(row=sig_start_row, column=6).font = Font(size=10)
        
        # Name placeholders (2 rows down)
        ws.cell(row=sig_start_row + 2, column=2, value='Name of the Secretary')
        ws.cell(row=sig_start_row + 2, column=2).font = Font(bold=True, size=10)
        
        ws.cell(row=sig_start_row + 2, column=6, value='Name of the Dean')
        ws.cell(row=sig_start_row + 2, column=6).font = Font(bold=True, size=10)
        
        # Titles (next row)
        ws.cell(row=sig_start_row + 3, column=2, value="Dean's Secretary")
        ws.cell(row=sig_start_row + 3, column=2).font = Font(size=10)
        
        dean_title = f"Dean, {dept_name}"
        ws.cell(row=sig_start_row + 3, column=6, value=dean_title)
        ws.cell(row=sig_start_row + 3, column=6).font = Font(size=10)
        ws.cell(row=sig_start_row + 3, column=6).alignment = Alignment(horizontal='center')
        
        # Set column widths for table format
        ws.column_dimensions['A'].width = 15  # Subject Code
        ws.column_dimensions['B'].width = 35  # Description
        ws.column_dimensions['C'].width = 8   # Lec
        ws.column_dimensions['D'].width = 8   # Lab
        ws.column_dimensions['E'].width = 15  # Date
        ws.column_dimensions['F'].width = 20  # Time
        ws.column_dimensions['G'].width = 12  # Room
        ws.column_dimensions['H'].width = 25  # Faculty
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{dept_code}_{section.year_level}{section.section_name}_Exam_Schedule.xlsx".replace(' ', '_')
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting exam schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', exam_section_id=section_id))


# Export for Posting Routes (Simplified, print-friendly versions)

@schedule_bp.route('/export/class/<int:section_id>/posting')
@login_required
def export_class_schedule_for_posting(section_id):
    """Export class schedule for posting - table format with subject details"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from datetime import datetime, time as dt_time, timedelta
    import io
    
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
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Schedule"
        
        # Add logos (use posting-specific function with placeholder)
        add_institution_logos_for_posting(ws)
        
        # Add header (posting-specific, centered across A-H)
        dept_name = section.department.department_name.upper() if section.department else 'COLLEGE'
        add_institution_header_for_posting(ws, dept_name)
        
        # Add title (posting-specific, centered across A-H)
        dept_code = section.department.department_code if section.department else ''
        semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year}" if current_settings else "CLASS SCHEDULE"
        section_display = f"Course - Section: {dept_code} {section.year_level}{section.section_name}"
        add_schedule_title_for_posting(ws, 'CLASS SCHEDULE', semester_text, section_display)
        
        # Define border style
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Row 10: "Units" label merged across columns C and D
        ws['C10'] = 'Units'
        ws['C10'].font = Font(bold=True, size=11)
        ws['C10'].alignment = Alignment(horizontal='center', vertical='center')
        ws['C10'].border = thin_border
        ws.merge_cells('C10:D10')
        # Apply border to merged cells
        for col in range(3, 5):  # C and D
            ws.cell(row=10, column=col).border = thin_border
        
        # Row 11: Column Headers
        headers = ['Subject Code', 'Description', 'Lec', 'Lab', 'Day', 'Time', 'Room', 'Professor']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=11, column=col_idx, value=header)
            cell.font = Font(bold=True, size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border
        
        # Data rows starting from row 12
        row = 12
        total_lec_units = 0
        
        for schedule in schedules:
            # Subject code with type suffix
            subject_code = schedule.subject.subject_code if schedule.subject else 'TBA'
            type_suffix = '-Lec' if schedule.schedule_type == 'lecture' else '-Lab'
            cell = ws.cell(row=row, column=1, value=f"{subject_code}{type_suffix}")
            cell.border = thin_border
            
            # Description
            description = schedule.subject.course_description if schedule.subject else ''
            cell = ws.cell(row=row, column=2, value=description)
            cell.border = thin_border
            
            # Lecture units
            lec_units = float(schedule.subject.lec_units) if schedule.subject and schedule.schedule_type == 'lecture' else 0
            cell = ws.cell(row=row, column=3, value=str(int(lec_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            total_lec_units += lec_units
            
            # Lab units
            lab_units = float(schedule.subject.lab_units) if schedule.subject and schedule.schedule_type == 'lab' else 0
            cell = ws.cell(row=row, column=4, value=str(int(lab_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            
            # Day
            cell = ws.cell(row=row, column=5, value=schedule.day_of_week)
            cell.border = thin_border
            
            # Time
            time_str = f"{schedule.start_time.strftime('%I:%M %p')}-{schedule.end_time.strftime('%I:%M %p')}"
            cell = ws.cell(row=row, column=6, value=time_str)
            cell.border = thin_border
            
            # Room
            room_display = schedule.room.room_number if schedule.room else 'TBA'
            cell = ws.cell(row=row, column=7, value=room_display)
            cell.border = thin_border
            
            # Professor
            faculty_name = schedule.faculty.full_name if schedule.faculty else 'TBA'
            cell = ws.cell(row=row, column=8, value=faculty_name)
            cell.border = thin_border
            
            row += 1
        
        # Add TOTAL row
        cell = ws.cell(row=row, column=1, value='TOTAL')
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='left')
        cell.border = thin_border
        
        # Empty cells in TOTAL row with borders
        for col in range(2, 3):  # Column B (Description)
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        cell = ws.cell(row=row, column=3, value=str(int(total_lec_units)))
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
        
        # Empty cells after total for proper borders
        for col in range(4, 9):  # Columns D through H
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        # Signature section (skip 3 rows after TOTAL)
        sig_start_row = row + 3
        
        # Prepared by: (column B)
        ws.cell(row=sig_start_row, column=2, value='Prepared by:')
        ws.cell(row=sig_start_row, column=2).font = Font(size=10)
        
        # Checked by: (column F)
        ws.cell(row=sig_start_row, column=6, value='Checked by:')
        ws.cell(row=sig_start_row, column=6).font = Font(size=10)
        
        # Name placeholders (2 rows down)
        ws.cell(row=sig_start_row + 2, column=2, value='Name of the Secretary')
        ws.cell(row=sig_start_row + 2, column=2).font = Font(bold=True, size=10)
        
        ws.cell(row=sig_start_row + 2, column=6, value='Name of the Dean')
        ws.cell(row=sig_start_row + 2, column=6).font = Font(bold=True, size=10)
        
        # Titles (next row)
        ws.cell(row=sig_start_row + 3, column=2, value="Dean's Secretary")
        ws.cell(row=sig_start_row + 3, column=2).font = Font(size=10)
        
        dean_title = f"Dean, {dept_name}"
        ws.cell(row=sig_start_row + 3, column=6, value=dean_title)
        ws.cell(row=sig_start_row + 3, column=6).font = Font(size=10)
        ws.cell(row=sig_start_row + 3, column=6).alignment = Alignment(horizontal='center')
        
        # Set column widths for table format
        ws.column_dimensions['A'].width = 15  # Subject Code
        ws.column_dimensions['B'].width = 35  # Description
        ws.column_dimensions['C'].width = 8   # Lec
        ws.column_dimensions['D'].width = 8   # Lab
        ws.column_dimensions['E'].width = 12  # Day
        ws.column_dimensions['F'].width = 18  # Time
        ws.column_dimensions['G'].width = 12  # Room
        ws.column_dimensions['H'].width = 25  # Professor
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{dept_code}_{section.year_level}{section.section_name}_Schedule_Posting.xlsx".replace(' ', '_')
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule for posting: {str(e)}', 'error')
        return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/export/faculty/<int:faculty_id>/posting')
@login_required
def export_faculty_schedule_for_posting(faculty_id):
    """Export faculty schedule for posting - table format with subject details"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from datetime import datetime, time as dt_time, timedelta
    import io
    
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules for this faculty
        query = Schedule.query.filter_by(faculty_id=faculty_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Schedule"
        
        # Add logos (use posting-specific function with placeholder)
        add_institution_logos_for_posting(ws)
        
        # Add header (posting-specific, centered across A-H)
        dept_name = faculty.department.department_name.upper() if faculty.department else 'COLLEGE'
        add_institution_header_for_posting(ws, dept_name)
        
        # Add title (posting-specific, centered across A-H)
        semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year}" if current_settings else "FACULTY SCHEDULE"
        add_schedule_title_for_posting(ws, 'FACULTY SCHEDULE', semester_text, f"Faculty: {faculty.full_name}")
        
        # Define border style
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Row 10: "Units" label merged across columns C and D
        ws['C10'] = 'Units'
        ws['C10'].font = Font(bold=True, size=11)
        ws['C10'].alignment = Alignment(horizontal='center', vertical='center')
        ws['C10'].border = thin_border
        ws.merge_cells('C10:D10')
        # Apply border to merged cells
        for col in range(3, 5):  # C and D
            ws.cell(row=10, column=col).border = thin_border
        
        # Row 11: Column Headers
        headers = ['Subject Code', 'Description', 'Lec', 'Lab', 'Day', 'Time', 'Room', 'Section']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=11, column=col_idx, value=header)
            cell.font = Font(bold=True, size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border
        
        # Data rows starting from row 12
        row = 12
        total_lec_units = 0
        
        for schedule in schedules:
            # Subject code with type suffix
            subject_code = schedule.subject.subject_code if schedule.subject else 'TBA'
            type_suffix = '-Lec' if schedule.schedule_type == 'lecture' else '-Lab'
            cell = ws.cell(row=row, column=1, value=f"{subject_code}{type_suffix}")
            cell.border = thin_border
            
            # Description
            description = schedule.subject.course_description if schedule.subject else ''
            cell = ws.cell(row=row, column=2, value=description)
            cell.border = thin_border
            
            # Lecture units
            lec_units = float(schedule.subject.lec_units) if schedule.subject and schedule.schedule_type == 'lecture' else 0
            cell = ws.cell(row=row, column=3, value=str(int(lec_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            total_lec_units += lec_units
            
            # Lab units
            lab_units = float(schedule.subject.lab_units) if schedule.subject and schedule.schedule_type == 'lab' else 0
            cell = ws.cell(row=row, column=4, value=str(int(lab_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            
            # Day
            cell = ws.cell(row=row, column=5, value=schedule.day_of_week)
            cell.border = thin_border
            
            # Time
            time_str = f"{schedule.start_time.strftime('%I:%M %p')}-{schedule.end_time.strftime('%I:%M %p')}"
            cell = ws.cell(row=row, column=6, value=time_str)
            cell.border = thin_border
            
            # Room
            room_display = schedule.room.room_number if schedule.room else 'TBA'
            cell = ws.cell(row=row, column=7, value=room_display)
            cell.border = thin_border
            
            # Section
            section_name = schedule.section.section_name if schedule.section else 'TBA'
            cell = ws.cell(row=row, column=8, value=section_name)
            cell.border = thin_border
            
            row += 1
        
        # Add TOTAL row
        cell = ws.cell(row=row, column=1, value='TOTAL')
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='left')
        cell.border = thin_border
        
        # Empty cells in TOTAL row with borders
        for col in range(2, 3):  # Column B (Description)
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        cell = ws.cell(row=row, column=3, value=str(int(total_lec_units)))
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
        
        # Empty cells after total for proper borders
        for col in range(4, 9):  # Columns D through H
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        # Signature section (skip 3 rows after TOTAL)
        sig_start_row = row + 3
        
        # Prepared by: (column B)
        ws.cell(row=sig_start_row, column=2, value='Prepared by:')
        ws.cell(row=sig_start_row, column=2).font = Font(size=10)
        
        # Checked by: (column F)
        ws.cell(row=sig_start_row, column=6, value='Checked by:')
        ws.cell(row=sig_start_row, column=6).font = Font(size=10)
        
        # Name placeholders (2 rows down)
        ws.cell(row=sig_start_row + 2, column=2, value='Name of the Secretary')
        ws.cell(row=sig_start_row + 2, column=2).font = Font(bold=True, size=10)
        
        ws.cell(row=sig_start_row + 2, column=6, value='Name of the Dean')
        ws.cell(row=sig_start_row + 2, column=6).font = Font(bold=True, size=10)
        
        # Titles (next row)
        ws.cell(row=sig_start_row + 3, column=2, value="Dean's Secretary")
        ws.cell(row=sig_start_row + 3, column=2).font = Font(size=10)
        
        dean_title = f"Dean, {dept_name}"
        ws.cell(row=sig_start_row + 3, column=6, value=dean_title)
        ws.cell(row=sig_start_row + 3, column=6).font = Font(size=10)
        ws.cell(row=sig_start_row + 3, column=6).alignment = Alignment(horizontal='center')
        
        # Set column widths for table format
        ws.column_dimensions['A'].width = 15  # Subject Code
        ws.column_dimensions['B'].width = 35  # Description
        ws.column_dimensions['C'].width = 8   # Lec
        ws.column_dimensions['D'].width = 8   # Lab
        ws.column_dimensions['E'].width = 12  # Day
        ws.column_dimensions['F'].width = 18  # Time
        ws.column_dimensions['G'].width = 12  # Room
        ws.column_dimensions['H'].width = 25  # Section
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{faculty.full_name.replace(' ', '_')}_Schedule_Posting.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting faculty schedule for posting: {str(e)}', 'error')
        return redirect(url_for('schedule.index', faculty_id=faculty_id))


@schedule_bp.route('/export/room/<int:room_id>/posting')
@login_required
def export_room_schedule_for_posting(room_id):
    """Export room schedule for posting - table format with subject details"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from datetime import datetime, time as dt_time, timedelta
    import io
    
    try:
        room = Room.query.get_or_404(room_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules for this room
        query = Schedule.query.filter_by(room_id=room_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Schedule"
        
        # Add logos (use posting-specific function with placeholder)
        add_institution_logos_for_posting(ws)
        
        # Add header (posting-specific, centered across A-H)
        building_display = room.building.building_name.upper() if room.building else 'BUILDING'
        add_institution_header_for_posting(ws, building_display)
        
        # Add title (posting-specific, centered across A-H)
        semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year}" if current_settings else "ROOM SCHEDULE"
        add_schedule_title_for_posting(ws, 'ROOM SCHEDULE', semester_text, f"Room: {room.room_number}")
        
        # Define border style
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Row 10: "Units" label merged across columns C and D
        ws['C10'] = 'Units'
        ws['C10'].font = Font(bold=True, size=11)
        ws['C10'].alignment = Alignment(horizontal='center', vertical='center')
        ws['C10'].border = thin_border
        ws.merge_cells('C10:D10')
        # Apply border to merged cells
        for col in range(3, 5):  # C and D
            ws.cell(row=10, column=col).border = thin_border
        
        # Row 11: Column Headers
        headers = ['Subject Code', 'Description', 'Lec', 'Lab', 'Day', 'Time', 'Section', 'Faculty']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=11, column=col_idx, value=header)
            cell.font = Font(bold=True, size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border
        
        # Data rows starting from row 12
        row = 12
        total_lec_units = 0
        
        for schedule in schedules:
            # Subject code with type suffix
            subject_code = schedule.subject.subject_code if schedule.subject else 'TBA'
            type_suffix = '-Lec' if schedule.schedule_type == 'lecture' else '-Lab'
            cell = ws.cell(row=row, column=1, value=f"{subject_code}{type_suffix}")
            cell.border = thin_border
            
            # Description
            description = schedule.subject.course_description if schedule.subject else ''
            cell = ws.cell(row=row, column=2, value=description)
            cell.border = thin_border
            
            # Lecture units
            lec_units = float(schedule.subject.lec_units) if schedule.subject and schedule.schedule_type == 'lecture' else 0
            cell = ws.cell(row=row, column=3, value=str(int(lec_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            total_lec_units += lec_units
            
            # Lab units
            lab_units = float(schedule.subject.lab_units) if schedule.subject and schedule.schedule_type == 'lab' else 0
            cell = ws.cell(row=row, column=4, value=str(int(lab_units)))
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            
            # Day
            cell = ws.cell(row=row, column=5, value=schedule.day_of_week)
            cell.border = thin_border
            
            # Time
            time_str = f"{schedule.start_time.strftime('%I:%M %p')}-{schedule.end_time.strftime('%I:%M %p')}"
            cell = ws.cell(row=row, column=6, value=time_str)
            cell.border = thin_border
            
            # Section
            section_name = schedule.section.section_name if schedule.section else 'TBA'
            cell = ws.cell(row=row, column=7, value=section_name)
            cell.border = thin_border
            
            # Faculty
            faculty_name = schedule.faculty.full_name if schedule.faculty else 'TBA'
            cell = ws.cell(row=row, column=8, value=faculty_name)
            cell.border = thin_border
            
            row += 1
        
        # Add TOTAL row
        cell = ws.cell(row=row, column=1, value='TOTAL')
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='left')
        cell.border = thin_border
        
        # Empty cells in TOTAL row with borders
        for col in range(2, 3):  # Column B (Description)
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        cell = ws.cell(row=row, column=3, value=str(int(total_lec_units)))
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
        
        # Empty cells after total for proper borders
        for col in range(4, 9):  # Columns D through H
            cell = ws.cell(row=row, column=col, value='')
            cell.border = thin_border
        
        # Signature section (skip 3 rows after TOTAL)
        sig_start_row = row + 3
        
        # Prepared by: (column B)
        ws.cell(row=sig_start_row, column=2, value='Prepared by:')
        ws.cell(row=sig_start_row, column=2).font = Font(size=10)
        
        # Checked by: (column F)
        ws.cell(row=sig_start_row, column=6, value='Checked by:')
        ws.cell(row=sig_start_row, column=6).font = Font(size=10)
        
        # Name placeholders (2 rows down)
        ws.cell(row=sig_start_row + 2, column=2, value='Name of the Secretary')
        ws.cell(row=sig_start_row + 2, column=2).font = Font(bold=True, size=10)
        
        ws.cell(row=sig_start_row + 2, column=6, value='Name of the Dean')
        ws.cell(row=sig_start_row + 2, column=6).font = Font(bold=True, size=10)
        
        # Titles (next row)
        ws.cell(row=sig_start_row + 3, column=2, value="Dean's Secretary")
        ws.cell(row=sig_start_row + 3, column=2).font = Font(size=10)
        
        dean_title = f"Dean, {building_display}"
        ws.cell(row=sig_start_row + 3, column=6, value=dean_title)
        ws.cell(row=sig_start_row + 3, column=6).font = Font(size=10)
        ws.cell(row=sig_start_row + 3, column=6).alignment = Alignment(horizontal='center')
        
        # Set column widths for table format
        ws.column_dimensions['A'].width = 15  # Subject Code
        ws.column_dimensions['B'].width = 35  # Description
        ws.column_dimensions['C'].width = 8   # Lec
        ws.column_dimensions['D'].width = 8   # Lab
        ws.column_dimensions['E'].width = 12  # Day
        ws.column_dimensions['F'].width = 18  # Time
        ws.column_dimensions['G'].width = 25  # Section
        ws.column_dimensions['H'].width = 25  # Faculty
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        building_name = room.building.building_name if room.building else 'Building'
        filename = f"{building_name}_{room.room_number}_Schedule_Posting.xlsx".replace(' ', '_')
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting room schedule for posting: {str(e)}', 'error')
        return redirect(url_for('schedule.index', room_id=room_id))


@schedule_bp.route('/export/exam/<int:section_id>/posting')
@login_required
def export_exam_schedule_for_posting(section_id):
    """Batch export - Export all exam schedules for the entire department, grouped by section"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from datetime import datetime, time as dt_time, timedelta
    import io
    
    try:
        section = Section.query.get_or_404(section_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Get all sections for this department
        department_id = section.department_id
        if not department_id:
            flash('Section must belong to a department for batch export', 'error')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Get ALL sections for this department
        all_sections = Section.query.filter_by(
            department_id=department_id, 
            is_active=True
        ).order_by(Section.year_level, Section.section_name).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Exam Schedule"
        
        # Add logos (use posting-specific function with placeholder)
        add_institution_logos_for_posting(ws)
        
        # Add header (posting-specific, centered across A-H)
        dept_name = section.department.department_name.upper() if section.department else 'COLLEGE'
        add_institution_header_for_posting(ws, dept_name)
        
        # Add title (posting-specific, centered across A-H)
        if current_settings:
            semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year} - {current_settings.exam_period.upper()}"
        else:
            semester_text = "EXAM SCHEDULE"
        dept_code = section.department.department_code if section.department else ''
        add_schedule_title_for_posting(ws, 'EXAMINATION SCHEDULE - BATCH EXPORT', semester_text, f"Department: {dept_name}")
        
        # Define border style
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Start row for content
        current_row = 10
        
        # Loop through each section and create a separate table
        for sect in all_sections:
            # Query exam schedules for this specific section
            query = ExamSchedule.query.filter_by(section_id=sect.id, is_active=True)
            if current_settings:
                query = query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester,
                    exam_period=current_settings.exam_period
                )
            
            exam_schedules = query.order_by(
                ExamSchedule.exam_date,
                ExamSchedule.start_time
            ).all()
            
            # Skip sections with no exam schedules
            if not exam_schedules:
                continue
            
            # Section Header (merged across A-H)
            section_header = f"{dept_code} {sect.year_level}{sect.section_name}"
            ws.merge_cells(f'A{current_row}:H{current_row}')
            cell = ws.cell(row=current_row, column=1, value=section_header)
            cell.font = Font(bold=True, size=12)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.fill = PatternFill(start_color='E5E7EB', end_color='E5E7EB', fill_type='solid')
            for col in range(1, 9):
                ws.cell(row=current_row, column=col).border = thin_border
            current_row += 1
            
            # "Units" label merged across columns C and D
            ws.merge_cells(f'C{current_row}:D{current_row}')
            cell = ws.cell(row=current_row, column=3, value='Units')
            cell.font = Font(bold=True, size=11)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            for col in range(3, 5):
                ws.cell(row=current_row, column=col).border = thin_border
            current_row += 1
            
            # Column Headers
            headers = ['Subject Code', 'Description', 'Lec', 'Lab', 'Date', 'Time', 'Room', 'Faculty']
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=current_row, column=col_idx, value=header)
                cell.font = Font(bold=True, size=11)
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = thin_border
            current_row += 1
            
            # Data rows for this section
            section_total_lec_units = 0
            
            for exam in exam_schedules:
                # Subject code
                subject_code = exam.subject.subject_code if exam.subject else 'TBA'
                cell = ws.cell(row=current_row, column=1, value=subject_code)
                cell.border = thin_border
                
                # Description
                description = exam.subject.course_description if exam.subject else ''
                cell = ws.cell(row=current_row, column=2, value=description)
                cell.border = thin_border
                
                # Lecture units
                lec_units = float(exam.subject.lec_units) if exam.subject else 0
                cell = ws.cell(row=current_row, column=3, value=str(int(lec_units)))
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border
                section_total_lec_units += lec_units
                
                # Lab units
                lab_units = float(exam.subject.lab_units) if exam.subject else 0
                cell = ws.cell(row=current_row, column=4, value=str(int(lab_units)))
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border
                
                # Exam Date
                date_str = exam.exam_date.strftime('%b %d, %Y')
                cell = ws.cell(row=current_row, column=5, value=date_str)
                cell.border = thin_border
                
                # Time
                time_str = f"{exam.start_time.strftime('%I:%M %p')}-{exam.end_time.strftime('%I:%M %p')}"
                cell = ws.cell(row=current_row, column=6, value=time_str)
                cell.border = thin_border
                
                # Room
                room_display = exam.room.room_number if exam.room else 'TBA'
                cell = ws.cell(row=current_row, column=7, value=room_display)
                cell.border = thin_border
                
                # Faculty
                faculty_name = exam.faculty.full_name if exam.faculty else 'TBA'
                cell = ws.cell(row=current_row, column=8, value=faculty_name)
                cell.border = thin_border
                
                current_row += 1
            
            # Add TOTAL row for this section
            cell = ws.cell(row=current_row, column=1, value='TOTAL')
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='left')
            cell.border = thin_border
            
            # Empty cell for Description
            cell = ws.cell(row=current_row, column=2, value='')
            cell.border = thin_border
            
            # Total lecture units
            cell = ws.cell(row=current_row, column=3, value=str(int(section_total_lec_units)))
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            
            # Empty cells after total
            for col in range(4, 9):
                cell = ws.cell(row=current_row, column=col, value='')
                cell.border = thin_border
            
            # Skip 3 rows before next section
            current_row += 4
        
        # Signature section at the end
        sig_start_row = current_row
        
        # Prepared by: (column B)
        ws.cell(row=sig_start_row, column=2, value='Prepared by:')
        ws.cell(row=sig_start_row, column=2).font = Font(size=10)
        
        # Checked by: (column F)
        ws.cell(row=sig_start_row, column=6, value='Checked by:')
        ws.cell(row=sig_start_row, column=6).font = Font(size=10)
        
        # Name placeholders (2 rows down)
        ws.cell(row=sig_start_row + 2, column=2, value='Name of the Secretary')
        ws.cell(row=sig_start_row + 2, column=2).font = Font(bold=True, size=10)
        
        ws.cell(row=sig_start_row + 2, column=6, value='Name of the Dean')
        ws.cell(row=sig_start_row + 2, column=6).font = Font(bold=True, size=10)
        
        # Titles (next row)
        ws.cell(row=sig_start_row + 3, column=2, value="Dean's Secretary")
        ws.cell(row=sig_start_row + 3, column=2).font = Font(size=10)
        
        dean_title = f"Dean, {dept_name}"
        ws.cell(row=sig_start_row + 3, column=6, value=dean_title)
        ws.cell(row=sig_start_row + 3, column=6).font = Font(size=10)
        ws.cell(row=sig_start_row + 3, column=6).alignment = Alignment(horizontal='center')
        
        # Set column widths for table format
        ws.column_dimensions['A'].width = 15  # Subject Code
        ws.column_dimensions['B'].width = 35  # Description
        ws.column_dimensions['C'].width = 8   # Lec
        ws.column_dimensions['D'].width = 8   # Lab
        ws.column_dimensions['E'].width = 15  # Date
        ws.column_dimensions['F'].width = 20  # Time
        ws.column_dimensions['G'].width = 12  # Room
        ws.column_dimensions['H'].width = 25  # Faculty
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{dept_code}_Exam_Schedule_Batch_Export.xlsx".replace(' ', '_')
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting exam schedule batch: {str(e)}', 'error')
        return redirect(url_for('schedule.index', exam_section_id=section_id))

