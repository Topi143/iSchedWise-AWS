"""
Activity Logging Helper Functions
Provides convenient functions to log user activities across the application
"""
from flask import request
from flask_login import current_user
from app.models.activity_log import UserActivityLog
from app.extensions import db


def log_activity(action, entity_type, entity_id=None, entity_name=None, details=None):
    """
    Log a user activity with automatic context extraction
    
    Args:
        action: Action performed (e.g., 'created', 'edited', 'deleted', 'archived')
        entity_type: Type of entity (e.g., 'schedule', 'faculty', 'building')
        entity_id: ID of the affected entity (optional)
        entity_name: Name/description of the entity (optional)
        details: Additional details about the action (optional, can be dict or string)
    
    Returns:
        UserActivityLog instance
    """
    # Convert details dict to readable string if needed
    if isinstance(details, dict) and details:
        detail_parts = []
        for key, value in details.items():
            if value is not None and value != '':
                # Format the key to be more readable
                readable_key = key.replace('_', ' ').title()
                detail_parts.append(f"{readable_key}: {value}")
        details = " | ".join(detail_parts) if detail_parts else None
    
    return UserActivityLog.log_action(
        user_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )


def log_create(entity_type, entity_id, entity_name, details=None):
    """Log entity creation"""
    return log_activity('created', entity_type, entity_id, entity_name, details)


def log_edit(entity_type, entity_id, entity_name, details=None):
    """Log entity editing"""
    return log_activity('edited', entity_type, entity_id, entity_name, details)


def log_delete(entity_type, entity_id, entity_name, details=None):
    """Log entity deletion"""
    return log_activity('deleted', entity_type, entity_id, entity_name, details)


def log_archive(entity_type, entity_id, entity_name, details=None):
    """Log entity archiving"""
    return log_activity('archived', entity_type, entity_id, entity_name, details)


def log_unarchive(entity_type, entity_id, entity_name, details=None):
    """Log entity unarchiving"""
    return log_activity('unarchived', entity_type, entity_id, entity_name, details)


def log_export(entity_type, export_format, details=None):
    """Log data export"""
    return log_activity('exported', entity_type, None, export_format, details)


def log_import(entity_type, import_source, details=None):
    """Log data import"""
    return log_activity('imported', entity_type, None, import_source, details)


def log_login():
    """Log user login"""
    return log_activity(
        'login',
        'user',
        current_user.id,
        current_user.full_name,
        f'User logged in from {request.remote_addr}'
    )


def log_logout():
    """Log user logout"""
    return log_activity(
        'logout',
        'user',
        current_user.id,
        current_user.full_name,
        f'User logged out from {request.remote_addr}'
    )


def log_password_change(user_id, user_name):
    """Log password change"""
    return log_activity(
        'password_changed',
        'user',
        user_id,
        user_name,
        'User changed their password'
    )


def log_settings_change(setting_name, details=None):
    """Log settings changes"""
    return log_activity(
        'settings_changed',
        'settings',
        None,
        setting_name,
        details
    )
