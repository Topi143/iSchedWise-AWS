"""
Settings routes - Academic settings management functionality
"""
import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models.settings import AcademicSettings, InstitutionSettings
from app.models.program import Program
from app.models.department import Department
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.archive import Archive
from app.models.faculty import FacultySubjectAssignment
from app.extensions import db
from app.utils.activity_logger import log_settings_change
from app.decorators import role_required
from datetime import datetime

settings_bp = Blueprint('settings', __name__)


def archive_current_schedules(reason, user_id):
    """
    Archive all active schedules before changing academic settings.
    
    Args:
        reason: The reason for archiving (e.g., 'Academic Year Change')
        user_id: The ID of the user performing the action
        
    Returns:
        Number of schedules archived
    """
    try:
        # Get all active schedules
        active_schedules = Schedule.query.filter_by(is_active=True).all()
        
        archived_count = 0
        for schedule in active_schedules:
            # Create archive record with all necessary information
            archive = Archive(
                # Foreign key references
                section_id=schedule.section_id,
                subject_id=schedule.subject_id,
                faculty_id=schedule.faculty_id,
                room_id=schedule.room_id,
                
                # Text-based historical data
                section_name=schedule.section.full_section_name if schedule.section else 'Unknown',
                subject_code=schedule.subject.subject_code if schedule.subject else 'Unknown',
                course_description=schedule.subject.course_description if schedule.subject else 'Unknown',
                faculty_name=schedule.faculty.full_name if schedule.faculty else 'TBA',
                room_number=schedule.room.room_number if schedule.room else 'TBA',
                building_name=schedule.room.building.building_name if schedule.room and schedule.room.building else 'TBA',
                program_name=schedule.section.program.program_name if schedule.section and schedule.section.program else 'Unknown',
                
                # Schedule details
                day_of_week=schedule.day_of_week,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                semester=schedule.semester,
                academic_year=schedule.academic_year,
                schedule_type=schedule.schedule_type,
                
                # Archive metadata
                original_schedule_id=schedule.id,
                archived_by=user_id,
                archive_reason=reason,
                archived_at=datetime.utcnow()
            )
            
            db.session.add(archive)
            
            # Mark the original schedule as inactive
            schedule.is_active = False
            
            archived_count += 1
        
        db.session.commit()
        return archived_count
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Error archiving schedules: {str(e)}')


def archive_current_exam_schedules(reason, user_id):
    """
    Archive all active exam schedules before changing exam period.
    
    Args:
        reason: The reason for archiving (e.g., 'Exam Period Change')
        user_id: The ID of the user performing the action
        
    Returns:
        Number of exam schedules archived
    """
    try:
        # Get all active exam schedules
        active_exam_schedules = ExamSchedule.query.filter_by(is_active=True).all()
        
        archived_count = 0
        for exam_schedule in active_exam_schedules:
            # Create archive record with all necessary information
            archive = Archive(
                # Foreign key references
                section_id=exam_schedule.section_id,
                subject_id=exam_schedule.subject_id,
                faculty_id=exam_schedule.faculty_id,
                room_id=exam_schedule.room_id,
                
                # Text-based historical data
                section_name=exam_schedule.section.full_section_name if exam_schedule.section else 'Unknown',
                subject_code=exam_schedule.subject.subject_code if exam_schedule.subject else 'Unknown',
                course_description=exam_schedule.subject.course_description if exam_schedule.subject else 'Unknown',
                faculty_name=exam_schedule.faculty.full_name if exam_schedule.faculty else 'TBA',
                room_number=exam_schedule.room.room_number if exam_schedule.room else 'TBA',
                building_name=exam_schedule.room.building.building_name if exam_schedule.room and exam_schedule.room.building else 'TBA',
                program_name=exam_schedule.section.program.program_name if exam_schedule.section and exam_schedule.section.program else 'Unknown',
                
                # Exam schedule details
                exam_date=exam_schedule.exam_date,
                start_time=exam_schedule.start_time,
                end_time=exam_schedule.end_time,
                semester=exam_schedule.semester,
                academic_year=exam_schedule.academic_year,
                schedule_type='exam',  # Mark as exam schedule
                exam_period=exam_schedule.exam_period,
                
                # Archive metadata
                original_schedule_id=exam_schedule.id,
                archived_by=user_id,
                archive_reason=reason,
                archived_at=datetime.utcnow()
            )
            
            db.session.add(archive)
            
            # Mark the original exam schedule as inactive
            exam_schedule.is_active = False
            
            archived_count += 1
        
        db.session.commit()
        return archived_count
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Error archiving exam schedules: {str(e)}')


def archive_faculty_assignments(academic_year, semester, reason, user_id):
    """
    Archive all faculty subject assignments for a specific academic year and semester using flags.
    
    Args:
        academic_year: The academic year to archive (e.g., '2024-2025')
        semester: The semester to archive (e.g., '1st Semester')
        reason: The reason for archiving
        user_id: The ID of the user performing the action
        
    Returns:
        Number of faculty assignments archived
    """
    try:
        # Get all active faculty subject assignments
        active_assignments = FacultySubjectAssignment.query.filter_by(is_archived=False).all()
        
        print(f"\n=== ARCHIVING FACULTY ASSIGNMENTS (FLAG-BASED) ===")
        print(f"Academic Year: {academic_year}, Semester: {semester}")
        print(f"Total assignments to archive: {len(active_assignments)}")
        print(f"Reason: {reason}")
        
        archived_count = 0
        for assignment in active_assignments:
            # Mark assignment as archived instead of creating archive record
            assignment.archive(user_id=user_id, reason=reason)
            archived_count += 1
        
        print(f"Total archived: {archived_count}")
        
        # Commit changes
        db.session.commit()
        print("=== ARCHIVING COMPLETE ===\n")
        
        return archived_count
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Error archiving faculty assignments: {str(e)}')


