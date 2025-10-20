"""
Schedule routes for managing class schedules
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from datetime import datetime, time
from app.extensions import db, csrf
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.department import Department, Section
from app.models.curriculum import Subject
from app.models.faculty import Faculty, FacultySubjectAssignment
from app.models.building import Room
from app.models.settings import AcademicSettings
from app.decorators import role_required

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')


@schedule_bp.route('/')
@login_required
def index():
    """Schedule management page with two-panel layout"""
    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    # Get user's department access
    user_department_ids = current_user.get_department_ids()
    
    # Get departments based on user access
    if user_department_ids is None:
        # Admin - see all departments
        departments = Department.query.filter_by(is_active=True).order_by(Department.department_code).all()
    else:
        # Dean - only assigned departments
        departments = Department.query.filter(
            Department.is_active == True,
            Department.id.in_(user_department_ids)
        ).order_by(Department.department_code).all()
    
    # Get department filter from query params
    department_filter = request.args.get('department_id', type=int)
    
    # Get sections based on filter
    sections_query = Section.query.filter_by(is_active=True)
    
    # Filter by user's department access
    if user_department_ids is not None:
        sections_query = sections_query.filter(Section.department_id.in_(user_department_ids))
    
    # Apply additional department filter if specified
    if department_filter:
        sections_query = sections_query.filter_by(department_id=department_filter)
    
    sections = sections_query.order_by(Section.section_name).all()
    
    # Calculate schedule counts for current academic period
    # Initialize empty dict to prevent Jinja2 undefined errors
    section_schedule_counts = {}
    
    if current_settings:
        for section in sections:
            count = Schedule.query.filter_by(
                section_id=section.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            section_schedule_counts[section.id] = count
    else:
        # No active settings, count all active schedules
        for section in sections:
            count = Schedule.query.filter_by(
                section_id=section.id,
                is_active=True
            ).count()
            section_schedule_counts[section.id] = count
    
    # Get selected section for class tab
    selected_section_id = request.args.get('section_id', type=int)
    selected_section = None
    schedules = []
    
    if selected_section_id:
        selected_section = Section.query.get(selected_section_id)
        if selected_section:
            # Get schedules for selected section
            schedules_query = Schedule.query.filter_by(
                section_id=selected_section_id,
                is_active=True
            )
            
            # Filter by current academic settings if available
            if current_settings:
                schedules_query = schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            
            schedules = schedules_query.order_by(
                Schedule.day_of_week,
                Schedule.start_time
            ).all()
    
    # Get faculties for faculty tab
    faculties_query = Faculty.query.filter_by(is_active=True)
    if current_user.role == 'Dean' and current_user.department_id:
        faculties_query = faculties_query.filter_by(department_id=current_user.department_id)
    faculties_list = faculties_query.order_by(Faculty.full_name).all()
    
    # Calculate faculty schedule counts for current academic period
    faculty_schedule_counts = {}
    if current_settings:
        for faculty in faculties_list:
            count = Schedule.query.filter_by(
                faculty_id=faculty.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            faculty_schedule_counts[faculty.id] = count
    else:
        for faculty in faculties_list:
            count = Schedule.query.filter_by(
                faculty_id=faculty.id,
                is_active=True
            ).count()
            faculty_schedule_counts[faculty.id] = count
    
    # Get selected faculty
    selected_faculty_id = request.args.get('faculty_id', type=int)
    selected_faculty = None
    faculty_schedules = []
    
    if selected_faculty_id:
        selected_faculty = Faculty.query.get(selected_faculty_id)
        if selected_faculty:
            faculty_schedules_query = Schedule.query.filter_by(
                faculty_id=selected_faculty_id,
                is_active=True
            )
            if current_settings:
                faculty_schedules_query = faculty_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            faculty_schedules = faculty_schedules_query.order_by(
                Schedule.day_of_week,
                Schedule.start_time
            ).all()
    
    # Get rooms for room tab
    rooms_list = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()
    
    # Calculate room schedule counts for current academic period
    room_schedule_counts = {}
    if current_settings:
        for room in rooms_list:
            count = Schedule.query.filter_by(
                room_id=room.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            room_schedule_counts[room.id] = count
    else:
        for room in rooms_list:
            count = Schedule.query.filter_by(
                room_id=room.id,
                is_active=True
            ).count()
            room_schedule_counts[room.id] = count
    
    # Get selected room
    selected_room_id = request.args.get('room_id', type=int)
    selected_room = None
    room_schedules = []
    
    if selected_room_id:
        selected_room = Room.query.get(selected_room_id)
        if selected_room:
            room_schedules_query = Schedule.query.filter_by(
                room_id=selected_room_id,
                is_active=True
            )
            if current_settings:
                room_schedules_query = room_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            room_schedules = room_schedules_query.order_by(
                Schedule.day_of_week,
                Schedule.start_time
            ).all()
    
    # Get all subjects for modals
    subjects = Subject.query.order_by(Subject.subject_code).all()
    
    # Get exam schedule data
    # Get sections for exam tab (reuse the sections query)
    exam_sections = sections
    exam_department_filter = request.args.get('exam_department_id', type=int)
    
    # Calculate exam schedule counts for current academic period
    exam_section_schedule_counts = {}
    if current_settings:
        for section in exam_sections:
            count = ExamSchedule.query.filter_by(
                section_id=section.id,
                is_active=True,
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            ).count()
            exam_section_schedule_counts[section.id] = count
    else:
        for section in exam_sections:
            count = ExamSchedule.query.filter_by(
                section_id=section.id,
                is_active=True
            ).count()
            exam_section_schedule_counts[section.id] = count
    
    # Get selected section for exam tab
    selected_exam_section_id = request.args.get('exam_section_id', type=int)
    selected_exam_section = None
    exam_schedules = []
    
    if selected_exam_section_id:
        selected_exam_section = Section.query.get(selected_exam_section_id)
        if selected_exam_section:
            exam_schedules_query = ExamSchedule.query.filter_by(
                section_id=selected_exam_section_id,
                is_active=True
            )
            if current_settings:
                exam_schedules_query = exam_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            exam_schedules = exam_schedules_query.order_by(
                ExamSchedule.exam_date,
                ExamSchedule.start_time
            ).all()
    
    # Get all faculties and rooms for exam modals
    all_faculties = Faculty.query.filter_by(is_active=True).order_by(Faculty.full_name).all()
    all_rooms = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()
    
    # Get all buildings for room filter
    from app.models.building import Building
    buildings = Building.query.filter_by(is_active=True).order_by(Building.building_name).all()
    
    return render_template(
        'schedule.html',
        sections=sections,
        selected_section=selected_section,
        schedules=schedules,
        departments=departments,
        department_filter=department_filter,
        subjects=subjects,
        faculties=faculties_list,
        selected_faculty=selected_faculty,
        faculty_schedules=faculty_schedules,
        rooms=rooms_list,
        selected_room=selected_room,
        room_schedules=room_schedules,
        current_settings=current_settings,
        section_schedule_counts=section_schedule_counts,
        faculty_schedule_counts=faculty_schedule_counts,
        room_schedule_counts=room_schedule_counts,
        # Exam schedule data
        exam_sections=exam_sections,
        selected_exam_section=selected_exam_section,
        exam_schedules=exam_schedules,
        exam_department_filter=exam_department_filter,
        exam_section_schedule_counts=exam_section_schedule_counts,
        all_faculties=all_faculties,
        all_rooms=all_rooms,
        buildings=buildings
    )


@schedule_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new schedule"""
    try:
        section_id = request.form.get('section_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int) or None
        room_id = request.form.get('room_id', type=int) or None
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        schedule_type = request.form.get('schedule_type', 'lecture')
        
        # Validation
        if not all([section_id, subject_id, day_of_week, start_time_str, end_time_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        academic_year = current_settings.academic_year if current_settings else None
        semester = current_settings.semester if current_settings else None
        
        # Convert time strings to time objects
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Check for conflicts - same section, day, and overlapping time
        conflict_query = Schedule.query.filter(
            Schedule.section_id == section_id,
            Schedule.day_of_week == day_of_week,
            Schedule.is_active == True,
            or_(
                and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
            )
        )
        
        if academic_year and semester:
            conflict_query = conflict_query.filter(
                Schedule.academic_year == academic_year,
                Schedule.semester == semester
            )
        
        if conflict_query.first():
            flash('Schedule conflict: This section already has a class at this time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Check for faculty conflicts if faculty assigned
        if faculty_id:
            faculty_conflict = Schedule.query.filter(
                Schedule.faculty_id == faculty_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                faculty_conflict = faculty_conflict.filter(
                    Schedule.academic_year == academic_year,
                    Schedule.semester == semester
                )
            
            if faculty_conflict.first():
                flash('Faculty conflict: This faculty member is already assigned to another class at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
        # Check for room conflicts if room assigned
        if room_id:
            room_conflict = Schedule.query.filter(
                Schedule.room_id == room_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if academic_year and semester:
                room_conflict = room_conflict.filter(
                    Schedule.academic_year == academic_year,
                    Schedule.semester == semester
                )
            
            if room_conflict.first():
                flash('Room conflict: This room is already booked at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
        # Create new schedule
        new_schedule = Schedule(
            section_id=section_id,
            subject_id=subject_id,
            faculty_id=faculty_id,
            room_id=room_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            schedule_type=schedule_type,
            academic_year=academic_year,
            semester=semester,
            is_active=True
        )
        
        db.session.add(new_schedule)
        db.session.commit()
        
        flash('Schedule added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing schedule"""
    try:
        schedule_id = request.form.get('schedule_id', type=int)
        subject_id = request.form.get('subject_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int) or None
        room_id = request.form.get('room_id', type=int) or None
        day_of_week = request.form.get('day_of_week')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        schedule_type = request.form.get('schedule_type', 'lecture')
        
        # Get schedule
        schedule = Schedule.query.get_or_404(schedule_id)
        section_id = schedule.section_id
        
        # Validation
        if not all([subject_id, day_of_week, start_time_str, end_time_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Convert time strings to time objects
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate time range
        if start_time >= end_time:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Check for conflicts (excluding current schedule)
        conflict_query = Schedule.query.filter(
            Schedule.id != schedule_id,
            Schedule.section_id == schedule.section_id,
            Schedule.day_of_week == day_of_week,
            Schedule.is_active == True,
            or_(
                and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
            )
        )
        
        if schedule.academic_year and schedule.semester:
            conflict_query = conflict_query.filter(
                Schedule.academic_year == schedule.academic_year,
                Schedule.semester == schedule.semester
            )
        
        if conflict_query.first():
            flash('Schedule conflict: This section already has a class at this time.', 'error')
            return redirect(url_for('schedule.index', section_id=section_id))
        
        # Check for faculty conflicts if faculty assigned
        if faculty_id:
            faculty_conflict = Schedule.query.filter(
                Schedule.id != schedule_id,
                Schedule.faculty_id == faculty_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if schedule.academic_year and schedule.semester:
                faculty_conflict = faculty_conflict.filter(
                    Schedule.academic_year == schedule.academic_year,
                    Schedule.semester == schedule.semester
                )
            
            if faculty_conflict.first():
                flash('Faculty conflict: This faculty member is already assigned to another class at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
        # Check for room conflicts if room assigned
        if room_id:
            room_conflict = Schedule.query.filter(
                Schedule.id != schedule_id,
                Schedule.room_id == room_id,
                Schedule.day_of_week == day_of_week,
                Schedule.is_active == True,
                or_(
                    and_(Schedule.start_time <= start_time, Schedule.end_time > start_time),
                    and_(Schedule.start_time < end_time, Schedule.end_time >= end_time),
                    and_(Schedule.start_time >= start_time, Schedule.end_time <= end_time)
                )
            )
            
            if schedule.academic_year and schedule.semester:
                room_conflict = room_conflict.filter(
                    Schedule.academic_year == schedule.academic_year,
                    Schedule.semester == schedule.semester
                )
            
            if room_conflict.first():
                flash('Room conflict: This room is already booked at this time.', 'error')
                return redirect(url_for('schedule.index', section_id=section_id))
        
        # Update schedule
        schedule.subject_id = subject_id
        schedule.faculty_id = faculty_id
        schedule.room_id = room_id
        schedule.day_of_week = day_of_week
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.schedule_type = schedule_type
        schedule.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Schedule updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a schedule"""
    try:
        schedule_id = request.form.get('schedule_id', type=int)
        
        schedule = Schedule.query.get_or_404(schedule_id)
        section_id = schedule.section_id
        
        # Soft delete (set is_active to False)
        schedule.is_active = False
        schedule.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Schedule deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/get-subjects/<int:section_id>')
@login_required
def get_subjects_for_section(section_id):
    """Get subjects for a specific section based on department, year level, and semester"""
    from flask import jsonify
    from app.models.curriculum import Curriculum, YearLevel, Semester
    
    try:
        # Get the section
        section = Section.query.get_or_404(section_id)
        
        # Get current academic settings to determine the semester
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if not current_settings:
            return jsonify({'subjects': []})
        
        # Determine semester number from semester name
        semester_mapping = {
            '1st Semester': 1,
            '2nd Semester': 2,
            'Summer': 3
        }
        semester_number = semester_mapping.get(current_settings.semester, 1)
        
        # Find curriculum for this department
        curriculum = Curriculum.query.filter_by(
            department_id=section.department_id,
            is_active=True
        ).first()
        
        if not curriculum:
            return jsonify({'subjects': []})
        
        # Find the year level
        year_level = YearLevel.query.filter_by(
            curriculum_id=curriculum.id,
            year_number=section.year_level
        ).first()
        
        if not year_level:
            return jsonify({'subjects': []})
        
        # Find the semester within that year level
        semester = Semester.query.filter_by(
            year_level_id=year_level.id,
            semester_number=semester_number
        ).first()
        
        if not semester:
            return jsonify({'subjects': []})
        
        # Get all subjects for this semester
        subjects = Subject.query.filter_by(semester_id=semester.id).order_by(Subject.subject_code).all()
        
        # Format subjects for JSON response with unit information
        subjects_data = [
            {
                'id': subject.id,
                'subject_code': subject.subject_code,
                'course_description': subject.course_description,
                'lec_units': float(subject.lec_units),
                'lab_units': float(subject.lab_units),
                'total_units': subject.total_units,
                'display': f"{subject.subject_code} - {subject.course_description} ({subject.total_units} units)"
            }
            for subject in subjects
        ]
        
        return jsonify({'subjects': subjects_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/get-faculty/<int:subject_id>')
@login_required
def get_faculty_for_subject(subject_id):
    """Get faculty members assigned to a specific subject"""
    try:
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if not current_settings:
            return jsonify({'faculty': []})
        
        # Get faculty assignments for this subject and current academic period
        assignments = FacultySubjectAssignment.query.filter_by(
            subject_id=subject_id,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            is_active=True,
            is_archived=False
        ).all()
        
        # Get unique faculty IDs
        faculty_ids = list(set([assignment.faculty_id for assignment in assignments]))
        
        # Get faculty details
        faculties = Faculty.query.filter(
            Faculty.id.in_(faculty_ids),
            Faculty.is_active == True,
            Faculty.is_archived == False
        ).order_by(Faculty.full_name).all()
        
        # Format faculty for JSON response
        faculty_data = [
            {
                'id': faculty.id,
                'full_name': faculty.full_name,
                'department_code': faculty.department.department_code if faculty.department else '',
                'display': f"{faculty.full_name}" + (f" - {faculty.department.department_code}" if faculty.department else "")
            }
            for faculty in faculties
        ]
        
        return jsonify({'faculty': faculty_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/ai-check-conflicts', methods=['POST'])
@login_required
@csrf.exempt  # Exempt CSRF for AJAX endpoints
def ai_check_conflicts():
    """AI-powered conflict detection and recommendations"""
    from app.ai_scheduler import ai_scheduler
    from datetime import datetime as dt
    
    try:
        data = request.get_json()
        
        # Debug logging
        print(f"[AI CHECK] Received data: {data}")
        
        if not data:
            return jsonify({'error': 'No data received', 'ai_enabled': False}), 400
        
        # Parse schedule data
        section_id = data.get('section_id')
        subject_id = data.get('subject_id')
        faculty_id = data.get('faculty_id')
        room_id = data.get('room_id')
        day_of_week = data.get('day_of_week')
        schedule_type = data.get('schedule_type', 'lecture')  # Default to lecture
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        schedule_id = data.get('schedule_id')  # For edit mode
        
        # Debug logging
        print(f"[AI CHECK] Parsed - section:{section_id} day:{day_of_week} type:{schedule_type} time:{start_time_str}-{end_time_str}")
        
        if not all([section_id, day_of_week, start_time_str, end_time_str]):
            missing = []
            if not section_id: missing.append('section_id')
            if not day_of_week: missing.append('day_of_week')
            if not start_time_str: missing.append('start_time')
            if not end_time_str: missing.append('end_time')
            error_msg = f'Missing required fields: {", ".join(missing)}'
            print(f"[AI CHECK] Validation failed: {error_msg}")
            return jsonify({'error': error_msg, 'ai_enabled': False}), 400
        
        # Convert times
        start_time = dt.strptime(start_time_str, '%H:%M').time()
        end_time = dt.strptime(end_time_str, '%H:%M').time()
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Get existing schedules for the same academic period
        existing_query = Schedule.query.filter_by(is_active=True)
        
        if current_settings:
            existing_query = existing_query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        # Exclude current schedule if editing
        if schedule_id:
            existing_query = existing_query.filter(Schedule.id != schedule_id)
        
        existing_schedules = existing_query.all()
        
        # Prepare schedule data for AI analysis
        schedule_data = {
            'section_id': section_id,
            'subject_id': subject_id,
            'faculty_id': faculty_id,
            'room_id': room_id,
            'day_of_week': day_of_week,
            'schedule_type': schedule_type,
            'start_time': start_time,
            'end_time': end_time
        }
        
        # Get AI analysis
        analysis = ai_scheduler.analyze_schedule_conflicts(schedule_data, existing_schedules)
        
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
            schedule = conflict.get('schedule')
            response['conflicts'].append({
                'type': conflict['type'],
                'message': conflict['message'],
                'severity': conflict['severity'],
                'details': {
                    'subject': schedule.subject.subject_code if schedule and schedule.subject else 'Unknown',
                    'time': f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}" if schedule else '',
                    'day': schedule.day_of_week if schedule else ''
                }
            })
        
        return jsonify(response)
        
    except Exception as e:
        print(f"AI check conflicts error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'ai_enabled': False}), 500


@schedule_bp.route('/ai-suggest-schedule', methods=['POST'])
@login_required
@csrf.exempt  # Exempt CSRF for AJAX endpoints
def ai_suggest_schedule():
    """Get AI suggestions for optimal scheduling"""
    from flask import jsonify
    from app.ai_scheduler import ai_scheduler
    
    try:
        data = request.get_json()
        
        section_id = data.get('section_id')
        subject_id = data.get('subject_id')
        faculty_id = data.get('faculty_id')
        
        if not section_id or not subject_id:
            return jsonify({'error': 'Section and subject are required'}), 400
        
        # Get models
        section = Section.query.get_or_404(section_id)
        subject = Subject.query.get_or_404(subject_id)
        faculty = Faculty.query.get(faculty_id) if faculty_id else None
        
        # Get AI suggestions
        result = ai_scheduler.suggest_optimal_schedule(section, subject, faculty)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"AI suggest schedule error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'ai_enabled': False}), 500


@schedule_bp.route('/export/class/<int:section_id>')
@login_required
def export_class_schedule(section_id):
    """Export class schedule to Excel"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    import io
    
    try:
        section = Section.query.get_or_404(section_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules for this section
        query = Schedule.query.filter_by(section_id=section_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Class Schedule"
        
        # Title
        title = f"{section.section_name} - Class Schedule"
        if current_settings:
            title += f" ({current_settings.academic_year} - {current_settings.semester})"
        
        ws['A1'] = title
        ws['A1'].font = Font(bold=True, size=14, color='FFFFFF')
        ws['A1'].fill = PatternFill(start_color='7C3AED', end_color='7C3AED', fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A1:H1')
        ws.row_dimensions[1].height = 30
        
        # Headers
        headers = ['Day', 'Time', 'Subject Code', 'Subject Description', 'Type', 'Faculty', 'Room', 'Units']
        header_fill = PatternFill(start_color='9333EA', end_color='9333EA', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border_style = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
        
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = border_style
        
        ws.row_dimensions[3].height = 25
        
        # Data rows
        data_border = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )
        
        for row_idx, schedule in enumerate(schedules, start=4):
            time_str = f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}"
            faculty_name = schedule.faculty.full_name if schedule.faculty else 'TBA'
            room_display = ''
            if schedule.room:
                building_name = schedule.room.building.building_name if schedule.room.building else ''
                room_display = f"{building_name} {schedule.room.room_number}".strip()
            else:
                room_display = 'TBA'
            
            row_data = [
                schedule.day_of_week,
                time_str,
                schedule.subject.subject_code if schedule.subject else '',
                schedule.subject.course_description if schedule.subject else '',
                schedule.schedule_type.title(),
                faculty_name,
                room_display,
                float(schedule.subject.total_units) if schedule.subject else 0
            ]
            
            # Alternate row colors
            if row_idx % 2 == 0:
                fill = PatternFill(start_color='F9FAFB', end_color='F9FAFB', fill_type='solid')
            else:
                fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
            
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.fill = fill
                cell.border = data_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if col_idx in [1, 5, 8]:  # Day, Type, Units
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            ws.row_dimensions[row_idx].height = 20
        
        # Column widths
        ws.column_dimensions['A'].width = 12  # Day
        ws.column_dimensions['B'].width = 20  # Time
        ws.column_dimensions['C'].width = 15  # Subject Code
        ws.column_dimensions['D'].width = 40  # Description
        ws.column_dimensions['E'].width = 12  # Type
        ws.column_dimensions['F'].width = 25  # Faculty
        ws.column_dimensions['G'].width = 20  # Room
        ws.column_dimensions['H'].width = 10  # Units
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{section.section_name.replace(' ', '_')}_Schedule.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', section_id=section_id))


@schedule_bp.route('/export/faculty/<int:faculty_id>')
@login_required
def export_faculty_schedule(faculty_id):
    """Export faculty schedule to Excel"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    import io
    
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules for this faculty
        query = Schedule.query.filter_by(faculty_id=faculty_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Faculty Schedule"
        
        # Title
        title = f"{faculty.full_name} - Teaching Schedule"
        if current_settings:
            title += f" ({current_settings.academic_year} - {current_settings.semester})"
        
        ws['A1'] = title
        ws['A1'].font = Font(bold=True, size=14, color='FFFFFF')
        ws['A1'].fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A1:H1')
        ws.row_dimensions[1].height = 30
        
        # Headers
        headers = ['Day', 'Time', 'Subject Code', 'Subject Description', 'Section', 'Type', 'Room', 'Units']
        header_fill = PatternFill(start_color='3B82F6', end_color='3B82F6', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border_style = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
        
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = border_style
        
        ws.row_dimensions[3].height = 25
        
        # Data rows
        data_border = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )
        
        total_units = 0
        for row_idx, schedule in enumerate(schedules, start=4):
            time_str = f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}"
            room_display = ''
            if schedule.room:
                building_name = schedule.room.building.building_name if schedule.room.building else ''
                room_display = f"{building_name} {schedule.room.room_number}".strip()
            else:
                room_display = 'TBA'
            
            units = float(schedule.subject.total_units) if schedule.subject else 0
            total_units += units
            
            row_data = [
                schedule.day_of_week,
                time_str,
                schedule.subject.subject_code if schedule.subject else '',
                schedule.subject.course_description if schedule.subject else '',
                schedule.section.section_name if schedule.section else '',
                schedule.schedule_type.title(),
                room_display,
                units
            ]
            
            # Alternate row colors
            if row_idx % 2 == 0:
                fill = PatternFill(start_color='F9FAFB', end_color='F9FAFB', fill_type='solid')
            else:
                fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
            
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.fill = fill
                cell.border = data_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if col_idx in [1, 6, 8]:  # Day, Type, Units
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            ws.row_dimensions[row_idx].height = 20
        
        # Add total row
        total_row = len(schedules) + 4
        ws.cell(row=total_row, column=7, value='Total Units:').font = Font(bold=True)
        ws.cell(row=total_row, column=7).alignment = Alignment(horizontal='right', vertical='center')
        ws.cell(row=total_row, column=8, value=total_units).font = Font(bold=True)
        ws.cell(row=total_row, column=8).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=total_row, column=8).fill = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')
        
        # Column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 40
        ws.column_dimensions['E'].width = 20
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 20
        ws.column_dimensions['H'].width = 10
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{faculty.full_name.replace(' ', '_')}_Schedule.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', faculty_id=faculty_id))


@schedule_bp.route('/export/room/<int:room_id>')
@login_required
def export_room_schedule(room_id):
    """Export room schedule to Excel"""
    from flask import send_file
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    import io
    
    try:
        room = Room.query.get_or_404(room_id)
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        # Query schedules for this room
        query = Schedule.query.filter_by(room_id=room_id, is_active=True)
        if current_settings:
            query = query.filter_by(
                academic_year=current_settings.academic_year,
                semester=current_settings.semester
            )
        
        schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Room Schedule"
        
        # Title
        building_name = room.building.building_name if room.building else ''
        title = f"{building_name} {room.room_number} - Room Schedule"
        if current_settings:
            title += f" ({current_settings.academic_year} - {current_settings.semester})"
        
        ws['A1'] = title
        ws['A1'].font = Font(bold=True, size=14, color='FFFFFF')
        ws['A1'].fill = PatternFill(start_color='10B981', end_color='10B981', fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A1:H1')
        ws.row_dimensions[1].height = 30
        
        # Headers
        headers = ['Day', 'Time', 'Subject Code', 'Subject Description', 'Section', 'Type', 'Faculty', 'Units']
        header_fill = PatternFill(start_color='059669', end_color='059669', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border_style = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
        
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = border_style
        
        ws.row_dimensions[3].height = 25
        
        # Data rows
        data_border = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )
        
        for row_idx, schedule in enumerate(schedules, start=4):
            time_str = f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}"
            faculty_name = schedule.faculty.full_name if schedule.faculty else 'TBA'
            
            row_data = [
                schedule.day_of_week,
                time_str,
                schedule.subject.subject_code if schedule.subject else '',
                schedule.subject.course_description if schedule.subject else '',
                schedule.section.section_name if schedule.section else '',
                schedule.schedule_type.title(),
                faculty_name,
                float(schedule.subject.total_units) if schedule.subject else 0
            ]
            
            # Alternate row colors
            if row_idx % 2 == 0:
                fill = PatternFill(start_color='F9FAFB', end_color='F9FAFB', fill_type='solid')
            else:
                fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
            
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.fill = fill
                cell.border = data_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if col_idx in [1, 6, 8]:  # Day, Type, Units
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            ws.row_dimensions[row_idx].height = 20
        
        # Column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 40
        ws.column_dimensions['E'].width = 20
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 25
        ws.column_dimensions['H'].width = 10
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{building_name}_{room.room_number}_Schedule.xlsx".replace(' ', '_')
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', room_id=room_id))


@schedule_bp.route('/export/exam/<int:section_id>')
@login_required
def export_exam_schedule(section_id):
    """Export exam schedule to Excel"""
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
        
        # Title
        title = f"{section.section_name} - Exam Schedule"
        if current_settings:
            title += f" ({current_settings.academic_year} - {current_settings.semester} - {current_settings.exam_period})"
        
        ws['A1'] = title
        ws['A1'].font = Font(bold=True, size=14, color='FFFFFF')
        ws['A1'].fill = PatternFill(start_color='DC2626', end_color='DC2626', fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.merge_cells('A1:G1')
        ws.row_dimensions[1].height = 30
        
        # Headers
        headers = ['Date', 'Time', 'Subject Code', 'Subject Description', 'Faculty', 'Room', 'Units']
        header_fill = PatternFill(start_color='EF4444', end_color='EF4444', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border_style = Border(
            left=Side(style='thin', color='FFFFFF'),
            right=Side(style='thin', color='FFFFFF'),
            top=Side(style='thin', color='FFFFFF'),
            bottom=Side(style='thin', color='FFFFFF')
        )
        
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = border_style
        
        ws.row_dimensions[3].height = 25
        
        # Data rows
        data_border = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )
        
        for row_idx, exam in enumerate(exam_schedules, start=4):
            date_str = exam.exam_date.strftime('%B %d, %Y')
            time_str = f"{exam.start_time.strftime('%I:%M %p')} - {exam.end_time.strftime('%I:%M %p')}"
            faculty_name = exam.faculty.full_name if exam.faculty else 'TBA'
            room_display = ''
            if exam.room:
                building_name = exam.room.building.building_name if exam.room.building else ''
                room_display = f"{building_name} {exam.room.room_number}".strip()
            else:
                room_display = 'TBA'
            
            row_data = [
                date_str,
                time_str,
                exam.subject.subject_code if exam.subject else '',
                exam.subject.course_description if exam.subject else '',
                faculty_name,
                room_display,
                float(exam.subject.total_units) if exam.subject else 0
            ]
            
            # Alternate row colors
            if row_idx % 2 == 0:
                fill = PatternFill(start_color='F9FAFB', end_color='F9FAFB', fill_type='solid')
            else:
                fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')
            
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.fill = fill
                cell.border = data_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if col_idx in [1, 7]:  # Date, Units
                    cell.alignment = Alignment(horizontal='center', vertical='center')
            
            ws.row_dimensions[row_idx].height = 20
        
        # Column widths
        ws.column_dimensions['A'].width = 18  # Date
        ws.column_dimensions['B'].width = 20  # Time
        ws.column_dimensions['C'].width = 15  # Subject Code
        ws.column_dimensions['D'].width = 40  # Description
        ws.column_dimensions['E'].width = 25  # Faculty
        ws.column_dimensions['F'].width = 20  # Room
        ws.column_dimensions['G'].width = 10  # Units
        
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"{section.section_name.replace(' ', '_')}_Exam_Schedule.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error exporting exam schedule: {str(e)}', 'error')
        return redirect(url_for('schedule.index', exam_section_id=section_id))

