"""
Faculty management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from app.extensions import db
from app.models import Faculty, FacultySubjectAssignment, Department, Subject, Curriculum, YearLevel, Semester
from app.models.schedule import Schedule
from app.models.settings import AcademicSettings
from app.utils.activity_logger import log_create, log_edit, log_delete, log_archive, log_unarchive

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')


def get_filter_params():
    """Get department_id filter from request args"""
    department_id = request.args.get('department_id', type=int)
    return {'department_id': department_id} if department_id else {}


def build_redirect_params(faculty_id=None, **kwargs):
    """Build redirect parameters preserving filters"""
    params = get_filter_params()
    
    if faculty_id:
        params['faculty_id'] = faculty_id
    
    # Add any additional parameters
    params.update(kwargs)
    return params


@faculty_bp.route('/')
@login_required
def index():
    """Faculty management page"""
    # Get current academic settings
    active_settings = AcademicSettings.query.filter_by(is_active=True).first()
    if not active_settings:
        flash('No active academic settings found. Please configure settings first.', 'error')
        return redirect(url_for('main.index'))
    
    # Get all active (non-archived) faculties and departments
    faculties = Faculty.query.filter_by(is_archived=False).order_by(Faculty.full_name).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    
    # Calculate workload for each faculty (filtered by current academic settings)
    faculty_workloads = {}
    for faculty in faculties:
        # Get total units from subject assignments (for current academic period, excluding archived)
        assignments = FacultySubjectAssignment.query\
            .filter_by(
                faculty_id=faculty.id,
                academic_year=active_settings.academic_year,
                semester=active_settings.semester,
                is_archived=False
            )\
            .all()
        
        assigned_units = 0.0
        assigned_count = len(assignments)  # Count of active assignments
        for assignment in assignments:
            if assignment.subject:
                assigned_units += assignment.subject.total_units
        
        # Get total units from schedules (actual teaching load)
        schedules = Schedule.query\
            .filter_by(faculty_id=faculty.id, is_active=True)\
            .all()
        
        schedule_units = 0.0
        class_count = len(schedules)
        for schedule in schedules:
            if schedule.subject:
                schedule_units += schedule.subject.total_units
        
        faculty_workloads[faculty.id] = {
            'assigned_count': assigned_count,  # Number of active assignments
            'assigned_units': assigned_units,
            'schedule_units': float(schedule_units or 0),
            'class_count': class_count,
            'total_units': float(schedule_units) if schedule_units else assigned_units
        }
    
    # Get all subjects grouped by curriculum for assignment
    # Filter subjects to only show those in semesters matching the current active semester
    curricula = Curriculum.query.filter_by(is_active=True).order_by(Curriculum.curriculum_code).all()
    
    # Filter curricula to only include those with subjects in the current semester
    filtered_curricula = []
    for curriculum in curricula:
        has_matching_subjects = False
        for year_level in curriculum.year_levels:
            for semester in year_level.semesters:
                # Check if semester name matches active settings
                if semester.semester_name == active_settings.semester and len(semester.subjects) > 0:
                    has_matching_subjects = True
                    break
            if has_matching_subjects:
                break
        
        if has_matching_subjects:
            filtered_curricula.append(curriculum)
    
    # Get selected faculty if faculty_id is provided
    selected_faculty = None
    selected_faculty_assignments = []
    faculty_id = request.args.get('faculty_id', type=int)
    if faculty_id:
        selected_faculty = Faculty.query.get(faculty_id)
        if selected_faculty:
            # Get only active (non-archived) assignments for current academic period
            selected_faculty_assignments = FacultySubjectAssignment.query.filter_by(
                faculty_id=selected_faculty.id,
                academic_year=active_settings.academic_year,
                semester=active_settings.semester,
                is_archived=False
            ).all()
    
    return render_template('faculty.html', 
                         user=current_user, 
                         faculties=faculties, 
                         departments=departments,
                         curricula=filtered_curricula,
                         selected_faculty=selected_faculty,
                         selected_faculty_assignments=selected_faculty_assignments,
                         faculty_workloads=faculty_workloads,
                         active_settings=active_settings)


@faculty_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new faculty member"""
    try:
        full_name = request.form.get('full_name', '').strip()
        department_id = request.form.get('department_id', '').strip()
        
        # Validation
        if not full_name:
            flash('Please enter the faculty full name.', 'error')
            return redirect(url_for('faculty.index'))
        
        if not department_id:
            flash('Please select a department.', 'error')
            return redirect(url_for('faculty.index'))
        
        # Validate department
        try:
            dept_id = int(department_id)
            if not Department.query.get(dept_id):
                flash('Selected department not found.', 'error')
                return redirect(url_for('faculty.index'))
        except ValueError:
            flash('Invalid department selected.', 'error')
            return redirect(url_for('faculty.index'))
        
        # Create new faculty
        new_faculty = Faculty(
            full_name=full_name,
            department_id=dept_id,
            is_active=True
        )
        
        db.session.add(new_faculty)
        db.session.flush()
        
        # Log activity with details
        details = {}
        if dept_id:
            dept = Department.query.get(dept_id)
            if dept:
                details['department'] = dept.department_code
        log_create('faculty', new_faculty.id, new_faculty.full_name, details if details else None)
        
        db.session.commit()
        
        flash(f'Faculty member {new_faculty.full_name} has been successfully added!', 'success')
        params = build_redirect_params(faculty_id=new_faculty.id)
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the faculty member: {str(e)}', 'error')
        return redirect(url_for('faculty.index'))


