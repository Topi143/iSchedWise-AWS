"""
Curriculum management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Department, Curriculum, YearLevel, Semester, Subject
from app.utils.activity_logger import log_create, log_edit, log_delete, log_archive, log_unarchive
import pandas as pd
import io
from werkzeug.utils import secure_filename
import os

curriculum_bp = Blueprint('curriculum', __name__, url_prefix='/curriculum')


def get_filter_params():
    """Get department_id filter from request args"""
    department_id = request.args.get('department_id', type=int)
    return {'department_id': department_id} if department_id else {}


def build_redirect_params(curriculum_id=None, year_level_id=None, semester_id=None, **kwargs):
    """Build redirect parameters preserving filters"""
    params = get_filter_params()
    
    if curriculum_id:
        params['curriculum_id'] = curriculum_id
        params['open'] = curriculum_id
    if year_level_id:
        params['year'] = year_level_id
    if semester_id:
        params['semester'] = semester_id
    
    # Add any additional parameters
    params.update(kwargs)
    return params


def get_open_curriculum_id():
    """Get the curriculum ID that should remain open from request or session"""
    # Check if there's an open parameter in the form
    open_id = request.form.get('_open_curriculum_id')
    if not open_id:
        # Check session
        open_id = session.get('open_curriculum_id')
    return open_id


def redirect_with_open(curriculum_id=None):
    """Redirect to curriculum index, preserving the open accordion state and filters"""
    # Preserve department_id filter from request
    department_id = request.args.get('department_id', type=int)
    
    url_params = {}
    if department_id:
        url_params['department_id'] = department_id
    
    if curriculum_id:
        session['open_curriculum_id'] = curriculum_id
        url_params['open'] = curriculum_id
        return redirect(url_for('curriculum.index', **url_params))
    else:
        # Try to get from session or request
        open_id = get_open_curriculum_id()
        if open_id:
            url_params['open'] = open_id
            return redirect(url_for('curriculum.index', **url_params))
    return redirect(url_for('curriculum.index', **url_params))


@curriculum_bp.route('/')
@login_required
def index():
    """Curriculum management page"""
    # Get filter parameters
    department_id = request.args.get('department_id', type=int)
    selected_curriculum_id = request.args.get('curriculum_id', type=int)
    
    # Get user's department access
    user_department_ids = current_user.get_department_ids()
    
    # Build query based on filters and user access
    query = Curriculum.query
    
    # Filter out archived curricula from main list
    query = query.filter_by(is_archived=False)
    
    # Filter by user's department access
    if user_department_ids is not None:
        query = query.filter(Curriculum.department_id.in_(user_department_ids))
    
    # Apply additional department filter if specified
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    curricula = query.order_by(Curriculum.created_at.desc()).all()
    
    # Filter departments by user access
    if user_department_ids is None:
        departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    else:
        departments = Department.query.filter(
            Department.is_active == True,
            Department.id.in_(user_department_ids)
        ).order_by(Department.department_name).all()
    
    # If a curriculum is selected, find it
    selected_curriculum = None
    if selected_curriculum_id and curricula:
        selected_curriculum = Curriculum.query.get(selected_curriculum_id)
    
    return render_template('curriculum.html', 
                         user=current_user, 
                         curricula=curricula, 
                         departments=departments,
                         selected_department_id=department_id,
                         selected_curriculum_id=selected_curriculum_id,
                         selected_curriculum=selected_curriculum)


@curriculum_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new curriculum"""
    try:
        curriculum_code = request.form.get('curriculum_code', '').strip().upper()
        department_id = request.form.get('department_id', '').strip()
        year_levels_count = request.form.get('year_levels', '').strip()
        
        if not all([curriculum_code, department_id, year_levels_count]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('curriculum.index'))
        
        try:
            year_levels_count = int(year_levels_count)
            if year_levels_count < 1 or year_levels_count > 10:
                flash('Number of year levels must be between 1 and 10.', 'error')
                return redirect(url_for('curriculum.index'))
        except ValueError:
            flash('Invalid number of year levels.', 'error')
            return redirect(url_for('curriculum.index'))
        
        try:
            department_id = int(department_id)
        except ValueError:
            flash('Invalid department selected.', 'error')
            return redirect(url_for('curriculum.index'))
        
        if Curriculum.query.filter_by(curriculum_code=curriculum_code).first():
            flash(f'Curriculum code "{curriculum_code}" already exists. Please use a different code.', 'error')
            return redirect(url_for('curriculum.index'))
        
        department = Department.query.get(department_id)
        if not department:
            flash('Selected department not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        # Auto-generate degree program from department and curriculum code
        if department.department_code.startswith('BS'):
            degree_program = f"Bachelor of Science in {curriculum_code}"
        elif department.department_code.startswith('BA') or department.department_code.startswith('AB'):
            degree_program = f"Bachelor of Arts in {curriculum_code}"
        else:
            degree_program = f"{department.department_code} - {curriculum_code}"
        
        new_curriculum = Curriculum(
            curriculum_code=curriculum_code,
            department_id=department.id,
            degree_program=degree_program,
            is_active=True,
            created_by=current_user.id
        )
        
        db.session.add(new_curriculum)
        db.session.flush()
        
        # Log activity
        log_create('curriculum', new_curriculum.id, new_curriculum.curriculum_code, {
            'department': department.department_code,
            'year_levels': year_levels_count
        })
        
        # Auto-create year levels with semesters
        year_names = ['1st Year', '2nd Year', '3rd Year', '4th Year', '5th Year', 
                      '6th Year', '7th Year', '8th Year', '9th Year', '10th Year']
        semester_names = {1: '1st Semester', 2: '2nd Semester', 3: 'Summer'}
        
        for i in range(year_levels_count):
            year_level = YearLevel(
                curriculum_id=new_curriculum.id,
                year_number=i + 1,
                year_name=year_names[i]
            )
            db.session.add(year_level)
            db.session.flush()  # Flush to get the year_level.id
            
            # Get the semester count for this year level from form
            semester_count_key = f'year_{i + 1}_semesters'
            semester_count = request.form.get(semester_count_key, '2')  # Default to 2 semesters
            try:
                semester_count = int(semester_count)
                if semester_count < 0 or semester_count > 3:
                    semester_count = 2
            except ValueError:
                semester_count = 2
            
            # Create the specified number of semesters for this year level
            for sem_num in range(1, semester_count + 1):
                semester = Semester(
                    year_level_id=year_level.id,
                    semester_number=sem_num,
                    semester_name=semester_names[sem_num]
                )
                db.session.add(semester)
        
        db.session.commit()
        
        flash('Curriculum has been successfully added!', 'success')
        
        # Preserve department filter in redirect
        department_id = request.form.get('department_id', type=int)
        url_params = {'curriculum_id': new_curriculum.id, 'open': new_curriculum.id}
        if department_id:
            url_params['department_id'] = department_id
        return redirect(url_for('curriculum.index', **url_params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the curriculum: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


@curriculum_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing curriculum"""
    try:
        curriculum_id = request.form.get('curriculum_id', '').strip()
        curriculum_code = request.form.get('curriculum_code', '').strip().upper()
        department_id = request.form.get('department_id', '').strip()
        year_levels_count = request.form.get('year_levels', '').strip()
        
        if not all([curriculum_id, curriculum_code, department_id, year_levels_count]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('curriculum.index'))
        
        try:
            year_levels_count = int(year_levels_count)
            if year_levels_count < 1 or year_levels_count > 10:
                flash('Number of year levels must be between 1 and 10.', 'error')
                return redirect(url_for('curriculum.index'))
        except ValueError:
            flash('Invalid number of year levels.', 'error')
            return redirect(url_for('curriculum.index'))
        
        curriculum = Curriculum.query.get(int(curriculum_id))
        if not curriculum:
            flash('Curriculum not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        if curriculum.curriculum_code != curriculum_code:
            if Curriculum.query.filter_by(curriculum_code=curriculum_code).first():
                flash(f'Curriculum code "{curriculum_code}" already exists. Please use a different code.', 'error')
                return redirect(url_for('curriculum.index'))
        
        department = Department.query.get(int(department_id))
        if not department:
            flash('Selected department not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        # Auto-generate degree program from department and curriculum code
        if department.department_code.startswith('BS'):
            degree_program = f"Bachelor of Science in {curriculum_code}"
        elif department.department_code.startswith('BA') or department.department_code.startswith('AB'):
            degree_program = f"Bachelor of Arts in {curriculum_code}"
        else:
            degree_program = f"{department.department_code} - {curriculum_code}"
        
        curriculum.curriculum_code = curriculum_code
        curriculum.department_id = int(department_id)
        curriculum.degree_program = degree_program
        
        # Handle year levels - add or remove as needed
        current_year_levels = len(curriculum.year_levels)
        year_names = ['1st Year', '2nd Year', '3rd Year', '4th Year', '5th Year', '6th Year', 
                      '7th Year', '8th Year', '9th Year', '10th Year']
        semester_names = {1: '1st Semester', 2: '2nd Semester', 3: 'Summer'}
        
        if year_levels_count > current_year_levels:
            # Add new year levels with semesters
            for i in range(current_year_levels, year_levels_count):
                year_level = YearLevel(
                    curriculum_id=curriculum.id,
                    year_number=i + 1,
                    year_name=year_names[i]
                )
                db.session.add(year_level)
                db.session.flush()  # Flush to get the year_level.id
                
                # Get the semester count for this year level from form
                semester_count_key = f'year_{i + 1}_semesters'
                semester_count = request.form.get(semester_count_key, '2')  # Default to 2 semesters
                try:
                    semester_count = int(semester_count)
                    if semester_count < 0 or semester_count > 3:
                        semester_count = 2
                except ValueError:
                    semester_count = 2
                
                # Create the specified number of semesters for this year level
                for sem_num in range(1, semester_count + 1):
                    semester = Semester(
                        year_level_id=year_level.id,
                        semester_number=sem_num,
                        semester_name=semester_names[sem_num]
                    )
                    db.session.add(semester)
        elif year_levels_count < current_year_levels:
            # Remove excess year levels (from the end)
            for i in range(year_levels_count, current_year_levels):
                year_level = curriculum.year_levels[i]
                db.session.delete(year_level)
        
        # Update semester configuration for existing year levels
        for i in range(min(year_levels_count, current_year_levels)):
            year_level = curriculum.year_levels[i]
            semester_count_key = f'year_{i + 1}_semesters'
            semester_count = request.form.get(semester_count_key)
            
            if semester_count is not None:
                try:
                    semester_count = int(semester_count)
                    if semester_count < 0 or semester_count > 3:
                        continue
                    
                    current_semesters = len(year_level.semesters)
                    
                    if semester_count > current_semesters:
                        # Add new semesters
                        for sem_num in range(current_semesters + 1, semester_count + 1):
                            # Check if semester already exists
                            existing = Semester.query.filter_by(
                                year_level_id=year_level.id,
                                semester_number=sem_num
                            ).first()
                            if not existing:
                                semester = Semester(
                                    year_level_id=year_level.id,
                                    semester_number=sem_num,
                                    semester_name=semester_names[sem_num]
                                )
                                db.session.add(semester)
                    elif semester_count < current_semesters:
                        # Remove excess semesters (from the end)
                        for sem_num in range(semester_count + 1, current_semesters + 1):
                            semester = Semester.query.filter_by(
                                year_level_id=year_level.id,
                                semester_number=sem_num
                            ).first()
                            if semester:
                                db.session.delete(semester)
                except ValueError:
                    continue
        
        # Log activity
        log_edit('curriculum', curriculum.id, curriculum.curriculum_code, {
            'department': curriculum.department.department_code
        })
        
        db.session.commit()
        
        flash('Curriculum has been successfully updated!', 'success')
        
        # Preserve department filter in redirect
        department_id = request.args.get('department_id', type=int)
        url_params = {'curriculum_id': curriculum.id, 'open': curriculum.id}
        if department_id:
            url_params['department_id'] = department_id
        return redirect(url_for('curriculum.index', **url_params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the curriculum: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


# Year Level routes
@curriculum_bp.route('/year-level/edit', methods=['POST'])
@login_required
def edit_year_level():
    """Edit a year level"""
    try:
        year_level_id = request.form.get('year_level_id', '').strip()
        year_name = request.form.get('year_name', '').strip()
        
        if not all([year_level_id, year_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('curriculum.index'))
        
        year_level = YearLevel.query.get(int(year_level_id))
        if not year_level:
            flash('Year level not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        year_level.year_name = year_name
        db.session.commit()
        
        flash('Year level has been successfully updated!', 'success')
        params = build_redirect_params(
            curriculum_id=year_level.curriculum_id, 
            year_level_id=year_level.id
        )
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the year level: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


@curriculum_bp.route('/year-level/delete', methods=['POST'])
@login_required
def delete_year_level():
    """Delete a year level"""
    try:
        year_level_id = request.form.get('year_level_id', '').strip()
        
        if not year_level_id:
            flash('Invalid year level.', 'error')
            return redirect(url_for('curriculum.index'))
        
        year_level = YearLevel.query.get(int(year_level_id))
        if not year_level:
            flash('Year level not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        curriculum_id = year_level.curriculum_id
        db.session.delete(year_level)
        db.session.commit()
        
        flash('Year level has been successfully deleted!', 'success')
        params = build_redirect_params(curriculum_id=curriculum_id)
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the year level: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


# Semester routes
@curriculum_bp.route('/semester/add', methods=['POST'])
@login_required
def add_semester():
    """Add semester(s) to a year level"""
    try:
        year_level_id = request.form.get('year_level_id', '').strip()
        semester_number = request.form.get('semester_number', '').strip()
        
        if not all([year_level_id, semester_number]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('curriculum.index'))
        
        try:
            semester_number = int(semester_number)
            if semester_number < 1 or semester_number > 3:
                flash('Semester number must be between 1 and 3.', 'error')
                return redirect(url_for('curriculum.index'))
        except ValueError:
            flash('Invalid semester number.', 'error')
            return redirect(url_for('curriculum.index'))
        
        try:
            year_level_id = int(year_level_id)
        except ValueError:
            flash('Invalid year level.', 'error')
            return redirect(url_for('curriculum.index'))
        
        year_level = YearLevel.query.get(year_level_id)
        if not year_level:
            flash('Year level not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        semester_names = {
            1: '1st Semester',
            2: '2nd Semester',
            3: 'Summer'
        }
        
        semesters_created = 0
        for i in range(1, semester_number + 1):
            existing_semester = Semester.query.filter_by(
                year_level_id=year_level_id,
                semester_number=i
            ).first()
            
            if not existing_semester:
                new_semester = Semester(
                    year_level_id=year_level_id,
                    semester_number=i,
                    semester_name=semester_names[i]
                )
                db.session.add(new_semester)
                semesters_created += 1
        
        if semesters_created > 0:
            db.session.commit()
            if semesters_created == 1:
                flash(f'{semester_names[semester_number]} has been successfully added!', 'success')
            else:
                flash(f'{semesters_created} semesters have been successfully added!', 'success')
        else:
            flash(f'All semesters up to {semester_names[semester_number]} already exist for this year level.', 'info')
        
        params = build_redirect_params(
            curriculum_id=year_level.curriculum_id, 
            year_level_id=year_level.id
        )
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the semester: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


@curriculum_bp.route('/semester/edit', methods=['POST'])
@login_required
def edit_semester():
    """Edit a semester"""
    try:
        semester_id = request.form.get('semester_id', '').strip()
        semester_name = request.form.get('semester_name', '').strip()
        
        if not all([semester_id, semester_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('curriculum.index'))
        
        semester = Semester.query.get(int(semester_id))
        if not semester:
            flash('Semester not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        semester.semester_name = semester_name
        db.session.commit()
        
        flash('Semester has been successfully updated!', 'success')
        params = build_redirect_params(
            curriculum_id=semester.year_level.curriculum_id,
            year_level_id=semester.year_level.id,
            semester_id=semester.id
        )
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the semester: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


@curriculum_bp.route('/semester/delete', methods=['POST'])
@login_required
def delete_semester():
    """Delete a semester"""
    try:
        semester_id = request.form.get('semester_id', '').strip()
        
        if not semester_id:
            flash('Invalid semester.', 'error')
            return redirect(url_for('curriculum.index'))
        
        semester = Semester.query.get(int(semester_id))
        if not semester:
            flash('Semester not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        curriculum_id = semester.year_level.curriculum_id
        year_level_id = semester.year_level.id
        db.session.delete(semester)
        db.session.commit()
        
        flash('Semester has been successfully deleted!', 'success')
        # Don't pass semester ID when deleting - the semester no longer exists
        params = build_redirect_params(
            curriculum_id=curriculum_id,
            year_level_id=year_level_id
        )
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the semester: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


# Subject Template routes - REMOVED (templates no longer used)
# Templates have been removed from the system. Subjects now store all data directly.

@curriculum_bp.route('/subject/add', methods=['POST'])
@login_required
def add_subject():
    """Add a new subject"""
    try:
        semester_id = request.form.get('semester_id', '').strip()
        subject_code = request.form.get('subject_code', '').strip().upper()
        course_description = request.form.get('course_description', '').strip()
        lec_units = request.form.get('lec_units', '').strip()
        lab_units = request.form.get('lab_units', '').strip()
        prerequisite = request.form.get('prerequisite', '').strip()
        
        # Validate required fields
        if not all([semester_id, subject_code, course_description, lec_units, lab_units]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('curriculum.index'))
        
        try:
            semester_id = int(semester_id)
            lec_units = float(lec_units)
            lab_units = float(lab_units)
            
            if lec_units < 0 or lec_units > 10 or lab_units < 0 or lab_units > 10:
                flash('Units must be between 0 and 10.', 'error')
                return redirect(url_for('curriculum.index'))
        except ValueError:
            flash('Invalid input values.', 'error')
            return redirect(url_for('curriculum.index'))
        
        semester = Semester.query.get(semester_id)
        if not semester:
            flash('Semester not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        # Create new subject directly
        new_subject = Subject(
            semester_id=semester_id,
            subject_code=subject_code,
            course_description=course_description,
            lec_units=lec_units,
            lab_units=lab_units,
            prerequisite=prerequisite if prerequisite else None
        )
        
        db.session.add(new_subject)
        db.session.flush()
        
        # Log activity
        log_create('subject', new_subject.id, subject_code, {
            'description': course_description,
            'semester': semester.semester_name
        })
        
        db.session.commit()
        
        flash(f'Subject "{subject_code}" added successfully!', 'success')
        
        params = build_redirect_params(
            curriculum_id=semester.year_level.curriculum_id,
            year_level_id=semester.year_level.id,
            semester_id=semester.id
        )
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the subject: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))




@curriculum_bp.route('/subject/edit', methods=['POST'])
@login_required
def edit_subject():
    """Edit a subject"""
    try:
        subject_id = request.form.get('subject_id', '').strip()
        subject_code = request.form.get('subject_code', '').strip().upper()
        course_description = request.form.get('course_description', '').strip()
        lec_units = request.form.get('lec_units', '').strip()
        lab_units = request.form.get('lab_units', '').strip()
        prerequisite = request.form.get('prerequisite', '').strip()
        
        if not all([subject_id, subject_code, course_description, lec_units, lab_units]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('curriculum.index'))
        
        try:
            lec_units = float(lec_units)
            lab_units = float(lab_units)
            if lec_units < 0 or lec_units > 10 or lab_units < 0 or lab_units > 10:
                flash('Units must be between 0 and 10.', 'error')
                return redirect(url_for('curriculum.index'))
        except ValueError:
            flash('Invalid units value.', 'error')
            return redirect(url_for('curriculum.index'))
        
        subject = Subject.query.get(int(subject_id))
        if not subject:
            flash('Subject not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        # Track changes
        changes = {}
        if subject.subject_code != subject_code:
            changes['code'] = f'{subject.subject_code} → {subject_code}'
        if subject.course_description != course_description:
            changes['description'] = f'{subject.course_description} → {course_description}'
        if subject.lec_units != lec_units:
            changes['lec_units'] = f'{subject.lec_units} → {lec_units}'
        if subject.lab_units != lab_units:
            changes['lab_units'] = f'{subject.lab_units} → {lab_units}'
        if subject.prerequisite != (prerequisite if prerequisite else None):
            old_prereq = subject.prerequisite or 'None'
            new_prereq = prerequisite if prerequisite else 'None'
            changes['prerequisite'] = f'{old_prereq} → {new_prereq}'
        
        # Update subject fields directly
        subject.subject_code = subject_code
        subject.course_description = course_description
        subject.lec_units = lec_units
        subject.lab_units = lab_units
        subject.prerequisite = prerequisite if prerequisite else None
        
        # Log activity with changes
        log_edit('subject', subject.id, subject_code, changes if changes else None)
        
        db.session.commit()
        
        flash('Subject has been successfully updated!', 'success')
        
        params = build_redirect_params(
            curriculum_id=subject.semester.year_level.curriculum_id,
            year_level_id=subject.semester.year_level.id,
            semester_id=subject.semester.id
        )
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the subject: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))



@curriculum_bp.route('/subject/delete', methods=['POST'])
@login_required
def delete_subject():
    """Delete a subject"""
    try:
        subject_id = request.form.get('subject_id', '').strip()
        
        if not subject_id:
            flash('Invalid subject.', 'error')
            return redirect(url_for('curriculum.index'))
        
        subject = Subject.query.get(int(subject_id))
        if not subject:
            flash('Subject not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        curriculum_id = subject.semester.year_level.curriculum_id
        year_level_id = subject.semester.year_level.id
        semester_id = subject.semester.id
        subject_code = subject.subject_code
        
        # Log activity before deletion
        log_delete('subject', subject.id, subject_code, {'description': subject.course_description})
        
        db.session.delete(subject)
        db.session.commit()
        
        flash('Subject has been successfully deleted!', 'success')
        params = build_redirect_params(
            curriculum_id=curriculum_id,
            year_level_id=year_level_id,
            semester_id=semester_id
        )
        return redirect(url_for('curriculum.index', **params))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the subject: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


@curriculum_bp.route('/archive', methods=['POST'])
@login_required
def archive():
    """Archive a curriculum"""
    try:
        curriculum_id = request.form.get('curriculum_id', '').strip()
        archive_reason = request.form.get('archive_reason', 'Manual archive by user').strip()
        
        if not curriculum_id:
            flash('Invalid curriculum.', 'error')
            return redirect(url_for('curriculum.index'))
        
        curriculum = Curriculum.query.get(int(curriculum_id))
        if not curriculum:
            flash('Curriculum not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        curriculum_code = curriculum.curriculum_code
        
        # Archive curriculum using helper method
        curriculum.archive(user_id=current_user.id, reason=archive_reason)
        
        # Log activity
        log_archive('curriculum', curriculum.id, curriculum_code, {
            'department': curriculum.department.department_code,
            'reason': archive_reason
        })
        
        db.session.commit()
        
        flash(f'Curriculum "{curriculum_code}" has been archived successfully!', 'success')
        return redirect(url_for('curriculum.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while archiving the curriculum: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


@curriculum_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a curriculum permanently (only for archived curricula)"""
    try:
        curriculum_id = request.form.get('curriculum_id', '').strip()
        
        if not curriculum_id:
            flash('Invalid curriculum.', 'error')
            return redirect(url_for('archive.index'))
        
        curriculum = Curriculum.query.get(int(curriculum_id))
        if not curriculum:
            flash('Curriculum not found.', 'error')
            return redirect(url_for('archive.index'))
        
        if not curriculum.is_archived:
            flash('Only archived curricula can be permanently deleted.', 'error')
            return redirect(url_for('curriculum.index'))
        
        curriculum_code = curriculum.curriculum_code
        
        # Log activity before deletion
        log_delete('curriculum', curriculum.id, curriculum_code, {
            'department': curriculum.department.department_code
        })
        
        # Delete curriculum (cascade will delete year levels, semesters, and subjects)
        db.session.delete(curriculum)
        db.session.commit()
        
        flash(f'Curriculum "{curriculum_code}" has been permanently deleted!', 'success')
        return redirect(url_for('archive.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the curriculum: {str(e)}', 'error')
        return redirect(url_for('archive.index'))


# Bulk Import Routes
@curriculum_bp.route('/bulk-import/template/<int:curriculum_id>')
@login_required
def download_bulk_import_template(curriculum_id):
    """Generate and download Excel template for bulk subject import"""
    try:
        curriculum = Curriculum.query.get(curriculum_id)
        if not curriculum:
            flash('Curriculum not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        # Create Excel template with instructions
        output = io.BytesIO()
        
        # Prepare data structure for the template
        template_data = []
        
        # Add empty rows for each year level and semester combination
        for year_level in curriculum.year_levels:
            for semester in year_level.semesters:
                template_data.append({
                    'Year Level': year_level.year_name,
                    'Semester': semester.semester_name,
                    'Subject Code': '',
                    'Course Description': '',
                    'Lecture Units': '',
                    'Lab Units': '',
                    'Prerequisite': ''
                })
        
        # Create DataFrame
        df = pd.DataFrame(template_data)
        
        # Write to Excel with formatting
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Subjects', index=False, startrow=2)
            
            # Get the workbook and worksheet
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            
            workbook = writer.book
            worksheet = writer.sheets['Subjects']
            
            # Add title
            worksheet['A1'] = f'{curriculum.curriculum_code} - Bulk Import Template'
            worksheet['A1'].font = Font(bold=True, size=14, color='FFFFFF')
            worksheet['A1'].fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
            worksheet['A1'].alignment = Alignment(horizontal='center', vertical='center')
            worksheet.merge_cells('A1:G1')  # Changed back to G1
            worksheet.row_dimensions[1].height = 25
            
            # Style header row (row 3 after title and blank row)
            header_fill = PatternFill(start_color='3B82F6', end_color='3B82F6', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            border_style = Border(
                left=Side(style='thin', color='FFFFFF'),
                right=Side(style='thin', color='FFFFFF'),
                top=Side(style='thin', color='FFFFFF'),
                bottom=Side(style='thin', color='FFFFFF')
            )
            
            for col in range(1, 8):  # A to G (7 columns)
                cell = worksheet.cell(row=3, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = border_style
            
            worksheet.row_dimensions[3].height = 30
            
            # Style data rows with alternating colors
            data_border = Border(
                left=Side(style='thin', color='E5E7EB'),
                right=Side(style='thin', color='E5E7EB'),
                top=Side(style='thin', color='E5E7EB'),
                bottom=Side(style='thin', color='E5E7EB')
            )
            
            for row_idx, row in enumerate(worksheet.iter_rows(min_row=4, max_row=len(template_data) + 3), start=4):
                # Alternate row colors
                if row_idx % 2 == 0:
                    fill = PatternFill(start_color='F9FAFB', end_color='F9FAFB', fill_type='solid')
                else:
                    fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
                
                for cell in row:
                    cell.fill = fill
                    cell.border = data_border
                    cell.alignment = Alignment(vertical='center', wrap_text=True)
                    
                    # Center align specific columns
                    if cell.column in [1, 2, 5, 6]:  # Year, Semester, Lec, Lab
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                
                worksheet.row_dimensions[row_idx].height = 20
            
            # Set column widths
            column_widths = {
                'A': 15,  # Year Level
                'B': 18,  # Semester
                'C': 18,  # Subject Code
                'D': 45,  # Course Description
                'E': 14,  # Lecture Units
                'F': 14,  # Lab Units
                'G': 25   # Prerequisite
            }
            
            for col_letter, width in column_widths.items():
                worksheet.column_dimensions[col_letter].width = width
            
            # Add data validation for numeric columns
            from openpyxl.worksheet.datavalidation import DataValidation
            
            # Lecture Units validation (0-9)
            lec_validation = DataValidation(
                type="decimal",
                operator="between",
                formula1=0,
                formula2=9,
                allow_blank=False,
                showErrorMessage=True,
                error='Lecture units must be between 0 and 9',
                errorTitle='Invalid Value'
            )
            worksheet.add_data_validation(lec_validation)
            lec_validation.add(f'E4:E{len(template_data) + 3}')
            
            # Lab Units validation (0-9)
            lab_validation = DataValidation(
                type="decimal",
                operator="between",
                formula1=0,
                formula2=9,
                allow_blank=False,
                showErrorMessage=True,
                error='Lab units must be between 0 and 9',
                errorTitle='Invalid Value'
            )
            worksheet.add_data_validation(lab_validation)
            lab_validation.add(f'F4:F{len(template_data) + 3}')
            
            # Freeze panes (freeze header rows - freeze at row 4 to keep title and headers visible)
            worksheet.freeze_panes = 'A4'
            
            # Add data validation for numeric columns
            from openpyxl.worksheet.datavalidation import DataValidation
            
            # Lecture Units validation (0-9)
            instructions_data = {
                'Step': [1, 2, 3, 4, 5, 6, 7],
                'Instructions': [
                    'Fill in the subject details for each year level and semester',
                    'Subject Code: Unique code (e.g., CS101, MATH101, ENG101)',
                    'Course Description: Full name of the subject',
                    'Lecture Units: Number of lecture units (0.0 to 9.0)',
                    'Lab Units: Number of lab units (0.0 to 9.0)',
                    'Prerequisite: Required subject code or "None" if no prerequisite',
                    'Delete unused rows or duplicate rows to add more subjects'
                ]
            }
            instructions_df = pd.DataFrame(instructions_data)
            instructions_df.to_excel(writer, sheet_name='Instructions', index=False, startrow=1)
            
            # Format instructions sheet
            inst_sheet = writer.sheets['Instructions']
            
            # Add title
            inst_sheet['A1'] = 'How to Use This Template'
            inst_sheet['A1'].font = Font(bold=True, size=14, color='FFFFFF')
            inst_sheet['A1'].fill = PatternFill(start_color='10B981', end_color='10B981', fill_type='solid')
            inst_sheet['A1'].alignment = Alignment(horizontal='center', vertical='center')
            inst_sheet.merge_cells('A1:B1')
            inst_sheet.row_dimensions[1].height = 25
            
            # Style header
            for col in [1, 2]:
                cell = inst_sheet.cell(row=2, column=col)
                cell.fill = PatternFill(start_color='34D399', end_color='34D399', fill_type='solid')
                cell.font = Font(bold=True, color='FFFFFF', size=11)
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Style instruction rows (7 steps)
            for row_idx in range(3, 10):
                inst_sheet.cell(row=row_idx, column=1).alignment = Alignment(horizontal='center', vertical='center')
                inst_sheet.cell(row=row_idx, column=1).font = Font(bold=True, size=11)
                inst_sheet.cell(row=row_idx, column=2).alignment = Alignment(vertical='center', wrap_text=True)
                inst_sheet.row_dimensions[row_idx].height = 30
            
            inst_sheet.column_dimensions['A'].width = 8
            inst_sheet.column_dimensions['B'].width = 80
            
            # Add important notes at the bottom
            notes_row = 11
            inst_sheet[f'A{notes_row}'] = '⚠️ Important Notes:'
            inst_sheet[f'A{notes_row}'].font = Font(bold=True, size=12, color='DC2626')
            inst_sheet.merge_cells(f'A{notes_row}:B{notes_row}')
            
            notes = [
                '• Year Level and Semester names must match EXACTLY with your curriculum structure',
                '• Subject codes should be clear and consistent (e.g., CS101, MATH101)',
                '• System automatically manages subject templates - no need to worry about it!',
                '• Identical subjects (same code & units) will be linked automatically',
                '• Duplicate subjects in the same semester will be skipped with an error',
                f'• This template is for curriculum: {curriculum.curriculum_code}',
                '• Upload only Excel files (.xlsx or .xls format)'
            ]
            
            for idx, note in enumerate(notes, start=1):
                inst_sheet[f'B{notes_row + idx}'] = note
                inst_sheet[f'B{notes_row + idx}'].font = Font(size=10, italic=True)
                inst_sheet[f'B{notes_row + idx}'].alignment = Alignment(wrap_text=True)
                inst_sheet.row_dimensions[notes_row + idx].height = 20
        
        output.seek(0)
        
        filename = f"{curriculum.curriculum_code}_bulk_import_template.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error generating template: {str(e)}', 'error')
        return redirect(url_for('curriculum.index'))


@curriculum_bp.route('/bulk-import/<int:curriculum_id>', methods=['POST'])
@login_required
def bulk_import_subjects(curriculum_id):
    """Process bulk import of subjects from Excel file"""
    try:
        curriculum = Curriculum.query.get(curriculum_id)
        if not curriculum:
            flash('Curriculum not found.', 'error')
            return redirect(url_for('curriculum.index'))
        
        # Check if file was uploaded
        if 'bulk_import_file' not in request.files:
            flash('No file uploaded.', 'error')
            return redirect(url_for('curriculum.index', curriculum_id=curriculum_id, open=curriculum_id))
        
        file = request.files['bulk_import_file']
        
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('curriculum.index', curriculum_id=curriculum_id, open=curriculum_id))
        
        # Validate file extension
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Invalid file format. Please upload an Excel file (.xlsx or .xls)', 'error')
            return redirect(url_for('curriculum.index', curriculum_id=curriculum_id, open=curriculum_id))
        
        # Read Excel file (skip title row, headers are at row 3 which is index 2)
        df = pd.read_excel(file, sheet_name='Subjects', header=2)
        
        # Validate required columns
        required_columns = ['Year Level', 'Semester', 'Subject Code', 'Course Description', 'Lecture Units', 'Lab Units']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            flash(f'Missing required columns: {", ".join(missing_columns)}', 'error')
            return redirect(url_for('curriculum.index', curriculum_id=curriculum_id, open=curriculum_id))
        
        # Process each row
        subjects_added = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Calculate actual Excel row number (header is at row 3, data starts at row 4)
                excel_row = index + 4
                
                # Skip empty rows
                if pd.isna(row['Subject Code']) or str(row['Subject Code']).strip() == '':
                    continue
                
                # Get subject data
                subject_code = str(row['Subject Code']).strip().upper()
                course_description = str(row['Course Description']).strip()
                
                # Validate required fields
                if not subject_code or not course_description:
                    errors.append(f"Row {excel_row}: Subject Code and Course Description are required")
                    continue
                
                # Find matching year level and semester
                year_level = None
                for yl in curriculum.year_levels:
                    if yl.year_name.strip().lower() == str(row['Year Level']).strip().lower():
                        year_level = yl
                        break
                
                if not year_level:
                    errors.append(f"Row {excel_row}: Year level '{row['Year Level']}' not found")
                    continue
                
                semester = None
                for sem in year_level.semesters:
                    if sem.semester_name.strip().lower() == str(row['Semester']).strip().lower():
                        semester = sem
                        break
                
                if not semester:
                    errors.append(f"Row {excel_row}: Semester '{row['Semester']}' not found in {year_level.year_name}")
                    continue
                
                lec_units = float(row['Lecture Units']) if not pd.isna(row['Lecture Units']) else 0.0
                lab_units = float(row['Lab Units']) if not pd.isna(row['Lab Units']) else 0.0
                prerequisite = str(row['Prerequisite']).strip() if not pd.isna(row['Prerequisite']) and str(row['Prerequisite']).strip().lower() != 'none' else None
                
                if prerequisite and prerequisite.lower() == 'none':
                    prerequisite = None
                
                # Check if subject already exists in this semester
                existing_subject = Subject.query.filter_by(
                    semester_id=semester.id,
                    subject_code=subject_code
                ).first()
                
                if existing_subject:
                    errors.append(f"Row {excel_row}: Subject '{subject_code}' already exists in {year_level.year_name} - {semester.semester_name}")
                    continue
                
                # Create new subject directly
                new_subject = Subject(
                    semester_id=semester.id,
                    subject_code=subject_code,
                    course_description=course_description,
                    lec_units=lec_units,
                    lab_units=lab_units,
                    prerequisite=prerequisite
                )
                
                db.session.add(new_subject)
                subjects_added += 1
                
            except Exception as e:
                errors.append(f"Row {excel_row}: {str(e)}")
                continue
        
        # Commit all changes
        db.session.commit()
        
        # Show results
        if subjects_added > 0:
            flash(f'Successfully imported {subjects_added} subject(s)!', 'success')
        
        if errors:
            error_msg = f'{len(errors)} error(s) occurred:<br>' + '<br>'.join(errors[:10])
            if len(errors) > 10:
                error_msg += f'<br>... and {len(errors) - 10} more errors'
            flash(error_msg, 'error')
        
        if subjects_added == 0 and not errors:
            flash('No subjects were imported. Please make sure your file contains valid subject data with all required fields filled in.', 'info')
        
        return redirect(url_for('curriculum.index', curriculum_id=curriculum_id, open=curriculum_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred during bulk import: {str(e)}', 'error')
        return redirect(url_for('curriculum.index', curriculum_id=curriculum_id, open=curriculum_id))

