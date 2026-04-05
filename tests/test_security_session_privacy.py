from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from types import SimpleNamespace

import flask_mail
from flask import Flask, session
from werkzeug.security import generate_password_hash

from app import _is_password_change_enforcement_exempt
from app.models.login_history import LoginHistory
from app.models.user import User
from app.routes import admin_tools as admin_tools_routes
from app.routes import auth as auth_routes
from app.routes import profile as profile_routes
from app.utils.security_email_templates import (
    build_branded_mail_sender,
    build_password_reset_email_payload,
    build_profile_otp_email_payload,
    build_sign_in_otp_email_payload,
    build_smtp_test_email_payload,
)


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_login_history_admin_dict_redacts_account_identifiers():
    entry = LoginHistory()
    entry.id = 10
    entry.user_id = 99
    entry.login_at = datetime(2026, 3, 22, 10, 0, 0)
    entry.logout_at = None
    entry.ip_address = '127.0.0.1'
    entry.user_agent = 'ExampleAgent/1.0'
    entry.session_id = 'secret-session-token'
    entry.is_active = True
    entry.user = User(
        username='admin_user',
        email='admin@example.com',
        password_hash='hash',
        role='admin',
        full_name='Admin User',
    )

    payload = entry.to_admin_dict()

    assert payload['id'] == 10
    assert payload['user_role'] == 'admin'
    assert payload['is_active'] is True
    assert 'user_id' not in payload
    assert 'user_name' not in payload
    assert 'ip_address' not in payload
    assert 'user_agent' not in payload
    assert 'session_id' not in payload


def test_password_change_enforcement_exemptions():
    assert _is_password_change_enforcement_exempt('static') is True
    assert _is_password_change_enforcement_exempt('auth.login') is True
    assert _is_password_change_enforcement_exempt('auth.verify_two_factor') is True
    assert _is_password_change_enforcement_exempt('profile.index') is True
    assert _is_password_change_enforcement_exempt('profile.change_password') is True
    assert _is_password_change_enforcement_exempt('main.dashboard') is False
    assert _is_password_change_enforcement_exempt(None) is False


def test_user_two_factor_enable_disable_helpers():
    user = User(
        username='security_user',
        email='security@example.com',
        password_hash='hash',
        role='admin',
        full_name='Security User',
    )

    user.enable_two_factor()

    assert user.two_factor_enabled is True
    assert user.two_factor_secret is None
    assert user.two_factor_enabled_at is not None

    user.disable_two_factor()

    assert user.two_factor_enabled is False
    assert user.two_factor_secret is None
    assert user.two_factor_enabled_at is None


def test_user_email_otp_hash_verification():
    code = User.generate_email_otp(length=6)
    salt = 'unit-test-salt'
    code_hash = User.hash_email_otp(code, salt)

    assert len(code) == 6
    assert code.isdigit()
    assert code_hash

    invalid_code = str((int(code) + 1) % 1000000).zfill(6)

    assert User.verify_email_otp_hash(code, code_hash, salt, length=6) is True
    assert User.verify_email_otp_hash(invalid_code, code_hash, salt, length=6) is False
    assert User.verify_email_otp_hash(code[:5], code_hash, salt, length=6) is False