@faculty_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing faculty member"""
    try:
        id = request.form.get('faculty_id_edit', '').strip()
        full_name = request.form.get('full_name_edit', '').strip()
        department_id = request.form.get('department_id_edit', '').strip()
        
        if not all([id, full_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty = Faculty.query.get(int(id))
        if not faculty:
            flash('Faculty member not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        # Validate department if provided
        dept_id = None
        old_dept = faculty.department.department_code if faculty.department else 'None'
        if department_id:
            try:
                dept_id = int(department_id)
                dept = Department.query.get(dept_id)
                if not dept:
                    flash('Selected department not found.', 'error')
                    return redirect(url_for('faculty.index'))
            except ValueError:
                flash('Invalid department selected.', 'error')
                return redirect(url_for('faculty.index'))
        
        # Track changes
        changes = {}
        if full_name != faculty.full_name:
            changes['name'] = f"{faculty.full_name} → {full_name}"
        if dept_id != faculty.department_id:
            new_dept = dept.department_code if dept_id else 'None'
            if old_dept != new_dept:
                changes['department'] = f"{old_dept} → {new_dept}"
        
        # Update faculty
        faculty.full_name = full_name
        faculty.department_id = dept_id
        
        # Log activity with details
        log_edit('faculty', faculty.id, faculty.full_name, changes if changes else None)
        
        db.session.commit()
        
        flash(f'Faculty member {faculty.full_name} has been successfully updated!', 'success')
        params = build_redirect_params(faculty_id=faculty.id)
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the faculty member: {str(e)}', 'error')
        return redirect(url_for('faculty.index'))


@faculty_bp.route('/archive', methods=['POST'])
@login_required
def archive():
    """Archive a faculty member"""
    try:
        faculty_id = request.form.get('faculty_id', '').strip()
        archive_reason = request.form.get('archive_reason', 'Manual archive by user').strip()
        
        if not faculty_id:
            flash('Invalid faculty member.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty = Faculty.query.get(int(faculty_id))
        if not faculty:
            flash('Faculty member not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty_name = faculty.full_name
        
        # Archive faculty using helper method
        faculty.archive(user_id=current_user.id, reason=archive_reason)
        
        # Log activity
        log_archive('faculty', faculty.id, faculty_name, {'reason': archive_reason})
        
        db.session.commit()
        
        flash(f'Faculty member {faculty_name} has been archived successfully!', 'success')
        params = build_redirect_params()
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while archiving the faculty member: {str(e)}', 'error')
        return redirect(url_for('faculty.index'))


@faculty_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a faculty member permanently (only for archived faculty)"""
    try:
        faculty_id = request.form.get('faculty_id', '').strip()
        
        if not faculty_id:
            flash('Invalid faculty member.', 'error')
            return redirect(url_for('archive.index'))
        
        faculty = Faculty.query.get(int(faculty_id))
        if not faculty:
            flash('Faculty member not found.', 'error')
            return redirect(url_for('archive.index'))
        
        if not faculty.is_archived:
            flash('Only archived faculty can be permanently deleted.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty_name = faculty.full_name
        
        # Log activity before deletion with details
        details = {}
        if faculty.department:
            details['department'] = faculty.department.department_code
        log_delete('faculty', faculty.id, faculty_name, details if details else None)
        
        db.session.delete(faculty)
        db.session.commit()
        
        flash(f'Faculty member {faculty_name} has been permanently deleted!', 'success')
        return redirect(url_for('archive.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the faculty member: {str(e)}', 'error')
        return redirect(url_for('archive.index'))


@faculty_bp.route('/assign-subjects', methods=['POST'])
@login_required
def assign_subjects():
    """Assign multiple subjects to a faculty member at once"""
    try:
        # Get current academic settings
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not active_settings:
            flash('No active academic settings found. Please configure settings first.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty_id = request.form.get('faculty_id_assign', '').strip()
        subject_ids = request.form.getlist('subject_ids[]')
        
        if not faculty_id:
            flash('Faculty member is required.', 'error')
            return redirect(url_for('faculty.index'))
        
        if not subject_ids or len(subject_ids) == 0:
            flash('Please select at least one subject.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty = Faculty.query.get(int(faculty_id))
        if not faculty:
            flash('Faculty member not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        # Track results
        assigned_count = 0
        skipped_count = 0
        skipped_subjects = []
        
        for subject_id in subject_ids:
            subject = Subject.query.get(int(subject_id))
            if not subject:
                skipped_count += 1
                continue
            
            # Check if already assigned for current academic period (excluding archived)
            existing = FacultySubjectAssignment.query.filter_by(
                faculty_id=int(faculty_id),
                subject_id=int(subject_id),
                academic_year=active_settings.academic_year,
                semester=active_settings.semester,
                is_archived=False
            ).first()
            
            if existing:
                skipped_count += 1
                skipped_subjects.append(subject.subject_code)
                continue
            
            # Create subject assignment with academic context
            assignment = FacultySubjectAssignment(
                faculty_id=int(faculty_id),
                subject_id=int(subject_id),
                academic_year=active_settings.academic_year,
                semester=active_settings.semester
            )
            
            db.session.add(assignment)
            assigned_count += 1
        
        db.session.commit()
        
        # Build success message
        if assigned_count > 0:
            plural = "subjects" if assigned_count > 1 else "subject"
            message = f'Successfully assigned {assigned_count} {plural} to {faculty.full_name} for {active_settings.academic_year} - {active_settings.semester}!'
            
            if skipped_count > 0:
                skipped_list = ', '.join(skipped_subjects[:3])
                if len(skipped_subjects) > 3:
                    skipped_list += f' and {len(skipped_subjects) - 3} more'
                message += f' ({skipped_count} already assigned: {skipped_list})'
            
            flash(message, 'success')
        elif skipped_count > 0:
            flash(f'All selected subjects ({skipped_count}) were already assigned to {faculty.full_name}.', 'error')
        else:
            flash('No subjects were assigned.', 'error')
        
        params = build_redirect_params(faculty_id=faculty.id)
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while assigning subjects: {str(e)}', 'error')
        return redirect(url_for('faculty.index'))


@faculty_bp.route('/assign-subject', methods=['POST'])
@login_required
def assign_subject():
    """Assign a single subject to a faculty member (kept for backwards compatibility)"""
    try:
        # Get current academic settings
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not active_settings:
            flash('No active academic settings found. Please configure settings first.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty_id = request.form.get('faculty_id_assign', '').strip()
        subject_id = request.form.get('subject_id', '').strip()
        
        if not faculty_id:
            flash('Faculty member is required.', 'error')
            return redirect(url_for('faculty.index'))
        
        if not subject_id:
            flash('Please select a subject.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty = Faculty.query.get(int(faculty_id))
        if not faculty:
            flash('Faculty member not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        subject = Subject.query.get(int(subject_id))
        if not subject:
            flash('Subject not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        # Check if already assigned for current academic period (excluding archived)
        existing = FacultySubjectAssignment.query.filter_by(
            faculty_id=int(faculty_id),
            subject_id=int(subject_id),
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_archived=False
        ).first()
        
        if existing:
            flash(f'Subject "{subject.subject_code}" is already assigned to {faculty.full_name} for {active_settings.academic_year} - {active_settings.semester}.', 'error')
            return redirect(url_for('faculty.index', faculty_id=faculty.id))
        
        # Create subject assignment with academic context
        assignment = FacultySubjectAssignment(
            faculty_id=int(faculty_id),
            subject_id=int(subject_id),
            academic_year=active_settings.academic_year,
            semester=active_settings.semester
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        # Get curriculum context
        context = ""
        if subject.semester and subject.semester.year_level and subject.semester.year_level.curriculum:
            curriculum = subject.semester.year_level.curriculum
            year_level = subject.semester.year_level
            semester = subject.semester
            context = f" ({curriculum.curriculum_code} - {year_level.year_name}, {semester.semester_name})"
        
        flash(f'Subject "{subject.subject_code}"{context} has been assigned to {faculty.full_name} for {active_settings.academic_year} - {active_settings.semester}!', 'success')
        
        params = build_redirect_params(faculty_id=faculty.id)
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while assigning the subject: {str(e)}', 'error')
        return redirect(url_for('faculty.index'))


@faculty_bp.route('/unassign-subject', methods=['POST'])
@login_required
def unassign_subject():
    """Remove a subject assignment from a faculty member"""
    try:
        assignment_id = request.form.get('assignment_id', '').strip()
        
        if not assignment_id:
            flash('Invalid assignment.', 'error')
            return redirect(url_for('faculty.index'))
        
        assignment = FacultySubjectAssignment.query.get(int(assignment_id))
        if not assignment:
            flash('Assignment not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty_id = assignment.faculty_id
        
        # Get subject code for message
        subject_code = assignment.subject.subject_code if assignment.subject else "Unknown"
        
        db.session.delete(assignment)
        db.session.commit()
        
        flash(f'Subject "{subject_code}" has been unassigned!', 'success')
        params = build_redirect_params(faculty_id=faculty_id)
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while removing the assignment: {str(e)}', 'error')
        return redirect(url_for('faculty.index'))
