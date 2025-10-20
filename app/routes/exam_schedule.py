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
            return redirect(url_for('schedule.index'))
        
        academic_year = current_settings.academic_year
        semester = current_settings.semester
        exam_period = current_settings.exam_period
        
        # Validation
        if not all([section_id, subject_id, exam_date_str, start_time_str, end_time_str]):
            flash('All required fields must be filled', 'danger')
            return redirect(url_for('schedule.index'))
        
        # Convert date and time strings
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('schedule.index'))
        
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
            return redirect(url_for('schedule.index'))
        
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
                return redirect(url_for('schedule.index'))
        
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
                return redirect(url_for('schedule.index'))
        
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
        schedule_id = request.form.get('schedule_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int) or None
        room_id = request.form.get('room_id', type=int) or None
        exam_date_str = request.form.get('exam_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        # Get existing schedule
        exam_schedule = ExamSchedule.query.get_or_404(schedule_id)
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
        
        db.session.commit()
        
        flash('Exam schedule updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating exam schedule: {str(e)}', 'danger')
    
    return redirect(url_for('schedule.index', exam_section_id=section_id))


@exam_schedule_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete an exam schedule"""
    try:
        schedule_id = request.form.get('schedule_id', type=int)
        exam_schedule = ExamSchedule.query.get_or_404(schedule_id)
        section_id = exam_schedule.section_id
        
        db.session.delete(exam_schedule)
        db.session.commit()
        
        flash('Exam schedule deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting exam schedule: {str(e)}', 'danger')
    
    return redirect(url_for('schedule.index', exam_section_id=section_id))
