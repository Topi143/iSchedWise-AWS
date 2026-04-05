from pathlib import Path
import sys
from types import SimpleNamespace

from flask import Flask
from sqlalchemy.exc import IntegrityError

# Support direct execution: `py tests/test_user_quick_generate_retry.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.routes import user as user_routes


class _QueryResultStub:
    def __init__(self, usernames):
        self._usernames = usernames

    def all(self):
        return [(username,) for username in self._usernames]


class _SessionStub:
    def __init__(self, usernames, collision_count):
        self._usernames = usernames
        self._collision_count = collision_count
        self._flush_calls = 0
        self.rollback_calls = 0
        self.last_added_user = None

    def query(self, _column):
        return _QueryResultStub(self._usernames)

    def add(self, user):
        self.last_added_user = user

    def flush(self):
        self._flush_calls += 1
        if self._flush_calls <= self._collision_count:
            raise IntegrityError(
                statement=None,
                params=None,
                orig=Exception("Duplicate entry 'user003@ischedwise.local' for key 'users.email'"),
            )
        self.last_added_user.id = 100 + self._flush_calls

    def commit(self):
        return None

    def rollback(self):
        self.rollback_calls += 1


class _FakeUser:
    username = 'username_column_marker'

    def __init__(self, username, email, full_name, role, is_active):
        self.id = None
        self.username = username
        self.email = email
        self.full_name = full_name
        self.role = role
        self.is_active = is_active
        self.programs = []

    def set_password(self, _password):
        return None


def _invoke_quick_generate_route(app):
    route_func = user_routes.quick_generate_user.__wrapped__.__wrapped__
    with app.test_request_context(
        '/users/api/users/quick-generate',
        method='POST',
        json={'role': 'dean', 'department_ids': []},
    ):
        result = route_func()
    if isinstance(result, tuple):
        response, status_code = result
    else:
        response, status_code = result, result.status_code
    return response.get_json(), status_code


def test_quick_generate_retries_and_succeeds(monkeypatch):
    app = Flask(__name__)
    session_stub = _SessionStub(usernames=['user001', 'user002'], collision_count=1)

    monkeypatch.setattr(user_routes.db, 'session', session_stub, raising=False)
    monkeypatch.setattr(user_routes, 'User', _FakeUser)
    monkeypatch.setattr(user_routes, 'current_user', SimpleNamespace(is_super_admin=True))
    monkeypatch.setattr(user_routes, 'log_create', lambda *args, **kwargs: None)
    monkeypatch.setattr(user_routes, '_assign_user_programs_from_departments', lambda *args, **kwargs: None)

    payload, status_code = _invoke_quick_generate_route(app)

    assert status_code == 200
    assert payload['success'] is True
    assert payload['credentials']['username'] == 'user004'
    assert payload['credentials']['email'] == 'user004@ischedwise.local'
    assert session_stub.rollback_calls == 1


def test_quick_generate_returns_error_after_exhausting_retries(monkeypatch):
    app = Flask(__name__)
    session_stub = _SessionStub(
        usernames=['user001', 'user002'],
        collision_count=user_routes._QUICK_USER_RETRY_LIMIT,
    )

    monkeypatch.setattr(user_routes.db, 'session', session_stub, raising=False)
    monkeypatch.setattr(user_routes, 'User', _FakeUser)
    monkeypatch.setattr(user_routes, 'current_user', SimpleNamespace(is_super_admin=True))
    monkeypatch.setattr(user_routes, 'log_create', lambda *args, **kwargs: None)
    monkeypatch.setattr(user_routes, '_assign_user_programs_from_departments', lambda *args, **kwargs: None)

    payload, status_code = _invoke_quick_generate_route(app)

    assert status_code == 500
    assert payload['success'] is False
    assert payload['message'] == 'Unable to generate a unique user account. Please try again.'
    assert session_stub.rollback_calls == user_routes._QUICK_USER_RETRY_LIMIT
