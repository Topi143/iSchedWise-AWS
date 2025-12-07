"""
Department and Section management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Department, Section
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.utils.activity_logger import log_create, log_edit, log_delete, log_archive, log_unarchive

department_bp = Blueprint('department', __name__, url_prefix='/program')


@department_bp.route('/')
@login_required
def index():
    """Department management page"""
    # Get selected department ID from query parameter
    selected_department_id = request.args.get('department_id', type=int)
    
    # Get user's department access
    user_department_ids = current_user.get_department_ids()
    
    # Filter departments by user access
    if user_department_ids is None:
        # Admin - see all departments (exclude archived)
        departments = Department.query.filter_by(is_archived=False).order_by(Department.created_at.desc()).all()
    else:
        # Dean - only assigned departments (exclude archived)
        departments = Department.query.filter(
            Department.id.in_(user_department_ids),
            Department.is_archived == False
        ).order_by(Department.created_at.desc()).all()
    
    # If a department is selected, find it (and verify access)
    selected_department = None
    if selected_department_id and departments:
        selected_department = Department.query.get(selected_department_id)
        # Verify user has access to this department
        if user_department_ids is not None and selected_department:
            if selected_department.id not in user_department_ids:
                selected_department = None
    
    return render_template('programs.html', 
                         user=current_user, 
                         departments=departments,
                         selected_department=selected_department)


@department_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new department"""
    try:
        department_code = request.form.get('department_code', '').strip().upper()
        department_name = request.form.get('department_name', '').strip()
        full_department_name = request.form.get('full_department_name', '').strip() or None
        secretary_name = request.form.get('secretary_name', '').strip() or None
        
        if not all([department_code, department_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('department.index'))
        
        if Department.query.filter_by(department_code=department_code).first():
            flash(f'Department code "{department_code}" already exists. Please use a different code.', 'error')
            return redirect(url_for('department.index'))
        
        new_department = Department(
            department_code=department_code,
            department_name=department_name,
            full_department_name=full_department_name,
            secretary_name=secretary_name,
            is_active=True
        )
        
        db.session.add(new_department)
        db.session.flush()
        
        # Log activity
        log_create('department', new_department.id, department_code, {'name': department_name})
        
        db.session.commit()
        
        flash('Department has been successfully added!', 'success')
        return redirect(url_for('department.index', department_id=new_department.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the department: {str(e)}', 'error')
        return redirect(url_for('department.index'))


@department_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing department"""
    try:
        department_id = request.form.get('department_id', '').strip()
        department_code = request.form.get('department_code', '').strip().upper()
        department_name = request.form.get('department_name', '').strip()
        full_department_name = request.form.get('full_department_name', '').strip() or None
        secretary_name = request.form.get('secretary_name', '').strip() or None
        
        if not all([department_id, department_code, department_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('department.index'))
        
        department = Department.query.get(int(department_id))
        if not department:
            flash('Department not found.', 'error')
            return redirect(url_for('department.index'))
        
        if department.department_code != department_code:
            if Department.query.filter_by(department_code=department_code).first():
                flash(f'Department code "{department_code}" already exists. Please use a different code.', 'error')
                return redirect(url_for('department.index', department_id=int(department_id)))
        
        # Track changes
        changes = {}
        if department.department_code != department_code:
            changes['code'] = f'{department.department_code} → {department_code}'
        if department.department_name != department_name:
            changes['name'] = f'{department.department_name} → {department_name}'
        if department.full_department_name != full_department_name:
            changes['full_name'] = f'{department.full_department_name or "None"} → {full_department_name or "None"}'
        if department.secretary_name != secretary_name:
            changes['secretary'] = f'{department.secretary_name or "None"} → {secretary_name or "None"}'
        
        department.department_code = department_code
        department.department_name = department_name
        department.full_department_name = full_department_name
        department.secretary_name = secretary_name
        
        # Log activity with changes
        log_edit('department', department.id, department_code, changes if changes else None)
        
        db.session.commit()
        
        flash('Department has been successfully updated!', 'success')
        return redirect(url_for('department.index', department_id=department.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the department: {str(e)}', 'error')
        return redirect(url_for('department.index'))


@department_bp.route('/toggle-status', methods=['POST'])
@login_required
def toggle_status():
    """Toggle department active status"""
    try:
        department_id = request.form.get('department_id', '').strip()
        
        if not department_id:
            flash('Invalid department.', 'error')
            return redirect(url_for('department.index'))
        
        department = Department.query.get(int(department_id))
        if not department:
            flash('Department not found.', 'error')
            return redirect(url_for('department.index'))
        
        department.is_active = not department.is_active
        db.session.commit()
        
        status = 'activated' if department.is_active else 'deactivated'
        flash(f'Department has been successfully {status}!', 'success')
        return redirect(url_for('department.index', department_id=department.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('department.index'))


@department_bp.route('/archive', methods=['POST'])
@login_required
def archive():
    """Archive a department, all its active curricula, and delete all schedules from its sections"""
    try:
        department_id = request.form.get('department_id', '').strip()
        archive_reason = request.form.get('archive_reason', 'Manual archive by user').strip()
        
        if not department_id:
            flash('Invalid department.', 'error')
            return redirect(url_for('department.index'))
        
        department = Department.query.get(int(department_id))
        if not department:
            flash('Department not found.', 'error')
            return redirect(url_for('department.index'))
        
        department_code = department.department_code
        
        # Get all section IDs from this department
        section_ids = [section.id for section in department.sections]
        
        # Count schedules that will be deleted
        class_schedules_count = 0
        exam_schedules_count = 0
        
        if section_ids:
            # Find and delete class schedules from sections in this department
            class_schedules = Schedule.query.filter(
                Schedule.section_id.in_(section_ids),
                Schedule.is_active == True
            ).all()
            
            for schedule in class_schedules:
                # Log deletion
                log_delete('schedule', schedule.id, 
                          f'{schedule.subject.subject_code if schedule.subject else "N/A"} - {schedule.section.section_name if schedule.section else "N/A"}',
                          {'reason': f'Department archived: {department_code}', 'department': department_code})
                db.session.delete(schedule)
                class_schedules_count += 1
            
            # Find and delete exam schedules from sections in this department
            exam_schedules = ExamSchedule.query.filter(
                ExamSchedule.section_id.in_(section_ids),
                ExamSchedule.is_active == True
            ).all()
            
            for exam_schedule in exam_schedules:
                # Log deletion
                log_delete('exam_schedule', exam_schedule.id,
                          f'{exam_schedule.subject.subject_code if exam_schedule.subject else "N/A"} - {exam_schedule.section.section_name if exam_schedule.section else "N/A"}',
                          {'reason': f'Department archived: {department_code}', 'department': department_code})
                db.session.delete(exam_schedule)
                exam_schedules_count += 1
        
        # Check if department has active curricula and archive them
        active_curricula = [c for c in department.curricula if not c.is_archived]
        archived_curricula_count = 0
        
        if active_curricula:
            # Archive all active curricula in this department
            for curriculum in active_curricula:
                curriculum.archive(
                    user_id=current_user.id, 
                    reason=f"Auto-archived with department {department_code}: {archive_reason}"
                )
                archived_curricula_count += 1
        
        # Archive department using helper method
        department.archive(user_id=current_user.id, reason=archive_reason)
        
        # Log department archive activity
        log_archive('department', department.id, department_code, {
            'reason': archive_reason,
            'curricula_archived': archived_curricula_count,
            'deleted_class_schedules': class_schedules_count,
            'deleted_exam_schedules': exam_schedules_count
        })
        
        db.session.commit()
        
        flash(f'Department "{department_code}" has been archived successfully!', 'success')
        return redirect(url_for('department.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while archiving the department: {str(e)}', 'error')
        return redirect(url_for('department.index'))


@department_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a department permanently (only for archived departments)"""
    try:
        department_id = request.form.get('department_id', '').strip()
        
        if not department_id:
            flash('Invalid department.', 'error')
            return redirect(url_for('archive.index'))
        
        department = Department.query.get(int(department_id))
        if not department:
            flash('Department not found.', 'error')
            return redirect(url_for('archive.index'))
        
        if not department.is_archived:
            flash('Only archived departments can be permanently deleted.', 'error')
            return redirect(url_for('department.index'))
        
        if department.curricula:
            flash(f'Cannot delete department "{department.department_code}" because it has {len(department.curricula)} associated curricula. Please delete the curricula first.', 'error')
            return redirect(url_for('archive.index'))
        
        department_code = department.department_code
        department_name = department.department_name
        
        # Log activity before deletion
        log_delete('department', department.id, department_code, {'name': department_name})
        
        db.session.delete(department)
        db.session.commit()
        
        flash(f'Department "{department_code}" has been permanently deleted!', 'success')
        return redirect(url_for('archive.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the department: {str(e)}', 'error')
        return redirect(url_for('archive.index'))


# Section routes
@department_bp.route('/section/add', methods=['POST'])
@login_required
def add_section():
    """Add a new section"""
    try:
        department_id = request.form.get('department_id', '').strip()
        section_name = request.form.get('section_name', '').strip()
        year_level = request.form.get('year_level', '').strip()
        
        if not all([department_id, section_name, year_level]):
            flash('Please fill in all required fields.', 'error')
            if department_id:
                return redirect(url_for('department.index', department_id=int(department_id)))
            return redirect(url_for('department.index'))
        
        try:
            year_level = int(year_level)
            if year_level < 1 or year_level > 10:
                flash('Year level must be between 1 and 10.', 'error')
                return redirect(url_for('department.index', department_id=int(department_id)))
        except ValueError:
            flash('Invalid year level.', 'error')
            return redirect(url_for('department.index', department_id=int(department_id)))
        
        department = Department.query.get(int(department_id))
        if not department:
            flash('Department not found.', 'error')
            return redirect(url_for('department.index'))
        
        new_section = Section(
            department_id=int(department_id),
            section_name=section_name,
            year_level=year_level,
            is_active=True
        )
        
        db.session.add(new_section)
        db.session.flush()
        
        # Log activity
        log_create('section', new_section.id, section_name, {
            'department': department.department_code,
            'year_level': year_level
        })
        
        db.session.commit()
        
        flash('Section has been successfully added!', 'success')
        return redirect(url_for('department.index', department_id=department.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the section: {str(e)}', 'error')
        dept_id = request.form.get('department_id', '').strip()
        if dept_id:
            return redirect(url_for('department.index', department_id=int(dept_id)))
        return redirect(url_for('department.index'))


@department_bp.route('/section/edit', methods=['POST'])
@login_required
def edit_section():
    """Edit an existing section"""
    try:
        section_id = request.form.get('section_id', '').strip()
        section_name = request.form.get('section_name', '').strip()
        year_level = request.form.get('year_level', '').strip()
        
        # Get section to preserve department context in case of error
        dept_id = None
        if section_id:
            temp_section = Section.query.get(int(section_id))
            if temp_section:
                dept_id = temp_section.department_id
        
        if not all([section_id, section_name, year_level]):
            flash('Please fill in all required fields.', 'error')
            if dept_id:
                return redirect(url_for('department.index', department_id=dept_id))
            return redirect(url_for('department.index'))
        
        try:
            year_level = int(year_level)
            if year_level < 1 or year_level > 10:
                flash('Year level must be between 1 and 10.', 'error')
                if dept_id:
                    return redirect(url_for('department.index', department_id=dept_id))
                return redirect(url_for('department.index'))
        except ValueError:
            flash('Invalid year level.', 'error')
            if dept_id:
                return redirect(url_for('department.index', department_id=dept_id))
            return redirect(url_for('department.index'))
        
        section = Section.query.get(int(section_id))
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('department.index'))
        
        # Track changes
        changes = {}
        if section.section_name != section_name:
            changes['name'] = f'{section.section_name} → {section_name}'
        if section.year_level != year_level:
            changes['year_level'] = f'{section.year_level} → {year_level}'
        
        section.section_name = section_name
        section.year_level = year_level
        
        # Log activity with changes
        log_edit('section', section.id, section_name, changes if changes else None)
        
        db.session.commit()
        
        flash('Section has been successfully updated!', 'success')
        return redirect(url_for('department.index', department_id=section.department_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the section: {str(e)}', 'error')
        section_id = request.form.get('section_id', '').strip()
        if section_id:
            temp_section = Section.query.get(int(section_id))
            if temp_section:
                return redirect(url_for('department.index', department_id=temp_section.department_id))
        return redirect(url_for('department.index'))


@department_bp.route('/section/delete', methods=['POST'])
@login_required
def delete_section():
    """Delete a section"""
    try:
        section_id = request.form.get('section_id', '').strip()
        
        if not section_id:
            flash('Invalid section.', 'error')
            return redirect(url_for('department.index'))
        
        section = Section.query.get(int(section_id))
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('department.index'))
        
        department_id = section.department_id
        section_name = section.section_name
        
        # Log activity before deletion
        log_delete('section', section.id, section_name, {'department': section.department.department_code})
        
        db.session.delete(section)
        db.session.commit()
        
        flash('Section has been successfully deleted!', 'success')
        return redirect(url_for('department.index', department_id=department_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the section: {str(e)}', 'error')
        section_id = request.form.get('section_id', '').strip()
        if section_id:
            temp_section = Section.query.get(int(section_id))
            if temp_section:
                return redirect(url_for('department.index', department_id=temp_section.department_id))
        return redirect(url_for('department.index'))