def test_change_password_clears_force_reset_flag(monkeypatch):
    app = Flask(__name__)

    fake_user = SimpleNamespace(
        id=5,
        username='dean_user',
        password_hash=generate_password_hash('OldPass123!'),
        needs_password_change=True,
    )

    commit_called = {'value': False}

    monkeypatch.setattr(profile_routes, 'current_user', fake_user)
    monkeypatch.setattr(profile_routes, 'log_password_change', lambda *args, **kwargs: None)
    monkeypatch.setattr(profile_routes.db.session, 'commit', lambda: commit_called.__setitem__('value', True))
    monkeypatch.setattr(profile_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context(
        '/account/change-password',
        method='POST',
        json={
            'current_password': 'OldPass123!',
            'new_password': 'NewPass123!',
            'confirm_password': 'NewPass123!',
        },
    ):
        response = profile_routes.change_password.__wrapped__()

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['message'] == 'Password changed successfully. You can now continue using the system.'
    assert payload['force_password_reset_required'] is False
    assert commit_called['value'] is True
    assert fake_user.needs_password_change is False


def test_verify_current_password_requires_value(monkeypatch):
    app = Flask(__name__)

    fake_user = SimpleNamespace(
        password_hash=generate_password_hash('OldPass123!')
    )
    monkeypatch.setattr(profile_routes, 'current_user', fake_user)

    with app.test_request_context(
        '/account/verify-current-password',
        method='POST',
        json={'current_password': ''},
    ):
        result = profile_routes.verify_current_password.__wrapped__()

    if isinstance(result, tuple):
        response, status_code = result
    else:
        response = result
        status_code = response.status_code

    assert status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert payload['valid'] is False
    assert payload['message'] == 'Current password is required'


def test_verify_current_password_reports_validity(monkeypatch):
    app = Flask(__name__)

    fake_user = SimpleNamespace(
        password_hash=generate_password_hash('OldPass123!')
    )
    monkeypatch.setattr(profile_routes, 'current_user', fake_user)

    with app.test_request_context(
        '/account/verify-current-password',
        method='POST',
        json={'current_password': 'OldPass123!'},
    ):
        ok_result = profile_routes.verify_current_password.__wrapped__()

    if isinstance(ok_result, tuple):
        ok_response, ok_status_code = ok_result
    else:
        ok_response = ok_result
        ok_status_code = ok_response.status_code

    assert ok_status_code == 200
    ok_payload = ok_response.get_json()
    assert ok_payload['success'] is True
    assert ok_payload['valid'] is True

    with app.test_request_context(
        '/account/verify-current-password',
        method='POST',
        json={'current_password': 'WrongPass123!'},
    ):
        bad_result = profile_routes.verify_current_password.__wrapped__()

    if isinstance(bad_result, tuple):
        bad_response, bad_status_code = bad_result
    else:
        bad_response = bad_result
        bad_status_code = bad_response.status_code

    assert bad_status_code == 400
    bad_payload = bad_response.get_json()
    assert bad_payload['success'] is False
    assert bad_payload['valid'] is False
    assert bad_payload['message'] == 'Current password is incorrect'


def test_verify_current_password_accepts_new_password_after_change(monkeypatch):
    app = Flask(__name__)

    fake_user = SimpleNamespace(
        id=7,
        username='dean_user',
        password_hash=generate_password_hash('OldPass123!'),
        needs_password_change=True,
    )

    monkeypatch.setattr(profile_routes, 'current_user', fake_user)
    monkeypatch.setattr(profile_routes, 'log_password_change', lambda *args, **kwargs: None)
    monkeypatch.setattr(profile_routes.db.session, 'commit', lambda: None)
    monkeypatch.setattr(profile_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context(
        '/account/change-password',
        method='POST',
        json={
            'current_password': 'OldPass123!',
            'new_password': 'NewPass123!',
            'confirm_password': 'NewPass123!',
        },
    ):
        change_response = profile_routes.change_password.__wrapped__()

    assert change_response.status_code == 200

    with app.test_request_context(
        '/account/verify-current-password',
        method='POST',
        json={'current_password': 'NewPass123!'},
    ):
        verify_result = profile_routes.verify_current_password.__wrapped__()

    if isinstance(verify_result, tuple):
        verify_response, verify_status_code = verify_result
    else:
        verify_response = verify_result
        verify_status_code = verify_response.status_code

    assert verify_status_code == 200
    verify_payload = verify_response.get_json()
    assert verify_payload['success'] is True
    assert verify_payload['valid'] is True


def test_profile_index_sets_forced_reset_context(monkeypatch):
    app = Flask(__name__)

    fake_user = SimpleNamespace(needs_password_change=True, two_factor_enabled=False, two_factor_secret=None)
    captured = {}

    def fake_render(template_name, **kwargs):
        captured['template_name'] = template_name
        captured['kwargs'] = kwargs
        return 'ok'

    monkeypatch.setattr(profile_routes, 'current_user', fake_user)
    monkeypatch.setattr(profile_routes, 'render_template', fake_render)

    with app.test_request_context('/account/', method='GET'):
        response = profile_routes.index.__wrapped__()

    assert response == 'ok'
    assert captured['template_name'] == 'profile.html'
    assert captured['kwargs']['force_password_reset_required'] is True
    assert captured['kwargs']['two_factor_enabled'] is False
    assert 'trusted_devices' not in captured['kwargs']
    assert captured['kwargs']['trusted_device_days'] == 1
    assert 'two_factor_recent_auth_minutes' not in captured['kwargs']


def test_profile_index_sets_non_forced_reset_context(monkeypatch):
    app = Flask(__name__)

    fake_user = SimpleNamespace(needs_password_change=False, two_factor_enabled=False, two_factor_secret=None)
    captured = {}

    def fake_render(template_name, **kwargs):
        captured['template_name'] = template_name
        captured['kwargs'] = kwargs
        return 'ok'

    monkeypatch.setattr(profile_routes, 'current_user', fake_user)
    monkeypatch.setattr(profile_routes, 'render_template', fake_render)

    with app.test_request_context('/account/', method='GET'):
        response = profile_routes.index.__wrapped__()

    assert response == 'ok'
    assert captured['template_name'] == 'profile.html'
    assert captured['kwargs']['force_password_reset_required'] is False
    assert captured['kwargs']['two_factor_enabled'] is False
    assert 'trusted_devices' not in captured['kwargs']
    assert captured['kwargs']['trusted_device_days'] == 1
    assert 'two_factor_recent_auth_minutes' not in captured['kwargs']


def test_enable_two_factor_succeeds_without_recent_auth_session(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-secret'

    fake_user = User(
        username='dean_user',
        email='dean@example.com',
        password_hash=generate_password_hash('OldPass123!'),
        role='dean',
        full_name='Dean User',
    )
    fake_user.id = 7
    fake_user.two_factor_enabled = False

    commit_called = {'value': False}

    monkeypatch.setattr(profile_routes, 'current_user', fake_user)
    monkeypatch.setattr(profile_routes.UserActivityLog, 'log_action', lambda **kwargs: None)
    monkeypatch.setattr(profile_routes.db.session, 'commit', lambda: commit_called.__setitem__('value', True))
    monkeypatch.setattr(profile_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context(
        '/account/two-factor/enable',
        method='POST',
        json={},
    ):
        result = profile_routes.enable_two_factor.__wrapped__()

    if isinstance(result, tuple):
        response, status_code = result
    else:
        response = result
        status_code = response.status_code

    payload = response.get_json()

    assert status_code == 200
    assert payload['success'] is True
    assert fake_user.two_factor_enabled is True
    assert commit_called['value'] is True


def test_enable_two_factor_succeeds_with_login_time_in_session(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-secret'

    fake_user = User(
        username='admin_user',
        email='admin@example.com',
        password_hash=generate_password_hash('OldPass123!'),
        role='admin',
        full_name='Admin User',
    )
    fake_user.id = 15
    fake_user.two_factor_enabled = False

    commit_called = {'value': False}

    monkeypatch.setattr(profile_routes, 'current_user', fake_user)
    monkeypatch.setattr(profile_routes.UserActivityLog, 'log_action', lambda **kwargs: None)
    monkeypatch.setattr(profile_routes.db.session, 'commit', lambda: commit_called.__setitem__('value', True))
    monkeypatch.setattr(profile_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context(
        '/account/two-factor/enable',
        method='POST',
        json={},
    ):
        session['_login_time'] = (_utcnow_naive() - timedelta(minutes=2)).isoformat()
        result = profile_routes.enable_two_factor.__wrapped__()

    if isinstance(result, tuple):
        response, status_code = result
    else:
        response = result
        status_code = response.status_code

    payload = response.get_json()

    assert status_code == 200
    assert payload['success'] is True
    assert fake_user.two_factor_enabled is True
    assert commit_called['value'] is True


def test_disable_two_factor_revokes_trusted_devices_without_recent_auth_session(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-secret'

    fake_user = User(
        username='admin_user',
        email='admin@example.com',
        password_hash=generate_password_hash('OldPass123!'),
        role='admin',
        full_name='Admin User',
    )
    fake_user.id = 21
    fake_user.enable_two_factor()

    commit_called = {'value': False}

    monkeypatch.setattr(profile_routes, 'current_user', fake_user)
    monkeypatch.setattr(profile_routes.TrustedDevice, 'revoke_all_for_user', lambda _user_id: 3)
    monkeypatch.setattr(profile_routes.UserActivityLog, 'log_action', lambda **kwargs: None)
    monkeypatch.setattr(profile_routes.db.session, 'commit', lambda: commit_called.__setitem__('value', True))
    monkeypatch.setattr(profile_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context('/account/two-factor/disable', method='POST', json={}):
        result = profile_routes.disable_two_factor.__wrapped__()

    if isinstance(result, tuple):
        response, status_code = result
    else:
        response = result
        status_code = response.status_code

    payload = response.get_json()
    cookie_header = response.headers.get('Set-Cookie', '')

    assert status_code == 200
    assert payload['success'] is True
    assert fake_user.two_factor_enabled is False
    assert commit_called['value'] is True
    assert 'isw_trusted_device=' in cookie_header


def test_auth_pending_two_factor_expires_and_clears_session():
    app = Flask(__name__)
    app.secret_key = 'test-secret'

    with app.test_request_context('/login', method='GET'):
        session[auth_routes.PENDING_TWO_FACTOR_SESSION_KEY] = {
            'user_id': 11,
            'created_at': _utcnow_naive().isoformat(),
            'expires_at': (_utcnow_naive() - timedelta(seconds=1)).isoformat(),
            'resend_available_at': (_utcnow_naive() + timedelta(seconds=30)).isoformat(),
            'code_hash': 'hash',
            'code_salt': 'salt',
            'attempts': 0,
        }

        pending = auth_routes._get_pending_two_factor()

        assert pending is None
        assert auth_routes.PENDING_TWO_FACTOR_SESSION_KEY not in session


def test_auth_pending_resend_seconds_remaining_never_negative():
    future = {'resend_available_at': (_utcnow_naive() + timedelta(seconds=30)).isoformat()}
    past = {'resend_available_at': (_utcnow_naive() - timedelta(seconds=30)).isoformat()}

    remaining_future = auth_routes._pending_resend_seconds_remaining(future)
    remaining_past = auth_routes._pending_resend_seconds_remaining(past)

    assert 0 < remaining_future <= 30
    assert remaining_past == 0


def test_auth_resolve_trusted_device_extends_window(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    app.config['TWO_FACTOR_TRUST_DAYS'] = 9

    captured = {}

    def fake_find_valid_for_user(user_id, raw_token, extend_days=None):
        captured['user_id'] = user_id
        captured['raw_token'] = raw_token
        captured['extend_days'] = extend_days
        return object()

    monkeypatch.setattr(auth_routes.TrustedDevice, 'find_valid_for_user', fake_find_valid_for_user)

    with app.test_request_context('/login', method='POST', headers={'Cookie': 'isw_trusted_device=abc123'}):
        device, raw_token, should_clear_cookie = auth_routes._resolve_trusted_device(42)

    assert device is not None
    assert raw_token == 'abc123'
    assert should_clear_cookie is False
    assert captured == {
        'user_id': 42,
        'raw_token': 'abc123',
        'extend_days': 9,
    }


def test_auth_resolve_trusted_device_marks_invalid_cookie_for_clear(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-secret'

    monkeypatch.setattr(auth_routes.TrustedDevice, 'find_valid_for_user', lambda *_args, **_kwargs: None)

    with app.test_request_context('/login', method='POST', headers={'Cookie': 'isw_trusted_device=abc123'}):
        device, raw_token, should_clear_cookie = auth_routes._resolve_trusted_device(7)

    assert device is None
    assert raw_token == 'abc123'
    assert should_clear_cookie is True


def test_auth_resolve_trusted_device_does_not_clear_cookie_on_exception(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-secret'

    def _raise_resolver_error(*_args, **_kwargs):
        raise RuntimeError('transient resolver failure')

    monkeypatch.setattr(auth_routes.TrustedDevice, 'find_valid_for_user', _raise_resolver_error)
    monkeypatch.setattr(auth_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context('/login', method='POST', headers={'Cookie': 'isw_trusted_device=abc123'}):
        device, raw_token, should_clear_cookie = auth_routes._resolve_trusted_device(7)

    assert device is None
    assert raw_token == 'abc123'
    assert should_clear_cookie is False


def test_verify_two_factor_template_keeps_verify_and_resend_forms_separate():
    template_path = Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'verify_two_factor.html'
    contents = template_path.read_text(encoding='utf-8')

    verify_form_open = "<form method=\"POST\" action=\"{{ url_for('auth.verify_two_factor') }}\""
    resend_form_open = "action=\"{{ url_for('auth.resend_two_factor_code') }}\""

    assert verify_form_open in contents
    assert resend_form_open in contents

    verify_start = contents.index(verify_form_open)
    verify_end = contents.index('</form>', verify_start)
    resend_start = contents.index(resend_form_open)

    assert 'name="trust_device"' not in contents
    assert 'Click Here to Resend Code' not in contents
    assert 'id="resend-link"' in contents
    assert 'data-initial-cooldown="{{ resend_available_in_seconds or 0 }}"' in contents
    assert 'id="resend-cooldown"' in contents
    assert 'id="resend-cooldown-seconds"' in contents
    assert 'window.setInterval(function()' in contents
    assert 'resendLink.disabled = false;' in contents
    assert 'aria-label="Resend verification code"' in contents
    assert 'Did not get the email code? Click' in contents
    assert 'to resend.' in contents
    assert resend_start > verify_end


def test_profile_template_hides_trusted_device_revoke_controls():
    template_path = Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'profile.html'
    contents = template_path.read_text(encoding='utf-8')

    assert 'id="disable2faBtn"' in contents
    assert 'id="revokeAllTrustedDevicesBtn"' not in contents
    assert 'revoke-trusted-device-btn' not in contents
    assert '/account/two-factor/revoke-all-trusted-devices' not in contents
    assert '/account/two-factor/revoke-trusted-device' not in contents
    assert 'Trusted Devices' not in contents
    assert 'id="confirmModal"' in contents
    assert 'data-force-sidebar-dim="true"' in contents
    assert 'data-sidebar-dim-alpha="0.5"' in contents
    assert "window.toggleSidebarBlur(true);" in contents
    assert "window.toggleSidebarBlur(false);" in contents
    assert 'id="strength-meter-fill"' in contents
    assert 'id="strength-text"' in contents
    assert 'id="password-match-text"' in contents
    assert 'id="req-length"' in contents
    assert 'id="req-upper"' in contents
    assert 'id="req-lower"' in contents
    assert 'id="req-number"' in contents
    assert 'Password Requirements:' in contents
    assert 'password-strength-bar' not in contents
    assert 'id="passwordMatchIndicator"' not in contents
    assert 'Password Tips' not in contents
    assert re.search(r'id="newPassword"[\s\S]*?disabled', contents)
    assert re.search(r'id="confirmPassword"[\s\S]*?disabled', contents)
    assert 'id="currentPasswordStatusRow"' in contents
    assert 'password-status-row' in contents
    assert 'status-dot-pulse' in contents
    assert "statusRow.setAttribute('aria-busy', 'true')" in contents
    assert 'id="currentPasswordStatus"' in contents
    assert 'id="currentPasswordStatusDot"' in contents
    assert 'id="newPasswordLockHint"' in contents
    assert 'id="confirmPasswordLockHint"' in contents
    assert 'password-target-card' in contents
    assert 'function updatePasswordLockHints(isUnlocked)' in contents
    assert 'function updatePasswordFieldGating()' in contents
    assert 'async function verifyCurrentPasswordForGating(currentPassword)' in contents
    assert '/account/verify-current-password' in contents
    assert "currentPasswordInput.addEventListener('input', function()" in contents


def test_reset_password_template_uses_live_feedback_regions():
    template_path = Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'reset_password.html'
    contents = template_path.read_text(encoding='utf-8')

    assert 'id="strength-text" aria-live="polite"' in contents
    assert 'id="password-match-text" aria-live="polite"' in contents
    assert 'id="strength-meter-fill"' in contents
    assert 'id="req-length"' in contents
    assert 'id="req-upper"' in contents
    assert 'id="req-lower"' in contents
    assert 'id="req-number"' in contents


def test_verify_two_factor_auto_issues_trusted_device(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-secret'

    fake_user = SimpleNamespace(
        id=31,
        username='dean_user',
        email='dean@example.com',
        full_name='Dean User',
        two_factor_enabled=True,
        is_active=True,
        check_and_disable_if_expired=lambda: False,
    )

    issued = {}
    cookie_applied = {}
    finalized = {}

    class _FakeTwoFactorForm:
        def __init__(self):
            self.code = SimpleNamespace(data='123456')

        def validate_on_submit(self):
            return True

    def _fake_issue_for_user(user_id, raw_token, days_valid=1, label=None, ip_address=None, user_agent=None):
        issued.update({
            'user_id': user_id,
            'raw_token': raw_token,
            'days_valid': days_valid,
            'label': label,
            'ip_address': ip_address,
            'user_agent': user_agent,
        })

    def _fake_finalize_login(user, next_page=None):
        finalized['user_id'] = user.id
        finalized['next_page'] = next_page
        return app.make_response('ok')

    def _fake_apply_cookie(response, raw_token, days_valid):
        cookie_applied['response'] = response
        cookie_applied['raw_token'] = raw_token
        cookie_applied['days_valid'] = days_valid

    monkeypatch.setattr(auth_routes, 'current_user', SimpleNamespace(is_authenticated=False))
    monkeypatch.setattr(auth_routes, '_get_pending_two_factor', lambda: {
        'user_id': fake_user.id,
        'next_page': '/main/dashboard',
        'attempts': 0,
        'code_hash': 'hash',
        'code_salt': 'salt',
    })
    monkeypatch.setattr(auth_routes, '_clear_pending_two_factor', lambda: None)
    monkeypatch.setattr(auth_routes, 'TwoFactorVerificationForm', _FakeTwoFactorForm)
    monkeypatch.setattr(auth_routes, 'ResendTwoFactorCodeForm', lambda: SimpleNamespace())
    fake_user_model = SimpleNamespace(
        query=SimpleNamespace(get=lambda _user_id: fake_user),
        verify_email_otp_hash=lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(auth_routes, 'User', fake_user_model)
    monkeypatch.setattr(auth_routes, '_trusted_device_days', lambda: 1)
    monkeypatch.setattr(auth_routes.TrustedDevice, 'issue_for_user', _fake_issue_for_user)
    monkeypatch.setattr(auth_routes.UserActivityLog, 'log_action', lambda **_kwargs: None)
    monkeypatch.setattr(auth_routes, '_finalize_login', _fake_finalize_login)
    monkeypatch.setattr(auth_routes, '_apply_trusted_device_cookie', _fake_apply_cookie)

    with app.test_request_context('/verify-2fa', method='POST'):
        response = auth_routes.verify_two_factor()

    assert response.get_data(as_text=True) == 'ok'
    assert issued['user_id'] == fake_user.id
    assert issued['days_valid'] == 1
    assert issued['raw_token']
    assert issued['label'].startswith('Trusted browser - ')
    assert finalized['user_id'] == fake_user.id
    assert finalized['next_page'] == '/main/dashboard'
    assert cookie_applied['response'] is response
    assert cookie_applied['raw_token'] == issued['raw_token']
    assert cookie_applied['days_valid'] == 1


def test_apply_trusted_device_cookie_honors_forwarded_https():
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    with app.test_request_context('/login', method='POST', headers={'X-Forwarded-Proto': 'https'}):
        response = app.make_response('ok')
        auth_routes._apply_trusted_device_cookie(response, 'token-123', 5)

    cookie_header = response.headers.get('Set-Cookie', '')
    assert 'isw_trusted_device=token-123' in cookie_header
    assert 'Secure' in cookie_header
    assert 'HttpOnly' in cookie_header
    assert 'SameSite=Lax' in cookie_header


def test_sign_in_otp_email_payload_contains_professional_sections():
    payload = build_sign_in_otp_email_payload(
        full_name='Dean User',
        institution_name='Norzagaray College',
        app_brand_name='iSchedWise',
        code='735912',
        expires_minutes=10,
    )

    assert payload['subject'] == 'Your sign-in verification code - Norzagaray College'
    assert '735912' in payload['text_body']
    assert 'This code expires in 10 minutes.' in payload['text_body']
    assert 'Sign-In Verification Code' in payload['html_body']
    assert 'Verification Code' in payload['html_body']
    assert 'role="presentation"' in payload['html_body']
    assert 'If you did not try to sign in' in payload['html_body']
    assert 'iSchedWise Team' in payload['html_body']
    assert 'Support Team' not in payload['html_body']


def test_profile_otp_email_payload_contains_requested_purpose():
    payload = build_profile_otp_email_payload(
        full_name='Faculty User',
        institution_name='Norzagaray College',
        app_brand_name='iSchedWise',
        purpose='enable two-factor authentication',
        code='184263',
        expires_minutes=15,
    )

    assert payload['subject'] == 'Your verification code - Norzagaray College'
    assert 'enable two-factor authentication' in payload['text_body']
    assert '184263' in payload['text_body']
    assert 'Security Verification Code' in payload['html_body']
    assert 'enable two-factor authentication' in payload['html_body']
    assert 'iSchedWise Team' in payload['html_body']
    assert 'Support Team' not in payload['html_body']


def test_password_reset_email_payload_contains_cta_and_fallback_link():
    reset_url = 'https://example.com/reset/token123'
    payload = build_password_reset_email_payload(
        full_name='Admin User',
        email='admin@example.com',
        institution_name='Norzagaray College',
        app_brand_name='iSchedWise',
        reset_url=reset_url,
        expires_minutes=60,
    )

    assert payload['subject'] == 'Password Reset Request - Norzagaray College'
    assert reset_url in payload['text_body']
    assert 'This link expires in 1 hour.' in payload['text_body']
    assert 'Reset Password' in payload['html_body']
    assert reset_url in payload['html_body']
    assert 'Alternative Link' in payload['html_body']
    assert 'iSchedWise Team' in payload['html_body']
    assert 'Support Team' not in payload['html_body']


def test_smtp_test_email_payload_contains_delivery_metadata():
    payload = build_smtp_test_email_payload(
        full_name='Super Admin',
        recipient_email='superadmin@example.com',
        institution_name='Norzagaray College',
        app_brand_name='iSchedWise',
        sent_by='Super Admin',
        sent_at_utc_label='2026-03-28 14:30:00 UTC',
    )

    assert payload['subject'] == 'SMTP Test Email - Norzagaray College'
    assert 'SMTP settings are working correctly' in payload['text_body']
    assert 'superadmin@example.com' in payload['text_body']
    assert '2026-03-28 14:30:00 UTC' in payload['text_body']
    assert 'SMTP Test Email' in payload['html_body']
    assert 'Delivery Details' in payload['html_body']
    assert 'iSchedWise Team' in payload['html_body']
    assert 'Support Team' not in payload['html_body']


def test_build_branded_mail_sender_uses_system_name_display():
    sender = build_branded_mail_sender(
        default_sender='Personal Account <owner@example.com>',
        app_brand_name='Campus Scheduler',
    )

    assert sender == ('Campus Scheduler', 'owner@example.com')


def test_send_two_factor_email_code_uses_branded_sender(monkeypatch):
    app = Flask(__name__)
    app.config['MAIL_DEFAULT_SENDER'] = 'Personal Account <owner@example.com>'

    captured = {}

    class _FakeMessage:
        def __init__(self, subject, recipients, sender):
            captured['subject'] = subject
            captured['recipients'] = recipients
            captured['sender'] = sender
            self.body = ''
            self.html = ''

    monkeypatch.setattr(auth_routes, 'Message', _FakeMessage)
    monkeypatch.setattr(auth_routes.mail, 'send', lambda msg: captured.__setitem__('message', msg))
    monkeypatch.setattr(auth_routes, 'get_institution_context', lambda: {
        'institution_name': 'Norzagaray College',
        'app_brand_name': 'Campus Scheduler',
    })

    with app.app_context():
        auth_routes._send_two_factor_email_code(
            SimpleNamespace(full_name='Dean User', email='dean@example.com'),
            '123456',
        )

    assert captured['recipients'] == ['dean@example.com']
    assert captured['sender'] == ('Campus Scheduler', 'owner@example.com')
    assert captured['message'].body
    assert captured['message'].html


def test_send_password_reset_email_uses_branded_sender(monkeypatch):
    app = Flask(__name__)
    app.config['MAIL_DEFAULT_SENDER'] = 'Personal Account <owner@example.com>'

    captured = {}

    class _FakeMessage:
        def __init__(self, subject, recipients, sender):
            captured['subject'] = subject
            captured['recipients'] = recipients
            captured['sender'] = sender
            self.body = ''
            self.html = ''

    monkeypatch.setattr(auth_routes, 'Message', _FakeMessage)
    monkeypatch.setattr(auth_routes.mail, 'send', lambda msg: captured.__setitem__('message', msg))
    monkeypatch.setattr(auth_routes, 'get_institution_context', lambda: {
        'institution_name': 'Norzagaray College',
        'app_brand_name': 'Campus Scheduler',
    })
    monkeypatch.setattr(
        auth_routes,
        'url_for',
        lambda *_args, **_kwargs: 'https://example.com/auth/reset-password/token-123',
    )

    with app.test_request_context('/auth/forgot-password'):
        auth_routes.send_password_reset_email(
            SimpleNamespace(full_name='Admin User', email='admin@example.com'),
            'token-123',
        )

    assert captured['recipients'] == ['admin@example.com']
    assert captured['sender'] == ('Campus Scheduler', 'owner@example.com')
    assert captured['message'].body
    assert captured['message'].html


def test_admin_smtp_test_email_uses_branded_sender(monkeypatch):
    app = Flask(__name__)
    app.config['MAIL_DEFAULT_SENDER'] = 'Personal Account <owner@example.com>'

    captured = {}

    class _FakeMessage:
        def __init__(self, subject, recipients, sender):
            captured['subject'] = subject
            captured['recipients'] = recipients
            captured['sender'] = sender
            self.body = ''
            self.html = ''

    monkeypatch.setattr(flask_mail, 'Message', _FakeMessage)

    from app.extensions import mail as app_mail

    monkeypatch.setattr(app_mail, 'send', lambda msg: captured.__setitem__('message', msg))
    monkeypatch.setattr(admin_tools_routes, 'current_user', SimpleNamespace(
        full_name='Super Admin',
        email='superadmin@example.com',
    ))
    monkeypatch.setattr(admin_tools_routes, 'InstitutionSettings', SimpleNamespace(
        query=SimpleNamespace(
            first=lambda: SimpleNamespace(
                institution_name='Norzagaray College',
                system_name='Campus Scheduler',
            )
        )
    ))

    with app.test_request_context('/admin/api/config/test-email', method='POST'):
        response = admin_tools_routes.api_config_test_email()

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert captured['recipients'] == ['superadmin@example.com']
    assert captured['sender'] == ('Campus Scheduler', 'owner@example.com')
    assert captured['message'].body
    assert captured['message'].html
