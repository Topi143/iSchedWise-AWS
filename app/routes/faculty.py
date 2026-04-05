"""
Faculty management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Faculty, FacultySubjectAssignment, Program, Curriculum, Department
from app.models.curriculum import Subject, Semester, YearLevel
from app.models.faculty import FacultyAvailability
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.settings import AcademicSettings
from app.utils.activity_logger import log_create, log_edit, log_delete, log_archive

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')


def _get_department_ids_from_departments(program_ids):
    """Derive department IDs from a list of program IDs.
    Used for dean access control: deans are assigned programs,
    and we need to determine which departments those programs belong to."""
    if not program_ids:
        return []
    depts = Program.query.filter(Program.id.in_(program_ids)).all()
    return list({d.department_id for d in depts if d.department_id})


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


def _validate_availability_within_schedule_window(start_time, end_time):
    """Validate availability range against active class schedule window."""
    active_settings = AcademicSettings.query.filter_by(is_active=True).first()
    if (
        not active_settings
        or not active_settings.schedule_start_time
        or not active_settings.schedule_end_time
    ):
        return None

    settings_start = active_settings.schedule_start_time
    settings_end = active_settings.schedule_end_time
    if settings_end <= settings_start:
        return None

    if start_time < settings_start or end_time > settings_end:
        settings_start_display = settings_start.strftime('%I:%M %p').lstrip('0')
        settings_end_display = settings_end.strftime('%I:%M %p').lstrip('0')
        return (
            f"Availability must be within class schedule hours "
            f"({settings_start_display} - {settings_end_display})."
        )

    return None


def _calculate_weekly_hours_from_schedules(schedules):
    """Calculate weekly teaching hours from schedule start/end times."""
    weekly_minutes = 0
    for schedule in schedules:
        if not schedule.start_time or not schedule.end_time:
            continue

        start_minutes = (schedule.start_time.hour * 60) + schedule.start_time.minute
        end_minutes = (schedule.end_time.hour * 60) + schedule.end_time.minute
        if end_minutes > start_minutes:
            weekly_minutes += (end_minutes - start_minutes)

    return round(weekly_minutes / 60, 1)


@faculty_bp.route('/')
@login_required
def index():
    """Faculty management page"""
    # Get current academic settings
    active_settings = AcademicSettings.query.filter_by(is_active=True).first()
    if not active_settings:
        flash('No active academic settings found. Please configure settings first.', 'error')
        return redirect(url_for('main.index'))
    
    # Get all active (non-archived) faculties and programs
    faculties = Faculty.query.options(
        db.joinedload(Faculty.department)
    ).filter_by(is_archived=False).order_by(Faculty.last_name, Faculty.first_name).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    programs = Program.query.options(
        db.joinedload(Program.department)
    ).filter_by(is_active=True).order_by(Program.program_name).all()

    export_program_query = Program.query.filter_by(is_active=True)
    user_program_ids = current_user.get_program_ids()
    if user_program_ids is not None:
        export_program_query = export_program_query.filter(Program.id.in_(user_program_ids))
    export_programs = export_program_query.order_by(Program.program_name).all()
    
    # Calculate workload for each faculty (filtered by current academic settings)
    # Batch-load all assignments & schedules with eager-loaded subjects to avoid N+1 queries
    from collections import defaultdict

    all_assignments = FacultySubjectAssignment.query\
        .options(db.joinedload(FacultySubjectAssignment.subject))\
        .filter_by(
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_archived=False
        ).all()
    assignments_by_faculty = defaultdict(list)
    for a in all_assignments:
        assignments_by_faculty[a.faculty_id].append(a)

    all_schedules = Schedule.query\
        .options(db.joinedload(Schedule.subject))\
        .filter_by(
            is_active=True,
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
        ).all()
    schedules_by_faculty = defaultdict(list)
    for s in all_schedules:
        if s.faculty_id:
            schedules_by_faculty[s.faculty_id].append(s)

    faculty_workloads = {}
    for faculty in faculties:
        assignments = assignments_by_faculty.get(faculty.id, [])
        fac_schedules = schedules_by_faculty.get(faculty.id, [])
        assignment_subject_ids = {a.subject_id for a in assignments if a.subject_id}
        scheduled_subject_ids = {s.subject_id for s in fac_schedules if s.subject_id}
        assigned_count = len(assignment_subject_ids.union(scheduled_subject_ids))

        schedule_units = 0.0
        class_count = len(fac_schedules)
        for schedule in fac_schedules:
            if schedule.subject:
                schedule_units += schedule.subject.total_units
        weekly_hours = _calculate_weekly_hours_from_schedules(fac_schedules)
        
        # Get load status using the model method (respects individual & system limits)
        current_load, max_units, utilization_pct, load_status = faculty.get_load_status(
            active_settings.academic_year, active_settings.semester
        )
        
        faculty_workloads[faculty.id] = {
            'assigned_count': assigned_count,  # Number of active assignments (unique subjects)
            'assigned_units': float(schedule_units),  # Units per section (for display consistency)
            'schedule_units': float(schedule_units or 0),
            'class_count': class_count,
            'weekly_hours': float(weekly_hours),
            'total_units': float(schedule_units),
            'max_units': int(max_units),
            'utilization_pct': round(utilization_pct, 1),
            'load_status': load_status  # 'normal', 'warning', 'exceeded'
        }
    
    # Get all subjects grouped by curriculum for assignment
    # Filter subjects to only show those in semesters matching the current active semester
    # AND filter by user's program access (Deans can only see their program's curricula)
    curricula_query = Curriculum.query.filter_by(is_active=True)
    
    # Apply program filter for non-admin users (Deans)
    user_program_ids = current_user.get_program_ids()
    if user_program_ids is not None:  # None means admin (access to all)
        curricula_query = curricula_query.filter(Curriculum.program_id.in_(user_program_ids))
    
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
    faculty_schedules = {}  # Dictionary to store schedules grouped by subject
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
            
            # Get all schedules for this faculty in current academic period
            faculty_schedule_list = Schedule.query.filter_by(
                faculty_id=selected_faculty.id,
                academic_year=active_settings.academic_year,
                semester=active_settings.semester,
                is_active=True
            ).order_by(Schedule.subject_id, Schedule.day_of_week, Schedule.start_time).all()
            
            # Group schedules by subject_id
            for schedule in faculty_schedule_list:
                if schedule.subject_id not in faculty_schedules:
                    faculty_schedules[schedule.subject_id] = []
                faculty_schedules[schedule.subject_id].append(schedule)
    
    return render_template('faculty.html', 
                         user=current_user, 
                         faculties=faculties, 
                         departments=departments,
                         programs=programs,
                         export_programs=export_programs,
                         curricula=filtered_curricula,
                         selected_faculty=selected_faculty,
                         selected_faculty_assignments=selected_faculty_assignments,
                         faculty_schedules=faculty_schedules,
                         faculty_workloads=faculty_workloads,
                         active_settings=active_settings)


@faculty_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new faculty member, optionally with subject assignments."""
    try:
        # Support both JSON and form data
        is_json = request.is_json
        if is_json:
            data = request.get_json()
            last_name = (data.get('last_name') or '').strip()
            first_name = (data.get('first_name') or '').strip()
            middle_initial = (data.get('middle_initial') or '').strip() or None
            gender = (data.get('gender') or '').strip() or None
            department_id = data.get('department_id', '')
            subject_ids = data.get('subject_ids', [])
        else:
            last_name = request.form.get('last_name', '').strip()
            first_name = request.form.get('first_name', '').strip()
            middle_initial = request.form.get('middle_initial', '').strip() or None
            gender = request.form.get('gender', '').strip() or None
            department_id = request.form.get('department_id', '').strip()
            subject_ids = []

        # Validation
        if not last_name or not first_name:
            msg = 'Please enter both the last name and first name.'
            if is_json:
                return jsonify({'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('faculty.index'))
        
        if not department_id:
            msg = 'Please select a department.'
            if is_json:
                return jsonify({'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('faculty.index'))
        
        # Validate department
        try:
            col_id = int(department_id)
            if not Department.query.get(col_id):
                msg = 'Selected department not found.'
                if is_json:
                    return jsonify({'error': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('faculty.index'))
        except ValueError:
            msg = 'Invalid department selected.'
            if is_json:
                return jsonify({'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('faculty.index'))
        
        # Create new faculty
        new_faculty = Faculty(
            last_name=last_name,
            first_name=first_name,
            middle_initial=middle_initial,
            gender=gender,
            department_id=col_id,
            is_active=True
        )
        
        db.session.add(new_faculty)
        db.session.flush()
        
        # Log activity with details
        details = {}
        if col_id:
            department = Department.query.get(col_id)
            if department:
                details['department'] = department.department_code
        log_create('faculty', new_faculty.id, new_faculty.full_name, details if details else None)

        # Assign subjects if provided
        assigned_names = []
        if subject_ids:
            active_settings = AcademicSettings.query.filter_by(is_active=True).first()
            if active_settings:
                for sid in subject_ids:
                    subject = Subject.query.get(sid)
                    if subject:
                        new_assignment = FacultySubjectAssignment(
                            faculty_id=new_faculty.id,
                            subject_id=sid,
                            academic_year=active_settings.academic_year,
                            semester=active_settings.semester,
                            is_active=True
                        )
                        db.session.add(new_assignment)
                        assigned_names.append(subject.subject_code)
                
                if assigned_names:
                    log_edit('faculty_subject_assignment', new_faculty.id, new_faculty.full_name, {
                        'changes': 'Assigned: ' + ', '.join(assigned_names),
                        'academic_year': active_settings.academic_year,
                        'semester': active_settings.semester
                    })
        
        db.session.commit()
        
        msg = f'Faculty member {new_faculty.full_name} has been successfully added!'
        if assigned_names:
            msg += f' ({len(assigned_names)} subject{"s" if len(assigned_names) != 1 else ""} assigned)'

        if is_json:
            return jsonify({
                'success': True,
                'message': msg,
                'faculty_id': new_faculty.id,
                'faculty_name': new_faculty.full_name,
                'assigned_count': len(assigned_names)
            })
        
        flash(msg, 'success')
        params = build_redirect_params(faculty_id=new_faculty.id)
        return redirect(url_for('faculty.index', **params))
        
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': f'An error occurred while adding the faculty member: {str(e)}'}), 500
        flash(f'An error occurred while adding the faculty member: {str(e)}', 'error')
        return redirect(url_for('faculty.index'))


@faculty_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing faculty member"""
    try:
        id = request.form.get('faculty_id_edit', '').strip()
        last_name = request.form.get('last_name_edit', '').strip()
        first_name = request.form.get('first_name_edit', '').strip()
        middle_initial = request.form.get('middle_initial_edit', '').strip() or None
        gender = request.form.get('gender_edit', '').strip() or None  # None if empty
        department_id = request.form.get('department_id_edit', '').strip()
        
        if not all([id, last_name, first_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('faculty.index'))
        
        faculty = Faculty.query.get(int(id))
        if not faculty:
            flash('Faculty member not found.', 'error')
            return redirect(url_for('faculty.index'))
        
        # Validate department if provided
        col_id = None
        old_department = faculty.department.department_code if faculty.department else 'None'
        if department_id:
            try:
                col_id = int(department_id)
                department = Department.query.get(col_id)
                if not department:
                    flash('Selected department not found.', 'error')
                    return redirect(url_for('faculty.index'))
            except ValueError:
                flash('Invalid department selected.', 'error')
                return redirect(url_for('faculty.index'))
        
        # Track changes
        changes = {}
        if last_name != faculty.last_name:
            changes['last_name'] = f"{faculty.last_name} → {last_name}"
        if first_name != faculty.first_name:
            changes['first_name'] = f"{faculty.first_name} → {first_name}"
        if middle_initial != faculty.middle_initial:
            old_mi = faculty.middle_initial or 'None'
            new_mi = middle_initial or 'None'
            changes['middle_initial'] = f"{old_mi} → {new_mi}"
        if gender != faculty.gender:
            old_gender = faculty.gender or 'Not set'
            new_gender = gender or 'Not set'
            changes['gender'] = f"{old_gender} → {new_gender}"
        if col_id != faculty.department_id:
            new_department = department.department_code if col_id else 'None'
            if old_department != new_department:
                changes['department'] = f"{old_department} → {new_department}"
        
        # Update faculty
        faculty.last_name = last_name
        faculty.first_name = first_name
        faculty.middle_initial = middle_initial
        faculty.gender = gender
        faculty.department_id = col_id
        
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


# ============================================================================
# Faculty-Subject Assignment API
# ============================================================================

@faculty_bp.route('/api/subjects-by-department', methods=['GET'])
@login_required
def get_subjects_by_department():
    """Get all subjects for current semester filtered by department (no faculty_id needed).
    Used by the Add Faculty modal to let users assign subjects during creation."""
    try:
        department_id = request.args.get('department_id', type=int)
        if not department_id:
            return jsonify({'error': 'department_id is required'}), 400

        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not active_settings:
            return jsonify({'error': 'No active academic settings', 'no_settings': True}), 400

        # Get program IDs for this department
        programs = Program.query.filter_by(department_id=department_id, is_active=True).all()
        program_ids = {p.id for p in programs}

        if not program_ids:
            return jsonify({
                'curricula': [],
                'academic_year': active_settings.academic_year,
                'semester': active_settings.semester
            })

        # Dean program restriction
        user_program_ids = current_user.get_program_ids() if hasattr(current_user, 'get_program_ids') else None
        if user_program_ids is not None:
            program_ids = program_ids & set(user_program_ids)

        # Get all active curricula for these programs
        curricula = Curriculum.query.filter(
            Curriculum.program_id.in_(program_ids),
            Curriculum.is_active == True,
            Curriculum.is_archived == False
        ).order_by(Curriculum.curriculum_name).all()

        result = []
        for curriculum in curricula:
            curriculum_subjects = []
            for yl in curriculum.year_levels:
                for sem in yl.semesters:
                    if sem.semester_name != active_settings.semester:
                        continue
                    for subj in sem.subjects:
                        curriculum_subjects.append({
                            'id': subj.id,
                            'subject_code': subj.subject_code,
                            'course_description': subj.course_description,
                            'total_units': float(subj.total_units),
                            'lec_units': float(subj.lec_units),
                            'lab_units': float(subj.lab_units),
                            'year_name': yl.year_name,
                            'semester_name': sem.semester_name,
                            'is_assigned': False
                        })

            if curriculum_subjects:
                curriculum_subjects.sort(key=lambda x: x['subject_code'])
                result.append({
                    'curriculum_code': curriculum.curriculum_code,
                    'curriculum_name': curriculum.curriculum_name,
                    'program_code': curriculum.program.program_code if curriculum.program else '',
                    'subjects': curriculum_subjects
                })

        return jsonify({
            'curricula': result,
            'academic_year': active_settings.academic_year,
            'semester': active_settings.semester
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/<int:faculty_id>/available-subjects', methods=['GET'])
@login_required
def get_available_subjects(faculty_id):
    """Get subjects with assignment status for this faculty.
    
    Query params:
        all_semesters: If 'true', return subjects from ALL semesters (not just active).
    """
    try:
        faculty = Faculty.query.get(faculty_id)
        if not faculty or faculty.is_archived:
            return jsonify({'error': 'Faculty not found'}), 404

        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not active_settings:
            return jsonify({'error': 'No active academic settings'}), 400

        all_semesters = request.args.get('all_semesters', 'false').lower() == 'true'

        # Get assigned subject IDs for this faculty in current period
        assignments = FacultySubjectAssignment.query.filter_by(
            faculty_id=faculty_id,
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_archived=False
        ).all()
        assigned_subject_ids = {a.subject_id for a in assignments}

        # Get all active curricula with subjects
        curricula = Curriculum.query.filter_by(is_active=True, is_archived=False).order_by(Curriculum.curriculum_name).all()

        # Dean program restriction
        user_program_ids = current_user.get_program_ids() if hasattr(current_user, 'get_program_ids') else None
        if user_program_ids is not None:
            curricula = [c for c in curricula if c.program_id in user_program_ids]

        result = []
        for curriculum in curricula:
            curriculum_subjects = []
            for yl in curriculum.year_levels:
                for sem in yl.semesters:
                    if not all_semesters and sem.semester_name != active_settings.semester:
                        continue
                    for subj in sem.subjects:
                        curriculum_subjects.append({
                            'id': subj.id,
                            'subject_code': subj.subject_code,
                            'course_description': subj.course_description,
                            'total_units': float(subj.total_units),
                            'lec_units': float(subj.lec_units),
                            'lab_units': float(subj.lab_units),
                            'year_name': yl.year_name,
                            'semester_name': sem.semester_name,
                            'is_assigned': subj.id in assigned_subject_ids
                        })

            if curriculum_subjects:
                # Sort: assigned first, then by subject code
                curriculum_subjects.sort(key=lambda x: (0 if x['is_assigned'] else 1, x['subject_code']))
                result.append({
                    'curriculum_code': curriculum.curriculum_code,
                    'curriculum_name': curriculum.curriculum_name,
                    'program_code': curriculum.program.program_code if curriculum.program else '',
                    'subjects': curriculum_subjects
                })

        return jsonify({
            'curricula': result,
            'faculty_name': faculty.full_name,
            'academic_year': active_settings.academic_year,
            'semester': active_settings.semester,
            'all_semesters': all_semesters
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/<int:faculty_id>/assign-subjects', methods=['POST'])
@login_required
def assign_subjects(faculty_id):
    """Sync subject assignments for a faculty. Accepts { subject_ids: [1,2,...] }."""
    try:
        faculty = Faculty.query.get(faculty_id)
        if not faculty or faculty.is_archived:
            return jsonify({'error': 'Faculty not found'}), 404

        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not active_settings:
            return jsonify({'error': 'No active academic settings'}), 400

        data = request.get_json()
        new_subject_ids = set(data.get('subject_ids', []))

        # Get current assignments
        current_assignments = FacultySubjectAssignment.query.filter_by(
            faculty_id=faculty_id,
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_archived=False
        ).all()
        current_ids = {a.subject_id for a in current_assignments}

        to_add = new_subject_ids - current_ids
        to_remove = current_ids - new_subject_ids

        added_names = []
        removed_names = []

        # Remove unselected assignments (only the assignment, NOT schedules)
        for assignment in current_assignments:
            if assignment.subject_id in to_remove:
                subject = Subject.query.get(assignment.subject_id)
                if subject:
                    removed_names.append(subject.subject_code)
                db.session.delete(assignment)

        # Add new assignments
        for sid in to_add:
            subject = Subject.query.get(sid)
            if subject:
                new_assignment = FacultySubjectAssignment(
                    faculty_id=faculty_id,
                    subject_id=sid,
                    academic_year=active_settings.academic_year,
                    semester=active_settings.semester,
                    is_active=True
                )
                db.session.add(new_assignment)
                added_names.append(subject.subject_code)

        db.session.commit()

        # Log
        changes = []
        if added_names:
            changes.append('Assigned: ' + ', '.join(added_names))
        if removed_names:
            changes.append('Unassigned: ' + ', '.join(removed_names))
        if changes:
            log_edit('faculty_subject_assignment', faculty.id, faculty.full_name, {
                'changes': '; '.join(changes),
                'academic_year': active_settings.academic_year,
                'semester': active_settings.semester
            })

        return jsonify({
            'success': True,
            'message': 'Subject assignments updated for ' + faculty.full_name,
            'added': len(added_names),
            'removed': len(removed_names)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/unassign', methods=['POST'])
@login_required
def unassign_subject():
    """Unassign a subject from faculty - deletes assignment and all associated schedules"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        assignment_id = data.get('assignment_id')
        if not assignment_id:
            return jsonify({'success': False, 'error': 'Assignment ID is required'}), 400
        
        # Get the assignment
        assignment = FacultySubjectAssignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'success': False, 'error': 'Assignment not found'}), 404
        
        # Store info for response and logging
        faculty_id = assignment.faculty_id
        faculty_name = assignment.faculty.full_name if assignment.faculty else 'Unknown'
        subject_code = assignment.subject.subject_code if assignment.subject else 'Unknown'
        subject_id = assignment.subject_id
        academic_year = assignment.academic_year
        semester = assignment.semester
        
        # Find and delete all associated class schedules
        schedules_deleted = 0
        schedules = Schedule.query.filter_by(
            faculty_id=faculty_id,
            subject_id=subject_id,
            academic_year=academic_year,
            semester=semester,
            is_active=True
        ).all()
        
        for schedule in schedules:
            section_name = schedule.section.section_name if schedule.section else 'N/A'
            log_delete('schedule', schedule.id, 
                      f'{subject_code} - {section_name}',
                      {'reason': f'Subject unassigned from {faculty_name}', 'faculty': faculty_name})
            db.session.delete(schedule)
            schedules_deleted += 1
        
        # Find and delete all associated exam schedules
        exam_schedules_deleted = 0
        exam_schedules = ExamSchedule.query.filter_by(
            faculty_id=faculty_id,
            subject_id=subject_id,
            is_active=True
        ).all()
        
        for exam in exam_schedules:
            section_name = exam.section.section_name if exam.section else 'N/A'
            log_delete('exam_schedule', exam.id,
                      f'{subject_code} - {section_name}',
                      {'reason': f'Subject unassigned from {faculty_name}', 'faculty': faculty_name})
            db.session.delete(exam)
            exam_schedules_deleted += 1
        
        # Delete the assignment
        log_delete('faculty_assignment', assignment.id, 
                  f'{subject_code} from {faculty_name}',
                  {'schedules_deleted': schedules_deleted, 'exam_schedules_deleted': exam_schedules_deleted})
        db.session.delete(assignment)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully unassigned {subject_code} from {faculty_name}',
            'schedules_deleted': schedules_deleted,
            'exam_schedules_deleted': exam_schedules_deleted,
            'faculty_id': faculty_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


def get_faculty_available_days(faculty_id):
    """Get a summary of days when faculty is available"""
    day_abbrevs = {
        'Monday': 'M', 'Tuesday': 'T', 'Wednesday': 'W', 
        'Thursday': 'Th', 'Friday': 'F', 'Saturday': 'Sa', 'Sunday': 'Su'
    }
    
    # Get all availability records for this faculty
    available_records = FacultyAvailability.query.filter_by(
        faculty_id=faculty_id,
        is_active=True
    ).all()
    
    if not available_records:
        return None  # No availability defined
    
    # Get unique days
    available_days = set()
    for record in available_records:
        if record.day_of_week:
            available_days.add(record.day_of_week)
    
    # Sort days in order and convert to abbreviations
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    sorted_days = [day for day in day_order if day in available_days]
    
    return [day_abbrevs.get(d, d) for d in sorted_days]


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
        query = Faculty.query.options(
            db.joinedload(Faculty.department)
        ).filter_by(is_archived=False)
        
        # Apply department filter
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        # Apply search filter
        if search_query:
            query = query.filter(
                db.or_(
                    Faculty.last_name.ilike(f'%{search_query}%'),
                    Faculty.first_name.ilike(f'%{search_query}%')
                )
            )
        
        # Order by name
        query = query.order_by(Faculty.last_name, Faculty.first_name)
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Calculate workloads for paginated results
        faculty_list = []
        for faculty in pagination.items:
            # Get assignment rows for current academic period
            assignments = FacultySubjectAssignment.query\
                .filter_by(
                    faculty_id=faculty.id,
                    academic_year=active_settings.academic_year,
                    semester=active_settings.semester,
                    is_archived=False
                )\
                .all()
            
            # Get schedules
            schedules = Schedule.query\
                .filter_by(
                    faculty_id=faculty.id,
                    is_active=True,
                    academic_year=active_settings.academic_year,
                    semester=active_settings.semester,
                )\
                .all()

            # Use a union of assigned and scheduled subjects so active-term classes
            # remain visible even if assignment rows drift.
            assignment_subject_ids = {a.subject_id for a in assignments if a.subject_id}
            scheduled_subject_ids = {s.subject_id for s in schedules if s.subject_id}
            assigned_count = len(assignment_subject_ids.union(scheduled_subject_ids))
            
            schedule_units = sum(s.subject.total_units for s in schedules if s.subject)
            class_count = len(schedules)
            weekly_hours = _calculate_weekly_hours_from_schedules(schedules)
            
            # Get load status using the model method (respects individual & system limits)
            current_load, max_units, utilization_pct, load_status = faculty.get_load_status(
                active_settings.academic_year, active_settings.semester
            )
            
            faculty_data = {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'last_name': faculty.last_name,
                'first_name': faculty.first_name,
                'middle_initial': faculty.middle_initial,
                'department_id': faculty.department_id,
                'department_name': faculty.department.department_name if faculty.department else None,
                'department_code': faculty.department.department_code if faculty.department else None,
                'workload': {
                    'assigned_count': assigned_count,
                    'assigned_units': float(schedule_units),  # Units per section for consistency
                    'schedule_units': float(schedule_units),
                    'class_count': class_count,
                    'weekly_hours': float(weekly_hours),
                    'total_units': float(schedule_units),
                    'max_units': int(max_units),
                    'utilization_pct': round(utilization_pct, 1),
                    'load_status': load_status  # 'normal', 'warning', 'exceeded'
                },
                'available_days': get_faculty_available_days(faculty.id)
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
        
        # Get assignments for active context first
        assignments = FacultySubjectAssignment.query.filter_by(
            faculty_id=faculty.id,
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_archived=False
        ).all()

        assignment_context = {
            'academic_year': active_settings.academic_year,
            'semester': active_settings.semester,
            'source': 'active'
        }
        
        # Get all schedules for this faculty in current academic period
        faculty_schedule_list = Schedule.query.filter_by(
            faculty_id=faculty.id,
            academic_year=active_settings.academic_year,
            semester=active_settings.semester,
            is_active=True
        ).order_by(Schedule.subject_id, Schedule.day_of_week, Schedule.start_time).all()
        
        # Group schedules by subject_id
        schedules_by_subject = {}
        for schedule in faculty_schedule_list:
            if schedule.subject_id not in schedules_by_subject:
                schedules_by_subject[schedule.subject_id] = []
            schedules_by_subject[schedule.subject_id].append({
                'id': schedule.id,
                'section_name': schedule.section.section_name if schedule.section else 'TBA',
                'full_section_name': schedule.section.full_section_name if schedule.section else 'TBA',
                'year_level': schedule.section.year_level if schedule.section else None,
                'day_of_week': schedule.day_of_week,
                'start_time': schedule.start_time.strftime('%I:%M %p') if schedule.start_time else None,
                'end_time': schedule.end_time.strftime('%I:%M %p') if schedule.end_time else None,
                'room_number': schedule.room.room_number if schedule.room else 'TBA',
                'building_name': schedule.room.building.building_name if schedule.room and schedule.room.building else None,
                'schedule_type': schedule.schedule_type
            })

        assignment_by_subject_id = {}
        for assignment in assignments:
            if assignment.subject and assignment.subject_id not in assignment_by_subject_id:
                assignment_by_subject_id[assignment.subject_id] = assignment

        subject_entry_by_id = {
            subject_id: {
                'assignment_id': assignment.id,
                'subject': assignment.subject
            }
            for subject_id, assignment in assignment_by_subject_id.items()
            if assignment.subject
        }

        # Include active-term schedule subjects even when assignment rows are missing.
        for schedule in faculty_schedule_list:
            if not schedule.subject_id or not schedule.subject:
                continue
            if schedule.subject_id not in subject_entry_by_id:
                subject_entry_by_id[schedule.subject_id] = {
                    'assignment_id': None,
                    'subject': schedule.subject
                }

        assignments_data = []
        for subject_id, entry in sorted(
            subject_entry_by_id.items(),
            key=lambda item: (item[1]['subject'].subject_code if item[1]['subject'] else '')
        ):
            subject = entry['subject']
            if not subject:
                continue

            semester = subject.semester
            year_level = semester.year_level if semester else None
            curriculum = year_level.curriculum if year_level else None

            # Get schedules for this subject
            subject_schedules = schedules_by_subject.get(subject_id, [])

            assignments_data.append({
                'id': entry['assignment_id'],
                'subject_id': subject_id,
                'subject_code': subject.subject_code,
                'course_description': subject.course_description,
                'total_units': float(subject.total_units),
                'curriculum_code': curriculum.curriculum_code if curriculum else None,
                'year_name': year_level.year_name if year_level else None,
                'semester_name': semester.semester_name if semester else None,
                'schedules': subject_schedules,
                'is_schedule_derived': entry['assignment_id'] is None
            })
        
        # Calculate workload with explicit assigned vs scheduled units.
        assigned_units = sum(a['total_units'] for a in assignments_data)
        schedule_units = sum(float(s.subject.total_units) for s in faculty_schedule_list if s.subject)
        weekly_hours = _calculate_weekly_hours_from_schedules(faculty_schedule_list)
        
        # Get load status using the model method (respects individual & system limits)
        current_load, max_units, utilization_pct, load_status = faculty.get_load_status(
            active_settings.academic_year, active_settings.semester
        )
        
        return jsonify({
            'faculty': {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'last_name': faculty.last_name,
                'first_name': faculty.first_name,
                'middle_initial': faculty.middle_initial,
                'gender': faculty.gender,
                'department_id': faculty.department_id,
                'department_name': faculty.department.department_name if faculty.department else None,
                'department_code': faculty.department.department_code if faculty.department else None
            },
            'assignments': assignments_data,
            'workload': {
                'assigned_count': len(assignments_data),
                'assigned_units': float(assigned_units),
                'scheduled_units': float(schedule_units),
                'class_count': len(faculty_schedule_list),
                'weekly_hours': float(weekly_hours),
                'total_units': float(schedule_units),
                'max_units': int(max_units),
                'utilization_pct': round(utilization_pct, 1),
                'load_status': load_status  # 'normal', 'warning', 'exceeded'
            },
            'academic_context': {
                'academic_year': active_settings.academic_year,
                'semester': active_settings.semester
            },
            'assignment_context': assignment_context,
            'context_warning': None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Faculty Availability Routes (for Proctor Scheduling)
# =============================================================================

@faculty_bp.route('/api/<int:faculty_id>/availability', methods=['GET'])
@login_required
def get_availability(faculty_id):
    """Get all availability records for a faculty member"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        # Get active settings for context
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Get recurring weekly availability
        weekly = FacultyAvailability.get_faculty_weekly_availability(faculty_id)
        
        return jsonify({
            'faculty_id': faculty_id,
            'faculty_name': faculty.full_name,
            'weekly_availability': weekly,
            'valid_days': FacultyAvailability.VALID_DAYS
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/<int:faculty_id>/availability', methods=['POST'])
@login_required
def add_availability(faculty_id):
    """Add a new availability record for a faculty member"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        data = request.get_json()
        
        # Validate required fields
        if not data.get('start_time') or not data.get('end_time'):
            return jsonify({'error': 'Start time and end time are required'}), 400
        
        # day_of_week is required
        if not data.get('day_of_week'):
            return jsonify({'error': 'Day of week is required'}), 400
        
        # Validate day_of_week
        if data.get('day_of_week') and data['day_of_week'] not in FacultyAvailability.VALID_DAYS:
            return jsonify({'error': f'Invalid day_of_week. Must be one of: {FacultyAvailability.VALID_DAYS}'}), 400
        
        # Parse times
        from datetime import datetime
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        if start_time >= end_time:
            return jsonify({'error': 'Start time must be before end time'}), 400

        window_error = _validate_availability_within_schedule_window(start_time, end_time)
        if window_error:
            return jsonify({'error': window_error}), 400
        
        # Get academic context
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Create availability record (not tied to a specific semester)
        availability = FacultyAvailability(
            faculty_id=faculty_id,
            day_of_week=data.get('day_of_week'),
            start_time=start_time,
            end_time=end_time,
            academic_year=None,
            semester=None,
            created_by=current_user.id
        )
        
        db.session.add(availability)
        db.session.commit()
        
        # Log activity
        log_create('FacultyAvailability', availability.id, 
                   f'Added availability for {faculty.full_name}: {data.get("day_of_week")} {data["start_time"]}-{data["end_time"]}')
        
        return jsonify({
            'success': True,
            'message': 'Availability added successfully',
            'availability': availability.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date/time format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/<int:faculty_id>/availability/<int:availability_id>', methods=['PUT'])
@login_required
def update_availability(faculty_id, availability_id):
    """Update an existing availability record"""
    try:
        availability = FacultyAvailability.query.filter_by(
            id=availability_id,
            faculty_id=faculty_id
        ).first_or_404()
        
        data = request.get_json()
        
        # Parse and validate times if provided
        from datetime import datetime
        if data.get('start_time'):
            availability.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        if data.get('end_time'):
            availability.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        if availability.start_time >= availability.end_time:
            return jsonify({'error': 'Start time must be before end time'}), 400

        window_error = _validate_availability_within_schedule_window(
            availability.start_time,
            availability.end_time
        )
        if window_error:
            return jsonify({'error': window_error}), 400
        
        # Update other fields
        if 'day_of_week' in data:
            if data['day_of_week'] and data['day_of_week'] not in FacultyAvailability.VALID_DAYS:
                return jsonify({'error': f'Invalid day_of_week'}), 400
            availability.day_of_week = data['day_of_week']
                
        if 'is_active' in data:
            availability.is_active = data['is_active']
        
        db.session.commit()
        
        faculty = Faculty.query.get(faculty_id)
        log_edit('FacultyAvailability', availability_id, 
                 f'Updated availability for {faculty.full_name}')
        
        return jsonify({
            'success': True,
            'message': 'Availability updated successfully',
            'availability': availability.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date/time format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/<int:faculty_id>/availability/<int:availability_id>', methods=['DELETE'])
@login_required
def delete_availability(faculty_id, availability_id):
    """Delete an availability record"""
    try:
        availability = FacultyAvailability.query.filter_by(
            id=availability_id,
            faculty_id=faculty_id
        ).first_or_404()
        
        faculty = Faculty.query.get(faculty_id)
        desc = f'Deleted availability for {faculty.full_name}: {availability.day_of_week}'
        
        db.session.delete(availability)
        db.session.commit()
        
        log_delete('FacultyAvailability', availability_id, desc)
        
        return jsonify({
            'success': True,
            'message': 'Availability deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/<int:faculty_id>/availability/check', methods=['POST'])
@login_required
def check_availability(faculty_id):
    """Check if a faculty member is available at a specific date/time"""
    try:
        data = request.get_json()
        
        if not data.get('date') or not data.get('start_time') or not data.get('end_time'):
            return jsonify({'error': 'date, start_time, and end_time are required'}), 400
        
        from datetime import datetime
        check_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        result = FacultyAvailability.check_faculty_available(
            faculty_id, check_date, start_time, end_time
        )
        
        faculty = Faculty.query.get(faculty_id)
        result['faculty_name'] = faculty.full_name if faculty else None
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date/time format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/api/available-proctors', methods=['POST'])
@login_required
def get_available_proctors():
    """Get list of available proctors for a specific exam slot"""
    try:
        data = request.get_json()
        
        # Support both 'date' and 'exam_date' keys for flexibility
        exam_date_str = data.get('exam_date') or data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        
        if not exam_date_str or not start_time_str or not end_time_str:
            return jsonify({'success': False, 'error': 'exam_date, start_time, and end_time are required'}), 400
        
        from datetime import datetime
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        program_id = data.get('program_id')
        
        result = FacultyAvailability.get_available_proctors_for_slot(
            exam_date, start_time, end_time, department_id=program_id
        )
        
        return jsonify({
            'success': True,
            'proctors': result,
            'exam_date': exam_date_str,
            'time_slot': f"{start_time_str} - {end_time_str}"
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid date/time format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@faculty_bp.route('/export/lineup')
@login_required
def export_faculty_lineup():
    """Export Faculty Line-Up Excel report for a specific program."""
    from datetime import datetime, timedelta
    from app.services.export_service import generate_faculty_lineup_excel
    from app.models.section import Section
    
    program_id = request.args.get('program_id', type=int)
    if not program_id:
        flash('Please select a program to export.', 'error')
        return redirect(url_for('faculty.index'))
    
    program = Program.query.options(db.joinedload(Program.department)).get_or_404(program_id)
    
    # Dean access check — deans can only export their assigned programs
    user_program_ids = current_user.get_program_ids()
    if user_program_ids is not None:
        if program_id not in user_program_ids:
            flash('You do not have access to this program.', 'error')
            return redirect(url_for('faculty.index'))
    
    # Get active academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    if not current_settings:
        flash('No active academic settings found.', 'error')
        return redirect(url_for('faculty.index'))

    # Get all sections under the selected program.
    program_sections = Section.query.filter_by(program_id=program_id).all()
    section_ids = [section.id for section in program_sections]
    if not section_ids:
        flash('No sections found for the selected program.', 'warning')
        return redirect(url_for('faculty.index'))
    
    schedules = Schedule.query.options(
        db.joinedload(Schedule.subject),
        db.joinedload(Schedule.section),
        db.joinedload(Schedule.faculty)
    ).filter(
        Schedule.section_id.in_(section_ids),
        Schedule.is_active.is_(True),
        Schedule.academic_year == current_settings.academic_year,
        Schedule.semester == current_settings.semester,
        Schedule.faculty_id.isnot(None)
    ).order_by(Schedule.faculty_id, Schedule.day_of_week, Schedule.start_time).all()

    # Keep only active, non-archived faculty schedule rows.
    schedules_by_faculty = {}
    for sched in schedules:
        if not sched.faculty or sched.faculty.is_archived:
            continue
        schedules_by_faculty.setdefault(sched.faculty_id, []).append(sched)

    faculties = Faculty.query.filter(
        Faculty.id.in_(list(schedules_by_faculty.keys())),
        Faculty.is_archived.is_(False)
    ).order_by(Faculty.last_name, Faculty.first_name).all() if schedules_by_faculty else []
    
    # Build schedule data for each faculty
    faculty_schedule_data = []
    
    for faculty in faculties:
        faculty_schedules = schedules_by_faculty.get(faculty.id, [])
        
        # Group by subject+section to get unique rows
        # Each unique (subject_code, section) gets one row with summed hours
        subject_section_map = {}
        for sched in faculty_schedules:
            subject_code = sched.subject.subject_code if sched.subject else 'N/A'
            section_name = sched.section.full_section_name if sched.section else 'N/A'
            key = (subject_code, section_name)
            
            # Calculate hours for this schedule slot
            if sched.start_time and sched.end_time:
                start_dt = datetime.combine(datetime.today(), sched.start_time)
                end_dt = datetime.combine(datetime.today(), sched.end_time)
                hours = (end_dt - start_dt).total_seconds() / 3600
            else:
                hours = 0
            
            units = float(sched.subject.total_units) if sched.subject else 0
            
            if key not in subject_section_map:
                subject_section_map[key] = {
                    'subject_code': subject_code,
                    'section_name': section_name,
                    'units': units,
                    'hours': 0
                }
            subject_section_map[key]['hours'] += hours
        
        # Now group by subject_code so sections under the same subject are together
        from collections import OrderedDict
        subject_groups = OrderedDict()
        for (subj_code, sec_name), data in subject_section_map.items():
            if subj_code not in subject_groups:
                subject_groups[subj_code] = {
                    'subject_code': subj_code,
                    'units': data['units'],
                    'sections': []
                }
            subject_groups[subj_code]['sections'].append({
                'section_name': sec_name,
                'hours': data['hours']
            })
        
        # Build flat rows but mark which ones start a new subject group
        rows = []
        for subj_code, group in subject_groups.items():
            for i, sec in enumerate(group['sections']):
                hr = round(sec['hours'], 1) if sec['hours'] else ''
                units = group['units']
                units = int(units) if units == int(units) else units
                rows.append({
                    'subject_code': subj_code if i == 0 else '',  # Only first row shows subject
                    'section_name': sec['section_name'],
                    'units': units if i == 0 else '',  # Only first row shows units
                    'hours': hr,
                    '_subject_group_size': len(group['sections']) if i == 0 else 0  # For merge info
                })
        
        # Only include faculty who have schedules
        if not rows:
            continue
        
        total_hours = sum(r['hours'] for r in rows if isinstance(r['hours'], (int, float)))
        total_hours = round(total_hours, 1) if total_hours else 0
        
        faculty_schedule_data.append({
            'faculty': faculty,
            'rows': rows,
            'total_hours': int(total_hours) if total_hours == int(total_hours) else total_hours
        })
    
    output, filename = generate_faculty_lineup_excel(
        program, faculty_schedule_data, current_settings, current_user
    )
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
