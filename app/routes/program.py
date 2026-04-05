"""
Program and Section management routes
"""
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import Program, Section, Department
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.system_config import SystemConfig
from app.utils.activity_logger import log_create, log_edit, log_delete, log_archive, log_unarchive

program_bp = Blueprint('program', __name__, url_prefix='/program')

# File upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@program_bp.route('/')
@login_required
def index():
    """Program management page"""
    # Get selected program ID from query parameter
    selected_department_id = request.args.get('program_id', type=int)
    
    # Get user's program access
    user_program_ids = current_user.get_program_ids()
    
    # Filter programs by user access
    if user_program_ids is None:
        # Admin - see all programs (exclude archived)
        programs = Program.query.options(
            db.joinedload(Program.department),
            db.joinedload(Program.sections)
        ).filter_by(is_archived=False).order_by(Program.created_at.desc()).all()
    else:
        # Dean - only assigned programs (exclude archived)
        programs = Program.query.options(
            db.joinedload(Program.department),
            db.joinedload(Program.sections)
        ).filter(
            Program.id.in_(user_program_ids),
            Program.is_archived == False
        ).order_by(Program.created_at.desc()).all()
    
    # If a program is selected, find it (and verify access)
    selected_department = None
    if selected_department_id and programs:
        selected_department = Program.query.get(selected_department_id)
        # Verify user has access to this program
        if user_program_ids is not None and selected_department:
            if selected_department.id not in user_program_ids:
                selected_department = None
    
    # Auto-seed program names from existing programs (one-time migration)
    _auto_seed_department_names()
    
    # Get departments for the department dropdown
    departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    
    return render_template('programs.html', 
                         user=current_user, 
                         programs=programs,
                         selected_department=selected_department,
                         program_names=_get_department_names(),
                         departments=departments)


def _auto_seed_department_names():
    """Auto-seed managed list from existing Department names"""
    existing = SystemConfig.get('program_names', None)
    if existing is not None and isinstance(existing, list) and len(existing) > 0:
        return  # Already seeded
    
    names = existing if isinstance(existing, list) else []
    all_depts = Department.query.filter(
        Department.department_name.isnot(None),
        Department.department_name != ''
    ).all()
    changed = False
    for dept in all_depts:
        name = dept.department_name.strip()
        if name and name not in names:
            names.append(name)
            changed = True
    if changed:
        SystemConfig.set('program_names', names)
        db.session.commit()


def _get_department_names():
    """Get the managed list of program names from SystemConfig"""
    names = SystemConfig.get('program_names', [])
    if not isinstance(names, list):
        names = []
    return sorted(set(names))


def _add_department_name(name):
    """Add a program name to the managed list if not already present"""
    if not name or not name.strip():
        return
    name = name.strip()
    names = SystemConfig.get('program_names', [])
    if not isinstance(names, list):
        names = []
    if name not in names:
        names.append(name)
        SystemConfig.set('program_names', names)


