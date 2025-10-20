"""
Role-based access control decorators and helper functions
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """
    Decorator to require specific user roles for route access.
    
    Usage:
        @role_required('admin')
        @role_required('admin', 'dean')
    
    Args:
        *roles: Variable length argument list of allowed roles
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator to require admin role for route access.
    
    Usage:
        @admin_required
        def admin_only_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin:
            flash('This page is only accessible to administrators.', 'error')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def dean_required(f):
    """
    Decorator to require dean role for route access.
    
    Usage:
        @dean_required
        def dean_only_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_dean:
            flash('This page is only accessible to deans.', 'error')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def get_department_filter():
    """
    Get department filter based on current user's role.
    
    Returns:
        dict: Empty dict for admin (see all), {'department_id': id} for dean
    
    Usage:
        filter_params = get_department_filter()
        faculties = Faculty.query.filter_by(**filter_params).all()
    """
    if current_user.is_admin:
        # Admin sees everything
        return {}
    elif current_user.is_dean and current_user.department_id:
        # Dean sees only their department
        return {'department_id': current_user.department_id}
    else:
        # No department assigned, see nothing
        return {'department_id': -1}


def apply_department_filter(query):
    """
    Apply department filter to a SQLAlchemy query based on user role.
    
    Args:
        query: SQLAlchemy query object
    
    Returns:
        Filtered query object
    
    Usage:
        query = Faculty.query
        query = apply_department_filter(query)
        faculties = query.all()
    """
    if current_user.is_dean and current_user.department_id:
        # Filter by dean's department
        return query.filter_by(department_id=current_user.department_id)
    
    # Admin or no filter needed
    return query


def can_access_department(department_id):
    """
    Check if current user can access a specific department.
    
    Args:
        department_id: ID of the department to check
    
    Returns:
        bool: True if user can access, False otherwise
    
    Usage:
        if can_access_department(faculty.department_id):
            # Allow access
        else:
            flash('Access denied', 'error')
            abort(403)
    """
    if current_user.is_admin:
        # Admin can access all departments
        return True
    
    if current_user.is_dean:
        # Dean can only access their own department
        return current_user.department_id == department_id
    
    return False


def check_department_access(department_id):
    """
    Check department access and abort with 403 if denied.
    
    Args:
        department_id: ID of the department to check
    
    Raises:
        403 error if access is denied
    
    Usage:
        check_department_access(faculty.department_id)
        # Continues if allowed, aborts if not
    """
    if not can_access_department(department_id):
        flash('You do not have permission to access this department.', 'error')
        abort(403)
