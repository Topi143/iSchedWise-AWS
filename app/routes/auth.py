"""
Authentication routes (login, logout, password reset)
"""
from datetime import datetime, timedelta, timezone
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app.extensions import db, mail
from app.models import User, TrustedDevice
from app.models.activity_log import UserActivityLog
from app.models.login_history import LoginHistory
from app.models.settings import InstitutionSettings
from app.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm, TwoFactorVerificationForm, ResendTwoFactorCodeForm
from app.utils.security_email_templates import (
    build_branded_mail_sender,
    build_password_reset_email_payload,
    build_sign_in_otp_email_payload,
)
import uuid

auth_bp = Blueprint('auth', __name__)

TRUSTED_DEVICE_COOKIE_NAME = 'isw_trusted_device'
PENDING_TWO_FACTOR_SESSION_KEY = '_pending_2fa_login'


def _utcnow_naive():
    """Return UTC now as naive datetime for backward compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_institution_context():
    """Get institution and branding context for auth templates."""
    try:
        settings = InstitutionSettings.query.first()
        if settings:
            institution_display_name = (settings.institution_name or '').strip() or 'Norzagaray College'
            app_brand_name = (settings.system_name or '').strip() or 'iSchedWise'
            branding_logo = settings.branding_logo or settings.institution_logo
            return {
                # Backward-compatible alias used by existing auth templates.
                'institution_name': institution_display_name,
                'institution_display_name': institution_display_name,
                'app_brand_name': app_brand_name,
                'institution_logo': branding_logo
            }
    except Exception:
        pass
    return {
        'institution_name': 'Norzagaray College',
        'institution_display_name': 'Norzagaray College',
        'app_brand_name': 'iSchedWise',
        'institution_logo': None
    }


def _trusted_device_days():
    """Get trusted-device lifespan in days from config."""
    value = current_app.config.get('TWO_FACTOR_TRUST_DAYS', 1)
    try:
        return max(1, int(value))
    except Exception:
        return 1


def _trusted_device_cookie_key():
    """Get trusted-device cookie name from config."""
    return current_app.config.get('TWO_FACTOR_TRUSTED_DEVICE_COOKIE', TRUSTED_DEVICE_COOKIE_NAME)


def _pending_two_factor_max_seconds():
    """Get pending 2FA timeout window in seconds from config."""
    value = current_app.config.get(
        'TWO_FACTOR_PENDING_SECONDS',
        current_app.config.get('TWO_FACTOR_OTP_EXPIRY_SECONDS', 600)
    )
    try:
        return max(60, int(value))
    except Exception:
        return 600


def _otp_length():
    """Get numeric OTP length from config."""
    value = current_app.config.get('TWO_FACTOR_OTP_LENGTH', 6)
    try:
        return min(max(int(value), 4), 8)
    except Exception:
        return 6


def _otp_expiry_seconds():
    """Get OTP expiration window from config."""
    value = current_app.config.get('TWO_FACTOR_OTP_EXPIRY_SECONDS', 600)
    try:
        return max(60, int(value))
    except Exception:
        return 600


def _otp_expiry_minutes():
    """Return OTP expiry in whole minutes for user messaging."""
    return max(1, _otp_expiry_seconds() // 60)


def _otp_resend_cooldown_seconds():
    """Get resend cooldown for login OTP emails."""
    value = current_app.config.get('TWO_FACTOR_OTP_RESEND_COOLDOWN_SECONDS', 60)
    try:
        return max(15, int(value))
    except Exception:
        return 60


def _otp_max_attempts():
    """Get maximum verification attempts for a pending login challenge."""
    value = current_app.config.get('TWO_FACTOR_OTP_MAX_ATTEMPTS', 5)
    try:
        return max(1, int(value))
    except Exception:
        return 5


def _parse_iso_datetime(raw_value):
    """Parse an ISO timestamp and return datetime or None."""
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except Exception:
        return None


def _set_pending_two_factor(user_id, next_page=None, challenge=None):
    """Persist pending post-password login state until email OTP verification."""
    pending = {
        'user_id': user_id,
        'next_page': next_page,
        'created_at': _utcnow_naive().isoformat(),
        'attempts': 0,
    }
    if challenge:
        pending.update(challenge)
    session[PENDING_TWO_FACTOR_SESSION_KEY] = pending


def _build_pending_two_factor_challenge(previous_attempts=0):
    """Create a new pending login email OTP challenge payload."""
    code = User.generate_email_otp(length=_otp_length())
    salt = secrets.token_hex(16)
    now = _utcnow_naive()

    challenge = {
        'code_hash': User.hash_email_otp(code, salt),
        'code_salt': salt,
        'sent_at': now.isoformat(),
        'expires_at': (now + timedelta(seconds=_otp_expiry_seconds())).isoformat(),
        'resend_available_at': (now + timedelta(seconds=_otp_resend_cooldown_seconds())).isoformat(),
        'attempts': max(0, int(previous_attempts or 0)),
    }
    return challenge, code


def _send_two_factor_email_code(user, code):
    """Send login verification code to the user's email address."""
    if not user.email:
        raise ValueError('A valid email address is required for two-factor verification.')

    institution_context = get_institution_context()
    institution_name = institution_context.get('institution_name', 'Norzagaray College')
    app_brand_name = institution_context.get('app_brand_name', 'iSchedWise')
    payload = build_sign_in_otp_email_payload(
        full_name=user.full_name,
        institution_name=institution_name,
        app_brand_name=app_brand_name,
        code=code,
        expires_minutes=_otp_expiry_minutes(),
    )

    msg = Message(
        subject=payload['subject'],
        recipients=[user.email],
        sender=build_branded_mail_sender(
            default_sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            app_brand_name=app_brand_name,
        ),
    )

    msg.body = payload['text_body']
    msg.html = payload['html_body']

    mail.send(msg)


