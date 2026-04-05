"""
User Management Routes
Handles CRUD operations for user accounts (Admin and Dean)
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.user import User
from app.models.program import Program
from app.models.department import Department
from app.utils.activity_logger import log_create, log_edit, log_delete
from app.utils.timezone_utils import to_utc_iso_z
from functools import wraps
from datetime import datetime
import secrets
import re

user_bp = Blueprint('user', __name__, url_prefix='/users')

_QUICK_USER_RETRY_LIMIT = 10
_QUICK_USER_NUMERIC_RE = re.compile(r'^user(\d+)$')
_RESET_PASSWORD_LENGTH = 12
_RESET_PASSWORD_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'


def _disable_expired_temporary_accounts():
    """
    Helper function to check and disable all expired temporary accounts.
    This runs automatically when admins view the users list.
    """
    from datetime import datetime, timedelta
    
    # Find all temporary users (user### pattern with default password)
    users = User.query.filter(User.is_active == True).all()
    disabled_count = 0
    
    for user in users:
        if user.is_temporary_user() and user.created_at:
            # Check if account is older than 24 hours
            expiry_time = user.created_at + timedelta(hours=24)
            if datetime.utcnow() > expiry_time:
                user.is_active = False
                disabled_count += 1
                
                # Log the auto-disable action
                log_edit('user', user.id, user.username, {
                    'status': 'Auto-disabled (24h expiry)',
                    'reason': 'Temporary account not configured within 24 hours'
                })
    
    if disabled_count > 0:
        db.session.commit()
    
    return disabled_count


def admin_required(f):
    """Decorator to require admin role (includes super_admin)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def _get_department_data_for_user(user):
    """Return unique department ids and names derived from the user's programs."""
    user_departments = {}
    for program in user.programs:
        if program.department_id and program.department:
            user_departments[program.department_id] = program.department.department_name
    return list(user_departments.keys()), list(user_departments.values())


def _serialize_user(user):
    """Serialize a user object for users API responses."""
    program_ids = [program.id for program in user.programs]
    program_names = [program.program_name for program in user.programs]
    department_ids, department_names = _get_department_data_for_user(user)
    is_pending_setup = user.is_temporary_user() and not user.email_verified
    name_parts = User.split_full_name(user.full_name)

    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'first_name': name_parts.get('first_name', ''),
        'middle_initial': name_parts.get('middle_initial', ''),
        'last_name': name_parts.get('last_name', ''),
        'role': user.role,
        'program_ids': program_ids,
        'department_ids': department_ids,
        'departments': department_names,
        'programs': program_names,
        'program_names': ', '.join(department_names) if department_names else ('-' if not program_names else ', '.join(program_names)),
        'is_active': user.is_active,
        'is_archived': user.is_archived,
        'archived_at': user.archived_at.strftime('%Y-%m-%d %H:%M:%S') if user.archived_at else None,
        'archive_reason': user.archive_reason,
        'is_pending_setup': is_pending_setup,
        'email_verified': user.email_verified,
        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
        'last_login_relative': _format_relative_time(user.last_login) if user.last_login else 'Never'
    }


def _normalize_department_ids(department_ids):
    if not department_ids:
        return []
    if not isinstance(department_ids, list):
        return [department_ids]
    return department_ids


def _assign_user_programs_from_departments(user, department_ids):
    """Assign all non-archived programs under selected departments to a dean user."""
    for cid in _normalize_department_ids(department_ids):
        department = Department.query.get(cid)
        if not department:
            continue
        for program in department.programs:
            if not program.is_archived:
                user.programs.append(program)


def _archive_user_or_response_error(user, reason):
    """Archive a user or return an error response tuple when constraints fail."""
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'You cannot archive your own account'}), 400

    if user.role == 'super_admin' and not current_user.is_super_admin:
        return jsonify({'success': False, 'message': 'You do not have permission to archive this user'}), 403

    if user.is_archived:
        return jsonify({'success': False, 'message': 'User is already archived'}), 400

    if user.role in ('admin', 'super_admin'):
        admin_count = User.query.filter(
            User.role.in_(['admin', 'super_admin']),
            User.is_active == True,
            User.is_archived == False
        ).count()
        if admin_count <= 1:
            return jsonify({'success': False, 'message': 'Cannot archive the last active admin account'}), 400

    user.archive(user_id=current_user.id, reason=reason)
    log_delete('user', user.id, user.username, {
        'role': user.role,
        'email': user.email,
        'action': 'archived',
        'reason': reason
    })
    return None