def restore_archived_faculty_assignments(academic_year, semester):
    """
    Restore archived faculty subject assignments for a specific academic year and semester using flags.
    
    Args:
        academic_year: The academic year to restore faculty assignments for
        semester: The semester to restore faculty assignments for
        
    Returns:
        Number of faculty assignments restored
    """
    try:
        # Get all archived faculty assignments for this academic year and semester
        archived_assignments = FacultySubjectAssignment.query.filter(
            FacultySubjectAssignment.academic_year == academic_year,
            FacultySubjectAssignment.semester == semester,
            FacultySubjectAssignment.is_archived == True
        ).all()
        
        if not archived_assignments:
            return 0
        
        restored_count = 0
        
        for assignment in archived_assignments:
            # Unarchive the assignment
            assignment.unarchive()
            restored_count += 1
        
        db.session.commit()
        return restored_count
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Error restoring faculty assignments: {str(e)}')


def restore_archived_schedules(academic_year, semester):
    """
    Restore archived class schedules (not exam schedules) for a specific academic year and semester.
    This function first checks for existing inactive schedules that can be reactivated,
    and only creates new schedules if no matching inactive schedule exists.
    
    Args:
        academic_year: The academic year to restore schedules for
        semester: The semester to restore schedules for
        
    Returns:
        Number of schedules restored
    """
    try:
        # Get all archived CLASS schedules (not exams) for this academic year and semester
        archived_schedules = Archive.query.filter(
            Archive.academic_year == academic_year,
            Archive.semester == semester,
            Archive.schedule_type != 'exam',  # Exclude exam schedules
            Archive.day_of_week.isnot(None)  # Must have day_of_week for class schedules
        ).all()
        
        if not archived_schedules:
            return 0
        
        restored_count = 0
        archives_to_delete = []
        
        for archive in archived_schedules:
            # Skip if day_of_week is None (shouldn't happen with filter above, but extra safety)
            if not archive.day_of_week:
                continue
                
            # Check if a schedule with the same details already exists and is active
            existing_active_schedule = Schedule.query.filter_by(
                section_id=archive.section_id,
                subject_id=archive.subject_id,
                day_of_week=archive.day_of_week,
                start_time=archive.start_time,
                end_time=archive.end_time,
                is_active=True
            ).first()
            
            # Skip if already active
            if existing_active_schedule:
                continue
            
            # Check if there's an existing INACTIVE schedule we can reactivate
            # This prevents unique constraint violations
            existing_inactive_schedule = Schedule.query.filter_by(
                section_id=archive.section_id,
                subject_id=archive.subject_id,
                day_of_week=archive.day_of_week,
                start_time=archive.start_time,
                end_time=archive.end_time,
                academic_year=archive.academic_year,
                semester=archive.semester,
                is_active=False
            ).first()
            
            if existing_inactive_schedule:
                # Reactivate the existing inactive schedule
                existing_inactive_schedule.is_active = True
                # Update faculty and room in case they changed
                existing_inactive_schedule.faculty_id = archive.faculty_id
                existing_inactive_schedule.room_id = archive.room_id
                restored_count += 1
                # Mark this archive for deletion after successful restoration
                archives_to_delete.append(archive)
            else:
                # Create a new schedule from the archive (no existing schedule found)
                restored_schedule = Schedule(
                    section_id=archive.section_id,
                    subject_id=archive.subject_id,
                    faculty_id=archive.faculty_id,
                    room_id=archive.room_id,
                    day_of_week=archive.day_of_week,
                    start_time=archive.start_time,
                    end_time=archive.end_time,
                    semester=archive.semester,
                    academic_year=archive.academic_year,
                    schedule_type=archive.schedule_type if archive.schedule_type != 'exam' else 'lecture',
                    is_active=True
                )
                
                db.session.add(restored_schedule)
                restored_count += 1
                
                # Mark this archive for deletion after successful restoration
                archives_to_delete.append(archive)
        
        # Delete the archives that were successfully restored
        for archive in archives_to_delete:
            db.session.delete(archive)
        
        db.session.commit()
        return restored_count
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Error restoring schedules: {str(e)}')


