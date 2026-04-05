import inspect
import io
from datetime import time

from flask import Flask

from app.routes import faculty as faculty_routes
from app.services import export_service


class _Criterion:
    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value


class _Field:
    def __init__(self, name):
        self.name = name

    def in_(self, values):
        return _Criterion(self.name, 'in', list(values))

    def is_(self, value):
        return _Criterion(self.name, 'is', value)

    def isnot(self, value):
        return _Criterion(self.name, 'isnot', value)

    def __eq__(self, value):
        return _Criterion(self.name, 'eq', value)


class _DummyUser:
    def __init__(self, program_ids):
        self._program_ids = program_ids
        self.full_name = 'Dean User'

    def get_program_ids(self):
        return self._program_ids


class _DummyDepartment:
    def __init__(self, name='College of Computing Studies', code='CCS'):
        self.department_name = name
        self.department_code = code
        self.secretary_name = 'Secretary Name'


class _DummyProgram:
    def __init__(self, program_id, code='BSCS', name='BS Computer Science', department=None):
        self.id = program_id
        self.program_code = code
        self.program_name = name
        self.department = department
        self.department_id = 1 if department else None


class _DummySection:
    def __init__(self, section_id, section_name):
        self.id = section_id
        self.full_section_name = section_name


class _DummySubject:
    def __init__(self, code='CS101', units=3):
        self.subject_code = code
        self.total_units = units


class _DummyFaculty:
    id = _Field('id')
    is_archived = _Field('is_archived')
    last_name = _Field('last_name')
    first_name = _Field('first_name')
    query = None

    def __init__(self, faculty_id, full_name, is_archived=False):
        self.id = faculty_id
        self.full_name = full_name
        self.is_archived = is_archived
        self.last_name = full_name.split(',')[0]
        self.first_name = full_name.split(',')[1].strip() if ',' in full_name else ''


class _DummySchedule:
    subject = object()
    section = object()
    faculty = object()
    section_id = _Field('section_id')
    is_active = _Field('is_active')
    academic_year = _Field('academic_year')
    semester = _Field('semester')
    faculty_id = _Field('faculty_id')
    day_of_week = _Field('day_of_week')
    start_time = _Field('start_time')
    query = None

    def __init__(
        self,
        section_id,
        faculty,
        section,
        subject,
        start_time_value,
        end_time_value,
        academic_year='2025-2026',
        semester='1st Semester',
        is_active=True,
    ):
        self.section_id = section_id
        self.faculty = faculty
        self.faculty_id = faculty.id if faculty else None
        self.section = section
        self.subject = subject
        self.start_time = start_time_value
        self.end_time = end_time_value
        self.academic_year = academic_year
        self.semester = semester
        self.is_active = is_active
        self.day_of_week = 'Monday'


class _SettingsQuery:
    def __init__(self, settings):
        self._settings = settings

    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return self._settings


class _ProgramQuery:
    def __init__(self, programs_by_id):
        self._programs_by_id = programs_by_id

    def options(self, *_args):
        return self

    def get_or_404(self, program_id):
        if program_id not in self._programs_by_id:
            raise AssertionError('Program not found in test stub')
        return self._programs_by_id[program_id]


class _SectionQuery:
    def __init__(self, sections_by_program):
        self._sections_by_program = sections_by_program
        self._selected_program_id = None

    def filter_by(self, **kwargs):
        self._selected_program_id = kwargs.get('program_id')
        return self

    def all(self):
        return list(self._sections_by_program.get(self._selected_program_id, []))


class _ScheduleQuery:
    def __init__(self, schedules):
        self._schedules = list(schedules)

    def options(self, *_args):
        return self

    def filter(self, *criteria):
        filtered = list(self._schedules)
        for criterion in criteria:
            if not isinstance(criterion, _Criterion):
                continue
            if criterion.field == 'section_id' and criterion.op == 'in':
                filtered = [row for row in filtered if row.section_id in set(criterion.value)]
            elif criterion.field == 'is_active' and criterion.op == 'is':
                filtered = [row for row in filtered if row.is_active is criterion.value]
            elif criterion.field == 'academic_year' and criterion.op == 'eq':
                filtered = [row for row in filtered if row.academic_year == criterion.value]
            elif criterion.field == 'semester' and criterion.op == 'eq':
                filtered = [row for row in filtered if row.semester == criterion.value]
            elif criterion.field == 'faculty_id' and criterion.op == 'isnot' and criterion.value is None:
                filtered = [row for row in filtered if row.faculty_id is not None]
        return _ScheduleResult(filtered)


class _ScheduleResult:
    def __init__(self, schedules):
        self._schedules = list(schedules)

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self._schedules)


class _FacultyQuery:
    def __init__(self, faculties):
        self._faculties = list(faculties)

    def filter(self, *criteria):
        filtered = list(self._faculties)
        for criterion in criteria:
            if not isinstance(criterion, _Criterion):
                continue
            if criterion.field == 'id' and criterion.op == 'in':
                filtered = [row for row in filtered if row.id in set(criterion.value)]
            elif criterion.field == 'is_archived' and criterion.op == 'is':
                filtered = [row for row in filtered if row.is_archived is criterion.value]
        return _FacultyResult(filtered)


class _FacultyResult:
    def __init__(self, faculties):
        self._faculties = list(faculties)

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self._faculties)


def _unwrap(func):
    return inspect.unwrap(func)


def _build_app():
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    app.register_blueprint(faculty_routes.faculty_bp)
    return app


def test_export_lineup_requires_program_id(monkeypatch):
    app = _build_app()

    monkeypatch.setattr(faculty_routes, 'current_user', _DummyUser(program_ids=None))

    with app.test_request_context('/faculty/export/lineup'):
        response = _unwrap(faculty_routes.export_faculty_lineup)()

    assert response.status_code == 302
    assert response.location.endswith('/faculty/')


def test_export_lineup_blocks_dean_unassigned_program(monkeypatch):
    app = _build_app()

    program = _DummyProgram(1, code='BSCS')

    monkeypatch.setattr(faculty_routes.db, 'joinedload', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(faculty_routes, 'Program', type('ProgramModel', (), {'query': _ProgramQuery({1: program}), 'department': object()}))
    monkeypatch.setattr(faculty_routes, 'current_user', _DummyUser(program_ids=[2]))

    with app.test_request_context('/faculty/export/lineup?program_id=1'):
        response = _unwrap(faculty_routes.export_faculty_lineup)()

    assert response.status_code == 302
    assert response.location.endswith('/faculty/')


def test_export_lineup_exports_faculty_from_selected_program_sections(monkeypatch):
    app = _build_app()

    settings = type('Settings', (), {'academic_year': '2025-2026', 'semester': '1st Semester'})()
    program = _DummyProgram(1, code='BSCS', department=_DummyDepartment())

    section_a = _DummySection(11, 'BSCS-1A')
    section_b = _DummySection(12, 'BSCS-1B')
    section_other = _DummySection(99, 'BSED-1A')

    faculty_program = _DummyFaculty(1, 'Doe, Jane')
    faculty_other = _DummyFaculty(2, 'Smith, John')

    subject = _DummySubject('CS101', 3)
    schedules = [
        _DummySchedule(11, faculty_program, section_a, subject, time(8, 0), time(10, 0)),
        _DummySchedule(12, faculty_program, section_b, subject, time(10, 0), time(12, 0)),
        _DummySchedule(99, faculty_other, section_other, subject, time(8, 0), time(10, 0)),
    ]

    captured = {}

    def _fake_export(program_obj, faculty_schedule_data, current_settings, _user):
        captured['program'] = program_obj
        captured['rows'] = faculty_schedule_data
        captured['settings'] = current_settings
        return io.BytesIO(b'test-file'), 'BSCS_Faculty_Lineup.xlsx'

    monkeypatch.setattr(faculty_routes.db, 'joinedload', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(faculty_routes, 'current_user', _DummyUser(program_ids=None))
    monkeypatch.setattr(faculty_routes, 'AcademicSettings', type('SettingsModel', (), {'query': _SettingsQuery(settings)}))
    monkeypatch.setattr(faculty_routes, 'Program', type('ProgramModel', (), {'query': _ProgramQuery({1: program}), 'department': object()}))
    monkeypatch.setattr('app.models.section.Section', type('SectionModel', (), {'query': _SectionQuery({1: [section_a, section_b]})}))
    monkeypatch.setattr(faculty_routes, 'Schedule', _DummySchedule)
    monkeypatch.setattr(_DummySchedule, 'query', _ScheduleQuery(schedules), raising=False)
    monkeypatch.setattr(faculty_routes, 'Faculty', _DummyFaculty)
    monkeypatch.setattr(_DummyFaculty, 'query', _FacultyQuery([faculty_program, faculty_other]), raising=False)
    monkeypatch.setattr(export_service, 'generate_faculty_lineup_excel', _fake_export)

    with app.test_request_context('/faculty/export/lineup?program_id=1'):
        response = _unwrap(faculty_routes.export_faculty_lineup)()

    assert response.status_code == 200
    assert captured['program'].id == 1
    assert captured['settings'].academic_year == '2025-2026'
    assert len(captured['rows']) == 1
    assert captured['rows'][0]['faculty'].id == 1

    section_names = [row['section_name'] for row in captured['rows'][0]['rows']]
    assert 'BSCS-1A' in section_names
    assert 'BSCS-1B' in section_names
    assert 'BSED-1A' not in section_names