@user_bp.route('/')
@login_required
@admin_required
def index():
    """Display all users"""
    # Auto-disable expired temporary accounts before displaying the list
    _disable_expired_temporary_accounts()
    
    users = User.query.order_by(User.created_at.desc()).all()
    programs = Program.query.filter_by(is_active=True).order_by(Program.program_name).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    return render_template('users.html', users=users, programs=programs, departments=departments)


@user_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """Get all users as JSON (excluding current user), includes archived users"""
    # Exclude the current logged-in user from the list
    query = User.query.filter(User.id != current_user.id)
    
    # Hide super_admin users from regular admins
    if current_user.role == 'admin':
        query = query.filter(User.role != 'super_admin')
    
    users = query.order_by(User.created_at.desc()).all()
    
    users_data = [_serialize_user(user) for user in users]
    
    return jsonify({'users': users_data})


def _format_relative_time(dt):
    """Format a datetime as relative time (e.g., '2 hours ago')"""
    if not dt:
        return 'Never'
    
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} day{"s" if days != 1 else ""} ago'
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f'{weeks} week{"s" if weeks != 1 else ""} ago'
    else:
        return dt.strftime('%b %d, %Y')


def _get_next_quick_user_number():
    """Return the next numeric suffix for auto-generated user### accounts."""
    max_num = 0
    for row in db.session.query(User.username).all():
        username = row[0] if isinstance(row, tuple) else getattr(row, 'username', None)
        if not username:
            continue
        match = _QUICK_USER_NUMERIC_RE.match(username)
        if not match:
            continue
        number = int(match.group(1))
        if number > max_num:
            max_num = number
    return max_num + 1


def _build_quick_user_identity(number):
    """Build username, email, and full-name values for quick-generated users."""
    suffix = str(number).zfill(3)
    username = f'user{suffix}'
    return username, f'{username}@ischedwise.local', f'User {suffix}'


def _generate_temporary_password(length=_RESET_PASSWORD_LENGTH):
    """Generate a human-friendly temporary password for admin-initiated resets."""
    return ''.join(secrets.choice(_RESET_PASSWORD_ALPHABET) for _ in range(length))


def _is_user_identity_conflict(exc):
    """Return True when IntegrityError indicates username/email uniqueness conflict."""
    message = str(getattr(exc, 'orig', exc)).lower()
    if 'duplicate entry' not in message and 'unique constraint failed' not in message:
        return False

    conflict_markers = (
        'users.username',
        'users.email',
        "key 'username'",
        'key "username"',
        "key 'email'",
        'key "email"',
    )
    return any(marker in message for marker in conflict_markers)


@user_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    """Get a single user by ID"""
    user = User.query.get_or_404(user_id)
    
    return jsonify(_serialize_user(user))


