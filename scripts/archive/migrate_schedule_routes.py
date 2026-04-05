"""
Migration script: Split monolithic schedule index into separate view routes
and update all redirect references.
"""
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# 1. Modify schedule.py - Replace index(), add new view routes
# ============================================================================
schedule_path = os.path.join(BASE_DIR, 'app', 'routes', 'schedule.py')
with open(schedule_path, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Find the index function boundaries (line 42 = @schedule_bp.route('/'))
# We want to replace lines from @schedule_bp.route('/') through the end of 
# the render_template() call + blank lines before @schedule_bp.route('/add')

# Find start of index function
idx_start = None
for i, line in enumerate(lines):
    if line.strip() == "@schedule_bp.route('/')":
        idx_start = i
        break

# Find start of add() function (the function AFTER index)
idx_add_start = None
for i, line in enumerate(lines):
    if line.strip() == "@schedule_bp.route('/add', methods=['POST'])":
        idx_add_start = i
        break

assert idx_start is not None, "Could not find index route"
assert idx_add_start is not None, "Could not find add route"

# Build the new code that replaces index() and adds view functions
new_routes_code = '''
@schedule_bp.route('/')
@login_required
def index():
    """Redirect to appropriate schedule view based on query params (backward compat)"""
    if request.args.get('faculty_id'):
        return redirect(url_for('schedule.faculty_view', **request.args))
    elif request.args.get('room_id'):
        return redirect(url_for('schedule.room_view', **request.args))
    elif request.args.get('exam_section_id'):
        args = request.args.to_dict()
        section_id = args.pop('exam_section_id', None)
        if section_id:
            args['section_id'] = section_id
        return redirect(url_for('schedule.exam_view', **args))
    return redirect(url_for('schedule.class_view', **request.args))


# ============================================================================
# HELPER: Common data loading functions
# ============================================================================

def _get_departments_for_user():
    """Get programs based on current user's access level."""
    user_department_ids = current_user.get_department_ids()
    if user_department_ids is None:
        return Program.query.filter_by(is_active=True).order_by(Program.program_code).all()
    else:
        return Program.query.filter(
            Program.is_active == True,
            Program.id.in_(user_department_ids)
        ).order_by(Program.program_code).all()


def _get_sections_for_user(department_filter=None):
    """Get sections based on current user's program access."""
    user_department_ids = current_user.get_department_ids()
    sections_query = Section.query
    if user_department_ids is not None:
        sections_query = sections_query.filter(Section.program_id.in_(user_department_ids))
    if department_filter:
        sections_query = sections_query.filter_by(program_id=department_filter)
    return sections_query.order_by(Section.section_name).all()


def _get_schedule_counts(items, model_class, id_field, current_settings, extra_filters=None):
    """Calculate schedule counts for a list of items."""
    counts = {}
    for item in items:
        q = model_class.query.filter(
            getattr(model_class, id_field) == item.id,
            model_class.is_active == True
        )
        if current_settings:
            q = q.filter(
                model_class.academic_year == current_settings.academic_year,
                model_class.semester == current_settings.semester
            )
        counts[item.id] = q.count()
    return counts


def _get_time_settings(current_settings):
    """Get schedule time range from settings."""
    return {
        'schedule_start_hour': current_settings.schedule_start_hour if current_settings else 7,
        'schedule_end_hour': current_settings.schedule_end_hour if current_settings else 20,
    }


def _get_exam_time_settings(current_settings):
    """Get exam-specific time settings."""
    settings = {
        'exam_start_hour': current_settings.exam_start_hour if current_settings else 7,
        'exam_end_hour': current_settings.exam_end_hour if current_settings else 17,
        'exam_lunch_start': '12:00',
        'exam_lunch_end': '13:00',
        'exam_slot_duration': current_settings.exam_slot_duration if current_settings else 30,
        'exam_duration_limit': current_settings.exam_duration_limit if current_settings else 120,
        'exam_period_start': None,
        'exam_period_end': None,
    }
    if current_settings:
        if current_settings.exam_lunch_start:
            settings['exam_lunch_start'] = current_settings.exam_lunch_start.strftime('%H:%M')
        if current_settings.exam_lunch_end:
            settings['exam_lunch_end'] = current_settings.exam_lunch_end.strftime('%H:%M')
        if hasattr(current_settings, 'exam_period_start') and current_settings.exam_period_start:
            settings['exam_period_start'] = current_settings.exam_period_start.strftime('%Y-%m-%d')
        if hasattr(current_settings, 'exam_period_end') and current_settings.exam_period_end:
            settings['exam_period_end'] = current_settings.exam_period_end.strftime('%Y-%m-%d')
    return settings


# ============================================================================
# VIEW ROUTES - Separate pages for each schedule type
# ============================================================================

@schedule_bp.route('/class')
@login_required
def class_view():
    """Class schedule view page - master-detail layout with sections"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    programs = _get_departments_for_user()

    department_filter = request.args.get('program_id', type=int)
    if department_filter is None and len(programs) == 1:
        department_filter = programs[0].id

    sections = _get_sections_for_user(department_filter)
    section_schedule_counts = _get_schedule_counts(sections, Schedule, 'section_id', current_settings)

    # Get selected section
    selected_section_id = request.args.get('section_id', type=int)
    selected_section = None
    schedules = []

    if selected_section_id:
        selected_section = Section.query.get(selected_section_id)
        if selected_section:
            schedules_query = Schedule.query.options(
                joinedload(Schedule.section),
                joinedload(Schedule.subject),
                joinedload(Schedule.faculty),
                joinedload(Schedule.room)
            ).filter_by(section_id=selected_section_id, is_active=True)
            if current_settings:
                schedules_query = schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            schedules = schedules_query.order_by(Schedule.day_of_week, Schedule.start_time).all()

    time_settings = _get_time_settings(current_settings)

    return render_template(
        'schedule_class.html',
        sections=sections,
        selected_section=selected_section,
        schedules=schedules,
        programs=programs,
        department_filter=department_filter,
        current_settings=current_settings,
        section_schedule_counts=section_schedule_counts,
        **time_settings
    )


@schedule_bp.route('/faculty')
@login_required
def faculty_view():
    """Faculty schedule view page - master-detail layout with faculty members"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    programs = _get_departments_for_user()

    faculty_department_filter = request.args.get('faculty_department_id', type=int)

    if faculty_department_filter:
        faculties_query = Faculty.query.filter(
            Faculty.is_active == True,
            Faculty.department_id == faculty_department_filter
        )
    else:
        faculties_query = Faculty.query.filter_by(is_active=True)

    faculties_list = faculties_query.order_by(Faculty.full_name).all()
    faculty_schedule_counts = _get_schedule_counts(faculties_list, Schedule, 'faculty_id', current_settings)

    # Get selected faculty
    selected_faculty_id = request.args.get('faculty_id', type=int)
    selected_faculty = None
    faculty_schedules = []

    if selected_faculty_id:
        selected_faculty = Faculty.query.get(selected_faculty_id)
        if selected_faculty:
            faculty_schedules_query = Schedule.query.options(
                joinedload(Schedule.section),
                joinedload(Schedule.subject),
                joinedload(Schedule.faculty),
                joinedload(Schedule.room)
            ).filter_by(faculty_id=selected_faculty_id, is_active=True)
            if current_settings:
                faculty_schedules_query = faculty_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            faculty_schedules = faculty_schedules_query.order_by(
                Schedule.day_of_week, Schedule.start_time
            ).all()

    time_settings = _get_time_settings(current_settings)

    return render_template(
        'schedule_faculty.html',
        faculties=faculties_list,
        selected_faculty=selected_faculty,
        faculty_schedules=faculty_schedules,
        programs=programs,
        faculty_department_filter=faculty_department_filter,
        current_settings=current_settings,
        faculty_schedule_counts=faculty_schedule_counts,
        **time_settings
    )


@schedule_bp.route('/room')
@login_required
def room_view():
    """Room schedule view page - master-detail layout with rooms"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()

    from app.models.building import Building
    buildings = Building.query.filter_by(is_active=True).order_by(Building.building_name).all()

    rooms_query = Room.query.filter_by(is_available=True)
    rooms_list = rooms_query.order_by(Room.room_number).all()
    room_schedule_counts = _get_schedule_counts(rooms_list, Schedule, 'room_id', current_settings)

    # Get selected room
    selected_room_id = request.args.get('room_id', type=int)
    selected_room = None
    room_schedules = []

    if selected_room_id:
        selected_room = Room.query.get(selected_room_id)
        if selected_room:
            room_schedules_query = Schedule.query.options(
                joinedload(Schedule.section),
                joinedload(Schedule.subject),
                joinedload(Schedule.faculty),
                joinedload(Schedule.room)
            ).filter_by(room_id=selected_room_id, is_active=True)
            if current_settings:
                room_schedules_query = room_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            room_schedules = room_schedules_query.order_by(
                Schedule.day_of_week, Schedule.start_time
            ).all()

    time_settings = _get_time_settings(current_settings)

    return render_template(
        'schedule_room.html',
        rooms=rooms_list,
        selected_room=selected_room,
        room_schedules=room_schedules,
        current_settings=current_settings,
        room_schedule_counts=room_schedule_counts,
        buildings=buildings,
        **time_settings
    )


@schedule_bp.route('/exam')
@login_required
def exam_view():
    """Exam schedule view page - master-detail layout with sections"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    programs = _get_departments_for_user()

    exam_department_filter = request.args.get('exam_department_id', type=int)
    if exam_department_filter is None and len(programs) == 1:
        exam_department_filter = programs[0].id

    exam_sections = _get_sections_for_user(exam_department_filter)
    exam_section_schedule_counts = _get_schedule_counts(
        exam_sections, ExamSchedule, 'section_id', current_settings
    )

    # Get selected section for exam
    selected_exam_section_id = request.args.get('section_id', type=int)
    selected_exam_section = None
    exam_schedules = []

    if selected_exam_section_id:
        selected_exam_section = Section.query.get(selected_exam_section_id)
        if selected_exam_section:
            exam_schedules_query = ExamSchedule.query.filter_by(
                section_id=selected_exam_section_id, is_active=True
            )
            if current_settings:
                exam_schedules_query = exam_schedules_query.filter_by(
                    academic_year=current_settings.academic_year,
                    semester=current_settings.semester
                )
            exam_schedules = exam_schedules_query.order_by(
                ExamSchedule.exam_date, ExamSchedule.start_time
            ).all()

    # Get all faculties and rooms for exam modals
    all_faculties = Faculty.query.filter_by(is_active=True).order_by(Faculty.full_name).all()
    all_rooms = Room.query.filter_by(is_available=True).order_by(Room.room_number).all()

    from app.models.building import Building
    buildings = Building.query.filter_by(is_active=True).order_by(Building.building_name).all()

    time_settings = _get_time_settings(current_settings)
    exam_time_settings = _get_exam_time_settings(current_settings)

    return render_template(
        'schedule_exam.html',
        exam_sections=exam_sections,
        selected_exam_section=selected_exam_section,
        exam_schedules=exam_schedules,
        programs=programs,
        exam_department_filter=exam_department_filter,
        current_settings=current_settings,
        exam_section_schedule_counts=exam_section_schedule_counts,
        all_faculties=all_faculties,
        all_rooms=all_rooms,
        buildings=buildings,
        **time_settings,
        **exam_time_settings
    )


@schedule_bp.route('/class/add')
@login_required
def class_add_page():
    """Render the add class schedule form page"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    section_id = request.args.get('section_id', type=int)
    selected_section = Section.query.get(section_id) if section_id else None

    time_settings = _get_time_settings(current_settings)

    return render_template(
        'schedule_class_form.html',
        mode='add',
        selected_section=selected_section,
        current_settings=current_settings,
        schedule=None,
        **time_settings
    )


@schedule_bp.route('/class/edit/<int:schedule_id>')
@login_required
def class_edit_page(schedule_id):
    """Render the edit class schedule form page"""
    schedule = Schedule.query.options(
        joinedload(Schedule.section),
        joinedload(Schedule.subject),
        joinedload(Schedule.faculty),
        joinedload(Schedule.room)
    ).get_or_404(schedule_id)

    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    time_settings = _get_time_settings(current_settings)

    return render_template(
        'schedule_class_form.html',
        mode='edit',
        selected_section=schedule.section,
        current_settings=current_settings,
        schedule=schedule,
        **time_settings
    )


@schedule_bp.route('/exam/add')
@login_required
def exam_add_page():
    """Render the add exam schedule form page"""
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    section_id = request.args.get('section_id', type=int)
    selected_section = Section.query.get(section_id) if section_id else None

    time_settings = _get_time_settings(current_settings)
    exam_time_settings = _get_exam_time_settings(current_settings)

    return render_template(
        'schedule_exam_form.html',
        mode='add',
        selected_section=selected_section,
        current_settings=current_settings,
        exam_schedule=None,
        **time_settings,
        **exam_time_settings
    )


@schedule_bp.route('/exam/edit/<int:exam_id>')
@login_required
def exam_edit_page(exam_id):
    """Render the edit exam schedule form page"""
    exam_schedule = ExamSchedule.query.get_or_404(exam_id)
    selected_section = Section.query.get(exam_schedule.section_id)

    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    time_settings = _get_time_settings(current_settings)
    exam_time_settings = _get_exam_time_settings(current_settings)

    return render_template(
        'schedule_exam_form.html',
        mode='edit',
        selected_section=selected_section,
        current_settings=current_settings,
        exam_schedule=exam_schedule,
        **time_settings,
        **exam_time_settings
    )

'''

# Reconstruct the file
before = '\n'.join(lines[:idx_start])
after = '\n'.join(lines[idx_add_start:])

new_content = before + '\n' + new_routes_code + '\n\n' + after

# ============================================================================
# 2. Update redirects in schedule.py: schedule.index → schedule.class_view
# ============================================================================
# All schedule.index redirects in schedule.py have section_id, so they go to class_view
new_content = new_content.replace(
    "url_for('schedule.index', section_id=section_id)",
    "url_for('schedule.class_view', section_id=section_id)"
)
# The cleanup_archived route redirects without section_id
new_content = new_content.replace(
    "url_for('schedule.index')",
    "url_for('schedule.class_view')"
)

with open(schedule_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"[OK] schedule.py updated: index→redirect, {4} view routes + {4} form routes added")
print(f"[OK] All schedule.index redirects updated to schedule.class_view")

# ============================================================================
# 3. Update exam_schedule.py redirects
# ============================================================================
exam_path = os.path.join(BASE_DIR, 'app', 'routes', 'exam_schedule.py')
with open(exam_path, 'r', encoding='utf-8') as f:
    exam_content = f.read()

# Replace exam redirects: schedule.index with exam_section_id → schedule.exam_view with section_id
exam_content = exam_content.replace(
    "url_for('schedule.index', exam_section_id=section_id)",
    "url_for('schedule.exam_view', section_id=section_id)"
)
exam_content = exam_content.replace(
    "url_for('schedule.index', exam_section_id=exam_schedule.section_id)",
    "url_for('schedule.exam_view', section_id=exam_schedule.section_id)"
)
# Generic schedule.index (no params)
exam_content = exam_content.replace(
    "url_for('schedule.index')",
    "url_for('schedule.exam_view')"
)

with open(exam_path, 'w', encoding='utf-8') as f:
    f.write(exam_content)

print(f"[OK] exam_schedule.py: All redirects updated to schedule.exam_view")

# ============================================================================
# 4. Update dashboard.html references
# ============================================================================
dash_path = os.path.join(BASE_DIR, 'app', 'templates', 'dashboard.html')
with open(dash_path, 'r', encoding='utf-8') as f:
    dash_content = f.read()

dash_content = dash_content.replace(
    "url_for('schedule.index')",
    "url_for('schedule.class_view')"
)

with open(dash_path, 'w', encoding='utf-8') as f:
    f.write(dash_content)

print(f"[OK] dashboard.html: Schedule links updated")

print("\n=== Route migration complete ===")