@program_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new program"""
    try:
        program_code = request.form.get('program_code', '').strip().upper()
        program_name = request.form.get('program_name', '').strip()
        department_id = request.form.get('department_id', type=int) or None
        year_levels = request.form.get('year_levels', '4').strip()
        shared_program_code = request.form.get('shared_program_code', '').strip().upper() or None
        shared_until_year = request.form.get('shared_until_year', '').strip()
        
        if not all([program_code, program_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('program.index'))
        
        if Program.query.filter_by(program_code=program_code, is_archived=False).first():
            flash(f'Program code "{program_code}" already exists. Please use a different code.', 'error')
            return redirect(url_for('program.index'))
        
        # Parse year_levels (default to 4 if invalid)
        try:
            year_levels_int = int(year_levels)
            if year_levels_int < 1 or year_levels_int > 10:
                year_levels_int = 4
        except ValueError:
            year_levels_int = 4
        
        # Parse shared_until_year if provided
        shared_until_year_int = None
        if shared_until_year:
            try:
                shared_until_year_int = int(shared_until_year)
            except ValueError:
                shared_until_year_int = None
        
        new_department = Program(
            program_code=program_code,
            program_name=program_name,
            department_id=department_id,
            year_levels=year_levels_int,
            shared_program_code=shared_program_code,
            shared_until_year=shared_until_year_int,
            is_active=True
        )
        
        db.session.add(new_department)
        db.session.flush()
        
        # Log activity
        log_create('program', new_department.id, program_code, {'name': program_name})
        
        db.session.commit()
        
        flash('Program has been successfully added!', 'success')
        return redirect(url_for('program.index', program_id=new_department.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the program: {str(e)}', 'error')
        return redirect(url_for('program.index'))


@program_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing program"""
    try:
        program_id = request.form.get('program_id', '').strip()
        program_code = request.form.get('program_code', '').strip().upper()
        program_name = request.form.get('program_name', '').strip()
        department_id = request.form.get('department_id', type=int) or None
        year_levels = request.form.get('year_levels', '').strip()
        shared_program_code = request.form.get('shared_program_code', '').strip().upper() or None
        shared_until_year = request.form.get('shared_until_year', '').strip()
        
        if not all([program_id, program_code, program_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('program.index'))
        
        program = Program.query.get(int(program_id))
        if not program:
            flash('Program not found.', 'error')
            return redirect(url_for('program.index'))
        
        if program.program_code != program_code:
            if Program.query.filter_by(program_code=program_code, is_archived=False).first():
                flash(f'Program code "{program_code}" already exists. Please use a different code.', 'error')
                return redirect(url_for('program.index', program_id=int(program_id)))
        
        # Parse year_levels if provided
        year_levels_int = program.year_levels or 4
        if year_levels:
            try:
                year_levels_int = int(year_levels)
                if year_levels_int < 1 or year_levels_int > 10:
                    year_levels_int = program.year_levels or 4
            except ValueError:
                year_levels_int = program.year_levels or 4
        
        # Parse shared_until_year if provided
        shared_until_year_int = None
        if shared_until_year:
            try:
                shared_until_year_int = int(shared_until_year)
            except ValueError:
                shared_until_year_int = None
        
        # Track changes
        changes = {}
        if program.program_code != program_code:
            changes['code'] = f'{program.program_code} â†’ {program_code}'
        if program.program_name != program_name:
            changes['name'] = f'{program.program_name} â†’ {program_name}'
        if program.year_levels != year_levels_int:
            changes['year_levels'] = f'{program.year_levels or 4} â†’ {year_levels_int}'
        if program.shared_program_code != shared_program_code:
            changes['shared_program'] = f'{program.shared_program_code or "None"} â†’ {shared_program_code or "None"}'
        if program.shared_until_year != shared_until_year_int:
            changes['shared_until_year'] = f'{program.shared_until_year or "None"} â†’ {shared_until_year_int or "None"}'
        if program.department_id != department_id:
            changes['department_id'] = f'{program.department_id or "None"} â†’ {department_id or "None"}'
        
        program.program_code = program_code
        program.program_name = program_name
        program.department_id = department_id
        program.year_levels = year_levels_int
        program.shared_program_code = shared_program_code
        program.shared_until_year = shared_until_year_int
        
        
        # Log activity with changes
        log_edit('program', program.id, program_code, changes if changes else None)
        
        db.session.commit()
        
        flash('Program has been successfully updated!', 'success')
        return redirect(url_for('program.index', program_id=program.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the program: {str(e)}', 'error')
        return redirect(url_for('program.index'))


@program_bp.route('/check-code', methods=['POST'])
@login_required
def check_code():
    """Check if a program code already exists (for inline validation)"""
    code = request.json.get('code', '').strip().upper() if request.is_json else ''
    exclude_id = request.json.get('exclude_id') if request.is_json else None
    
    if not code:
        return jsonify({'exists': False})
    
    query = Program.query.filter_by(program_code=code, is_archived=False)
    if exclude_id:
        query = query.filter(Program.id != int(exclude_id))
    
    exists = query.first() is not None
    return jsonify({'exists': exists, 'code': code})


@program_bp.route('/toggle-status', methods=['POST'])
@login_required
def toggle_status():
    """Toggle program active status"""
    try:
        program_id = request.form.get('program_id', '').strip()
        
        if not program_id:
            flash('Invalid program.', 'error')
            return redirect(url_for('program.index'))
        
        program = Program.query.get(int(program_id))
        if not program:
            flash('Program not found.', 'error')
            return redirect(url_for('program.index'))
        
        program.is_active = not program.is_active
        db.session.commit()
        
        status = 'activated' if program.is_active else 'deactivated'
        flash(f'Program has been successfully {status}!', 'success')
        return redirect(url_for('program.index', program_id=program.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('program.index'))


@program_bp.route('/archive', methods=['POST'])
@login_required
def archive():
    """Archive a program, all its active curricula, and delete all schedules from its sections"""
    try:
        program_id = request.form.get('program_id', '').strip()
        archive_reason = request.form.get('archive_reason', 'Manual archive by user').strip()
        
        if not program_id:
            flash('Invalid program.', 'error')
            return redirect(url_for('program.index'))
        
        program = Program.query.get(int(program_id))
        if not program:
            flash('Program not found.', 'error')
            return redirect(url_for('program.index'))
        
        program_code = program.program_code
        
        # Get all section IDs from this program
        section_ids = [section.id for section in program.sections]
        
        # Count schedules that will be deleted
        class_schedules_count = 0
        exam_schedules_count = 0
        
        if section_ids:
            # Find and delete class schedules from sections in this program
            class_schedules = Schedule.query.filter(
                Schedule.section_id.in_(section_ids),
                Schedule.is_active == True
            ).all()
            
            for schedule in class_schedules:
                # Log deletion
                log_delete('schedule', schedule.id, 
                          f'{schedule.subject.subject_code if schedule.subject else "N/A"} - {schedule.section.section_name if schedule.section else "N/A"}',
                          {'reason': f'Program archived: {program_code}', 'program': program_code})
                db.session.delete(schedule)
                class_schedules_count += 1
            
            # Find and delete exam schedules from sections in this program
            exam_schedules = ExamSchedule.query.filter(
                ExamSchedule.section_id.in_(section_ids),
                ExamSchedule.is_active == True
            ).all()
            
            for exam_schedule in exam_schedules:
                # Log deletion
                log_delete('exam_schedule', exam_schedule.id,
                          f'{exam_schedule.subject.subject_code if exam_schedule.subject else "N/A"} - {exam_schedule.section.section_name if exam_schedule.section else "N/A"}',
                          {'reason': f'Program archived: {program_code}', 'program': program_code})
                db.session.delete(exam_schedule)
                exam_schedules_count += 1
        
        # Check if program has active curricula and archive them
        active_curricula = [c for c in program.curricula if not c.is_archived]
        archived_curricula_count = 0
        
        if active_curricula:
            # Archive all active curricula in this program
            for curriculum in active_curricula:
                curriculum.archive(
                    user_id=current_user.id, 
                    reason=f"Auto-archived with program {program_code}: {archive_reason}"
                )
                archived_curricula_count += 1
        
        # Archive program using helper method
        program.archive(user_id=current_user.id, reason=archive_reason)
        
        # Log program archive activity
        log_archive('program', program.id, program_code, {
            'reason': archive_reason,
            'curricula_archived': archived_curricula_count,
            'deleted_class_schedules': class_schedules_count,
            'deleted_exam_schedules': exam_schedules_count
        })
        
        db.session.commit()
        
        flash(f'Program "{program_code}" has been archived successfully!', 'success')
        return redirect(url_for('program.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while archiving the program: {str(e)}', 'error')
        return redirect(url_for('program.index'))


@program_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a program permanently (only for archived programs)"""
    try:
        program_id = request.form.get('program_id', '').strip()
        
        if not program_id:
            flash('Invalid program.', 'error')
            return redirect(url_for('archive.index'))
        
        program = Program.query.get(int(program_id))
        if not program:
            flash('Program not found.', 'error')
            return redirect(url_for('archive.index'))
        
        if not program.is_archived:
            flash('Only archived programs can be permanently deleted.', 'error')
            return redirect(url_for('program.index'))
        
        if program.curricula:
            flash(f'Cannot delete program "{program.program_code}" because it has {len(program.curricula)} associated curricula. Please delete the curricula first.', 'error')
            return redirect(url_for('archive.index'))
        
        program_code = program.program_code
        program_name = program.program_name
        
        # Log activity before deletion
        log_delete('program', program.id, program_code, {'name': program_name})
        
        db.session.delete(program)
        db.session.commit()
        
        flash(f'Program "{program_code}" has been permanently deleted!', 'success')
        return redirect(url_for('archive.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the program: {str(e)}', 'error')
        return redirect(url_for('archive.index'))


# Section routes
@program_bp.route('/section/add', methods=['POST'])
@login_required
def add_section():
    """Add new section(s) - supports bulk creation"""
    try:
        program_id = request.form.get('program_id', '').strip()
        section_names = request.form.get('section_names', '').strip()  # Comma-separated: A, B, C
        year_levels = request.form.getlist('year_levels')  # Multiple year levels
        
        # Fallback for single section (backward compatibility)
        if not section_names:
            section_names = request.form.get('section_name', '').strip()
        if not year_levels:
            single_year = request.form.get('year_level', '').strip()
            if single_year:
                year_levels = [single_year]
        
        if not all([program_id, section_names, year_levels]):
            flash('Please fill in all required fields.', 'error')
            if program_id:
                return redirect(url_for('program.index', program_id=int(program_id)))
            return redirect(url_for('program.index'))
        
        program = Program.query.get(int(program_id))
        if not program:
            flash('Program not found.', 'error')
            return redirect(url_for('program.index'))
        
        # Parse section names (comma-separated)
        section_list = [s.strip().upper() for s in section_names.split(',') if s.strip()]
        if not section_list:
            flash('Please enter at least one section name.', 'error')
            return redirect(url_for('program.index', program_id=int(program_id)))
        
        # Parse and validate year levels
        valid_year_levels = []
        for yl in year_levels:
            try:
                year = int(yl)
                if 1 <= year <= 10:
                    valid_year_levels.append(year)
            except ValueError:
                continue
        
        if not valid_year_levels:
            flash('Please select at least one valid year level.', 'error')
            return redirect(url_for('program.index', program_id=int(program_id)))
        
        # Get existing sections to check for duplicates
        existing_sections = Section.query.filter_by(
            program_id=int(program_id)
        ).all()
        existing_combos = {(s.year_level, s.section_name.upper()) for s in existing_sections}
        
        # Create sections for each year level and section name combination
        created_count = 0
        skipped_count = 0
        
        for year_level in valid_year_levels:
            for section_name in section_list:
                # Check if this combination already exists
                if (year_level, section_name) in existing_combos:
                    skipped_count += 1
                    continue
                
                new_section = Section(
                    program_id=int(program_id),
                    section_name=section_name,
                    year_level=year_level
                )
                
                db.session.add(new_section)
                db.session.flush()
                
                # Log activity
                log_create('section', new_section.id, f"{year_level}{section_name}", {
                    'program': program.program_code,
                    'year_level': year_level,
                    'section_name': section_name
                })
                
                created_count += 1
        
        db.session.commit()
        
        # Build appropriate success message
        if created_count > 0 and skipped_count > 0:
            flash(f'{created_count} section(s) created successfully! {skipped_count} skipped (already exist).', 'success')
        elif created_count > 0:
            flash(f'{created_count} section(s) created successfully!', 'success')
        else:
            flash('No new sections created. All specified sections already exist.', 'info')
        
        return redirect(url_for('program.index', program_id=program.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding sections: {str(e)}', 'error')
        dept_id = request.form.get('program_id', '').strip()
        if dept_id:
            return redirect(url_for('program.index', program_id=int(dept_id)))
        return redirect(url_for('program.index'))


@program_bp.route('/section/edit', methods=['POST'])
@login_required
def edit_section():
    """Edit an existing section"""
    try:
        section_id = request.form.get('section_id', '').strip()
        section_name = request.form.get('section_name', '').strip()
        year_level = request.form.get('year_level', '').strip()
        
        # Get section to preserve program context in case of error
        dept_id = None
        if section_id:
            temp_section = Section.query.get(int(section_id))
            if temp_section:
                dept_id = temp_section.program_id
        
        if not all([section_id, section_name, year_level]):
            flash('Please fill in all required fields.', 'error')
            if dept_id:
                return redirect(url_for('program.index', program_id=dept_id))
            return redirect(url_for('program.index'))
        
        try:
            year_level = int(year_level)
            if year_level < 1 or year_level > 10:
                flash('Year level must be between 1 and 10.', 'error')
                if dept_id:
                    return redirect(url_for('program.index', program_id=dept_id))
                return redirect(url_for('program.index'))
        except ValueError:
            flash('Invalid year level.', 'error')
            if dept_id:
                return redirect(url_for('program.index', program_id=dept_id))
            return redirect(url_for('program.index'))
        
        section = Section.query.get(int(section_id))
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('program.index'))
        
        # Track changes
        changes = {}
        if section.section_name != section_name:
            changes['name'] = f'{section.section_name} â†’ {section_name}'
        if section.year_level != year_level:
            changes['year_level'] = f'{section.year_level} â†’ {year_level}'
        
        section.section_name = section_name
        section.year_level = year_level
        
        # Log activity with changes
        log_edit('section', section.id, section_name, changes if changes else None)
        
        db.session.commit()
        
        flash('Section has been successfully updated!', 'success')
        return redirect(url_for('program.index', program_id=section.program_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the section: {str(e)}', 'error')
        section_id = request.form.get('section_id', '').strip()
        if section_id:
            temp_section = Section.query.get(int(section_id))
            if temp_section:
                return redirect(url_for('program.index', program_id=temp_section.program_id))
        return redirect(url_for('program.index'))


@program_bp.route('/section/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_sections():
    """Bulk delete sections"""
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        if not ids:
            return jsonify({'success': False, 'message': 'No sections selected'}), 400

        sections = Section.query.filter(Section.id.in_(ids)).all()
        if not sections:
            return jsonify({'success': False, 'message': 'No sections found'}), 404

        program_id = sections[0].program_id
        count = 0
        for section in sections:
            # Delete associated schedules
            Schedule.query.filter_by(section_id=section.id).delete()
            ExamSchedule.query.filter_by(section_id=section.id).delete()
            log_delete('section', section.id, section.section_name, {'program': section.program.program_code})
            db.session.delete(section)
            count += 1

        db.session.commit()
        return jsonify({'success': True, 'message': f'Successfully deleted {count} section{"s" if count != 1 else ""}', 'affected': count, 'program_id': program_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@program_bp.route('/section/delete', methods=['POST'])
@login_required
def delete_section():
    """Delete a section"""
    try:
        section_id = request.form.get('section_id', '').strip()
        
        if not section_id:
            flash('Invalid section.', 'error')
            return redirect(url_for('program.index'))
        
        section = Section.query.get(int(section_id))
        if not section:
            flash('Section not found.', 'error')
            return redirect(url_for('program.index'))
        
        program_id = section.program_id
        section_name = section.section_name
        
        # Log activity before deletion
        log_delete('section', section.id, section_name, {'program': section.program.program_code})
        
        db.session.delete(section)
        db.session.commit()
        
        flash('Section has been successfully deleted!', 'success')
        return redirect(url_for('program.index', program_id=program_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the section: {str(e)}', 'error')
        section_id = request.form.get('section_id', '').strip()
        if section_id:
            temp_section = Section.query.get(int(section_id))
            if temp_section:
                return redirect(url_for('program.index', program_id=temp_section.program_id))
        return redirect(url_for('program.index'))


# â”€â”€ Program Names Management API â”€â”€

@program_bp.route('/program-names', methods=['GET'])
@login_required
def get_department_names():
    """Get the managed list of program names"""
    return jsonify({'names': _get_department_names()})


@program_bp.route('/program-names/add', methods=['POST'])
@login_required
def add_department_name():
    """Add a new program name to the managed list"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Name is required'}), 400
    
    names = SystemConfig.get('program_names', [])
    if not isinstance(names, list):
        names = []
    if name in names:
        return jsonify({'success': False, 'message': 'Name already exists'}), 400
    
    names.append(name)
    SystemConfig.set('program_names', names, user_id=current_user.id)
    db.session.commit()
    return jsonify({'success': True, 'names': sorted(set(names))})


@program_bp.route('/program-names/delete', methods=['POST'])
@login_required
def delete_department_name():
    """Delete a program name from the managed list"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Name is required'}), 400
    
    names = SystemConfig.get('program_names', [])
    if not isinstance(names, list):
        names = []
    if name not in names:
        return jsonify({'success': False, 'message': 'Name not found'}), 404
    
    names.remove(name)
    SystemConfig.set('program_names', names, user_id=current_user.id)
    db.session.commit()
    return jsonify({'success': True, 'names': sorted(set(names))})


@program_bp.route('/program-names/seed', methods=['POST'])
@login_required
def seed_department_names():
    """One-time seed: populate managed list from existing departments"""
    existing = SystemConfig.get('program_names', [])
    if not isinstance(existing, list):
        existing = []
    
    all_depts = Department.query.filter(
        Department.department_name.isnot(None),
        Department.department_name != ''
    ).all()
    
    for dept in all_depts:
        name = dept.department_name.strip()
        if name and name not in existing:
            existing.append(name)
    
    SystemConfig.set('program_names', existing, user_id=current_user.id)
    db.session.commit()
    return jsonify({'success': True, 'names': sorted(set(existing))})