@user_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create a new user"""
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'role']
        for field in required_fields:
            value = data.get(field)
            if isinstance(value, str):
                value = value.strip()
                data[field] = value
            if not value:
                return jsonify({'success': False, 'message': f'{field.replace("_", " ").title()} is required'}), 400

        is_valid_name, name_error, normalized_name = User.resolve_full_name_input(
            full_name=data.get('full_name'),
            first_name=data.get('first_name'),
            middle_initial=data.get('middle_initial'),
            last_name=data.get('last_name'),
        )
        if not is_valid_name:
            return jsonify({'success': False, 'message': name_error}), 400
        
        # Validate role
        if data['role'] not in ['super_admin', 'admin', 'dean']:
            return jsonify({'success': False, 'message': 'Invalid role'}), 400
        
        # Only super_admin can create admin or super_admin users
        if data['role'] in ['admin', 'super_admin'] and not current_user.is_super_admin:
            return jsonify({'success': False, 'message': 'Only Super Admins can create Admin users'}), 400

        # Validate username format
        is_valid_username, username_error, normalized_username = User.validate_username_format(data.get('username'))
        if not is_valid_username:
            return jsonify({'success': False, 'message': username_error}), 400
        data['username'] = normalized_username
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Validate password length
        if len(data['password']) < 8 or len(data['password']) > 30:
            return jsonify({'success': False, 'message': 'Password must be between 8 and 30 characters'}), 400
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            full_name=normalized_name['full_name'],
            role=data['role'],
            is_active=data.get('is_active', True)
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Get user ID before adding programs
        
        # Log activity
        log_create('user', user.id, user.username, {
            'email': user.email,
            'role': user.role,
            'full_name': user.full_name
        })
        
        # Handle department -> program assignments
        if data['role'] == 'dean' and data.get('department_ids'):
            _assign_user_programs_from_departments(user, data['department_ids'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating user: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """Update an existing user"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json() or {}
        
        # Prevent regular admins from editing super_admin users
        if user.role == 'super_admin' and not current_user.is_super_admin:
            return jsonify({'success': False, 'message': 'You do not have permission to edit this user'}), 403

        # Prevent self-modification of role or status if it would lock out the admin
        if user.id == current_user.id:
            if 'role' in data and data['role'] != user.role:
                return jsonify({'success': False, 'message': 'You cannot change your own role'}), 400
            if 'is_active' in data and not data['is_active']:
                return jsonify({'success': False, 'message': 'You cannot deactivate your own account'}), 400

        # Update username if provided and different
        if 'username' in data:
            proposed_username = User.normalize_username(data.get('username'))
            if proposed_username != user.username:
                is_valid_username, username_error, normalized_username = User.validate_username_format(proposed_username)
                if not is_valid_username:
                    return jsonify({'success': False, 'message': username_error}), 400

                if User.query.filter_by(username=normalized_username).first():
                    return jsonify({'success': False, 'message': 'Username already exists'}), 400

                user.username = normalized_username

        # Update email if provided and different
        if 'email' in data:
            proposed_email = (data.get('email') or '').strip()
            if proposed_email != user.email:
                if not proposed_email:
                    return jsonify({'success': False, 'message': 'Email is required'}), 400

                if User.query.filter_by(email=proposed_email).first():
                    return jsonify({'success': False, 'message': 'Email already exists'}), 400

                user.email = proposed_email

        # Update other fields
        if any(key in data for key in ('full_name', 'first_name', 'middle_initial', 'last_name')):
            is_valid_name, name_error, normalized_name = User.resolve_full_name_input(
                full_name=data.get('full_name'),
                first_name=data.get('first_name'),
                middle_initial=data.get('middle_initial'),
                last_name=data.get('last_name'),
            )
            if not is_valid_name:
                return jsonify({'success': False, 'message': name_error}), 400

            user.full_name = normalized_name['full_name']

        if 'role' in data and data['role'] in ['super_admin', 'admin', 'dean']:
            # Only super_admin can assign admin or super_admin roles
            if data['role'] in ['admin', 'super_admin'] and not current_user.is_super_admin:
                return jsonify({'success': False, 'message': 'Only Super Admins can assign Admin roles'}), 400
            user.role = data['role']

        if 'is_active' in data:
            user.is_active = data['is_active']

        # Existing-user passwords must be reset via the dedicated reset endpoint.
        if data.get('password'):
            return jsonify({
                'success': False,
                'message': 'Password cannot be edited here. Use Reset Password instead.'
            }), 400

        # Handle department -> program assignments
        if 'department_ids' in data:
            # Clear existing programs (lazy='dynamic' doesn't support list assignment)
            from app.models.user import user_programs as ud_table
            db.session.execute(ud_table.delete().where(ud_table.c.user_id == user.id))

            # Add all programs under selected departments (only for deans)
            if user.role == 'dean' and data['department_ids']:
                _assign_user_programs_from_departments(user, data['department_ids'])

        # Log activity
        log_edit('user', user.id, user.username, {
            'email': user.email,
            'role': user.role,
            'full_name': user.full_name
        })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating user: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Reset a user's password and require change on next login."""
    try:
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Use Account Security to change your own password'}), 400

        if user.role == 'super_admin' and not current_user.is_super_admin:
            return jsonify({'success': False, 'message': 'You do not have permission to reset this user password'}), 403

        if user.is_archived:
            return jsonify({'success': False, 'message': 'Cannot reset password for archived users'}), 400

        temporary_password = _generate_temporary_password()
        user.set_password(temporary_password)
        user.needs_password_change = True

        log_edit('user', user.id, user.username, {
            'action': 'password_reset',
            'reset_by': current_user.username
        })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Password reset successfully. Share the temporary password securely.',
            'credentials': {
                'username': user.username,
                'temporary_password': temporary_password
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error resetting password: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>/archive', methods=['POST'])
@login_required
@admin_required
def archive_user_post(user_id):
    """Archive a user (soft delete) via POST request"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'No reason provided')
        
        user = User.query.get_or_404(user_id)
        
        error_response = _archive_user_or_response_error(user, reason)
        if error_response:
            return error_response
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User archived successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error archiving user: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def archive_user(user_id):
    """Archive a user (soft delete) instead of hard delete"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'No reason provided')
        
        user = User.query.get_or_404(user_id)
        
        error_response = _archive_user_or_response_error(user, reason)
        if error_response:
            return error_response
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User archived successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error archiving user: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>/unarchive', methods=['POST'])
@login_required
@admin_required
def unarchive_user(user_id):
    """Restore a user from archive"""
    try:
        user = User.query.get_or_404(user_id)
        
        if not user.is_archived:
            return jsonify({'success': False, 'message': 'User is not archived'}), 400
        
        # Unarchive the user
        user.unarchive()
        
        # Log activity
        log_edit('user', user.id, user.username, {
            'action': 'unarchived',
            'restored_by': current_user.username
        })
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User restored successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error restoring user: {str(e)}'}), 500


@user_bp.route('/api/users/bulk-action', methods=['POST'])
@login_required
@admin_required
def bulk_action():
    """Perform bulk actions on multiple users (activate, deactivate, archive, unarchive)."""
    try:
        data = request.get_json()
        action = data.get('action')
        # Accept both 'user_ids' (legacy) and 'ids' (BatchSelect.js)
        user_ids = data.get('user_ids') or data.get('ids', [])
        reason = data.get('reason', 'Bulk action')
        
        if not action or not user_ids:
            return jsonify({'success': False, 'message': 'Action and user IDs are required'}), 400
        
        if action not in ['activate', 'deactivate', 'archive', 'unarchive']:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        # Remove current user from the list (can't modify self)
        user_ids = [uid for uid in user_ids if uid != current_user.id]
        
        if not user_ids:
            return jsonify({'success': False, 'message': 'No valid users selected'}), 400
        
        users = User.query.filter(User.id.in_(user_ids)).all()
        affected = 0
        
        for user in users:
            # Skip super_admin users if current user is not super_admin
            if user.role == 'super_admin' and not current_user.is_super_admin:
                continue
            
            # Skip last admin protection
            if user.role in ('admin', 'super_admin') and action in ['deactivate', 'archive']:
                admin_count = User.query.filter(User.role.in_(['admin', 'super_admin']), User.is_active == True, User.is_archived == False).count()
                if admin_count <= 1:
                    continue
            
            if action == 'activate':
                if not user.is_active and not user.is_archived:
                    user.is_active = True
                    affected += 1
            elif action == 'deactivate':
                if user.is_active and not user.is_archived:
                    user.is_active = False
                    affected += 1
            elif action == 'archive':
                if not user.is_archived:
                    user.archive(user_id=current_user.id, reason=reason)
                    affected += 1
            elif action == 'unarchive':
                if user.is_archived:
                    user.unarchive()
                    affected += 1
        
        if affected > 0:
            # Log bulk action
            log_edit('user', None, f'Bulk {action}', {
                'action': action,
                'affected_count': affected,
                'user_ids': user_ids
            })
            db.session.commit()
        
        action_past = {'activate': 'activated', 'deactivate': 'deactivated', 'archive': 'archived', 'unarchive': 'unarchived'}.get(action, f'{action}d')
        return jsonify({
            'success': True,
            'message': f'{affected} user(s) {action_past} successfully',
            'affected': affected
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error performing bulk action: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>/permanent-delete', methods=['POST'])
@login_required
@admin_required
def permanent_delete_user(user_id):
    """Permanently delete an archived user (super-admin only)."""
    try:
        if not current_user.is_super_admin:
            return jsonify({'success': False, 'message': 'Only Super Admins can permanently delete users'}), 403

        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'You cannot permanently delete your own account'}), 400

        if not user.is_archived:
            return jsonify({'success': False, 'message': 'Only archived users can be permanently deleted'}), 400

        log_delete('user', user.id, user.username, {
            'role': user.role,
            'email': user.email,
            'action': 'permanently_deleted',
            'deleted_by': current_user.username
        })

        db.session.delete(user)
        db.session.commit()

        return jsonify({'success': True, 'message': 'User permanently deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error permanently deleting user: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>/activity', methods=['GET'])
@login_required
@admin_required
def get_user_activity(user_id):
    """Get activity history for a specific user"""
    try:
        from app.models.activity_log import UserActivityLog
        
        user = User.query.get_or_404(user_id)
        
        # Get activity logs for this user, ordered by most recent
        activities = UserActivityLog.query.filter_by(user_id=user_id)\
            .order_by(UserActivityLog.created_at.desc())\
            .limit(50)\
            .all()
        
        activity_data = []
        for activity in activities:
            activity_data.append({
                'id': activity.id,
                'action': activity.action,
                'entity_type': activity.entity_type,
                'entity_id': activity.entity_id,
                'entity_name': activity.entity_name,
                'details': activity.details,
                'ip_address': activity.ip_address,
                'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M:%S') if activity.created_at else None,
                'created_at_iso': to_utc_iso_z(activity.created_at),
                'created_at_relative': _format_relative_time(activity.created_at)
            })
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name
            },
            'activities': activity_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching activity: {str(e)}'}), 500


