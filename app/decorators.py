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


def super_admin_required(f):
    """
    Decorator to require super_admin role for route access.
    
    Usage:
        @super_admin_required
        def super_admin_only_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_super_admin:
            flash('This page is only accessible to super administrators.', 'error')
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


def setup_required(f):
    """
    Decorator to require that quick-generated users complete their account setup.
    Redirects temporary/quick-generated users to the first-login setup page
    if they haven't completed their account configuration.
    
    Usage:
        @login_required
        @setup_required
        def protected_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user needs to complete first-login setup
        if current_user.needs_first_login_setup():
            flash('Please complete your account setup before continuing.', 'info')
            return redirect(url_for('auth.first_login_setup'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_program_filter():
    """
    Get program filter based on current user's role.
    
    Returns:
        dict: Empty dict for admin (see all), {'program_id': id} for dean
    
    Usage:
        filter_params = get_program_filter()
        faculties = Faculty.query.filter_by(**filter_params).all()
    """
    if current_user.is_admin:
        # Admin sees everything
        return {}
    elif current_user.is_dean and current_user.program_id:
        # Dean sees only their program
        return {'program_id': current_user.program_id}
    else:
        # No program assigned, see nothing
        return {'program_id': -1}


def get_department_filter():
    """
    Get department filter based on current user's role.
    Derives department IDs from the user's assigned programs.
    
    Returns:
        dict: Empty dict for admin (see all), {'department_id': id} for dean
    """
    if current_user.is_admin:
        return {}
    department_ids = current_user.get_department_ids()
    if department_ids:
        # Return the first department (most deans have one)
        return {'department_id': department_ids[0]}
    return {'department_id': -1}


def apply_program_filter(query):
    """
    Apply program filter to a SQLAlchemy query based on user role.
    
    Args:
        query: SQLAlchemy query object
    
    Returns:
        Filtered query object
    
    Usage:
        query = Faculty.query
        query = apply_program_filter(query)
        faculties = query.all()
    """
    if current_user.is_dean and current_user.program_id:
        # Filter by dean's program
        return query.filter_by(program_id=current_user.program_id)
    
    # Admin or no filter needed
    return query


def apply_department_filter(query):
    """
    Apply department filter to a SQLAlchemy query based on user role.
    Derives department IDs from the user's assigned programs.
    
    Args:
        query: SQLAlchemy query object (must have department_id column)
    
    Returns:
        Filtered query object
    """
    if current_user.is_dean:
        department_ids = current_user.get_department_ids()
        if department_ids:
            return query.filter(query.column_descriptions[0]['type'].department_id.in_(department_ids))
        return query.filter_by(department_id=-1)  # No access
    return query


def can_access_program(program_id):
    """
    Check if current user can access a specific program.
    
    Args:
        program_id: ID of the program to check
    
    Returns:
        bool: True if user can access, False otherwise
    """
    if current_user.is_admin:
        return True
    
    if current_user.is_dean:
        return current_user.program_id == program_id
    
    return False


def can_access_department(department_id):
    """
    Check if current user can access a specific department.
    Derives accessible department IDs from the user's assigned programs.
    
    Args:
        department_id: ID of the department to check
    
    Returns:
        bool: True if user can access, False otherwise
    """
    if current_user.is_admin:
        return True
    
    if not department_id:
        return True  # Allow access to records without department
    
    if current_user.is_dean:
        department_ids = current_user.get_department_ids()
        return department_id in department_ids
    
    return False


def check_program_access(program_id):
    """
    Check program access and abort with 403 if denied.
    """
    if not can_access_program(program_id):
        flash('You do not have permission to access this program.', 'error')
        abort(403)


def check_department_access(department_id):
    """
    Check department access and abort with 403 if denied.
    """
    if not can_access_department(department_id):
        flash('You do not have permission to access this department.', 'error')
        abort(403)
