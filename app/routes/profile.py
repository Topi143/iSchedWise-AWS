"""
User Profile Management Routes
Allows users to view and edit their own profile
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from app.utils.activity_logger import log_edit, log_password_change
import os

profile_bp = Blueprint('profile', __name__, url_prefix='/account')

# Configuration for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


@profile_bp.route('/update-department', methods=['POST'])
@login_required
def update_department():
    """Update department information (for users assigned to a single department)"""
    try:
        data = request.get_json()
        
        # Get the department ID to update
        department_id = data.get('department_id')
        if not department_id:
            return jsonify({'success': False, 'message': 'Department ID is required'}), 400
        
        # Get the department
        department = Department.query.get(int(department_id))
        if not department:
            return jsonify({'success': False, 'message': 'Department not found'}), 400
        
        # Check if user has access to this department
        user_department_ids = current_user.get_department_ids()
        if user_department_ids is not None:  # Dean user
            if department.id not in user_department_ids:
                return jsonify({'success': False, 'message': 'You do not have access to this department'}), 403
        # Admin can update any department
        
        # Track changes
        changes = {}
        
        # Update full department name
        if 'full_department_name' in data:
            full_name = data['full_department_name'].strip() or None
            if department.full_department_name != full_name:
                changes['full_department_name'] = f"{department.full_department_name or 'None'} → {full_name or 'None'}"
                department.full_department_name = full_name
        
        # Update secretary name
        if 'secretary_name' in data:
            secretary = data['secretary_name'].strip() or None
            if department.secretary_name != secretary:
                changes['secretary_name'] = f"{department.secretary_name or 'None'} → {secretary or 'None'}"
                department.secretary_name = secretary
        
        # Note: Logo upload would need file handling - placeholder for now
        
        db.session.commit()
        
        # Log the department update
        if changes:
            log_edit('department_info', department.id, department.department_code, changes)
        
        return jsonify({
            'success': True,
            'message': 'Department information updated successfully',
            'department': {
                'id': department.id,
                'full_name': department.full_department_name,
                'secretary_name': department.secretary_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating department: {str(e)}'}), 500


@profile_bp.route('/upload-department-logo', methods=['POST'])
@login_required
def upload_department_logo():
    """Upload department logo"""
    try:
        # Check if file was uploaded
        if 'logo' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['logo']
        
        # Check if filename is empty
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Get department ID from form data
        department_id = request.form.get('department_id')
        if not department_id:
            return jsonify({'success': False, 'message': 'Department ID is required'}), 400
        
        # Get the department
        department = Department.query.get(int(department_id))
        if not department:
            return jsonify({'success': False, 'message': 'Department not found'}), 404
        
        # Check if user has access to this department
        user_department_ids = current_user.get_department_ids()
        if user_department_ids is not None:  # Dean user
            if department.id not in user_department_ids:
                return jsonify({'success': False, 'message': 'You do not have access to this department'}), 403
        # Admin can update any department
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, SVG'}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'message': f'File too large. Maximum size: 5MB'}), 400
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        filename = f"dept_{department.department_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        
        # Create upload directory if it doesn't exist
        from flask import current_app
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'department_logos')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Delete old logo file if exists
        if department.department_logo:
            old_logo_path = os.path.join(current_app.root_path, 'static', department.department_logo.lstrip('/'))
            if os.path.exists(old_logo_path):
                try:
                    os.remove(old_logo_path)
                except Exception as e:
                    print(f"Warning: Could not delete old logo: {str(e)}")
        
        # Update database with relative path
        logo_url = f"/static/uploads/department_logos/{filename}"
        department.department_logo = logo_url
        
        db.session.commit()
        
        # Log the logo upload
        log_edit('department_info', department.id, department.department_code, {
            'department_logo': f"Logo uploaded: {filename}"
        })
        
        return jsonify({
            'success': True,
            'message': 'Logo uploaded successfully',
            'logo_url': logo_url
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error uploading logo: {str(e)}'}), 500


@profile_bp.route('/remove-department-logo', methods=['POST'])
@login_required
def remove_department_logo():
    """Remove department logo"""
    try:
        data = request.get_json()
        
        # Get department ID
        department_id = data.get('department_id')
        if not department_id:
            return jsonify({'success': False, 'message': 'Department ID is required'}), 400
        
        # Get the department
        department = Department.query.get(int(department_id))
        if not department:
            return jsonify({'success': False, 'message': 'Department not found'}), 404
        
        # Check if user has access to this department
        user_department_ids = current_user.get_department_ids()
        if user_department_ids is not None:  # Dean user
            if department.id not in user_department_ids:
                return jsonify({'success': False, 'message': 'You do not have access to this department'}), 403
        # Admin can update any department
        
        # Delete logo file if exists
        if department.department_logo:
            from flask import current_app
            logo_path = os.path.join(current_app.root_path, 'static', department.department_logo.lstrip('/'))
            if os.path.exists(logo_path):
                try:
                    os.remove(logo_path)
                except Exception as e:
                    print(f"Warning: Could not delete logo file: {str(e)}")
            
            # Clear logo from database
            department.department_logo = None
            db.session.commit()
            
            # Log the logo removal
            log_edit('department_info', department.id, department.department_code, {
                'department_logo': 'Logo removed'
            })
            
            return jsonify({
                'success': True,
                'message': 'Logo removed successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'No logo to remove'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error removing logo: {str(e)}'}), 500
