from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from flask import Flask

from app.routes import admin_tools as admin_tools_routes
import app.models.settings as settings_models
import app.utils.activity_logger as activity_logger


def _unwrap_route(route_func):
    current = route_func
    while hasattr(current, '__wrapped__'):
        current = current.__wrapped__
    return current


def _response_and_status(result):
    if isinstance(result, tuple):
        response, status = result
        return response, status
    return result, result.status_code


class _ComparableField:
    def __lt__(self, _other):
        return True


class _CountResult:
    def __init__(self, *, count_value=0, first_value=None, delete_value=None):
        self._count_value = count_value
        self._first_value = first_value
        self._delete_value = count_value if delete_value is None else delete_value

    def count(self):
        return self._count_value

    def first(self):
        return self._first_value

    def delete(self):
        return self._delete_value


class _CountQuery:
    def __init__(self, *, total_count=0, filter_counts=None, filter_count=None, first_value=None, delete_count=None):
        self._total_count = total_count
        self._filter_counts = filter_counts or {}
        self._filter_count = filter_count
        self._first_value = first_value
        self._delete_count = delete_count

    def count(self):
        return self._total_count

    def filter_by(self, **kwargs):
        key = tuple(sorted(kwargs.items()))
        count_value = self._filter_counts.get(key, self._total_count)
        delete_value = count_value if self._delete_count is None else self._delete_count
        return _CountResult(count_value=count_value, first_value=self._first_value, delete_value=delete_value)

    def filter(self, *_args, **_kwargs):
        count_value = self._total_count if self._filter_count is None else self._filter_count
        delete_value = count_value if self._delete_count is None else self._delete_count
        return _CountResult(count_value=count_value, first_value=self._first_value, delete_value=delete_value)

    def first(self):
        return self._first_value

    def delete(self):
        return self._total_count if self._delete_count is None else self._delete_count


def _make_model(*, total_count=0, filter_counts=None, filter_count=None, first_value=None, delete_count=None, with_created_at=False):
    attrs = {
        'query': _CountQuery(
            total_count=total_count,
            filter_counts=filter_counts,
            filter_count=filter_count,
            first_value=first_value,
            delete_count=delete_count,
        )
    }
    if with_created_at:
        attrs['created_at'] = _ComparableField()
    return type('ModelStub', (), attrs)


def _patch_active_settings(monkeypatch, settings_record):
    settings_stub = type('AcademicSettingsStub', (), {'query': _CountQuery(first_value=settings_record)})
    monkeypatch.setattr(settings_models, 'AcademicSettings', settings_stub)


@pytest.fixture()
def app_context():
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    with app.app_context():
        yield app


def test_api_database_cleanup_dry_run_contract(monkeypatch, app_context):
    monkeypatch.setattr(
        admin_tools_routes,
        'UserActivityLog',
        _make_model(total_count=12, filter_count=7, with_created_at=True),
    )

    route = _unwrap_route(admin_tools_routes.api_database_cleanup)
    with app_context.test_request_context(
        '/admin/api/database/cleanup/old_logs',
        method='POST',
        json={'days': 45, 'dry_run': True},
    ):
        result = route('old_logs')

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 200
    assert payload['success'] is True
    assert payload['dry_run'] is True
    assert payload['action'] == 'cleanup_old_logs'
    assert payload['days'] == 45
    assert payload['would_delete'] == 7
    assert payload['required_phrase'] == admin_tools_routes.DB_ACTION_CONFIRM_PHRASES['cleanup_old_logs']


def test_api_database_cleanup_rejects_phrase_mismatch(monkeypatch, app_context):
    monkeypatch.setattr(
        admin_tools_routes,
        'UserActivityLog',
        _make_model(total_count=8, filter_count=3, with_created_at=True),
    )

    route = _unwrap_route(admin_tools_routes.api_database_cleanup)
    with app_context.test_request_context(
        '/admin/api/database/cleanup/old_logs',
        method='POST',
        json={'days': 30, 'dry_run': False, 'confirm_phrase': 'WRONG PHRASE'},
    ):
        result = route('old_logs')

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 400
    assert payload['success'] is False
    assert payload['required_phrase'] == admin_tools_routes.DB_ACTION_CONFIRM_PHRASES['cleanup_old_logs']