def restore_archived_exam_schedules(academic_year, semester, exam_period):
    """
    Restore archived exam schedules for a specific academic year, semester, and exam period.
    This function first checks for existing inactive exam schedules that can be reactivated,
    and only creates new exam schedules if no matching inactive exam schedule exists.
    
    Args:
        academic_year: The academic year to restore exam schedules for
        semester: The semester to restore exam schedules for
        exam_period: The exam period to restore exam schedules for
        
    Returns:
        Number of exam schedules restored
    """
    try:
        # Get all archived exam schedules for this academic year, semester, and exam period
        archived_exam_schedules = Archive.query.filter(
            Archive.academic_year == academic_year,
            Archive.semester == semester,
            Archive.exam_period == exam_period,
            Archive.schedule_type == 'exam',
            Archive.exam_date.isnot(None)  # Must have exam_date for exam schedules
        ).all()
        
        if not archived_exam_schedules:
            return 0
        
        restored_count = 0
        archives_to_delete = []
        
        for archive in archived_exam_schedules:
            # Skip if exam_date is None (shouldn't happen with filter above, but extra safety)
            if not archive.exam_date:
                continue
                
            # Check if an exam schedule with the same details already exists and is active
            existing_active_exam = ExamSchedule.query.filter_by(
                section_id=archive.section_id,
                subject_id=archive.subject_id,
                exam_date=archive.exam_date,
                start_time=archive.start_time,
                end_time=archive.end_time,
                is_active=True
            ).first()
            
            # Skip if already active
            if existing_active_exam:
                continue
            
            # Check if there's an existing INACTIVE exam schedule we can reactivate
            # This prevents unique constraint violations
            existing_inactive_exam = ExamSchedule.query.filter_by(
                section_id=archive.section_id,
                subject_id=archive.subject_id,
                exam_date=archive.exam_date,
                start_time=archive.start_time,
                end_time=archive.end_time,
                academic_year=archive.academic_year,
                semester=archive.semester,
                exam_period=archive.exam_period,
                is_active=False
            ).first()
            
            if existing_inactive_exam:
                # Reactivate the existing inactive exam schedule
                existing_inactive_exam.is_active = True
                # Update faculty and room in case they changed
                existing_inactive_exam.faculty_id = archive.faculty_id
                existing_inactive_exam.room_id = archive.room_id
                restored_count += 1
                # Mark this archive for deletion after successful restoration
                archives_to_delete.append(archive)
            else:
                # Create a new exam schedule from the archive (no existing schedule found)
                restored_exam_schedule = ExamSchedule(
                    section_id=archive.section_id,
                    subject_id=archive.subject_id,
                    faculty_id=archive.faculty_id,
                    room_id=archive.room_id,
                    exam_date=archive.exam_date,
                    start_time=archive.start_time,
                    end_time=archive.end_time,
                    semester=archive.semester,
                    academic_year=archive.academic_year,
                    exam_period=archive.exam_period,
                    is_active=True
                )
                
                db.session.add(restored_exam_schedule)
                restored_count += 1
                
                # Mark this archive for deletion after successful restoration
                archives_to_delete.append(archive)
        
        # Delete the archives that were successfully restored
        for archive in archives_to_delete:
            db.session.delete(archive)
        
        db.session.commit()
        return restored_count
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f'Error restoring exam schedules: {str(e)}')


@settings_bp.route('/settings')
@login_required
def index():
    """Settings page"""
    # Get current active settings
    active_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    # Get all settings history
    all_settings = AcademicSettings.query.order_by(AcademicSettings.created_at.desc()).all()
    
    # Get institution settings (admin only feature, but pass to template for display)
    institution_settings = InstitutionSettings.get_settings()
    
    # Get branding settings for the System tab
    branding_settings = institution_settings
    
    # Get departments for the Departments tab
    if current_user.is_admin:
        departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    elif current_user.is_dean:
        # Deans only see departments linked to their programs
        from app.models.program import Program
        dean_program_ids = current_user.get_program_ids() or []
        if dean_program_ids:
            dean_department_ids = [
                cid for (cid,) in db.session.query(db.distinct(Program.department_id)).filter(
                    Program.id.in_(dean_program_ids),
                    Program.department_id.isnot(None)
                ).all()
            ]
            departments = Department.query.filter(
                Department.id.in_(dean_department_ids),
                Department.is_active == True
            ).order_by(Department.department_name).all() if dean_department_ids else []
        else:
            departments = []
    else:
        departments = []
    
    # Quick stats for the sidebar panel
    from app.models.faculty import Faculty
    from app.models.building import Building, Room
    from app.models.section import Section

    quick_stats = {
        'faculty': Faculty.query.filter_by(is_active=True).count(),
        'sections': Section.query.count(),
        'rooms': Room.query.filter_by(is_available=True).count(),
        'buildings': Building.query.filter_by(is_active=True).count(),
        'departments': len(departments),
    }
    if active_settings:
        quick_stats['schedules'] = Schedule.query.filter_by(
            is_active=True,
            academic_year=active_settings.academic_year,
            semester=active_settings.semester
        ).count()
    else:
        quick_stats['schedules'] = 0

    return render_template('settings.html', 
                         user=current_user,
                         active_settings=active_settings,
                         all_settings=all_settings,
                         institution_settings=institution_settings,
                         branding_settings=branding_settings,
                         departments=departments,
                         quick_stats=quick_stats)