def _issue_pending_two_factor_code(user, next_page=None, previous_attempts=0):
    """Issue and email a fresh login OTP challenge, then persist it in the session."""
    challenge, code = _build_pending_two_factor_challenge(previous_attempts=previous_attempts)
    _set_pending_two_factor(user.id, next_page=next_page, challenge=challenge)
    _send_two_factor_email_code(user, code)


def _clear_pending_two_factor():
    """Clear pending post-password login state from the session."""
    session.pop(PENDING_TWO_FACTOR_SESSION_KEY, None)


def _get_pending_two_factor():
    """Return valid pending 2FA context or None when missing/expired."""
    pending = session.get(PENDING_TWO_FACTOR_SESSION_KEY)
    if not pending:
        return None

    created_at = _parse_iso_datetime(pending.get('created_at'))
    if not created_at:
        _clear_pending_two_factor()
        return None

    age_seconds = (_utcnow_naive() - created_at).total_seconds()
    if age_seconds > _pending_two_factor_max_seconds():
        _clear_pending_two_factor()
        return None

    expires_at = _parse_iso_datetime(pending.get('expires_at'))
    if not expires_at or _utcnow_naive() > expires_at:
        _clear_pending_two_factor()
        return None

    if not pending.get('code_hash') or not pending.get('code_salt'):
        _clear_pending_two_factor()
        return None

    try:
        pending['attempts'] = max(0, int(pending.get('attempts', 0)))
    except Exception:
        pending['attempts'] = 0
    session[PENDING_TWO_FACTOR_SESSION_KEY] = pending

    return pending


def _pending_resend_seconds_remaining(pending):
    """Return remaining resend cooldown in seconds for a pending challenge."""
    resend_available_at = _parse_iso_datetime(pending.get('resend_available_at'))
    if not resend_available_at:
        return 0

    remaining = int((resend_available_at - _utcnow_naive()).total_seconds())
    return max(0, remaining)


def _increment_pending_two_factor_attempts(pending):
    """Increment and persist pending challenge attempt count."""
    attempts = max(0, int(pending.get('attempts', 0))) + 1
    pending['attempts'] = attempts
    session[PENDING_TWO_FACTOR_SESSION_KEY] = pending
    session.modified = True
    return attempts


