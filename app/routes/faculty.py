"""
Faculty management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from app.extensions import db
from app.models import Faculty, FacultySubjectAssignment, Department, Subject, Curriculum, YearLevel, Semester
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
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
    # AND filter by user's department access (Deans can only see their department's curricula)
    curricula_query = Curriculum.query.filter_by(is_active=True)
    
    # Apply department filter for non-admin users (Deans)
    user_department_ids = current_user.get_department_ids()
    if user_department_ids is not None:  # None means admin (access to all)
        curricula_query = curricula_query.filter(Curriculum.department_id.in_(user_department_ids))
    
    curricula = curricula_query.order_by(Curriculum.curriculum_code).all()
    
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
    """Archive a faculty member and delete all schedules assigned to them"""
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
        
        # Count schedules that will be deleted
        class_schedules_count = 0
        exam_schedules_count = 0
        
        # Find and delete class schedules assigned to this faculty
        class_schedules = Schedule.query.filter(
            Schedule.faculty_id == int(faculty_id),
            Schedule.is_active == True
        ).all()
        
        for schedule in class_schedules:
            # Log deletion
            log_delete('schedule', schedule.id, 
                      f'{schedule.subject.subject_code if schedule.subject else "N/A"} - {schedule.section.section_name if schedule.section else "N/A"}',
                      {'reason': f'Faculty archived: {faculty_name}', 'faculty': faculty_name})
            db.session.delete(schedule)
            class_schedules_count += 1
        
        # Find and delete exam schedules assigned to this faculty
        exam_schedules = ExamSchedule.query.filter(
            ExamSchedule.faculty_id == int(faculty_id),
            ExamSchedule.is_active == True
        ).all()
        
        for exam_schedule in exam_schedules:
            # Log deletion
            log_delete('exam_schedule', exam_schedule.id,
                      f'{exam_schedule.subject.subject_code if exam_schedule.subject else "N/A"} - {exam_schedule.section.section_name if exam_schedule.section else "N/A"}',
                      {'reason': f'Faculty archived: {faculty_name}', 'faculty': faculty_name})
            db.session.delete(exam_schedule)
            exam_schedules_count += 1
        
        # Archive faculty using helper method
        faculty.archive(user_id=current_user.id, reason=archive_reason)
        
        # Log faculty archive activity
        log_archive('faculty', faculty.id, faculty_name, {
            'reason': archive_reason,
            'deleted_class_schedules': class_schedules_count,
            'deleted_exam_schedules': exam_schedules_count
        })
        
        db.session.commit()
        
        flash(f'Faculty member "{faculty_name}" has been archived successfully!', 'success')
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
        
        # Allow empty subject_ids - this means user wants to unassign all subjects
        # if not subject_ids or len(subject_ids) == 0:
        #     flash('Please select at least one subject.', 'error')
        #     return redirect(url_for('faculty.index'))
        
        faculty = Faculty.query.get(int(faculty_id))
        if not faculty:
            flash('Faculty member not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        # Get all currently assigned subjects for this faculty in the current academic period
        current_assignments = FacultySubjectAssignment.query.filter_by(
            faculty_id=int(faculty_id),
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_archived=False
        ).all()
        
        # Create a set of currently assigned subject IDs
        currently_assigned_ids = {str(a.subject_id) for a in current_assignments}
        
        # Create a set of new selected subject IDs
        selected_ids = set(subject_ids)
        
        # Track results
        assigned_count = 0
        unassigned_count = 0
        skipped_count = 0
        unauthorized_subjects = []
        
        # Get user's accessible department IDs
        user_department_ids = current_user.get_department_ids()
        
        # Subjects to add (in selected but not in current)
        to_add = selected_ids - currently_assigned_ids
        
        # Subjects to remove (in current but not in selected)
        to_remove = currently_assigned_ids - selected_ids
        
        # Add new assignments
        for subject_id in to_add:
            subject = Subject.query.get(int(subject_id))
            if not subject:
                skipped_count += 1
                continue
            
            # Check department access
            curriculum = subject.semester.year_level.curriculum if subject.semester and subject.semester.year_level else None
            
            # Validate user has access to this subject's department
            if user_department_ids is not None:  # None means admin (access to all)
                if not curriculum or curriculum.department_id not in user_department_ids:
                    unauthorized_subjects.append(subject.subject_code)
                    skipped_count += 1
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
        
        # Remove unselected assignments
        for subject_id in to_remove:
            assignment = FacultySubjectAssignment.query.filter_by(
                faculty_id=int(faculty_id),
                subject_id=int(subject_id),
                academic_year=active_settings.academic_year,
                semester=active_settings.semester,
                is_archived=False
            ).first()
            
            if assignment:
                db.session.delete(assignment)
                unassigned_count += 1
        
        db.session.commit()
        
        # Build success message
        actions = []
        if assigned_count > 0:
            plural = "subjects" if assigned_count > 1 else "subject"
            actions.append(f'assigned {assigned_count} {plural}')
        
        if unassigned_count > 0:
            plural = "subjects" if unassigned_count > 1 else "subject"
            actions.append(f'unassigned {unassigned_count} {plural}')
        
        if actions:
            message = f'Successfully {" and ".join(actions)} for {faculty.full_name} ({active_settings.academic_year} - {active_settings.semester})'
            
            if len(unauthorized_subjects) > 0:
                unauthorized_list = ', '.join(unauthorized_subjects[:3])
                if len(unauthorized_subjects) > 3:
                    unauthorized_list += f' and {len(unauthorized_subjects) - 3} more'
                message += f'. Skipped {len(unauthorized_subjects)} unauthorized: {unauthorized_list}'
            
            flash(message + '!', 'success')
        elif skipped_count > 0:
            if len(unauthorized_subjects) > 0:
                flash(f'Cannot assign subjects from other departments. You can only assign subjects from your department.', 'error')
            else:
                flash('No changes were made.', 'info')
        else:
            flash('No changes were made.', 'info')
        
        params = build_redirect_params(faculty_id=faculty.id)
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while assigning subjects: {str(e)}', 'error')
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


@faculty_bp.route('/api/list', methods=['GET'])
@login_required
def api_list():
    """API endpoint for dynamically loading faculty list with pagination"""
    try:
        # Get current academic settings
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not active_settings:
            return jsonify({'error': 'No active academic settings found'}), 400
        
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        department_id = request.args.get('department_id', type=int)
        search_query = request.args.get('search', '').strip()
        
        # Build query
        query = Faculty.query.filter_by(is_archived=False)
        
        # Apply department filter
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        # Apply search filter
        if search_query:
            query = query.filter(Faculty.full_name.ilike(f'%{search_query}%'))
        
        # Order by name
        query = query.order_by(Faculty.full_name)
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Calculate workloads for paginated results
        faculty_list = []
        for faculty in pagination.items:
            # Get assignments for current academic period
            assignments = FacultySubjectAssignment.query\
                .filter_by(
                    faculty_id=faculty.id,
                    academic_year=active_settings.academic_year,
                    semester=active_settings.semester,
                    is_archived=False
                )\
                .all()
            
            assigned_units = sum(a.subject.total_units for a in assignments if a.subject)
            assigned_count = len(assignments)
            
            # Get schedules
            schedules = Schedule.query\
                .filter_by(faculty_id=faculty.id, is_active=True)\
                .all()
            
            schedule_units = sum(s.subject.total_units for s in schedules if s.subject)
            class_count = len(schedules)
            
            faculty_data = {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_id': faculty.department_id,
                'department_name': faculty.department.department_name if faculty.department else None,
                'department_code': faculty.department.department_code if faculty.department else None,
                'workload': {
                    'assigned_count': assigned_count,
                    'assigned_units': float(assigned_units),
                    'schedule_units': float(schedule_units),
                    'class_count': class_count,
                    'total_units': float(schedule_units) if schedule_units else float(assigned_units)
                }
            }
            faculty_list.append(faculty_data)
        
        return jsonify({
            'faculties': faculty_list,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/detail/<int:faculty_id>', methods=['GET'])
@login_required
def api_detail(faculty_id):
    """API endpoint for fetching detailed faculty information"""
    try:
        # Get current academic settings
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not active_settings:
            return jsonify({'error': 'No active academic settings found'}), 400
        
        faculty = Faculty.query.get(faculty_id)
        if not faculty or faculty.is_archived:
            return jsonify({'error': 'Faculty not found'}), 404
        
        # Get assignments
        assignments = FacultySubjectAssignment.query.filter_by(
            faculty_id=faculty.id,
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_archived=False
        ).all()
        
        assignments_data = []
        for assignment in assignments:
            if assignment.subject:
                semester = assignment.subject.semester
                year_level = semester.year_level if semester else None
                curriculum = year_level.curriculum if year_level else None
                
                assignments_data.append({
                    'id': assignment.id,
                    'subject_id': assignment.subject_id,
                    'subject_code': assignment.subject.subject_code,
                    'course_description': assignment.subject.course_description,
                    'total_units': float(assignment.subject.total_units),
                    'curriculum_code': curriculum.curriculum_code if curriculum else None,
                    'year_name': year_level.year_name if year_level else None,
                    'semester_name': semester.semester_name if semester else None
                })
        
        # Get schedules
        schedules = Schedule.query.filter_by(
            faculty_id=faculty.id,
            is_active=True
        ).all()
        
        schedules_data = []
        for schedule in schedules:
            schedules_data.append({
                'id': schedule.id,
                'subject_code': schedule.subject.subject_code if schedule.subject else None,
                'section_name': schedule.section.section_name if schedule.section else None,
                'day_of_week': schedule.day_of_week,
                'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                'room_number': schedule.room.room_number if schedule.room else None,
                'building_name': schedule.room.building.building_name if schedule.room and schedule.room.building else None
            })
        
        return jsonify({
            'faculty': {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_id': faculty.department_id,
                'department_name': faculty.department.department_name if faculty.department else None,
                'department_code': faculty.department.department_code if faculty.department else None
            },
            'assignments': assignments_data,
            'schedules': schedules_data,
            'academic_context': {
                'academic_year': active_settings.academic_year,
                'semester': active_settings.semester
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
