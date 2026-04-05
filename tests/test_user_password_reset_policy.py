from types import SimpleNamespace

from flask import Flask

from app.models.user import User
from app.routes import user as user_routes


class _SessionStub:
    def __init__(self):
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1


class _QueryStub:
    def __init__(self, user):
        self._user = user

    def get_or_404(self, user_id):
        assert user_id == self._user.id
        return self._user

    def filter_by(self, **_kwargs):
        return SimpleNamespace(first=lambda: None)


class _UserStub:
    def __init__(self):
        self.id = 2
        self.username = 'dean.user'
        self.email = 'dean@example.com'
        self.full_name = 'Dean User'
        self.role = 'dean'
        self.is_active = True
        self.is_archived = False
        self.needs_password_change = False
        self.password_set_to = None

    def set_password(self, password):
        self.password_set_to = password


def _invoke_user_route(route_func, app, method, path, user_id, payload):
    with app.test_request_context(path, method=method, json=payload):
        result = route_func(user_id)

    if isinstance(result, tuple):
        response, status_code = result
    else:
        response, status_code = result, result.status_code

    return response.get_json(), status_code


def test_username_format_validator_accepts_and_rejects_expected_values():
    is_valid, message, normalized = User.validate_username_format(' dean.user_1 ')
    assert is_valid is True
    assert message is None
    assert normalized == 'dean.user_1'

    is_valid, message, normalized = User.validate_username_format('bad username')
    assert is_valid is False
    assert '3-30 characters' in message
    assert normalized == 'bad username'


def test_split_full_name_extracts_first_middle_initial_and_last_name():
    parts = User.split_full_name('  Jane   Q.   Doe  ')

    assert parts['first_name'] == 'Jane'
    assert parts['middle_initial'] == 'Q'
    assert parts['last_name'] == 'Doe'
    assert parts['full_name'] == 'Jane Q. Doe'


def test_split_full_name_extracts_uppercase_multi_letter_middle_initial():
    parts = User.split_full_name('Jane MA Doe')

    assert parts['first_name'] == 'Jane'
    assert parts['middle_initial'] == 'MA'
    assert parts['last_name'] == 'Doe'


def test_split_full_name_keeps_last_name_particles_when_not_uppercase_middle_token():
    parts = User.split_full_name('Juan Dela Cruz')

    assert parts['first_name'] == 'Juan'
    assert parts['middle_initial'] == ''
    assert parts['last_name'] == 'Dela Cruz'


def test_resolve_full_name_input_normalizes_split_name_payload():
    is_valid, message, normalized = User.resolve_full_name_input(
        first_name='  Jane  ',
        middle_initial='ma.',
        last_name='  Doe  ',
    )

    assert is_valid is True
    assert message is None
    assert normalized['first_name'] == 'Jane'
    assert normalized['middle_initial'] == 'MA'
    assert normalized['last_name'] == 'Doe'
    assert normalized['full_name'] == 'Jane MA Doe'


def test_resolve_full_name_input_rejects_invalid_middle_initial():
    is_valid, message, normalized = User.resolve_full_name_input(
        first_name='Jane',
        middle_initial='12',
        last_name='Doe',
    )

    assert is_valid is False
    assert 'Middle initial must be 1 to 5 letters' in message
    assert normalized is None


def test_update_user_rejects_direct_password_changes(monkeypatch):
    app = Flask(__name__)
    user = _UserStub()
    session_stub = _SessionStub()
    user_model_stub = SimpleNamespace(
        query=_QueryStub(user),
        normalize_username=User.normalize_username,
        validate_username_format=User.validate_username_format,
    )

    monkeypatch.setattr(user_routes, 'User', user_model_stub)
    monkeypatch.setattr(user_routes.db, 'session', session_stub, raising=False)
    monkeypatch.setattr(
        user_routes,
        'current_user',
        SimpleNamespace(id=1, is_super_admin=True, username='admin.user'),
    )

    route_func = user_routes.update_user.__wrapped__.__wrapped__
    payload, status_code = _invoke_user_route(
        route_func,
        app,
        'PUT',
        '/users/api/users/2',
        user.id,
        {'password': 'ValidPass123'},
    )

    assert status_code == 400
    assert payload['success'] is False
    assert 'Reset Password' in payload['message']


def test_reset_user_password_sets_temporary_password_and_force_change(monkeypatch):
    app = Flask(__name__)
    user = _UserStub()
    session_stub = _SessionStub()
    user_model_stub = SimpleNamespace(
        query=_QueryStub(user),
        normalize_username=User.normalize_username,
        validate_username_format=User.validate_username_format,
    )

    monkeypatch.setattr(user_routes, 'User', user_model_stub)
    monkeypatch.setattr(user_routes.db, 'session', session_stub, raising=False)
    monkeypatch.setattr(user_routes, '_generate_temporary_password', lambda: 'TempPass123')
    monkeypatch.setattr(user_routes, 'log_edit', lambda *args, **kwargs: None)
    monkeypatch.setattr(
        user_routes,
        'current_user',
        SimpleNamespace(id=1, is_super_admin=True, username='admin.user'),
    )

    route_func = user_routes.reset_user_password.__wrapped__.__wrapped__
    payload, status_code = _invoke_user_route(
        route_func,
        app,
        'POST',
        '/users/api/users/2/reset-password',
        user.id,
        {},
    )

    assert status_code == 200
    assert payload['success'] is True
    assert payload['credentials']['username'] == user.username
    assert payload['credentials']['temporary_password'] == 'TempPass123'
    assert user.password_set_to == 'TempPass123'
    assert user.needs_password_change is True
    assert session_stub.commit_calls == 1
