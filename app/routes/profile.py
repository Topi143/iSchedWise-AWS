"""
User Profile Management Routes
Allows users to view and edit their own profile
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.utils.activity_logger import log_edit, log_password_change

profile_bp = Blueprint('profile', __name__, url_prefix='/account')


@profile_bp.route('/')
@login_required
def index():
    """Display current user's profile"""
    return render_template('profile.html', user=current_user)


@profile_bp.route('/update', methods=['POST'])
@login_required
def update_profile():
    """Update current user's profile information"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('full_name'):
            return jsonify({'success': False, 'message': 'Full name is required'}), 400
        
        if not data.get('email'):
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if email is already used by another user
        if data['email'] != current_user.email:
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user:
                return jsonify({'success': False, 'message': 'Email already in use'}), 400
        
        # Check if username is already used by another user
        if data.get('username') and data['username'] != current_user.username:
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user:
                return jsonify({'success': False, 'message': 'Username already in use'}), 400
        
        # Track changes for activity log
        changes = {}
        if data['full_name'] != current_user.full_name:
            changes['full_name'] = f"{current_user.full_name} → {data['full_name']}"
        if data['email'] != current_user.email:
            changes['email'] = f"{current_user.email} → {data['email']}"
        if data.get('username') and data['username'] != current_user.username:
            changes['username'] = f"{current_user.username} → {data['username']}"
        
        # Update profile information
        current_user.full_name = data['full_name']
        current_user.email = data['email']
        
        if data.get('username'):
            current_user.username = data['username']
        
        db.session.commit()
        
        # Log the profile update with detailed changes
        if changes:
            log_edit('user_profile', current_user.id, current_user.username, changes)
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'full_name': current_user.full_name,
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
        if len(data['new_password']) < 6:
            return jsonify({'success': False, 'message': 'New password must be at least 6 characters'}), 400
        
        if data['new_password'] != data['confirm_password']:
            return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
        
        # Update password
        current_user.password_hash = generate_password_hash(data['new_password'])
        db.session.commit()
        
        # Log password change
        log_password_change(current_user.id, current_user.username)
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error changing password: {str(e)}'}), 500