@settings_bp.route('/settings/update', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def update():
    """Update academic settings and archive existing schedules (Admin only)"""
    from datetime import time as dt_time, datetime as dt_datetime

    def _parse_hhmm(value, fallback):
        try:
            return dt_datetime.strptime(value, '%H:%M').time()
        except Exception:
            return fallback

    def _to_minutes(t):
        return t.hour * 60 + t.minute
    
    try:
        academic_year = request.form.get('academic_year')
        semester = request.form.get('semester')
        exam_period = request.form.get('exam_period')
        available_semesters = request.form.getlist('available_semesters')  # Checkboxes return list
        operation_days = request.form.getlist('operation_days')  # Checkboxes return list
        default_faculty_max_units = request.form.get('default_faculty_max_units', type=int)

        # Get current active settings to check if they're changing
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        term_changed = bool(
            current_settings and (
                current_settings.academic_year != academic_year or
                current_settings.semester != semester
            )
        )
        exam_period_changed_preparse = bool(
            current_settings and current_settings.exam_period != exam_period
        )
        
        # Get exam period date range
        exam_period_start_str = request.form.get('exam_period_start', '')
        exam_period_end_str = request.form.get('exam_period_end', '')
        
        # Parse exam period dates
        exam_period_start = None
        exam_period_end = None
        if exam_period_start_str:
            try:
                exam_period_start = dt_datetime.strptime(exam_period_start_str, '%Y-%m-%d').date()
            except:
                exam_period_start = None
        if exam_period_end_str:
            try:
                exam_period_end = dt_datetime.strptime(exam_period_end_str, '%Y-%m-%d').date()
            except:
                exam_period_end = None
        
        # Validate exam period dates
        if exam_period_start and exam_period_end and exam_period_end < exam_period_start and not (term_changed or exam_period_changed_preparse):
            flash('Exam period end date must be after start date.', 'error')
            return redirect(url_for('settings.index'))
        
        # Get class schedule time range (now as time strings like "07:00")
        schedule_start_time_str = request.form.get('schedule_start_time', '07:00')
        schedule_end_time_str = request.form.get('schedule_end_time', '20:00')
        schedule_start_time = _parse_hhmm(schedule_start_time_str, dt_time(7, 0))
        schedule_end_time = _parse_hhmm(schedule_end_time_str, dt_time(20, 0))
        schedule_start_hour = schedule_start_time.hour
        schedule_end_hour = schedule_end_time.hour
        
        # Get exam schedule time range (now as time strings like "07:00")
        exam_start_time_str = request.form.get('exam_start_time', '07:00')
        exam_end_time_str = request.form.get('exam_end_time', '17:00')
        exam_start_time = _parse_hhmm(exam_start_time_str, dt_time(7, 0))
        exam_end_time = _parse_hhmm(exam_end_time_str, dt_time(17, 0))
        exam_start_hour = exam_start_time.hour
        exam_end_hour = exam_end_time.hour
        
        # Get lunch break times
        exam_lunch_start_str = request.form.get('exam_lunch_start', '12:00')
        exam_lunch_end_str = request.form.get('exam_lunch_end', '13:00')
        exam_slot_duration = request.form.get('exam_slot_duration', type=int)
        exam_duration_limit = request.form.get('exam_duration_limit', type=int)
        
        # Parse lunch times
        exam_lunch_start = _parse_hhmm(exam_lunch_start_str, dt_time(12, 0))
        exam_lunch_end = _parse_hhmm(exam_lunch_end_str, dt_time(13, 0))
        
        # Normalize available semesters with business rule:
        # selecting 2nd Semester automatically includes 1st Semester.
        valid_semesters_order = ['1st Semester', '2nd Semester', 'Summer']
        available_semesters = [s for s in available_semesters if s in valid_semesters_order]
        if '2nd Semester' in available_semesters and '1st Semester' not in available_semesters:
            available_semesters.append('1st Semester')
        if not available_semesters:
            available_semesters = ['1st Semester', '2nd Semester']

        available_semesters_set = set(available_semesters)
        available_semesters = [s for s in valid_semesters_order if s in available_semesters_set]
        available_semesters_str = ','.join(available_semesters)

        if semester not in available_semesters:
            semester = '2nd Semester' if '2nd Semester' in available_semesters else available_semesters[0]
        
        # Convert operation_days list to comma-separated string
        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        operation_days = [d for d in operation_days if d in valid_days]
        if not operation_days:
            operation_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']  # Default
        operation_days_str = ','.join(operation_days)
        
        # Validate required fields
        if not all([academic_year, semester, exam_period]):
            flash('Academic year, semester, and exam period are required.', 'error')
            return redirect(url_for('settings.index'))
        
        
        # Validate class schedule time range
        if schedule_start_time >= schedule_end_time:
            flash('Class schedule start time must be before end time.', 'error')
            return redirect(url_for('settings.index'))
        
        # Validate exam schedule time range
        if exam_start_time >= exam_end_time:
            flash('Exam schedule start time must be before end time.', 'error')
            return redirect(url_for('settings.index'))
        
        # Validate exam slot duration
        if exam_slot_duration not in [30, 60, 90, 120]:
            exam_slot_duration = 30
        
        # Validate exam duration limit
        if exam_duration_limit not in [60, 90, 120, 150, 180, 240]:
            exam_duration_limit = 120
        
        # Validate lunch break within exam hours
        exam_start_mins = _to_minutes(exam_start_time)
        exam_end_mins = _to_minutes(exam_end_time)
        lunch_start_mins = _to_minutes(exam_lunch_start)
        lunch_end_mins = _to_minutes(exam_lunch_end)
        if lunch_start_mins < exam_start_mins or lunch_end_mins > exam_end_mins:
            flash('Lunch break must be within exam schedule hours.', 'warning')
        
        # Validate faculty max units
        if default_faculty_max_units is None or default_faculty_max_units < 1:
            default_faculty_max_units = 24  # Default fallback
        
        # Check if academic year or semester is changing
        settings_changed = False
        exam_period_changed = False
        exam_period_dates_cleared = False
        
        if current_settings:
            if (current_settings.academic_year != academic_year or 
                current_settings.semester != semester):
                settings_changed = True
            if current_settings.exam_period != exam_period:
                exam_period_changed = True
        
        # Archive current schedules if academic year or semester is changing
        archived_count = 0
        archived_exam_count = 0
        archived_faculty_count = 0
        
        print(f"\n=== SETTINGS UPDATE ===")
        print(f"Current settings: {current_settings.academic_year if current_settings else 'None'} - {current_settings.semester if current_settings else 'None'}")
        print(f"New settings: {academic_year} - {semester}")
        print(f"Settings changed: {settings_changed}")
        print(f"Exam period changed: {exam_period_changed}")

        # Never carry exam period date range across a new academic term or exam period change.
        if settings_changed or exam_period_changed:
            exam_period_start = None
            exam_period_end = None
            exam_period_dates_cleared = True
        
        if settings_changed:
            # Archive both class schedules AND exam schedules when semester/year changes
            archive_reason = f'Academic settings changed from {current_settings.academic_year} - {current_settings.semester} to {academic_year} - {semester}'
            archived_count = archive_current_schedules(archive_reason, current_user.id)
            
            # Also archive exam schedules since it's a new academic period
            exam_archive_reason = f'New semester/academic year: {academic_year} - {semester}'
            archived_exam_count = archive_current_exam_schedules(exam_archive_reason, current_user.id)
            
            # Archive faculty subject assignments for the old academic year/semester
            faculty_archive_reason = f'Academic settings changed from {current_settings.academic_year} - {current_settings.semester} to {academic_year} - {semester}'
            archived_faculty_count = archive_faculty_assignments(
                current_settings.academic_year,
                current_settings.semester,
                faculty_archive_reason,
                current_user.id
            )
        elif exam_period_changed:
            # Only archive exam schedules if just the exam period changed (not semester/year)
            exam_archive_reason = f'Exam period changed from {current_settings.exam_period} to {exam_period}'
            archived_exam_count = archive_current_exam_schedules(exam_archive_reason, current_user.id)
        
        # Deactivate all current settings
        AcademicSettings.query.update({AcademicSettings.is_active: False})
        
        # Create new settings
        new_settings = AcademicSettings(
            academic_year=academic_year,
            semester=semester,
            exam_period=exam_period,
            exam_period_start=exam_period_start,
            exam_period_end=exam_period_end,
            available_semesters=available_semesters_str,
            operation_days=operation_days_str,
            schedule_start_hour=schedule_start_hour,
            schedule_end_hour=schedule_end_hour,
            exam_start_hour=exam_start_hour,
            exam_end_hour=exam_end_hour,
            schedule_start_time=schedule_start_time,
            schedule_end_time=schedule_end_time,
            exam_start_time=exam_start_time,
            exam_end_time=exam_end_time,
            exam_lunch_start=exam_lunch_start,
            exam_lunch_end=exam_lunch_end,
            exam_slot_duration=exam_slot_duration,
            exam_duration_limit=exam_duration_limit,
            default_faculty_max_units=default_faculty_max_units,
            is_active=True
        )
        
        db.session.add(new_settings)
        db.session.flush()
        
        # Log activity
        log_settings_change(f'Updated academic settings to {academic_year} - {semester} - {exam_period}', {
            'academic_year': academic_year,
            'semester': semester,
            'exam_period': exam_period,
            'archived_schedules': archived_count,
            'archived_exam_schedules': archived_exam_count,
            'archived_faculty_assignments': archived_faculty_count
        })
        
        db.session.commit()
        
        # Try to restore archived schedules for the new academic year/semester
        restored_count = 0
        restored_exam_count = 0
        restored_faculty_count = 0
        
        try:
            restored_count = restore_archived_schedules(academic_year, semester)
        except Exception as restore_error:
            # Log the error but don't fail the entire operation
            flash(f'Warning: Could not restore archived schedules: {str(restore_error)}', 'error')
        
        try:
            restored_exam_count = restore_archived_exam_schedules(academic_year, semester, exam_period)
        except Exception as restore_error:
            # Log the error but don't fail the entire operation
            flash(f'Warning: Could not restore archived exam schedules: {str(restore_error)}', 'error')
        
        try:
            restored_faculty_count = restore_archived_faculty_assignments(academic_year, semester)
        except Exception as restore_error:
            # Log the error but don't fail the entire operation
            flash(f'Warning: Could not restore archived faculty assignments: {str(restore_error)}', 'error')
        
        # Provide feedback to user
        messages = []
        if archived_count > 0:
            messages.append(f'{archived_count} class schedule(s) archived')
        if archived_exam_count > 0:
            messages.append(f'{archived_exam_count} exam schedule(s) archived')
        if archived_faculty_count > 0:
            messages.append(f'{archived_faculty_count} faculty assignment(s) archived')
        if restored_count > 0:
            messages.append(f'{restored_count} class schedule(s) restored')
        if restored_exam_count > 0:
            messages.append(f'{restored_exam_count} exam schedule(s) restored')
        if restored_faculty_count > 0:
            messages.append(f'{restored_faculty_count} faculty assignment(s) restored')
        if exam_period_dates_cleared:
            messages.append('exam period dates reset for the new academic term')
        
        if messages:
            flash(f'Academic settings updated! {", ".join(messages)}.', 'success')
        else:
            flash('Academic settings updated successfully!', 'success')
        
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating settings: {str(e)}', 'error')
        return redirect(url_for('settings.index'))


@settings_bp.route('/settings/<int:settings_id>/activate', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def activate(settings_id):
    """Activate a previous settings configuration and archive current schedules (Admin only)"""
    try:
        settings = AcademicSettings.query.get_or_404(settings_id)
        
        # Get current active settings to check if they're changing
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Check if academic year or semester is changing
        settings_changed = False
        exam_period_changed = False
        
        if current_settings:
            if (current_settings.academic_year != settings.academic_year or 
                current_settings.semester != settings.semester):
                settings_changed = True
            if current_settings.exam_period != settings.exam_period:
                exam_period_changed = True
        
        # Archive current schedules if academic year or semester is changing
        archived_count = 0
        archived_exam_count = 0
        archived_faculty_count = 0
        
        if settings_changed and current_settings:
            # Archive both class schedules AND exam schedules when semester/year changes
            archive_reason = f'Academic settings changed from {current_settings.academic_year} - {current_settings.semester} to {settings.academic_year} - {settings.semester}'
            archived_count = archive_current_schedules(archive_reason, current_user.id)
            
            # Also archive exam schedules since it's a new academic period
            exam_archive_reason = f'New semester/academic year: {settings.academic_year} - {settings.semester}'
            archived_exam_count = archive_current_exam_schedules(exam_archive_reason, current_user.id)
            
            # Archive faculty subject assignments for the old academic year/semester
            faculty_archive_reason = f'Academic settings changed from {current_settings.academic_year} - {current_settings.semester} to {settings.academic_year} - {settings.semester}'
            archived_faculty_count = archive_faculty_assignments(
                current_settings.academic_year,
                current_settings.semester,
                faculty_archive_reason,
                current_user.id
            )
        elif exam_period_changed and current_settings:
            # Only archive exam schedules if just the exam period changed (not semester/year)
            exam_archive_reason = f'Exam period changed from {current_settings.exam_period} to {settings.exam_period}'
            archived_exam_count = archive_current_exam_schedules(exam_archive_reason, current_user.id)
        
        # Deactivate all current settings
        AcademicSettings.query.update({AcademicSettings.is_active: False})
        
        # Activate the selected settings
        settings.is_active = True
        db.session.commit()
        
        # Try to restore archived schedules for the activated academic year/semester
        restored_count = 0
        restored_exam_count = 0
        restored_faculty_count = 0
        
        try:
            restored_count = restore_archived_schedules(settings.academic_year, settings.semester)
        except Exception as restore_error:
            # Log the error but don't fail the entire operation
            flash(f'Warning: Could not restore archived schedules: {str(restore_error)}', 'error')
        
        try:
            restored_exam_count = restore_archived_exam_schedules(settings.academic_year, settings.semester, settings.exam_period)
        except Exception as restore_error:
            # Log the error but don't fail the entire operation
            flash(f'Warning: Could not restore archived exam schedules: {str(restore_error)}', 'error')
        
        try:
            restored_faculty_count = restore_archived_faculty_assignments(settings.academic_year, settings.semester)
        except Exception as restore_error:
            # Log the error but don't fail the entire operation
            flash(f'Warning: Could not restore archived faculty assignments: {str(restore_error)}', 'error')
        
        # Provide feedback to user
        messages = []
        if archived_count > 0:
            messages.append(f'{archived_count} class schedule(s) archived')
        if archived_exam_count > 0:
            messages.append(f'{archived_exam_count} exam schedule(s) archived')
        if archived_faculty_count > 0:
            messages.append(f'{archived_faculty_count} faculty assignment(s) archived')
        if restored_count > 0:
            messages.append(f'{restored_count} class schedule(s) restored')
        if restored_exam_count > 0:
            messages.append(f'{restored_exam_count} exam schedule(s) restored')
        if restored_faculty_count > 0:
            messages.append(f'{restored_faculty_count} faculty assignment(s) restored')
        
        if messages:
            flash(f'Activated {settings.academic_year} - {settings.semester} - {settings.exam_period}. {", ".join(messages)}.', 'success')
        else:
            flash(f'Activated settings: {settings.academic_year} - {settings.semester} - {settings.exam_period}', 'success')
        
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error activating settings: {str(e)}', 'error')
        return redirect(url_for('settings.index'))


@settings_bp.route('/settings/<int:settings_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def delete(settings_id):
    """Delete a settings configuration (Admin only)"""
    try:
        settings = AcademicSettings.query.get_or_404(settings_id)
        
        # Prevent deletion of active settings
        if settings.is_active:
            flash('Cannot delete active settings. Please activate another configuration first.', 'error')
            return redirect(url_for('settings.index'))
        
        db.session.delete(settings)
        db.session.commit()
        
        flash('Settings configuration deleted successfully!', 'success')
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting settings: {str(e)}', 'error')
        return redirect(url_for('settings.index'))


# ============================================================================
# Institution Settings Routes (Admin Only)
# ============================================================================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@settings_bp.route('/settings/institution/update', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def update_institution():
    """Update institution settings (admin only)"""
    try:
        institution_name = request.form.get('institution_name', '').strip()
        institution_head = request.form.get('institution_head', '').strip() or None
        excel_header_line1 = request.form.get('excel_header_line1', '').strip() or 'Republic of the Philippines'
        excel_header_line2 = request.form.get('excel_header_line2', '').strip() or 'Municipality of Norzagaray'
        excel_schedule_color = request.form.get('excel_schedule_color', '').strip()
        if excel_schedule_color and not (len(excel_schedule_color) == 7 and excel_schedule_color.startswith('#')):
            excel_schedule_color = ''
        
        # Validate institution name
        if not institution_name:
            flash('Institution name is required.', 'error')
            return redirect(url_for('settings.index'))
        
        if len(institution_name) > 255:
            flash('Institution name must be 255 characters or less.', 'error')
            return redirect(url_for('settings.index'))
        
        # Get or create institution settings
        settings = InstitutionSettings.get_settings()
        
        # Update institution name and department president
        old_name = settings.institution_name
        old_president = settings.institution_head
        settings.institution_name = institution_name
        settings.institution_head = institution_head
        settings.excel_header_line1 = excel_header_line1
        settings.excel_header_line2 = excel_header_line2
        settings.excel_schedule_color = excel_schedule_color
        settings.updated_by = current_user.id
        
        # Handle logo upload
        if 'institution_logo' in request.files:
            file = request.files['institution_logo']
            if file and file.filename and allowed_file(file.filename):
                # Create upload folder if it doesn't exist
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'institution_logos')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(upload_folder, unique_filename)
                
                # Delete old logo if exists
                if settings.institution_logo:
                    old_logo_path = os.path.join(current_app.root_path, 'static', settings.institution_logo)
                    if os.path.exists(old_logo_path):
                        try:
                            os.remove(old_logo_path)
                        except Exception:
                            pass  # Ignore errors when deleting old file
                
                # Save new logo
                file.save(filepath)
                settings.institution_logo = f"uploads/institution_logos/{unique_filename}"
        
        # Handle right logo upload
        if 'institution_logo_right' in request.files:
            file_right = request.files['institution_logo_right']
            if file_right and file_right.filename and allowed_file(file_right.filename):
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'institution_logos')
                os.makedirs(upload_folder, exist_ok=True)
                
                filename_right = secure_filename(file_right.filename)
                unique_filename_right = f"{uuid.uuid4().hex}_{filename_right}"
                filepath_right = os.path.join(upload_folder, unique_filename_right)
                
                # Delete old right logo if exists
                if settings.institution_logo_right:
                    old_right_path = os.path.join(current_app.root_path, 'static', settings.institution_logo_right)
                    if os.path.exists(old_right_path):
                        try:
                            os.remove(old_right_path)
                        except Exception:
                            pass
                
                file_right.save(filepath_right)
                settings.institution_logo_right = f"uploads/institution_logos/{unique_filename_right}"
        
        db.session.commit()
        
        # Log activity
        log_settings_change(f'Updated institution settings: {institution_name}', {
            'old_name': old_name,
            'new_name': institution_name,
            'old_president': old_president,
            'new_president': institution_head,
            'logo_updated': 'institution_logo' in request.files and request.files['institution_logo'].filename,
            'logo_right_updated': 'institution_logo_right' in request.files and request.files['institution_logo_right'].filename
        })
        
        flash('Institution settings updated successfully!', 'success')
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating institution settings: {str(e)}', 'error')
        return redirect(url_for('settings.index'))


@settings_bp.route('/settings/institution/remove-logo', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def remove_institution_logo():
    """Remove institution logo (admin only)"""
    try:
        settings = InstitutionSettings.get_settings()
        
        # Delete logo file if exists
        if settings.institution_logo:
            logo_path = os.path.join(current_app.root_path, 'static', settings.institution_logo)
            if os.path.exists(logo_path):
                try:
                    os.remove(logo_path)
                except Exception:
                    pass  # Ignore errors when deleting file
            
            settings.institution_logo = None
            settings.updated_by = current_user.id
            db.session.commit()
            
            flash('Institution logo removed successfully!', 'success')
        else:
            flash('No logo to remove.', 'info')
        
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing logo: {str(e)}', 'error')
        return redirect(url_for('settings.index'))


@settings_bp.route('/settings/institution/remove-logo-right', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def remove_institution_logo_right():
    """Remove right institution logo (admin only)"""
    try:
        settings = InstitutionSettings.get_settings()
        
        if settings.institution_logo_right:
            logo_path = os.path.join(current_app.root_path, 'static', settings.institution_logo_right)
            if os.path.exists(logo_path):
                try:
                    os.remove(logo_path)
                except Exception:
                    pass
            
            settings.institution_logo_right = None
            settings.updated_by = current_user.id
            db.session.commit()
            
            flash('Right logo removed successfully!', 'success')
        else:
            flash('No right logo to remove.', 'info')
        
        return redirect(url_for('settings.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing right logo: {str(e)}', 'error')
        return redirect(url_for('settings.index'))


@settings_bp.route('/settings/text-size/update', methods=['POST'])
@login_required
def update_text_size():
    """Update user's text size preference (any authenticated user)"""
    try:
        data = request.get_json()
        if not data or 'text_size' not in data:
            return jsonify({'success': False, 'error': 'Missing text_size parameter'}), 400
        
        text_size = int(data['text_size'])
        
        # Validate range
        if text_size < 70 or text_size > 150:
            return jsonify({'success': False, 'error': 'Text size must be between 70 and 150'}), 400
        
        current_user.text_size = text_size
        db.session.commit()
        
        return jsonify({'success': True, 'text_size': text_size}), 200
        
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid text_size value'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/settings/dark-mode/update', methods=['POST'])
@login_required
def update_dark_mode():
    """Update user's dark mode preference (any authenticated user)"""
    try:
        data = request.get_json()
        if not data or 'dark_mode' not in data:
            return jsonify({'success': False, 'error': 'Missing dark_mode parameter'}), 400
        
        dark_mode = bool(data['dark_mode'])
        
        current_user.dark_mode = dark_mode
        db.session.commit()
        
        return jsonify({'success': True, 'dark_mode': dark_mode}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Department Management (Settings → Departments tab) ──

@settings_bp.route('/settings/departments/add', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def add_department():
    """Add a new department"""
    try:
        department_name = request.form.get('department_name', '').strip()
        department_code = request.form.get('department_code', '').strip().upper() or None
        secretary_name = request.form.get('secretary_name', '').strip() or None

        if not department_name:
            flash('Department name is required.', 'error')
            return redirect(url_for('settings.index'))

        # Check for duplicates
        existing = Department.query.filter(
            db.func.lower(Department.department_name) == department_name.lower()
        ).first()
        if existing:
            flash(f'A department named "{department_name}" already exists.', 'error')
            return redirect(url_for('settings.index'))

        new_department = Department(
            department_name=department_name,
            department_code=department_code,
            secretary_name=secretary_name,
        )
        db.session.add(new_department)
        db.session.commit()

        log_settings_change(f'Added department: {department_name}', {
            'department_name': department_name,
            'department_code': department_code,
        })

        flash(f'Department "{department_name}" has been added!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding department: {str(e)}', 'error')

    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/departments/edit', methods=['POST'])
@login_required
@role_required('admin', 'super_admin', 'dean')
def edit_department():
    """Edit an existing department (admins: any, deans: only their assigned departments)"""
    try:
        department_id = request.form.get('department_id', type=int)
        department_name = request.form.get('department_name', '').strip()
        department_code = request.form.get('department_code', '').strip().upper() or None
        secretary_name = request.form.get('secretary_name', '').strip() or None

        if not department_id or not department_name:
            flash('Department ID and name are required.', 'error')
            return redirect(url_for('settings.index'))

        department = Department.query.get(department_id)
        if not department:
            flash('Department not found.', 'error')
            return redirect(url_for('settings.index'))

        # Deans can only edit departments assigned to their programs
        if current_user.is_dean:
            dean_program_ids = current_user.get_program_ids() or []
            department_program_ids = [d.id for d in department.programs if not d.is_archived]
            if not any(did in dean_program_ids for did in department_program_ids):
                flash('You do not have permission to edit this department.', 'error')
                return redirect(url_for('settings.index'))

        # Check for duplicates (excluding self)
        existing = Department.query.filter(
            db.func.lower(Department.department_name) == department_name.lower(),
            Department.id != department_id
        ).first()
        if existing:
            flash(f'A department named "{department_name}" already exists.', 'error')
            return redirect(url_for('settings.index'))

        old_name = department.department_name
        department.department_name = department_name
        department.department_code = department_code
        department.secretary_name = secretary_name
        db.session.commit()

        log_settings_change(f'Updated department: {old_name} → {department_name}', {
            'department_id': department_id,
            'old_name': old_name,
            'new_name': department_name,
        })

        flash(f'Department "{department_name}" has been updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating department: {str(e)}', 'error')

    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/departments/delete', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def delete_department():
    """Delete a department (only if no programs are assigned)"""
    try:
        department_id = request.form.get('department_id', type=int)

        if not department_id:
            flash('Department ID is required.', 'error')
            return redirect(url_for('settings.index'))

        department = Department.query.get(department_id)
        if not department:
            flash('Department not found.', 'error')
            return redirect(url_for('settings.index'))

        # Check if any programs are assigned
        assigned = [d for d in department.programs if not d.is_archived]
        if assigned:
            dept_codes = ', '.join(d.program_code for d in assigned)
            flash(f'Cannot delete "{department.department_name}" — it is assigned to: {dept_codes}. Remove the assignment first.', 'error')
            return redirect(url_for('settings.index'))

        name = department.department_name
        db.session.delete(department)
        db.session.commit()

        log_settings_change(f'Deleted department: {name}', {'department_name': name})

        flash(f'Department "{name}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting department: {str(e)}', 'error')

    return redirect(url_for('settings.index'))
