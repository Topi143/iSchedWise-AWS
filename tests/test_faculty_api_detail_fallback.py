import inspect
from datetime import datetime, time

from flask import Flask

from app.routes import faculty as faculty_routes


class _DummyField:
    def desc(self):
        return self


class _ResultSet:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def order_by(self, *_args):
        ordered = sorted(
            self._rows,
            key=lambda row: (getattr(row, 'created_at', datetime.min), getattr(row, 'id', 0)),
            reverse=True,
        )
        return _ResultSet(ordered)


class _AssignmentQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter_by(self, **kwargs):
        filtered = []
        for row in self._rows:
            if all(getattr(row, key, None) == value for key, value in kwargs.items()):
                filtered.append(row)
        return _ResultSet(filtered)


class _AcademicSettingsQuery:
    def __init__(self, settings):
        self._settings = settings

    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return self._settings


class _FacultyQuery:
    def __init__(self, faculty):
        self._faculty = faculty

    def get(self, faculty_id):
        return self._faculty if self._faculty and self._faculty.id == faculty_id else None


class _ScheduleQuery:
    def __init__(self, rows=None):
        self._rows = list(rows or [])

    def filter_by(self, **_kwargs):
        filtered = []
        for row in self._rows:
            if all(getattr(row, key, None) == value for key, value in _kwargs.items()):
                filtered.append(row)
        return _ResultSet(filtered)

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self._rows)


class _Department:
    department_name = 'Engineering'
    department_code = 'ENG'


class _FacultyObj:
    def __init__(self, faculty_id=1):
        self.id = faculty_id
        self.is_archived = False
        self.full_name = 'Doe, Jane'
        self.last_name = 'Doe'
        self.first_name = 'Jane'
        self.middle_initial = 'Q'
        self.gender = 'Female'
        self.department_id = 1
        self.department = _Department()

    def get_load_status(self, *_args):
        return (0.0, 21, 0.0, 'normal')


class _Curriculum:
    def __init__(self, code='BSCS-2024'):
        self.curriculum_code = code


class _YearLevel:
    def __init__(self, name='1st Year', curriculum=None):
        self.year_name = name
        self.curriculum = curriculum or _Curriculum()


class _Semester:
    def __init__(self, name='1st Semester', year_level=None):
        self.semester_name = name
        self.year_level = year_level or _YearLevel()


class _Subject:
    def __init__(self, subject_id, code, units=3.0, semester=None):
        self.id = subject_id
        self.subject_code = code
        self.course_description = f'{code} description'
        self.total_units = units
        self.semester = semester or _Semester()


class _Assignment:
    def __init__(
        self,
        assignment_id,
        faculty_id,
        subject,
        academic_year,
        semester,
        is_active=True,
        is_archived=False,
        created_at=None,
    ):
        self.id = assignment_id
        self.faculty_id = faculty_id
        self.subject_id = subject.id
        self.subject = subject
        self.academic_year = academic_year
        self.semester = semester
        self.is_active = is_active
        self.is_archived = is_archived
        self.created_at = created_at or datetime(2026, 1, 1)


class _ScheduleObj:
    def __init__(
        self,
        schedule_id,
        faculty_id,
        subject,
        academic_year,
        semester,
        start_time,
        end_time,
        day_of_week='Monday',
        schedule_type='Lecture',
        is_active=True,
    ):
        self.id = schedule_id
        self.faculty_id = faculty_id
        self.subject = subject
        self.subject_id = subject.id if subject else None
        self.academic_year = academic_year
        self.semester = semester
        self.start_time = start_time
        self.end_time = end_time
        self.day_of_week = day_of_week
        self.schedule_type = schedule_type
        self.section = None
        self.room = None
        self.is_active = is_active


def _unwrap(func):
    return inspect.unwrap(func)


def _install_common_stubs(monkeypatch, settings, faculty_obj, assignments, schedules=None):
    settings_model = type('SettingsModel', (), {'query': _AcademicSettingsQuery(settings)})
    faculty_model = type('FacultyModel', (), {'query': _FacultyQuery(faculty_obj)})
    assignment_model = type(
        'AssignmentModel',
        (),
        {
            'query': _AssignmentQuery(assignments),
            'created_at': _DummyField(),
            'id': _DummyField(),
        },
    )
    schedule_model = type('ScheduleModel', (), {
        'query': _ScheduleQuery(schedules),
        'subject_id': _DummyField(),
        'day_of_week': _DummyField(),
        'start_time': _DummyField(),
    })

    monkeypatch.setattr(faculty_routes, 'AcademicSettings', settings_model)
    monkeypatch.setattr(faculty_routes, 'Faculty', faculty_model)
    monkeypatch.setattr(faculty_routes, 'FacultySubjectAssignment', assignment_model)
    monkeypatch.setattr(faculty_routes, 'Schedule', schedule_model)


def test_api_detail_prefers_active_context_when_assignments_exist(monkeypatch):
    app = Flask(__name__)

    settings = type('Settings', (), {'academic_year': '2025-2026', 'semester': '2nd Semester'})()
    faculty_obj = _FacultyObj(1)

    active_sem = _Semester('2nd Semester', _YearLevel('2nd Year', _Curriculum('BSCS-2025')))
    old_sem = _Semester('1st Semester', _YearLevel('1st Year', _Curriculum('BSCS-2024')))
    assignments = [
        _Assignment(
            1,
            1,
            _Subject(11, 'CS201', 3.0, active_sem),
            '2025-2026',
            '2nd Semester',
            is_active=False,
            created_at=datetime(2026, 2, 1),
        ),
        _Assignment(2, 1, _Subject(12, 'CS101', 3.0, old_sem), '2025-2026', '1st Semester', created_at=datetime(2025, 8, 1)),
    ]

    _install_common_stubs(monkeypatch, settings, faculty_obj, assignments)

    with app.app_context():
        response = _unwrap(faculty_routes.api_detail)(1)

    data = response.get_json()
    assert data['assignment_context']['source'] == 'active'
    assert data['assignment_context']['academic_year'] == '2025-2026'
    assert data['assignment_context']['semester'] == '2nd Semester'
    assert data['context_warning'] is None
    assert len(data['assignments']) == 1
    assert data['assignments'][0]['subject_code'] == 'CS201'


