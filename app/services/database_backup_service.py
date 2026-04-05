"""
Database backup service.

Centralizes backup creation/list/delete and automatic backup settings so
manual and scheduled backups use the same implementation.
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from flask import current_app

from app.extensions import db
from app.models import SystemConfig, User, UserActivityLog


class BackupError(Exception):
    """Raised when backup operations fail in a user-facing way."""


class DatabaseBackupService:
    """Service methods for SQL backup management and auto-backup settings."""

    BACKUP_PREFIX = 'ischedwise_backup_'
    BACKUP_SUFFIX = '.sql'
    DEFAULT_RETENTION_COUNT = 30
    AUTO_BACKUP_TIMEZONE = 'Asia/Manila'
    AUTO_BACKUP_LAST_SUCCESS_KEY = 'auto_backup_last_success_at'
    _DUMMY_BACKUP_CONTENT = '-- dummy backup'

    @classmethod
    def _resolve_timezone_name(cls) -> str:
        """Get the timezone used by schedule labels."""
        return cls.AUTO_BACKUP_TIMEZONE

    @classmethod
    def _build_schedule_label(cls) -> str:
        """Build the human-readable auto-backup schedule label."""
        return f'Daily at 12:00 AM ({cls._resolve_timezone_name()})'

    @classmethod
    def _build_backup_filename(cls) -> str:
        """Create a collision-safe backup filename."""
        backups_dir = cls.get_backups_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f'{cls.BACKUP_PREFIX}{timestamp}'
        filename = f'{base_name}{cls.BACKUP_SUFFIX}'
        counter = 1

        while (backups_dir / filename).exists():
            filename = f'{base_name}_{counter}{cls.BACKUP_SUFFIX}'
            counter += 1

        return filename

    @classmethod
    def get_backups_dir(cls) -> Path:
        """Return backup directory path and ensure it exists."""
        backups_dir = (Path(current_app.root_path).parent / 'backups').resolve()
        backups_dir.mkdir(parents=True, exist_ok=True)
        return backups_dir

    @classmethod
    def _resolve_actor_user_id(cls, user_id: int | None = None) -> int | None:
        """Resolve an actor for activity logging when no user id is provided."""
        if user_id:
            return user_id
        super_admin = User.query.filter_by(role='super_admin', is_archived=False).order_by(User.id.asc()).first()
        return super_admin.id if super_admin else None

    @classmethod
    def _log_system_activity(cls, action: str, details: str, user_id: int | None = None) -> None:
        """Write a system activity log entry when a valid actor is available."""
        actor_user_id = cls._resolve_actor_user_id(user_id)
        if not actor_user_id:
            return

        UserActivityLog.log_action(
            user_id=actor_user_id,
            action=action,
            entity_type='system',
            entity_name='database_backup',
            details=details,
        )
        db.session.commit()

    @classmethod
    def create_backup(cls, source: str = 'manual', initiated_by_user_id: int | None = None) -> dict[str, Any]:
        """Create a mysqldump SQL backup file and return backup metadata."""
        backups_dir = cls.get_backups_dir()
        filename = cls._build_backup_filename()
        filepath = backups_dir / filename

        db_url = db.engine.url
        host = db_url.host or 'localhost'
        port = db_url.port or 3306
        user = db_url.username or 'root'
        password = db_url.password or ''
        database = db_url.database

        mysqldump_path = shutil.which('mysqldump') or r'C:\xampp\mysql\bin\mysqldump.exe'
        if not mysqldump_path or not Path(mysqldump_path).exists():
            raise BackupError('mysqldump not found. Install MySQL client tools and ensure mysqldump is in PATH.')

        if not database:
            raise BackupError('Database name is missing from the current SQLAlchemy connection URL.')

        cmd = [
            mysqldump_path,
            f'--host={host}',
            f'--port={port}',
            f'--user={user}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--add-drop-table',
            database,
        ]
        if password:
            cmd.insert(4, f'--password={password}')

        try:
            with filepath.open('w', encoding='utf-8') as output_file:
                result = subprocess.run(cmd, stdout=output_file, stderr=subprocess.PIPE, timeout=120)
        except subprocess.TimeoutExpired as exc:
            if filepath.exists():
                filepath.unlink(missing_ok=True)
            raise BackupError('Backup timed out after 120 seconds') from exc
        except FileNotFoundError as exc:
            if filepath.exists():
                filepath.unlink(missing_ok=True)
            raise BackupError('mysqldump not found. Make sure MySQL client tools are installed and in your PATH.') from exc

        if result.returncode != 0:
            if filepath.exists():
                filepath.unlink(missing_ok=True)
            error_msg = result.stderr.decode('utf-8', errors='replace').strip()
            raise BackupError(f'mysqldump failed: {error_msg}')

        file_size = filepath.stat().st_size
        cls._log_system_activity(
            action='database_backup',
            details=f'Created {source} backup: {filename} ({file_size / 1024:.1f} KB)',
            user_id=initiated_by_user_id,
        )

        return {
            'filename': filename,
            'size': file_size,
            'created_at': datetime.now().isoformat(),
        }

    @classmethod
    def list_backups(cls) -> list[dict[str, Any]]:
        """List SQL backups in descending filename order."""
        backups_dir = cls.get_backups_dir()
        backups: list[dict[str, Any]] = []

        cls.cleanup_known_dummy_backups()

        for entry in sorted(backups_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if entry.is_file() and entry.suffix.lower() == '.sql' and cls._is_valid_backup_file(entry):
                stat = entry.stat()
                backups.append({
                    'filename': entry.name,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        return backups

    @classmethod
    def validate_backup_filename(cls, filename: str) -> None:
        """Validate file name to prevent traversal and invalid paths."""
        if not filename:
            raise BackupError('Invalid filename')
        if '..' in filename or '/' in filename or '\\' in filename:
            raise BackupError('Invalid filename')
        if not filename.lower().endswith(cls.BACKUP_SUFFIX):
            raise BackupError('Invalid backup file type')
        if not filename.startswith(cls.BACKUP_PREFIX):
            raise BackupError('Invalid backup filename')

    @classmethod
    def get_backup_path(cls, filename: str) -> Path:
        """Resolve and validate a specific backup path."""
        decoded_filename = unquote(filename)
        cls.validate_backup_filename(decoded_filename)
        return cls.get_backups_dir() / decoded_filename

    @classmethod
    def delete_backup(cls, filename: str, initiated_by_user_id: int | None = None, source: str = 'manual') -> None:
        """Delete one backup file and write activity log."""
        filepath = cls.get_backup_path(filename)
        if not filepath.exists():
            raise BackupError('Backup not found')

        filepath.unlink()
        cls._log_system_activity(
            action='delete_backup',
            details=f'Deleted {source} backup: {filename}',
            user_id=initiated_by_user_id,
        )

    @classmethod
    def _is_valid_backup_file(cls, path: Path) -> bool:
        """Return True when a backup file should be visible in the backups list."""
        if not path.name.startswith(cls.BACKUP_PREFIX):
            return False
        if path.name.lower().endswith(cls.BACKUP_SUFFIX) is False:
            return False
        if path.stat().st_size == 0:
            return False
        if cls._is_dummy_backup_file(path):
            return False
        return True

    @classmethod
    def _is_dummy_backup_file(cls, path: Path) -> bool:
        """Detect known test-generated dummy backup placeholders."""
        try:
            if path.stat().st_size > 128:
                return False
            content = path.read_text(encoding='utf-8').strip()
            return content == cls._DUMMY_BACKUP_CONTENT
        except (UnicodeDecodeError, OSError):
            return False

    @classmethod
    def cleanup_known_dummy_backups(cls) -> list[str]:
        """Delete known dummy placeholder backups and return deleted filenames."""
        deleted: list[str] = []
        for entry in cls.get_backups_dir().glob(f'*{cls.BACKUP_SUFFIX}'):
            if not entry.is_file():
                continue
            if cls._is_dummy_backup_file(entry):
                entry.unlink(missing_ok=True)
                deleted.append(entry.name)
        return deleted

    @classmethod
    def get_auto_backup_settings(cls) -> dict[str, Any]:
        """Get automatic backup settings from SystemConfig."""
        enabled = bool(SystemConfig.get('auto_backup_enabled', False))
        retention = SystemConfig.get('auto_backup_retention_count', cls.DEFAULT_RETENTION_COUNT)

        try:
            retention_count = int(retention)
        except (TypeError, ValueError):
            retention_count = cls.DEFAULT_RETENTION_COUNT

        retention_count = max(1, min(365, retention_count))

        return {
            'enabled': enabled,
            'retention_count': retention_count,
            'schedule_label': cls._build_schedule_label(),
            'hour': 0,
            'minute': 0,
        }

    @classmethod
    def update_auto_backup_settings(cls, enabled: bool, retention_count: int, user_id: int | None = None) -> dict[str, Any]:
        """Persist automatic backup settings in SystemConfig."""
        retention_count = max(1, min(365, int(retention_count)))

        SystemConfig.set('auto_backup_enabled', bool(enabled), user_id=user_id)
        SystemConfig.set('auto_backup_retention_count', retention_count, user_id=user_id)
        db.session.commit()

        cls._log_system_activity(
            action='auto_backup_settings_updated',
            details=f'Auto backup: enabled={bool(enabled)}, retention_count={retention_count}',
            user_id=user_id,
        )

        return cls.get_auto_backup_settings()

    @classmethod
    def enforce_retention(
        cls,
        retention_count: int,
        initiated_by_user_id: int | None = None,
        source: str = 'auto',
    ) -> list[str]:
        """Delete oldest backups beyond retention count and return deleted names."""
        retention_count = max(1, int(retention_count))
        backups = cls.list_backups()

        deleted_files: list[str] = []
        for backup in backups[retention_count:]:
            filename = backup['filename']
            try:
                filepath = cls.get_backup_path(filename)
                if filepath.exists():
                    filepath.unlink()
                    deleted_files.append(filename)
            except Exception:
                continue

        if deleted_files:
            cls._log_system_activity(
                action='backup_retention_cleanup',
                details=f'Retention cleanup ({source}): removed {len(deleted_files)} backup(s)',
                user_id=initiated_by_user_id,
            )

        return deleted_files

    @classmethod
    def get_last_auto_backup_success_at(cls) -> datetime | None:
        """Return the last successful auto-backup timestamp in UTC."""
        value = SystemConfig.get(cls.AUTO_BACKUP_LAST_SUCCESS_KEY)
        if not isinstance(value, str) or not value.strip():
            return None

        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @classmethod
    def has_auto_backup_for_local_date(cls, local_date, tz_name: str | None = None) -> bool:
        """Return whether a successful auto-backup already exists for a local calendar date."""
        last_success = cls.get_last_auto_backup_success_at()
        if not last_success:
            return False

        tz = ZoneInfo(tz_name or cls.AUTO_BACKUP_TIMEZONE)
        return last_success.astimezone(tz).date() == local_date

    @classmethod
    def mark_auto_backup_success(cls, when_utc: datetime | None = None) -> None:
        """Persist the timestamp of the latest successful automatic backup."""
        effective_when = when_utc or datetime.now(timezone.utc)
        if effective_when.tzinfo is None:
            effective_when = effective_when.replace(tzinfo=timezone.utc)

        SystemConfig.set(cls.AUTO_BACKUP_LAST_SUCCESS_KEY, effective_when.astimezone(timezone.utc).isoformat())
        db.session.commit()
