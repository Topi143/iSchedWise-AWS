"""
User Management Routes
Handles CRUD operations for user accounts (Admin and Dean)
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.department import Department
from app.utils.activity_logger import log_create, log_edit, log_delete
from functools import wraps
from datetime import datetime

user_bp = Blueprint('user', __name__, url_prefix='/users')


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@user_bp.route('/')
@login_required
@admin_required
def index():
    """Display all users"""
    users = User.query.order_by(User.created_at.desc()).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    return render_template('users.html', users=users, departments=departments)


@user_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """Get all users as JSON (excluding current user)"""
    # Exclude the current logged-in user from the list
    users = User.query.filter(User.id != current_user.id).order_by(User.created_at.desc()).all()
    
    users_data = []
    for user in users:
        # Get all departments for this user
        department_ids = [dept.id for dept in user.departments]
        department_names = [dept.department_name for dept in user.departments]
        
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'department_ids': department_ids,
            'department_names': ', '.join(department_names) if department_names else '-',
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
        })
    
    return jsonify({'users': users_data})


@user_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    """Get a single user by ID"""
    user = User.query.get_or_404(user_id)
    
    # Get all departments for this user
    department_ids = [dept.id for dept in user.departments]
    department_names = [dept.department_name for dept in user.departments]
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role,
        'department_ids': department_ids,
        'department_names': ', '.join(department_names) if department_names else '-',
        'is_active': user.is_active,
        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
    })


@user_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'full_name', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field.replace("_", " ").title()} is required'}), 400
        
        # Validate role
        if data['role'] not in ['admin', 'dean']:
            return jsonify({'success': False, 'message': 'Role must be either admin or dean'}), 400
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            full_name=data['full_name'],
            role=data['role'],
            is_active=data.get('is_active', True)
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Get user ID before adding departments
        
        # Log activity
        log_create('user', user.id, user.username, {
            'email': user.email,
            'role': user.role,
            'full_name': user.full_name
        })
        
        # Handle department assignments
        if data['role'] == 'dean' and data.get('department_ids'):
            department_ids = data['department_ids']
            if not isinstance(department_ids, list):
                department_ids = [department_ids]
            
            for dept_id in department_ids:
                department = Department.query.get(dept_id)
                if department:
                    user.departments.append(department)
        
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
        data = request.get_json()
        
        # Prevent self-modification of role or status if it would lock out the admin
        if user.id == current_user.id:
            if 'role' in data and data['role'] != user.role:
                return jsonify({'success': False, 'message': 'You cannot change your own role'}), 400
            if 'is_active' in data and not data['is_active']:
                return jsonify({'success': False, 'message': 'You cannot deactivate your own account'}), 400
        
        # Update username if provided and different
        if 'username' in data and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'success': False, 'message': 'Username already exists'}), 400
            user.username = data['username']
        
        # Update email if provided and different
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'success': False, 'message': 'Email already exists'}), 400
            user.email = data['email']
        
        # Update other fields
        if 'full_name' in data:
            user.full_name = data['full_name']
        
        if 'role' in data and data['role'] in ['admin', 'dean']:
            user.role = data['role']
        
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        # Update password if provided
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        # Handle department assignments
        if 'department_ids' in data:
            # Clear existing departments
            user.departments = []
            
            # Add new departments (only for deans)
            if user.role == 'dean' and data['department_ids']:
                department_ids = data['department_ids']
                if not isinstance(department_ids, list):
                    department_ids = [department_ids]
                
                for dept_id in department_ids:
                    department = Department.query.get(dept_id)
                    if department:
                        user.departments.append(department)
        
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


@user_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent self-deletion
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'You cannot delete your own account'}), 400
        
        # Check if user is the last admin
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin', is_active=True).count()
            if admin_count <= 1:
                return jsonify({'success': False, 'message': 'Cannot delete the last active admin account'}), 400
        
        username = user.username
        
        # Log activity before deletion
        log_delete('user', user.id, username, {'role': user.role, 'email': user.email})
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting user: {str(e)}'}), 500


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
        
        # Check if user is the last admin
        if user.role == 'admin' and user.is_active:
            admin_count = User.query.filter_by(role='admin', is_active=True).count()
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
