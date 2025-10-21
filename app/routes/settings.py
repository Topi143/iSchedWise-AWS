"""
Settings routes - Academic settings management functionality
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models.settings import AcademicSettings
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.archive import Archive
from app.models.faculty import FacultySubjectAssignment
from app.extensions import db
from app.utils.activity_logger import log_settings_change
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
                department_name=schedule.section.department.department_name if schedule.section and schedule.section.department else 'Unknown',
                
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
                department_name=exam_schedule.section.department.department_name if exam_schedule.section and exam_schedule.section.department else 'Unknown',
                
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
            existing_schedule = Schedule.query.filter_by(
                section_id=archive.section_id,
                subject_id=archive.subject_id,
                day_of_week=archive.day_of_week,
                start_time=archive.start_time,
                end_time=archive.end_time,
                is_active=True
            ).first()
            
            # Only restore if no active schedule exists with the same details
            if not existing_schedule:
                # Create a new schedule from the archive
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
            existing_exam_schedule = ExamSchedule.query.filter_by(
                section_id=archive.section_id,
                subject_id=archive.subject_id,
                exam_date=archive.exam_date,
                start_time=archive.start_time,
                end_time=archive.end_time,
                is_active=True
            ).first()
            
            # Only restore if no active exam schedule exists with the same details
            if not existing_exam_schedule:
                # Create a new exam schedule from the archive
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
    
    return render_template('settings.html', 
                         user=current_user,
                         active_settings=active_settings,
                         all_settings=all_settings)


@settings_bp.route('/settings/update', methods=['POST'])
@login_required
def update():
    """Update academic settings and archive existing schedules"""
    try:
        academic_year = request.form.get('academic_year')
        semester = request.form.get('semester')
        exam_period = request.form.get('exam_period')
        
        # Validate required fields
        if not all([academic_year, semester, exam_period]):
            flash('Academic year, semester, and exam period are required.', 'error')
            return redirect(url_for('settings.index'))
        
        # Get current active settings to check if they're changing
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Check if academic year or semester is changing
        settings_changed = False
        exam_period_changed = False
        
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
def activate(settings_id):
    """Activate a previous settings configuration and archive current schedules"""
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
def delete(settings_id):
    """Delete a settings configuration"""
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
