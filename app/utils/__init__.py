"""
Utilities package - Helper functions and logging
"""


def log_create(*args, **kwargs):
    from app.utils.activity_logger import log_create as _log_create
    return _log_create(*args, **kwargs)


def log_edit(*args, **kwargs):
    from app.utils.activity_logger import log_edit as _log_edit
    return _log_edit(*args, **kwargs)


def log_delete(*args, **kwargs):
    from app.utils.activity_logger import log_delete as _log_delete
    return _log_delete(*args, **kwargs)


def log_archive(*args, **kwargs):
    from app.utils.activity_logger import log_archive as _log_archive
    return _log_archive(*args, **kwargs)


def log_unarchive(*args, **kwargs):
    from app.utils.activity_logger import log_unarchive as _log_unarchive
    return _log_unarchive(*args, **kwargs)


def log_activity(*args, **kwargs):
    from app.utils.activity_logger import log_activity as _log_activity
    return _log_activity(*args, **kwargs)

__all__ = [
    'log_create',
    'log_edit',
    'log_delete',
    'log_archive',
    'log_unarchive',
    'log_activity',
]