def _mask_identifier(value):
    """Mask email/username identifier for challenge screen display."""
    if not value:
        return 'your account'
    if '@' not in value:
        if len(value) <= 2:
            return '*' * len(value)
        return value[0] + ('*' * max(len(value) - 2, 1)) + value[-1]

    local, _, domain = value.partition('@')
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + ('*' * max(len(local) - 2, 1)) + local[-1]
    return f'{masked_local}@{domain}'


def _is_request_secure_for_cookie():
    """Infer whether secure cookies should be attached for this request."""
    if request.is_secure:
        return True

    forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()
    return forwarded_proto == 'https'


def _resolve_trusted_device(user_id):
    """Return valid trusted device for current request cookie, if any."""
    raw_token = request.cookies.get(_trusted_device_cookie_key())
    if not raw_token:
        return None, None, False

    try:
        device = TrustedDevice.find_valid_for_user(
            user_id,
            raw_token,
            extend_days=_trusted_device_days()
        )
        if not device:
            return None, raw_token, True
        return device, raw_token, False
    except Exception:
        db.session.rollback()
        return None, raw_token, False


def _apply_trusted_device_cookie(response, raw_token, days_valid):
    """Attach trusted-device cookie to the response."""
    try:
        resolved_days = max(1, int(days_valid))
    except Exception:
        resolved_days = _trusted_device_days()

    secure_cookie = bool(current_app.config.get('SESSION_COOKIE_SECURE', False)) or _is_request_secure_for_cookie()
    same_site_policy = current_app.config.get('SESSION_COOKIE_SAMESITE', 'Lax') or 'Lax'

    response.set_cookie(
        _trusted_device_cookie_key(),
        raw_token,
        max_age=resolved_days * 24 * 60 * 60,
        httponly=True,
        secure=secure_cookie,
        samesite=same_site_policy,
        domain=current_app.config.get('SESSION_COOKIE_DOMAIN'),
        path='/'
    )


def _clear_trusted_device_cookie(response):
    """Clear trusted-device cookie from the response."""
    response.delete_cookie(_trusted_device_cookie_key(), path='/')