def test_api_database_cleanup_executes_with_normalized_phrase(monkeypatch, app_context):
    monkeypatch.setattr(
        admin_tools_routes,
        'UserActivityLog',
        _make_model(total_count=8, filter_count=5, delete_count=5, with_created_at=True),
    )

    commit_called = {'value': False}
    logged_actions = []
    monkeypatch.setattr(admin_tools_routes.db.session, 'commit', lambda: commit_called.__setitem__('value', True))
    monkeypatch.setattr(admin_tools_routes.db.session, 'rollback', lambda: None)
    monkeypatch.setattr(activity_logger, 'log_activity', lambda *args, **kwargs: logged_actions.append((args, kwargs)))

    route = _unwrap_route(admin_tools_routes.api_database_cleanup)
    with app_context.test_request_context(
        '/admin/api/database/cleanup/old_logs',
        method='POST',
        json={'days': 30, 'confirm_phrase': 'cleanup   old logs'},
    ):
        result = route('old_logs')

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 200
    assert payload['success'] is True
    assert payload['deleted'] == 5
    assert payload['required_phrase'] == admin_tools_routes.DB_ACTION_CONFIRM_PHRASES['cleanup_old_logs']
    assert commit_called['value'] is True
    assert logged_actions
    assert logged_actions[0][0][0] == 'cleanup_old_logs'


def test_api_database_truncate_dry_run_and_invalid_table_guard(monkeypatch, app_context):
    monkeypatch.setattr(admin_tools_routes, 'Archive', _make_model(total_count=4, delete_count=4))
    monkeypatch.setattr(admin_tools_routes, 'UserActivityLog', _make_model(total_count=9, with_created_at=True))
    monkeypatch.setattr(admin_tools_routes, 'LoginHistory', _make_model(total_count=6))

    route = _unwrap_route(admin_tools_routes.api_database_truncate)

    with app_context.test_request_context(
        '/admin/api/database/truncate/archives',
        method='POST',
        json={'dry_run': True},
    ):
        dry_run_result = route('archives')

    dry_run_response, dry_run_status = _response_and_status(dry_run_result)
    dry_run_payload = dry_run_response.get_json()

    assert dry_run_status == 200
    assert dry_run_payload['success'] is True
    assert dry_run_payload['dry_run'] is True
    assert dry_run_payload['action'] == 'truncate_archives'
    assert dry_run_payload['would_delete'] == 4
    assert dry_run_payload['required_phrase'] == admin_tools_routes.DB_ACTION_CONFIRM_PHRASES['truncate_archives']

    with app_context.test_request_context(
        '/admin/api/database/truncate/not_allowed',
        method='POST',
        json={},
    ):
        invalid_result = route('not_allowed')

    invalid_response, invalid_status = _response_and_status(invalid_result)
    invalid_payload = invalid_response.get_json()

    assert invalid_status == 400
    assert invalid_payload['success'] is False


def test_api_database_truncate_requires_confirmation_phrase(monkeypatch, app_context):
    monkeypatch.setattr(admin_tools_routes, 'Archive', _make_model(total_count=1, delete_count=1))
    monkeypatch.setattr(admin_tools_routes, 'UserActivityLog', _make_model(total_count=2, with_created_at=True))
    monkeypatch.setattr(admin_tools_routes, 'LoginHistory', _make_model(total_count=3, delete_count=3))

    route = _unwrap_route(admin_tools_routes.api_database_truncate)
    with app_context.test_request_context(
        '/admin/api/database/truncate/login_history',
        method='POST',
        json={'confirm_phrase': 'TRUNCATE HISTORY'},
    ):
        result = route('login_history')

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 400
    assert payload['success'] is False
    assert payload['required_phrase'] == admin_tools_routes.DB_ACTION_CONFIRM_PHRASES['truncate_login_history']


def test_api_database_reset_schedules_dry_run_contract(monkeypatch, app_context):
    active_settings = SimpleNamespace(
        semester='1st Semester',
        academic_year='2025-2026',
        exam_period='Midterm',
    )
    _patch_active_settings(monkeypatch, active_settings)

    term_key = tuple(sorted({'semester': active_settings.semester, 'academic_year': active_settings.academic_year}.items()))
    monkeypatch.setattr(admin_tools_routes, 'Schedule', _make_model(total_count=11, filter_counts={term_key: 3}, delete_count=3))
    monkeypatch.setattr(admin_tools_routes, 'ExamSchedule', _make_model(total_count=6, filter_counts={term_key: 2}, delete_count=2))

    route = _unwrap_route(admin_tools_routes.api_database_reset_schedules)
    with app_context.test_request_context(
        '/admin/api/database/reset-schedules',
        method='POST',
        json={'type': 'all', 'dry_run': True},
    ):
        result = route()

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 200
    assert payload['success'] is True
    assert payload['dry_run'] is True
    assert payload['action'] == 'reset_all_schedules'
    assert payload['would_delete_class'] == 3
    assert payload['would_delete_exam'] == 2
    assert payload['total_would_delete'] == 5
    assert payload['required_phrase'] == admin_tools_routes.DB_ACTION_CONFIRM_PHRASES['reset_all_schedules']
    assert payload['term']['semester'] == active_settings.semester
    assert payload['term']['academic_year'] == active_settings.academic_year


def test_api_database_reset_schedules_rejects_invalid_type(monkeypatch, app_context):
    active_settings = SimpleNamespace(
        semester='1st Semester',
        academic_year='2025-2026',
        exam_period='Final',
    )
    _patch_active_settings(monkeypatch, active_settings)

    route = _unwrap_route(admin_tools_routes.api_database_reset_schedules)
    with app_context.test_request_context(
        '/admin/api/database/reset-schedules',
        method='POST',
        json={'type': 'invalid-type'},
    ):
        result = route()

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 400
    assert payload['success'] is False
    assert 'Invalid reset type' in payload['error']


def test_api_database_reset_schedules_executes_with_valid_phrase(monkeypatch, app_context):
    active_settings = SimpleNamespace(
        semester='2nd Semester',
        academic_year='2025-2026',
        exam_period='Final',
    )
    _patch_active_settings(monkeypatch, active_settings)

    term_key = tuple(sorted({'semester': active_settings.semester, 'academic_year': active_settings.academic_year}.items()))
    monkeypatch.setattr(admin_tools_routes, 'Schedule', _make_model(total_count=9, filter_counts={term_key: 4}, delete_count=4))
    monkeypatch.setattr(admin_tools_routes, 'ExamSchedule', _make_model(total_count=7, filter_counts={term_key: 3}, delete_count=3))

    commit_called = {'value': False}
    logged_actions = []
    monkeypatch.setattr(admin_tools_routes.db.session, 'commit', lambda: commit_called.__setitem__('value', True))
    monkeypatch.setattr(admin_tools_routes.db.session, 'rollback', lambda: None)
    monkeypatch.setattr(activity_logger, 'log_activity', lambda *args, **kwargs: logged_actions.append((args, kwargs)))

    route = _unwrap_route(admin_tools_routes.api_database_reset_schedules)
    with app_context.test_request_context(
        '/admin/api/database/reset-schedules',
        method='POST',
        json={'type': 'class', 'confirm_phrase': '  reset class schedules '},
    ):
        result = route()

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 200
    assert payload['success'] is True
    assert payload['action'] == 'reset_class_schedules'
    assert payload['deleted_class'] == 4
    assert payload['deleted_exam'] == 0
    assert payload['total_deleted'] == 4
    assert payload['required_phrase'] == admin_tools_routes.DB_ACTION_CONFIRM_PHRASES['reset_class_schedules']
    assert commit_called['value'] is True
    assert logged_actions
    assert logged_actions[0][0][0] == 'reset_class_schedules'


def test_api_database_stats_exposes_actions_and_backup_metadata(monkeypatch, app_context):
    archived_key = (('is_archived', True),)
    active_settings = SimpleNamespace(
        semester='1st Semester',
        academic_year='2025-2026',
        exam_period='Midterm',
        exam_period_start=None,
        exam_period_end=None,
    )
    term_key = tuple(sorted({'semester': active_settings.semester, 'academic_year': active_settings.academic_year}.items()))

    _patch_active_settings(monkeypatch, active_settings)

    monkeypatch.setattr(admin_tools_routes, 'User', _make_model(total_count=21, filter_counts={archived_key: 2}))
    monkeypatch.setattr(admin_tools_routes, 'Program', _make_model(total_count=6, filter_counts={archived_key: 1}))
    monkeypatch.setattr(admin_tools_routes, 'Curriculum', _make_model(total_count=8, filter_counts={archived_key: 1}))
    monkeypatch.setattr(admin_tools_routes, 'Faculty', _make_model(total_count=14, filter_counts={archived_key: 3}))
    monkeypatch.setattr(admin_tools_routes, 'Building', _make_model(total_count=4, filter_counts={archived_key: 1}))
    monkeypatch.setattr(admin_tools_routes, 'Room', _make_model(total_count=18))
    monkeypatch.setattr(admin_tools_routes, 'Section', _make_model(total_count=17))
    monkeypatch.setattr(admin_tools_routes, 'Schedule', _make_model(total_count=30, filter_counts={term_key: 6}))
    monkeypatch.setattr(admin_tools_routes, 'ExamSchedule', _make_model(total_count=12, filter_counts={term_key: 4}))
    monkeypatch.setattr(admin_tools_routes, 'Archive', _make_model(total_count=11))
    monkeypatch.setattr(admin_tools_routes, 'UserActivityLog', _make_model(total_count=41, filter_count=9, with_created_at=True))
    monkeypatch.setattr(admin_tools_routes, 'LoginHistory', _make_model(total_count=13))
    monkeypatch.setattr(admin_tools_routes, 'SystemConfig', _make_model(total_count=5))
    monkeypatch.setattr(admin_tools_routes, 'FacultySubjectAssignment', _make_model(total_count=22))

    recent_backup_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    monkeypatch.setattr(admin_tools_routes.DatabaseBackupService, 'list_backups', lambda: [{'created_at': recent_backup_iso}])

    route = _unwrap_route(admin_tools_routes.api_database_stats)
    with app_context.test_request_context('/admin/api/database/stats?days=60'):
        result = route()

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 200
    assert payload['success'] is True
    assert payload['backup']['latest_backup_at'] == recent_backup_iso
    assert payload['backup']['has_recent_backup'] is True
    assert payload['current_semester']['academic_year'] == active_settings.academic_year
    assert payload['actions']['cleanup_old_logs']['count'] == 9
    assert payload['actions']['reset_class_schedules']['count'] == 6
    assert payload['actions']['reset_exam_schedules']['count'] == 4
    assert payload['actions']['reset_all_schedules']['count'] == 10
    assert payload['actions']['truncate_archives']['count'] == 11
    assert payload['actions']['truncate_activity_logs']['count'] == 41
    assert payload['actions']['truncate_login_history']['count'] == 13

    for action_key, phrase in admin_tools_routes.DB_ACTION_CONFIRM_PHRASES.items():
        assert payload['actions'][action_key]['required_phrase'] == phrase