def test_api_detail_does_not_fallback_to_latest_non_archived_context(monkeypatch):
    app = Flask(__name__)

    settings = type('Settings', (), {'academic_year': '2026-2027', 'semester': '1st Semester'})()
    faculty_obj = _FacultyObj(1)

    sem_1 = _Semester('1st Semester', _YearLevel('2nd Year', _Curriculum('BSCS-2025')))
    sem_2 = _Semester('2nd Semester', _YearLevel('2nd Year', _Curriculum('BSCS-2025')))
    assignments = [
        _Assignment(5, 1, _Subject(21, 'CS220', 3.0, sem_2), '2025-2026', '2nd Semester', created_at=datetime(2026, 2, 15)),
        _Assignment(4, 1, _Subject(20, 'CS210', 3.0, sem_1), '2025-2026', '1st Semester', created_at=datetime(2025, 9, 1)),
    ]

    _install_common_stubs(monkeypatch, settings, faculty_obj, assignments)

    with app.app_context():
        response = _unwrap(faculty_routes.api_detail)(1)

    data = response.get_json()
    assert data['assignment_context']['source'] == 'active'
    assert data['assignment_context']['academic_year'] == '2026-2027'
    assert data['assignment_context']['semester'] == '1st Semester'
    assert data.get('context_warning') is None
    assert data['assignments'] == []
    assert data['workload']['assigned_units'] == 0.0
    assert data['workload']['scheduled_units'] == 0.0


def test_api_detail_returns_empty_when_only_archived_history_exists(monkeypatch):
    app = Flask(__name__)

    settings = type('Settings', (), {'academic_year': '2026-2027', 'semester': '1st Semester'})()
    faculty_obj = _FacultyObj(1)

    old_sem = _Semester('2nd Semester', _YearLevel('2nd Year', _Curriculum('BSCS-2025')))
    assignments = [
        _Assignment(
            7,
            1,
            _Subject(30, 'CS299', 3.0, old_sem),
            '2025-2026',
            '2nd Semester',
            is_archived=True,
            created_at=datetime(2026, 2, 10),
        )
    ]

    _install_common_stubs(monkeypatch, settings, faculty_obj, assignments)

    with app.app_context():
        response = _unwrap(faculty_routes.api_detail)(1)

    data = response.get_json()
    assert data['assignment_context']['source'] == 'active'
    assert data['context_warning'] is None
    assert data['assignments'] == []
    assert data['workload']['assigned_units'] == 0.0
    assert data['workload']['scheduled_units'] == 0.0
    assert data['workload']['weekly_hours'] == 0.0


def test_api_detail_includes_weekly_hours_from_active_term_schedules(monkeypatch):
    app = Flask(__name__)

    settings = type('Settings', (), {'academic_year': '2025-2026', 'semester': '2nd Semester'})()
    faculty_obj = _FacultyObj(1)

    active_sem = _Semester('2nd Semester', _YearLevel('2nd Year', _Curriculum('BSCS-2025')))
    subject = _Subject(11, 'CS201', 3.0, active_sem)
    assignments = [
        _Assignment(1, 1, subject, '2025-2026', '2nd Semester', created_at=datetime(2026, 2, 1)),
    ]
    schedules = [
        _ScheduleObj(1, 1, subject, '2025-2026', '2nd Semester', time(8, 0), time(9, 30)),
        _ScheduleObj(2, 1, subject, '2025-2026', '2nd Semester', time(10, 0), time(12, 0)),
    ]

    _install_common_stubs(monkeypatch, settings, faculty_obj, assignments, schedules=schedules)

    with app.app_context():
        response = _unwrap(faculty_routes.api_detail)(1)

    data = response.get_json()
    assert data['workload']['weekly_hours'] == 3.5


def test_api_detail_includes_schedule_derived_subject_when_assignment_row_missing(monkeypatch):
    app = Flask(__name__)

    settings = type('Settings', (), {'academic_year': '2025-2026', 'semester': '2nd Semester'})()
    faculty_obj = _FacultyObj(1)

    active_sem = _Semester('2nd Semester', _YearLevel('2nd Year', _Curriculum('BSCS-2025')))
    subject = _Subject(31, 'CS231', 3.0, active_sem)
    assignments = []
    schedules = [
        _ScheduleObj(10, 1, subject, '2025-2026', '2nd Semester', time(13, 0), time(14, 30)),
    ]

    _install_common_stubs(monkeypatch, settings, faculty_obj, assignments, schedules=schedules)

    with app.app_context():
        response = _unwrap(faculty_routes.api_detail)(1)

    data = response.get_json()
    assert data['assignment_context']['source'] == 'active'
    assert data['context_warning'] is None
    assert len(data['assignments']) == 1
    assert data['assignments'][0]['subject_code'] == 'CS231'
    assert data['assignments'][0]['id'] is None
    assert data['assignments'][0]['is_schedule_derived'] is True
    assert data['workload']['assigned_count'] == 1
