import inspect
from datetime import datetime
from types import SimpleNamespace

from flask import Flask

from app.models.activity_log import UserActivityLog
from app.routes import reports as reports_routes


def test_activity_log_to_dict_includes_created_at_iso_and_legacy_created_at():
    log = UserActivityLog(
        user_id=1,
        action='created',
        entity_type='schedule',
        entity_id=99,
        entity_name='Test Schedule',
        details='sample',
        ip_address='127.0.0.1',
    )
    log.created_at = datetime(2026, 3, 28, 14, 0, 0)

    payload = log.to_dict()

    assert payload['created_at'] == '2026-03-28 14:00:00'
    assert payload['created_at_iso'] == '2026-03-28T14:00:00Z'


def _unwrap(func):
    return inspect.unwrap(func)


class _DummyColumn:
    def __init__(self, name):
        self.name = name

    def desc(self):
        return self

    def isnot(self, _value):
        return self

    def __ne__(self, _other):
        return self


class _DummyUserRecord:
    def __init__(self, user_id, full_name, role):
        self.id = user_id
        self.full_name = full_name
        self.role = role


class _DummyActivityLogRecord:
    def __init__(self, user):
        self.id = 77
        self.user_id = user.id
        self.user = user
        self.action = 'login'
        self.entity_type = 'auth'
        self.entity_id = 77
        self.entity_name = 'Session'
        self.details = 'Signed in'
        self.ip_address = '127.0.0.1'
        self.user_agent = 'pytest-agent'
        self.created_at = datetime(2026, 4, 9, 8, 30, 0)


class _DummyLogQuery:
    def __init__(self, rows):
        self._rows = rows
        self._offset = 0
        self._limit = len(rows)

    def options(self, *_args, **_kwargs):
        return self

    def count(self):
        return len(self._rows)

    def order_by(self, *_args, **_kwargs):
        return self

    def offset(self, value):
        self._offset = value
        return self

    def limit(self, value):
        self._limit = value
        return self

    def all(self):
        end = self._offset + self._limit
        return self._rows[self._offset:end]


class _DummyTupleQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def distinct(self):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def group_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


def test_activity_report_route_renders_without_preloaded_filter_context(monkeypatch):
    app = Flask(__name__)

    monkeypatch.setattr(
        reports_routes,
        'render_template',
        lambda template, **ctx: {'template': template, 'ctx': ctx},
    )

    route_func = _unwrap(reports_routes.activity_report)

    with app.test_request_context('/reports/activity'):
        response = route_func()

    assert response['template'] == 'reports/activity.html'
    assert response['ctx'] == {}


def test_user_activity_api_includes_filters_for_client_hydration(monkeypatch):
    app = Flask(__name__)

    dummy_user = _DummyUserRecord(user_id=1, full_name='Admin User', role='admin')
    dummy_logs = [_DummyActivityLogRecord(dummy_user)]

    class _DummyUserQuery:
        def filter_by(self, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return [dummy_user]

    class _DummyUserModel:
        query = _DummyUserQuery()
        full_name = _DummyColumn('full_name')

    class _DummyUserActivityLogModel:
        query = _DummyLogQuery(dummy_logs)
        user = object()
        action = _DummyColumn('action')
        entity_type = _DummyColumn('entity_type')
        id = _DummyColumn('id')
        created_at = _DummyColumn('created_at')

    def _query_stub(*columns):
        if len(columns) == 1 and columns[0] is _DummyUserActivityLogModel.action:
            return _DummyTupleQuery([('login',), ('edited',)])
        if len(columns) == 1 and columns[0] is _DummyUserActivityLogModel.entity_type:
            return _DummyTupleQuery([('auth',), ('schedule',)])
        return _DummyTupleQuery([('login', 1)])

    monkeypatch.setattr(reports_routes, 'joinedload', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(reports_routes, 'UserActivityLog', _DummyUserActivityLogModel)
    monkeypatch.setattr(reports_routes, 'User', _DummyUserModel)
    monkeypatch.setattr(reports_routes, '_parse_user_activity_filters', lambda _args: {})
    monkeypatch.setattr(reports_routes, '_apply_user_activity_filters', lambda query, _filters: query)
    monkeypatch.setattr(
        reports_routes,
        'db',
        SimpleNamespace(session=SimpleNamespace(query=_query_stub)),
    )

    route_func = _unwrap(reports_routes.get_user_activity)

    with app.test_request_context('/reports/api/user-activity?page=1&per_page=30'):
        response = route_func()

    assert not isinstance(response, tuple)
    data = response.get_json()
    assert response.status_code == 200
    assert data['success'] is True
    assert data['logs'] and data['logs'][0]['created_at_iso'].endswith('Z')
    assert data['pagination']['page'] == 1
    assert data['pagination']['has_next'] is False
    assert 'filters' in data
    assert data['filters']['users'][0]['name'] == 'Admin User'
    assert data['filters']['actions'] == ['login', 'edited']
    assert data['filters']['entities'] == ['auth', 'schedule']


def test_user_activity_api_still_returns_filters_when_logs_empty(monkeypatch):
    app = Flask(__name__)

    dummy_user = _DummyUserRecord(user_id=1, full_name='Admin User', role='admin')

    class _DummyUserQuery:
        def filter_by(self, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return [dummy_user]

    class _DummyUserModel:
        query = _DummyUserQuery()
        full_name = _DummyColumn('full_name')

    class _DummyUserActivityLogModel:
        query = _DummyLogQuery([])
        user = object()
        action = _DummyColumn('action')
        entity_type = _DummyColumn('entity_type')
        id = _DummyColumn('id')
        created_at = _DummyColumn('created_at')

    def _query_stub(*columns):
        if len(columns) == 1 and columns[0] is _DummyUserActivityLogModel.action:
            return _DummyTupleQuery([('login',), ('edited',)])
        if len(columns) == 1 and columns[0] is _DummyUserActivityLogModel.entity_type:
            return _DummyTupleQuery([('auth',), ('schedule',)])
        return _DummyTupleQuery([])

    monkeypatch.setattr(reports_routes, 'joinedload', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(reports_routes, 'UserActivityLog', _DummyUserActivityLogModel)
    monkeypatch.setattr(reports_routes, 'User', _DummyUserModel)
    monkeypatch.setattr(reports_routes, '_parse_user_activity_filters', lambda _args: {})
    monkeypatch.setattr(reports_routes, '_apply_user_activity_filters', lambda query, _filters: query)
    monkeypatch.setattr(
        reports_routes,
        'db',
        SimpleNamespace(session=SimpleNamespace(query=_query_stub)),
    )

    route_func = _unwrap(reports_routes.get_user_activity)

    with app.test_request_context('/reports/api/user-activity?page=1&per_page=30'):
        response = route_func()

    assert not isinstance(response, tuple)
    data = response.get_json()
    assert response.status_code == 200
    assert data['success'] is True
    assert data['logs'] == []
    assert data['total'] == 0
    assert data['total_pages'] == 0
    assert data['pagination']['has_next'] is False
    assert data['filters']['users'][0]['name'] == 'Admin User'
    assert data['filters']['actions'] == ['login', 'edited']
    assert data['filters']['entities'] == ['auth', 'schedule']