@user_bp.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent self-deactivation
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'You cannot deactivate your own account'}), 400
        
        # Prevent regular admins from toggling super_admin users
        if user.role == 'super_admin' and not current_user.is_super_admin:
            return jsonify({'success': False, 'message': 'You do not have permission to modify this user'}), 403
        
        # Check if user is the last admin
        if user.role in ('admin', 'super_admin') and user.is_active:
            admin_count = User.query.filter(User.role.in_(['admin', 'super_admin']), User.is_active == True).count()
            if admin_count <= 1:
                return jsonify({'success': False, 'message': 'Cannot deactivate the last active admin account'}), 400
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'activated' if user.is_active else 'deactivated'
        return jsonify({
            'success': True,
            'message': f'User {status} successfully',
            'is_active': user.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error toggling user status: {str(e)}'}), 500


@user_bp.route('/api/users/quick-generate', methods=['POST'])
@login_required
@admin_required
def quick_generate_user():
    """
    Quick user generation - Creates a user with auto-generated username and default password
    Returns the credentials for distribution
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields (only role is required)
        role = data.get('role', 'dean')
        if role not in ['super_admin', 'admin', 'dean']:
            return jsonify({'success': False, 'message': 'Invalid role'}), 400
        
        # Only super_admin can quick-generate admin or super_admin users
        if role in ['admin', 'super_admin'] and not current_user.is_super_admin:
            return jsonify({'success': False, 'message': 'Only Super Admins can create Admin users'}), 400
        
        # Default password
        default_password = "ischedwise"
        next_number = _get_next_quick_user_number()

        for attempt in range(_QUICK_USER_RETRY_LIMIT):
            candidate_number = next_number + attempt
            new_username, auto_email, auto_full_name = _build_quick_user_identity(candidate_number)

            user = User(
                username=new_username,
                email=auto_email,
                full_name=auto_full_name,
                role=role,
                is_active=True
            )
            user.set_password(default_password)

            db.session.add(user)

            try:
                db.session.flush()  # Get user ID before adding programs

                # Log activity
                log_create('user', user.id, user.username, {
                    'email': user.email,
                    'role': user.role,
                    'full_name': user.full_name,
                    'type': 'quick_generated'
                })

                # Handle department -> program assignments for deans
                if role == 'dean' and data.get('department_ids'):
                    _assign_user_programs_from_departments(user, data['department_ids'])

                db.session.commit()
                break
            except IntegrityError as exc:
                db.session.rollback()
                if _is_user_identity_conflict(exc):
                    continue
                raise
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to generate a unique user account. Please try again.'
            }), 500
        
        # Get department names for display
        user_departments = {}
        for dept in user.programs:
            if dept.department_id and dept.department:
                user_departments[dept.department_id] = dept.department.department_name
        department_names = list(user_departments.values())
        
        return jsonify({
            'success': True,
            'message': 'User account generated successfully',
            'credentials': {
                'username': new_username,
                'password': default_password,
                'email': auto_email,
                'full_name': auto_full_name,
                'role': role,
                'program_names': ', '.join(department_names) if department_names else 'None'
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error generating user: {str(e)}'}), 500


# ============================================================================
# EXPORT ROUTES
# ============================================================================

@user_bp.route('/export/<format>')
@login_required
@admin_required
def export_users(format):
    """
    Export users list to Excel or PDF
    
    Query parameters:
    - include_archived: 'true' to include archived users (default: false)
    - status: 'active', 'inactive', 'archived', or 'all' (default: 'all')
    - role: 'admin', 'dean', or empty for all
    """
    from flask import send_file
    from app.services.export_service import export_users_excel, export_users_pdf
    
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    status_filter = request.args.get('status', 'all')
    role_filter = request.args.get('role', '')
    
    # Build query
    query = User.query
    
    # Apply status filter
    if status_filter == 'active':
        query = query.filter(User.is_active == True, User.is_archived == False)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False, User.is_archived == False)
    elif status_filter == 'archived':
        query = query.filter(User.is_archived == True)
    elif not include_archived:
        query = query.filter(User.is_archived == False)
    
    # Apply role filter
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    # Get users
    users = query.order_by(User.full_name).all()
    
    if format == 'excel':
        output, filename = export_users_excel(users, include_archived=include_archived)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif format == 'pdf':
        output, filename = export_users_pdf(users, include_archived=include_archived)
        mimetype = 'application/pdf'
    else:
        return jsonify({'success': False, 'message': 'Invalid format. Use "excel" or "pdf".'}), 400
    
    return send_file(
        output,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )
