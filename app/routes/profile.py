"""
User Profile Management Routes
Allows users to view and edit their own profile
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.trusted_device import TrustedDevice
from app.models.activity_log import UserActivityLog
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.activity_logger import log_edit, log_password_change

profile_bp = Blueprint('profile', __name__, url_prefix='/account')

# Configuration for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
TRUSTED_DEVICE_COOKIE_NAME = 'isw_trusted_device'

def _trusted_device_days():
    """Return configured trusted-device lifespan in days."""
    value = current_app.config.get('TWO_FACTOR_TRUST_DAYS', 1)
    try:
        return max(1, int(value))
    except Exception:
        return 1

def _trusted_device_cookie_key():
    """Return trusted-device cookie name from config."""
    return current_app.config.get('TWO_FACTOR_TRUSTED_DEVICE_COOKIE', TRUSTED_DEVICE_COOKIE_NAME)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route('/')
@login_required
def index():
    """Display current user's profile"""
    two_factor_enabled = bool(getattr(current_user, 'two_factor_enabled', False))
    name_parts = User.split_full_name(getattr(current_user, 'full_name', ''))

    return render_template(
        'profile.html',
        user=current_user,
        name_parts=name_parts,
        force_password_reset_required=bool(getattr(current_user, 'needs_password_change', False)),
        two_factor_enabled=two_factor_enabled,
        trusted_device_days=_trusted_device_days(),
    )


@profile_bp.route('/update', methods=['POST'])
@login_required
def update_profile():
    """Update current user's profile information"""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        username_input = User.normalize_username(data.get('username')) if 'username' in data else current_user.username

        is_valid_name, name_error, normalized_name = User.resolve_full_name_input(
            full_name=data.get('full_name'),
            first_name=data.get('first_name'),
            middle_initial=data.get('middle_initial'),
            last_name=data.get('last_name'),
        )
        if not is_valid_name:
            return jsonify({'success': False, 'message': name_error}), 400

        full_name = normalized_name['full_name']
        
        # Validate required fields
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if email is already used by another user
        if email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return jsonify({'success': False, 'message': 'Email already in use'}), 400
        
        # Check if username is already used by another user
        if username_input != current_user.username:
            is_valid_username, username_error, normalized_username = User.validate_username_format(username_input)
            if not is_valid_username:
                return jsonify({'success': False, 'message': username_error}), 400

            existing_user = User.query.filter_by(username=normalized_username).first()
            if existing_user:
                return jsonify({'success': False, 'message': 'Username already in use'}), 400
        
        # Track changes for activity log
        changes = {}
        if full_name != current_user.full_name:
            changes['full_name'] = f"{current_user.full_name} -> {full_name}"
        if email != current_user.email:
            changes['email'] = f"{current_user.email} -> {email}"
        if username_input != current_user.username:
            changes['username'] = f"{current_user.username} -> {username_input}"
        
        # Update profile information
        current_user.full_name = full_name
        current_user.email = email
        
        if username_input != current_user.username:
            current_user.username = username_input
        
        db.session.commit()
        
        # Log the profile update with detailed changes
        if changes:
            log_edit('user_profile', current_user.id, current_user.username, changes)
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'full_name': current_user.full_name,
                'first_name': normalized_name['first_name'],
                'middle_initial': normalized_name['middle_initial'],
                'last_name': normalized_name['last_name'],
                'username': current_user.username,
                'email': current_user.email
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating profile: {str(e)}'}), 500


@profile_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change current user's password"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password'):
            return jsonify({'success': False, 'message': 'Current password is required'}), 400
        
        if not data.get('new_password'):
            return jsonify({'success': False, 'message': 'New password is required'}), 400
        
        if not data.get('confirm_password'):
            return jsonify({'success': False, 'message': 'Password confirmation is required'}), 400
        
        # Verify current password
        if not check_password_hash(current_user.password_hash, data['current_password']):
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
        
        # Validate new password
        if len(data['new_password']) < 8:
            return jsonify({'success': False, 'message': 'Password must be between 8 and 30 characters'}), 400
        
        if len(data['new_password']) > 30:
            return jsonify({'success': False, 'message': 'Password must be between 8 and 30 characters'}), 400
        
        if data['new_password'] != data['confirm_password']:
            return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
        
        # Update password
        current_user.password_hash = generate_password_hash(data['new_password'])
        current_user.needs_password_change = False
        db.session.commit()
        
        # Log password change
        log_password_change(current_user.id, current_user.username)
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully. You can now continue using the system.',
            'force_password_reset_required': False
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error changing password: {str(e)}'}), 500


@profile_bp.route('/verify-current-password', methods=['POST'])
@login_required
def verify_current_password():
    """Verify the current password before enabling new password inputs."""
    try:
        data = request.get_json(silent=True) or {}
        current_password = data.get('current_password')
        if current_password is None:
            current_password = ''
        elif not isinstance(current_password, str):
            current_password = str(current_password)

        if not current_password:
            return jsonify({
                'success': False,
                'valid': False,
                'message': 'Current password is required'
            }), 400

        is_valid = check_password_hash(current_user.password_hash, current_password)
        if not is_valid:
            return jsonify({
                'success': False,
                'valid': False,
                'message': 'Current password is incorrect'
            }), 400

        return jsonify({
            'success': True,
            'valid': True,
            'message': 'Current password verified'
        })

    except Exception:
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Unable to verify current password right now'
        }), 500


@profile_bp.route('/two-factor/setup', methods=['POST'])
@login_required
def setup_two_factor():
    """Backward-compatible alias for one-click 2FA enable action."""
    return enable_two_factor()


@profile_bp.route('/two-factor/enable', methods=['POST'])
@login_required
def enable_two_factor():
    """Enable 2FA from profile."""
    try:
        if current_user.two_factor_enabled:
            return jsonify({'success': False, 'message': 'Two-factor authentication is already enabled'}), 400

        current_user.enable_two_factor(secret=None)

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='2fa_enabled',
            entity_type='user',
            entity_id=current_user.id,
            entity_name=current_user.full_name,
            details='User enabled two-factor authentication via profile quick toggle',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Two-factor authentication enabled successfully.'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error enabling 2FA: {str(e)}'}), 500


@profile_bp.route('/two-factor/send-disable-code', methods=['POST'])
@login_required
def send_disable_two_factor_code():
    """Backward-compatible alias for one-click 2FA disable action."""
    return disable_two_factor()


@profile_bp.route('/two-factor/disable', methods=['POST'])
@login_required
def disable_two_factor():
    """Disable 2FA from profile."""
    try:
        if not current_user.two_factor_enabled:
            return jsonify({'success': False, 'message': 'Two-factor authentication is already disabled'}), 400

        revoked_count = TrustedDevice.revoke_all_for_user(current_user.id)
        current_user.disable_two_factor()

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='2fa_disabled',
            entity_type='user',
            entity_id=current_user.id,
            entity_name=current_user.full_name,
            details=f'User disabled two-factor authentication via profile quick toggle and revoked {revoked_count} trusted devices',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.commit()

        response = jsonify({
            'success': True,
            'message': 'Two-factor authentication disabled successfully.'
        })
        response.delete_cookie(_trusted_device_cookie_key(), path='/')
        return response

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error disabling 2FA: {str(e)}'}), 500


@profile_bp.route('/two-factor/revoke-trusted-device', methods=['POST'])
@login_required
def revoke_trusted_device():
    """Revoke one trusted device by id for the current user."""
    try:
        data = request.get_json(silent=True) or {}
        device_id = data.get('device_id')

        if not device_id:
            return jsonify({'success': False, 'message': 'Device ID is required'}), 400

        device = TrustedDevice.query.filter_by(user_id=current_user.id, id=device_id).first()
        if not device:
            return jsonify({'success': False, 'message': 'Trusted device not found'}), 404

        cookie_matches_device = False
        raw_cookie_token = request.cookies.get(_trusted_device_cookie_key())
        if raw_cookie_token:
            cookie_matches_device = TrustedDevice.hash_token(raw_cookie_token) == device.token_hash

        db.session.delete(device)

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='trusted_device_revoked',
            entity_type='user',
            entity_id=current_user.id,
            entity_name=current_user.full_name,
            details=f'User revoked trusted device {device_id}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.commit()

        response = jsonify({
            'success': True,
            'message': 'Trusted device revoked successfully.'
        })
        if cookie_matches_device:
            response.delete_cookie(_trusted_device_cookie_key(), path='/')
        return response

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error revoking trusted device: {str(e)}'}), 500


@profile_bp.route('/two-factor/revoke-all-trusted-devices', methods=['POST'])
@login_required
def revoke_all_trusted_devices():
    """Revoke all trusted devices for the current user."""
    try:
        revoked_count = TrustedDevice.revoke_all_for_user(current_user.id)

        UserActivityLog.log_action(
            user_id=current_user.id,
            action='trusted_devices_revoked_all',
            entity_type='user',
            entity_id=current_user.id,
            entity_name=current_user.full_name,
            details=f'User revoked all trusted devices ({revoked_count})',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.commit()

        response = jsonify({
            'success': True,
            'message': 'All trusted devices were revoked successfully.',
            'revoked_count': revoked_count
        })
        response.delete_cookie(_trusted_device_cookie_key(), path='/')
        return response

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error revoking trusted devices: {str(e)}'}), 500
