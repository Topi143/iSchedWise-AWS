import inspect

from flask import Flask

from app.routes import schedule as schedule_routes


class _DummyField:
    def desc(self):
        return self


class _SimpleQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *_args, **_kwargs):
        return self

    def filter_by(self, **_kwargs):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class _Department:
    def __init__(self, code='ENG', name='Engineering'):
        self.department_code = code
        self.department_name = name


class _FacultyObj:
    def __init__(self, faculty_id, first_name, last_name, department=None):
        self.id = faculty_id
        self.first_name = first_name
        self.last_name = last_name
        self.full_name = f'{last_name}, {first_name}'
        self.department = department

    def get_max_units(self):
        return 21


def _unwrap(func):
    return inspect.unwrap(func)


def test_get_faculty_for_subject_returns_available_days_when_no_active_settings(monkeypatch):
    app = Flask(__name__)

    faculties = [_FacultyObj(1, 'Jane', 'Doe', _Department())]
    faculty_model = type('FacultyModel', (), {
        'query': _SimpleQuery(faculties),
        'is_active': True,
        'is_archived': False,
        'last_name': _DummyField(),
        'first_name': _DummyField(),
    })
    settings_model = type('SettingsModel', (), {'query': _SimpleQuery([])})
    assignment_model = type('AssignmentModel', (), {'query': _SimpleQuery([])})
    schedule_model = type('ScheduleModel', (), {'query': _SimpleQuery([])})

    monkeypatch.setattr(schedule_routes, 'Faculty', faculty_model)
    monkeypatch.setattr(schedule_routes, 'AcademicSettings', settings_model)
    monkeypatch.setattr(schedule_routes, 'FacultySubjectAssignment', assignment_model)
    monkeypatch.setattr(schedule_routes, 'Schedule', schedule_model)

    calls = {'count': 0}

    def fake_days_map(faculty_ids):
        calls['count'] += 1
        return {faculty_ids[0]: ['Monday', 'Wednesday']}

    monkeypatch.setattr(schedule_routes, '_build_faculty_available_days_map', fake_days_map)

    with app.app_context():
        response = _unwrap(schedule_routes.get_faculty_for_subject)(999)

    data = response.get_json()
    assert 'faculty' in data
    assert len(data['faculty']) == 1
    assert data['faculty'][0]['available_days'] == ['Monday', 'Wednesday']
    assert calls['count'] == 1


def test_get_faculty_for_subject_returns_available_days_when_no_schedules(monkeypatch):
    app = Flask(__name__)

    faculties = [
        _FacultyObj(1, 'Jane', 'Doe', _Department('ENG', 'Engineering')),
        _FacultyObj(2, 'John', 'Smith', _Department('SCI', 'Science')),
    ]
    faculty_model = type('FacultyModel', (), {
        'query': _SimpleQuery(faculties),
        'is_active': True,
        'is_archived': False,
        'last_name': _DummyField(),
        'first_name': _DummyField(),
    })
    active_settings = type('Settings', (), {'academic_year': '2025-2026', 'semester': '2nd Semester'})()
    settings_model = type('SettingsModel', (), {'query': _SimpleQuery([active_settings])})
    assignment_model = type('AssignmentModel', (), {'query': _SimpleQuery([])})
    schedule_model = type('ScheduleModel', (), {'query': _SimpleQuery([])})

    monkeypatch.setattr(schedule_routes, 'Faculty', faculty_model)
    monkeypatch.setattr(schedule_routes, 'AcademicSettings', settings_model)
    monkeypatch.setattr(schedule_routes, 'FacultySubjectAssignment', assignment_model)
    monkeypatch.setattr(schedule_routes, 'Schedule', schedule_model)
    monkeypatch.setattr(
        schedule_routes,
        '_build_faculty_available_days_map',
        lambda faculty_ids: {faculty_ids[0]: ['Tuesday'], faculty_ids[1]: []},
    )

    with app.app_context():
        response = _unwrap(schedule_routes.get_faculty_for_subject)(123)

    data = response.get_json()
    assert len(data['faculty']) == 2
    by_id = {item['id']: item for item in data['faculty']}
    assert by_id[1]['available_days'] == ['Tuesday']
    assert by_id[2]['available_days'] == []
