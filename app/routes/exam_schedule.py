"""
Exam Schedule routes for managing exam schedules
"""
from flask import Blueprint, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from datetime import datetime
import io
import traceback
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
        faculty_id = request.form.get('faculty_id', type=int)
        room_id = request.form.get('room_id', type=int)
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
        
        # Validation - faculty and room are now required
        if not all([section_id, subject_id, faculty_id, room_id, exam_date_str, start_time_str, end_time_str]):
            flash('All required fields must be filled (including faculty and room)', 'danger')
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
    try:
        exam_schedule_id = request.form.get('exam_schedule_id', type=int)
        exam_schedule = ExamSchedule.query.get(exam_schedule_id)
        
        if not exam_schedule:
            flash('Exam schedule not found', 'danger')
            return redirect(url_for('schedule.index'))
        
        section_id = request.form.get('section_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int)
        room_id = request.form.get('room_id', type=int)
        exam_date_str = request.form.get('exam_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            flash('No active academic settings found. Please configure academic settings first.', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        academic_year = current_settings.academic_year
        semester = current_settings.semester
        exam_period = current_settings.exam_period
        
        # Validation - faculty and room are now required
        if not all([section_id, subject_id, faculty_id, room_id, exam_date_str, start_time_str, end_time_str]):
            flash('All required fields must be filled (including faculty and room)', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Convert date and time strings
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('schedule.index', exam_section_id=section_id))
        
        # Check for conflicts - same section, date, and overlapping time (excluding current exam)
        conflict_query = ExamSchedule.query.filter(
            ExamSchedule.id != exam_schedule_id,
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
        
        # Check for faculty conflicts if faculty assigned (excluding current exam)
        if faculty_id:
            faculty_conflict = ExamSchedule.query.filter(
                ExamSchedule.id != exam_schedule_id,
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
        
        # Check for room conflicts if room assigned (excluding current exam)
        if room_id:
            room_conflict = ExamSchedule.query.filter(
                ExamSchedule.id != exam_schedule_id,
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
        
        # Update exam schedule
        exam_schedule.section_id = section_id
        exam_schedule.subject_id = subject_id
        exam_schedule.faculty_id = faculty_id
        exam_schedule.room_id = room_id
        exam_schedule.exam_date = exam_date
        exam_schedule.start_time = start_time
        exam_schedule.end_time = end_time
        exam_schedule.semester = semester
        exam_schedule.academic_year = academic_year
        exam_schedule.exam_period = exam_period
        
        # Log activity
        log_edit('exam_schedule', exam_schedule.id, f'{exam_schedule.subject.subject_code} - {exam_schedule.section.section_name}', {
            'exam_date': str(exam_date),
            'exam_period': exam_period
        })
        
        db.session.commit()
        
        flash('Exam schedule updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating exam schedule: {str(e)}', 'danger')
    
    return redirect(url_for('schedule.index', exam_section_id=section_id))


@exam_schedule_bp.route('/get/<int:exam_schedule_id>')
@login_required
def get_exam_schedule(exam_schedule_id):
    """Get exam schedule data for editing"""
    try:
        exam_schedule = ExamSchedule.query.get(exam_schedule_id)
        if not exam_schedule:
            return jsonify({'error': 'Exam schedule not found'}), 404
        
        return jsonify({
            'id': exam_schedule.id,
            'section_id': exam_schedule.section_id,
            'subject_id': exam_schedule.subject_id,
            'faculty_id': exam_schedule.faculty_id,
            'room_id': exam_schedule.room_id,
            'exam_date': exam_schedule.exam_date.strftime('%Y-%m-%d'),
            'start_time': exam_schedule.start_time.strftime('%H:%M'),
            'end_time': exam_schedule.end_time.strftime('%H:%M'),
            'semester': exam_schedule.semester,
            'academic_year': exam_schedule.academic_year,
            'exam_period': exam_schedule.exam_period
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


@exam_schedule_bp.route('/ai-check-conflicts', methods=['POST'])
@login_required
@csrf.exempt  # Exempt CSRF for AJAX endpoints
def ai_check_exam_conflicts():
    """AI-powered conflict detection for exam schedules"""
    from app.ai_scheduler import ai_scheduler
    from datetime import datetime as dt
    
    try:
        data = request.get_json()
        
        # Debug logging
        print(f"[AI CHECK EXAM] Received data: {data}")
        
        if not data:
            return jsonify({'error': 'No data received', 'ai_enabled': False}), 400
        
        # Parse exam schedule data
        section_id = data.get('section_id')
        subject_id = data.get('subject_id')
        faculty_id = data.get('faculty_id')
        room_id = data.get('room_id')
        exam_date_str = data.get('exam_date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        exam_schedule_id = data.get('exam_schedule_id')  # For edit mode
        
        # Debug logging
        print(f"[AI CHECK EXAM] Parsed - section:{section_id} date:{exam_date_str} time:{start_time_str}-{end_time_str}")
        
        if not all([section_id, exam_date_str, start_time_str, end_time_str]):
            missing = []
            if not section_id: missing.append('section_id')
            if not exam_date_str: missing.append('exam_date')
            if not start_time_str: missing.append('start_time')
            if not end_time_str: missing.append('end_time')
            error_msg = f'Missing required fields: {", ".join(missing)}'
            print(f"[AI CHECK EXAM] Validation failed: {error_msg}")
            return jsonify({'error': error_msg, 'ai_enabled': False}), 400
        
        # Convert times and date
        start_time = dt.strptime(start_time_str, '%H:%M').time()
        end_time = dt.strptime(end_time_str, '%H:%M').time()
        exam_date = dt.strptime(exam_date_str, '%Y-%m-%d').date()
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Get existing exam schedules for the same academic period
        existing_query = ExamSchedule.query.filter_by(is_active=True)
        
        if current_settings:
            existing_query = existing_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester,
                exam_period=current_settings.exam_period
            )
        
        # Exclude current exam schedule if editing
        if exam_schedule_id:
            existing_query = existing_query.filter(ExamSchedule.id != exam_schedule_id)
        
        existing_exams = existing_query.all()
        
        # Prepare exam schedule data for AI analysis
        exam_data = {
            'section_id': section_id,
            'subject_id': subject_id,
            'faculty_id': faculty_id,
            'room_id': room_id,
            'exam_date': exam_date,
            'start_time': start_time,
            'end_time': end_time,
            'is_exam': True  # Flag to indicate this is an exam schedule
        }
        
        # Get AI analysis
        analysis = ai_scheduler.analyze_exam_conflicts(exam_data, existing_exams)
        
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
            exam_schedule = conflict.get('schedule')
            response['conflicts'].append({
                'type': conflict['type'],
                'message': conflict['message'],
                'severity': conflict['severity'],
                'details': {
                    'subject': exam_schedule.subject.subject_code if exam_schedule and exam_schedule.subject else 'Unknown',
                    'time': f"{exam_schedule.start_time.strftime('%I:%M %p')} - {exam_schedule.end_time.strftime('%I:%M %p')}" if exam_schedule else '',
                    'date': str(exam_schedule.exam_date) if exam_schedule else ''
                }
            })
        
        return jsonify(response)
        
    except Exception as e:
        print(f"AI check exam conflicts error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'ai_enabled': False}), 500


@exam_schedule_bp.route('/batch-export/excel')
@login_required
def batch_export_excel():
    """Export all exam schedules for current academic period to Excel"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    import io
    from flask import send_file
    
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            flash('No active academic settings found.', 'danger')
            return redirect(url_for('schedule.index'))
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Build query for exam schedules
        query = ExamSchedule.query.filter_by(
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            exam_period=current_settings.exam_period,
            is_active=True
        )
        
        # Filter by user's department access if Dean
        if user_department_ids is not None:
            query = query.join(Section).filter(Section.department_id.in_(user_department_ids))
        
        exam_schedules = query.order_by(ExamSchedule.exam_date, ExamSchedule.start_time).all()
        
        if not exam_schedules:
            flash('No exam schedules found for the current academic period.', 'info')
            return redirect(url_for('schedule.index'))
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'Exam Schedules'
        
        # Add header
        ws['A1'] = 'EXAM SCHEDULES - BATCH EXPORT'
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A1:J1')
        
        ws['A2'] = f'{current_settings.semester} - {current_settings.academic_year}'
        ws['A2'].font = Font(bold=True, size=12)
        ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A2:J2')
        
        ws['A3'] = f'Exam Period: {current_settings.exam_period}'
        ws['A3'].font = Font(bold=True, size=11)
        ws['A3'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A3:J3')
        
        # Column headers
        headers = ['Section', 'Subject Code', 'Subject', 'Faculty', 'Room', 'Exam Date', 'Start Time', 'End Time', 'Department', 'Year Level']
        header_fill = PatternFill(start_color='2563eb', end_color='2563eb', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_alignment = Alignment(horizontal='center', vertical='center')
        
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=5, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        # Data rows
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for row_idx, exam in enumerate(exam_schedules, start=6):
            ws.cell(row=row_idx, column=1, value=exam.section.section_name if exam.section else 'N/A')
            ws.cell(row=row_idx, column=2, value=exam.subject.subject_code if exam.subject else 'N/A')
            ws.cell(row=row_idx, column=3, value=exam.subject.course_description if exam.subject else 'N/A')
            ws.cell(row=row_idx, column=4, value=exam.faculty.full_name if exam.faculty else 'TBA')
            ws.cell(row=row_idx, column=5, value=exam.room.room_number if exam.room else 'TBA')
            ws.cell(row=row_idx, column=6, value=exam.exam_date.strftime('%B %d, %Y') if exam.exam_date else 'N/A')
            ws.cell(row=row_idx, column=7, value=exam.start_time.strftime('%I:%M %p') if exam.start_time else 'N/A')
            ws.cell(row=row_idx, column=8, value=exam.end_time.strftime('%I:%M %p') if exam.end_time else 'N/A')
            ws.cell(row=row_idx, column=9, value=exam.section.department.department_name if exam.section and exam.section.department else 'N/A')
            ws.cell(row=row_idx, column=10, value=str(exam.section.year_level) if exam.section else 'N/A')
            
            # Apply borders and alignment
            for col in range(1, 11):
                cell = ws.cell(row=row_idx, column=col)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Set column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 25
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 12
        ws.column_dimensions['H'].width = 12
        ws.column_dimensions['I'].width = 25
        ws.column_dimensions['J'].width = 10
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f'Exam_Schedules_Batch_{current_settings.semester}_{current_settings.academic_year.replace("/", "-")}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Batch export error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error generating batch export: {str(e)}', 'danger')
        return redirect(url_for('schedule.index'))


@exam_schedule_bp.route('/batch-export/pdf')
@login_required
def batch_export_pdf():
    """Export all exam schedules for current academic period to PDF"""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.enums import TA_CENTER
    import io
    from flask import send_file
    
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            flash('No active academic settings found.', 'danger')
            return redirect(url_for('schedule.index'))
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Build query for exam schedules
        query = ExamSchedule.query.filter_by(
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            exam_period=current_settings.exam_period,
            is_active=True
        )
        
        # Filter by user's department access if Dean
        if user_department_ids is not None:
            query = query.join(Section).filter(Section.department_id.in_(user_department_ids))
        
        exam_schedules = query.order_by(ExamSchedule.exam_date, ExamSchedule.start_time).all()
        
        if not exam_schedules:
            flash('No exam schedules found for the current academic period.', 'info')
            return redirect(url_for('schedule.index'))
        
        # Create PDF
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(letter),
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Add title
        story.append(Paragraph('EXAM SCHEDULES - BATCH EXPORT', title_style))
        story.append(Paragraph(f'{current_settings.semester} - {current_settings.academic_year}', subtitle_style))
        story.append(Paragraph(f'Exam Period: {current_settings.exam_period}', subtitle_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Prepare table data
        table_data = [['Section', 'Subject', 'Faculty', 'Room', 'Exam Date', 'Time']]
        
        for exam in exam_schedules:
            section_display = exam.section.section_name if exam.section else 'N/A'
            subject_display = f"{exam.subject.subject_code}\n{exam.subject.course_description[:30]}..." if exam.subject else 'N/A'
            faculty_display = exam.faculty.full_name if exam.faculty else 'TBA'
            room_display = exam.room.room_number if exam.room else 'TBA'
            date_display = exam.exam_date.strftime('%m/%d/%Y') if exam.exam_date else 'N/A'
            time_display = f"{exam.start_time.strftime('%I:%M %p')}-{exam.end_time.strftime('%I:%M %p')}" if exam.start_time and exam.end_time else 'N/A'
            
            table_data.append([
                section_display,
                subject_display,
                faculty_display,
                room_display,
                date_display,
                time_display
            ])
        
        # Create table
        col_widths = [1*inch, 2.5*inch, 1.8*inch, 1*inch, 1*inch, 1.5*inch]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style table
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # Data cells
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, rl_colors.black),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#f9fafb')]),
        ]))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)
        output.seek(0)
        
        filename = f'Exam_Schedules_Batch_{current_settings.semester}_{current_settings.academic_year.replace("/", "-")}.pdf'
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Batch PDF export error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error generating batch PDF export: {str(e)}', 'danger')
        return redirect(url_for('schedule.index'))


@exam_schedule_bp.route('/export-for-posting/<int:section_id>')
@login_required
def export_for_posting(section_id):
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
        
        # Import helper functions from schedule.py
        from app.routes.schedule import add_institution_logos_for_posting, add_institution_header_for_posting, add_schedule_title_for_posting
        
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


@exam_schedule_bp.route('/export/<int:section_id>')
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
        
        # Import helper functions from schedule.py
        from app.routes.schedule import add_institution_logos_for_posting, add_institution_header_for_posting, add_schedule_title_for_posting
        
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


@exam_schedule_bp.route('/export/<int:section_id>/pdf')
@login_required
def export_exam_schedule_pdf(section_id):
    """Export exam schedule to PDF - weekly grid format"""
    try:
        section = Section.query.get_or_404(section_id)
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query exam schedules
        query = ExamSchedule.query.filter_by(section_id=section_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester,
                exam_period=current_settings.exam_period
            )
        exam_schedules = query.order_by(ExamSchedule.day_of_week, ExamSchedule.start_time).all()
        
        # Convert ExamSchedule to Schedule-like format for PDF function
        schedules = []
        for exam in exam_schedules:
            # Create a mock Schedule object with exam schedule attributes
            class MockSchedule:
                def __init__(self, exam):
                    self.day_of_week = exam.day_of_week
                    self.start_time = exam.start_time
                    self.end_time = exam.end_time
                    self.subject = exam.subject
                    self.faculty = exam.faculty
                    self.room = exam.room
                    self.schedule_type = 'EXAM'
            
            schedules.append(MockSchedule(exam))
        
        # Prepare metadata
        dept_name = section.department.department_name if section.department else 'COLLEGE'
        dept_code = section.department.department_code if section.department else ''
        
        if current_settings:
            semester_text = f"{current_settings.semester.upper()}, AY {current_settings.academic_year} - {current_settings.exam_period.upper()}"
        else:
            semester_text = "EXAM SCHEDULE"
        
        section_display = f"{dept_code} {section.year_level}{section.section_name}"
        
        # Import PDF creation function from schedule.py
        from app.routes.schedule import create_pdf_schedule
        
        # Create PDF
        output = create_pdf_schedule(
            schedules=schedules,
            title='EXAMINATION SCHEDULE',
            semester_text=semester_text,
            section_display=section_display,
            dept_name=dept_name.upper(),
            filename=f"{dept_code}_{section.year_level}{section.section_name}_Exam_Schedule.pdf"
        )
        
        filename = f"{dept_code}_{section.year_level}{section.section_name}_Exam_Schedule.pdf".replace(' ', '_')
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting exam PDF schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', exam_section_id=section_id))