def _finalize_login(user, next_page=None):
    """Create authenticated browser session and apply existing post-login routing."""
    login_user(user, remember=False)

    # Update last login time
    user.last_login = db.func.current_timestamp()

    # Store login timestamp in session for force-logout enforcement
    now_iso = _utcnow_naive().isoformat()
    login_session_token = uuid.uuid4().hex
    session.permanent = False
    session['_login_time'] = now_iso
    session['_last_activity'] = now_iso
    session['_login_session_token'] = login_session_token

    # Clear any previous force_logout_at since user just logged in fresh
    user.force_logout_at = None

    # Log the login action
    UserActivityLog.log_action(
        user_id=user.id,
        action='login',
        entity_type='user',
        entity_id=user.id,
        entity_name=user.full_name,
        details=f'User logged in from {request.remote_addr}',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    # Record login in login_history for session tracking
    try:
        LoginHistory.record_login(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            session_id=login_session_token
        )
    except Exception:
        pass  # Don't block login if history recording fails

    db.session.commit()

    # Check if this is a temporary auto-generated user that needs setup
    if user.needs_first_login_setup():
        flash('Welcome! Please complete your account setup to continue.', 'info')
        return redirect(url_for('auth.first_login_setup'))

    if user.needs_password_change:
        flash('You must change your password before continuing.', 'warning')
        return redirect(url_for('profile.index'))

    # Redirect to next page or dashboard
    if next_page:
        return redirect(next_page)
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'GET':
        _clear_pending_two_factor()

    # Redirect authenticated users to dashboard (unless maintenance mode blocks them)
    if current_user.is_authenticated:
        if not getattr(current_user, 'is_active', True) or getattr(current_user, 'is_archived', False):
            from flask import session as flask_session
            logout_user()
            flask_session.clear()
            flash('Your account is inactive. Please contact the administrator.', 'warning')
        else:
            try:
                from app.models.system_config import SystemConfig
                if SystemConfig.get('maintenance_mode', False) and not getattr(current_user, 'is_super_admin', False):
                    # During maintenance, log out non-super-admin users so they see the login page
                    logout_user()
                else:
                    return redirect(url_for('main.dashboard'))
            except Exception:
                return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.username.data)
        ).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username/email or password', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if temporary account has expired and disable it
        if user.check_and_disable_if_expired():
            db.session.commit()
            flash('This temporary account has expired (24 hours). Please contact the administrator for a new account.', 'error')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact the administrator.', 'error')
            return redirect(url_for('auth.login'))
        next_page = request.args.get('next')

        trusted_device = None
        trusted_device_token = None
        should_clear_trusted_device_cookie = False

        if user.two_factor_enabled:
            trusted_device, trusted_device_token, should_clear_trusted_device_cookie = _resolve_trusted_device(user.id)
            if not trusted_device:
                try:
                    _issue_pending_two_factor_code(user, next_page=next_page)
                except Exception:
                    _clear_pending_two_factor()
                    flash('Unable to send a verification code right now. Please try again later.', 'error')
                    return redirect(url_for('auth.login'))

                flash(
                    f'We sent a 6-digit verification code to {_mask_identifier(user.email or user.username)}.',
                    'info'
                )
                response = redirect(url_for('auth.verify_two_factor'))
                if should_clear_trusted_device_cookie:
                    _clear_trusted_device_cookie(response)
                return response

            UserActivityLog.log_action(
                user_id=user.id,
                action='trusted_device_used',
                entity_type='user',
                entity_id=user.id,
                entity_name=user.full_name,
                details='Login completed via trusted device bypass',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

        response = _finalize_login(user, next_page=next_page)
        if trusted_device and trusted_device_token:
            _apply_trusted_device_cookie(response, trusted_device_token, _trusted_device_days())
        return response
    
    response = make_response(render_template('login.html', form=form, **get_institution_context()))
    # Prevent caching of login page
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_two_factor():
    """Verify pending login using an emailed one-time code."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    pending = _get_pending_two_factor()
    if not pending:
        flash('Two-factor verification expired. Please sign in again.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.get(pending.get('user_id'))
    if not user:
        _clear_pending_two_factor()
        flash('Unable to verify this account. Please sign in again.', 'error')
        return redirect(url_for('auth.login'))

    if user.check_and_disable_if_expired():
        db.session.commit()
        _clear_pending_two_factor()
        flash('This temporary account has expired (24 hours). Please contact the administrator for a new account.', 'error')
        return redirect(url_for('auth.login'))

    if not user.is_active:
        _clear_pending_two_factor()
        flash('Your account has been deactivated. Please contact the administrator.', 'error')
        return redirect(url_for('auth.login'))

    if not user.two_factor_enabled:
        _clear_pending_two_factor()
        return _finalize_login(user, next_page=pending.get('next_page'))

    form = TwoFactorVerificationForm()
    resend_form = ResendTwoFactorCodeForm()
    if form.validate_on_submit():
        max_attempts = _otp_max_attempts()
        if int(pending.get('attempts', 0)) >= max_attempts:
            _clear_pending_two_factor()
            flash('Too many invalid attempts. Please sign in again.', 'error')
            return redirect(url_for('auth.login'))

        if not User.verify_email_otp_hash(
            form.code.data,
            pending.get('code_hash'),
            pending.get('code_salt'),
            length=_otp_length()
        ):
            attempts = _increment_pending_two_factor_attempts(pending)
            remaining_attempts = max_attempts - attempts
            if remaining_attempts <= 0:
                _clear_pending_two_factor()
                flash('Too many invalid attempts. Please sign in again.', 'error')
                return redirect(url_for('auth.login'))

            flash(f'Invalid verification code. {remaining_attempts} attempt(s) remaining.', 'error')
            return redirect(url_for('auth.verify_two_factor'))

        _clear_pending_two_factor()

        trusted_device_token = secrets.token_urlsafe(48)
        trusted_device_days = _trusted_device_days()

        trusted_label = f'Trusted browser - {_utcnow_naive().strftime("%Y-%m-%d %H:%M")}'
        TrustedDevice.issue_for_user(
            user_id=user.id,
            raw_token=trusted_device_token,
            days_valid=trusted_device_days,
            label=trusted_label,
            ip_address=request.remote_addr,
            user_agent=(request.headers.get('User-Agent') or '')[:255]
        )

        UserActivityLog.log_action(
            user_id=user.id,
            action='trusted_device_added',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.full_name,
            details=f'Trusted device added for {trusted_device_days} days',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        UserActivityLog.log_action(
            user_id=user.id,
            action='2fa_verified',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.full_name,
            details='Email verification code accepted during login',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        response = _finalize_login(user, next_page=pending.get('next_page'))
        if trusted_device_token:
            _apply_trusted_device_cookie(response, trusted_device_token, trusted_device_days)
        return response

    return make_response(render_template(
        'verify_two_factor.html',
        form=form,
        resend_form=resend_form,
        masked_identifier=_mask_identifier(user.email or user.username),
        trusted_device_days=_trusted_device_days(),
        otp_expiry_minutes=_otp_expiry_minutes(),
        resend_available_in_seconds=_pending_resend_seconds_remaining(pending),
        **get_institution_context()
    ))


@auth_bp.route('/verify-2fa/resend', methods=['POST'])
def resend_two_factor_code():
    """Resend the login verification code when cooldown has elapsed."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ResendTwoFactorCodeForm()
    if not form.validate_on_submit():
        flash('Invalid request. Please try again.', 'error')
        return redirect(url_for('auth.verify_two_factor'))

    pending = _get_pending_two_factor()
    if not pending:
        flash('Two-factor verification expired. Please sign in again.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.get(pending.get('user_id'))
    if not user:
        _clear_pending_two_factor()
        flash('Unable to verify this account. Please sign in again.', 'error')
        return redirect(url_for('auth.login'))

    if user.check_and_disable_if_expired():
        db.session.commit()
        _clear_pending_two_factor()
        flash('This temporary account has expired (24 hours). Please contact the administrator for a new account.', 'error')
        return redirect(url_for('auth.login'))

    if not user.is_active:
        _clear_pending_two_factor()
        flash('Your account has been deactivated. Please contact the administrator.', 'error')
        return redirect(url_for('auth.login'))

    if not user.two_factor_enabled:
        _clear_pending_two_factor()
        return _finalize_login(user, next_page=pending.get('next_page'))

    cooldown_remaining = _pending_resend_seconds_remaining(pending)
    if cooldown_remaining > 0:
        flash(f'Please wait {cooldown_remaining} seconds before requesting another code.', 'warning')
        return redirect(url_for('auth.verify_two_factor'))

    try:
        _issue_pending_two_factor_code(
            user,
            next_page=pending.get('next_page'),
            previous_attempts=pending.get('attempts', 0)
        )
    except Exception:
        flash('Unable to resend the verification code right now. Please try again later.', 'error')
        return redirect(url_for('auth.verify_two_factor'))

    flash(
        f'A new verification code was sent to {_mask_identifier(user.email or user.username)}.',
        'success'
    )
    return redirect(url_for('auth.verify_two_factor'))


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    # Log the logout action before logging out
    UserActivityLog.log_action(
        user_id=current_user.id,
        action='logout',
        entity_type='user',
        entity_id=current_user.id,
        entity_name=current_user.full_name,
        details=f'User logged out from {request.remote_addr}',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    # Record logout in login_history
    try:
        from flask import session as flask_session
        current_session_token = flask_session.get('_login_session_token')
        if current_session_token:
            LoginHistory.record_logout(session_id=current_session_token)
        else:
            LoginHistory.record_logout(user_id=current_user.id)
    except Exception:
        pass  # Don't block logout if history recording fails
    
    db.session.commit()
    
    from flask import session as flask_session
    logout_user()
    flask_session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password - send reset email"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Generate reset token
            token = user.generate_reset_token()
            
            # Send reset email
            try:
                send_password_reset_email(user, token)
                flash('Password reset instructions have been sent to your email.', 'success')
            except Exception as e:
                flash('An error occurred while sending the email. Please try again later.', 'error')
                print(f"Email error: {str(e)}")
        else:
            flash('No account found with that email address.', 'error')
            return render_template('forgot_password.html', form=form, **get_institution_context())
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', form=form, **get_institution_context())


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Verify token
    user = User.verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired reset link. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Set new password
        user.set_password(form.password.data)
        user.needs_password_change = False
        db.session.commit()
        
        flash('Your password has been reset successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form, token=token, **get_institution_context())


@auth_bp.route('/first-login-setup', methods=['GET', 'POST'])
@login_required
def first_login_setup():
    """
    Handle first-login setup for quick-generated accounts.
    Requires the user to set a valid email and new password.
    """
    # If user doesn't need setup, redirect to dashboard
    if not current_user.needs_first_login_setup():
        return redirect(url_for('main.dashboard'))

    name_parts = User.split_full_name(current_user.full_name)
    
    if request.method == 'POST':
        new_email = request.form.get('email', '').strip()
        new_username = User.normalize_username(request.form.get('username', ''))
        new_first_name = request.form.get('first_name')
        new_middle_initial = request.form.get('middle_initial')
        new_last_name = request.form.get('last_name')
        new_full_name = request.form.get('full_name')
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        submitted_name_parts = {
            'first_name': User.normalize_name_component(new_first_name),
            'middle_initial': User.normalize_name_component(new_middle_initial).replace('.', '').upper(),
            'last_name': User.normalize_name_component(new_last_name),
        }
        
        errors = []
        
        # Validate email
        if not new_email:
            errors.append('Email is required')
        elif '@ischedwise.local' in new_email:
            errors.append('Please provide a valid personal email address')
        elif User.query.filter(User.email == new_email, User.id != current_user.id).first():
            errors.append('This email is already in use')
        
        # Validate username (optional, but check if changed)
        if new_username and new_username != current_user.username:
            is_valid_username, username_error, normalized_username = User.validate_username_format(new_username)
            if not is_valid_username:
                errors.append(username_error)
            elif User.query.filter(User.username == normalized_username, User.id != current_user.id).first():
                errors.append('This username is already in use')
            else:
                new_username = normalized_username

        is_valid_name, name_error, normalized_name = User.resolve_full_name_input(
            full_name=new_full_name,
            first_name=new_first_name,
            middle_initial=new_middle_initial,
            last_name=new_last_name,
        )
        if not is_valid_name:
            errors.append(name_error)
        
        # Validate password
        if not new_password:
            errors.append('Password is required')
        elif len(new_password) < 8 or len(new_password) > 30:
            errors.append('Password must be between 8 and 30 characters')
        elif new_password != confirm_password:
            errors.append('Passwords do not match')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template(
                'first_login_setup.html',
                name_parts=submitted_name_parts,
                **get_institution_context()
            )
        
        # Complete the setup
        current_user.complete_first_login_setup(
            new_email=new_email,
            new_password=new_password,
            new_username=new_username if new_username and new_username != current_user.username else None,
            new_full_name=normalized_name['full_name'] if normalized_name['full_name'] != current_user.full_name else None
        )
        
        # Log the setup completion
        UserActivityLog.log_action(
            user_id=current_user.id,
            action='first_login_setup_completed',
            entity_type='user',
            entity_id=current_user.id,
            entity_name=current_user.full_name,
            details='User completed first-login account setup',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        brand_name = get_institution_context().get('app_brand_name', 'iSchedWise')
        flash(f'Account setup completed successfully! Welcome to {brand_name}.', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('first_login_setup.html', name_parts=name_parts, **get_institution_context())


def send_password_reset_email(user, token):
    """
    Send password reset email to user
    
    Args:
        user: User object
        token: Reset token
    """
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    institution_context = get_institution_context()
    institution_name = institution_context.get('institution_name', 'Norzagaray College')
    app_brand_name = institution_context.get('app_brand_name', 'iSchedWise')
    payload = build_password_reset_email_payload(
        full_name=user.full_name,
        email=user.email,
        institution_name=institution_name,
        app_brand_name=app_brand_name,
        reset_url=reset_url,
        expires_minutes=60,
    )
    
    msg = Message(
        subject=payload['subject'],
        recipients=[user.email],
        sender=build_branded_mail_sender(
            default_sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            app_brand_name=app_brand_name,
        ),
    )
    msg.html = payload['html_body']
    msg.body = payload['text_body']
    
    mail.send(msg)
