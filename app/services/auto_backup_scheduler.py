"""Automatic database backup scheduler setup."""
from __future__ import annotations

import atexit
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.database_backup_service import BackupError, DatabaseBackupService

_scheduler: Optional[BackgroundScheduler] = None
AUTO_BACKUP_LOCK_PREFIX = '.auto_backup_lock_'
AUTO_BACKUP_LOCK_SUFFIX = '.lock'
AUTO_BACKUP_LOCK_STALE_SECONDS = 6 * 60 * 60
AUTO_BACKUP_STARTUP_CATCHUP_WINDOW_MINUTES = 90


def _build_auto_backup_daily_lock_path(local_date) -> Path:
    """Return the date-scoped lock file path for automatic backups."""
    backups_dir = DatabaseBackupService.get_backups_dir()
    return backups_dir / f'{AUTO_BACKUP_LOCK_PREFIX}{local_date.strftime("%Y%m%d")}{AUTO_BACKUP_LOCK_SUFFIX}'


def _is_auto_backup_lock_stale(lock_path: Path, now_utc: datetime) -> bool:
    """Return True when an existing lock file is older than the stale threshold."""
    try:
        lock_mtime = datetime.fromtimestamp(lock_path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return False

    return (now_utc - lock_mtime).total_seconds() > AUTO_BACKUP_LOCK_STALE_SECONDS


def _acquire_auto_backup_daily_lock(local_date, app, trigger: str, now_utc: datetime) -> Path | None:
    """Acquire a date-scoped lock file to prevent duplicate automatic backups."""
    lock_path = _build_auto_backup_daily_lock_path(local_date)

    for attempt in range(2):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as lock_file:
                lock_file.write(f'trigger={trigger}\n')
                lock_file.write(f'created_at_utc={now_utc.isoformat()}\n')
            return lock_path
        except FileExistsError:
            if attempt == 0 and _is_auto_backup_lock_stale(lock_path, now_utc):
                try:
                    lock_path.unlink(missing_ok=True)
                    app.logger.warning(
                        'Removed stale auto backup lock (%s) before retrying acquisition.',
                        lock_path.name,
                    )
                    continue
                except OSError:
                    pass

            app.logger.info(
                'Auto backup skipped because daily lock is already held '
                '(trigger=%s, local_date=%s).',
                trigger,
                local_date.isoformat(),
            )
            return None
        except OSError as exc:
            app.logger.warning(
                'Auto backup skipped because lock acquisition failed '
                '(trigger=%s, local_date=%s, error=%s).',
                trigger,
                local_date.isoformat(),
                exc,
            )
            return None

    return None


def _release_auto_backup_daily_lock(lock_path: Path | None, app) -> None:
    """Release a previously acquired date-scoped lock file."""
    if not lock_path:
        return

    try:
        lock_path.unlink(missing_ok=True)
    except OSError as exc:
        app.logger.warning('Auto backup lock release failed for %s: %s', lock_path.name, exc)


def _cleanup_stale_auto_backup_locks(app, now_local_date) -> int:
    """Remove stale date-scoped lock files from prior days."""
    backups_dir = DatabaseBackupService.get_backups_dir()
    removed_count = 0

    for lock_path in backups_dir.glob(f'{AUTO_BACKUP_LOCK_PREFIX}*{AUTO_BACKUP_LOCK_SUFFIX}'):
        date_part = lock_path.name[len(AUTO_BACKUP_LOCK_PREFIX):-len(AUTO_BACKUP_LOCK_SUFFIX)]
        try:
            lock_date = datetime.strptime(date_part, '%Y%m%d').date()
        except ValueError:
            continue

        if (now_local_date - lock_date).days >= 2:
            try:
                lock_path.unlink(missing_ok=True)
                removed_count += 1
            except OSError:
                continue

    if removed_count:
        app.logger.warning('Removed %s stale auto backup lock file(s).', removed_count)

    return removed_count


def _can_start_scheduler(app) -> bool:
    """Start only in the active runtime process to avoid duplicate jobs."""
    if not app.debug:
        return True

    # Flask reloader starts a parent process and a child process.
    # Start the scheduler only in the child process.
    run_main = os.environ.get('WERKZEUG_RUN_MAIN')
    return str(run_main).lower() == 'true'


def _resolve_scheduler_timezone() -> str:
    """Force scheduler timezone to Asia/Manila for midnight backups."""
    return DatabaseBackupService.AUTO_BACKUP_TIMEZONE


def _is_within_startup_catchup_window(local_now: datetime) -> bool:
    """Allow startup catch-up only shortly after local midnight."""
    minutes_after_midnight = (local_now.hour * 60) + local_now.minute
    return 0 <= minutes_after_midnight <= AUTO_BACKUP_STARTUP_CATCHUP_WINDOW_MINUTES


def _should_run_startup_catchup(settings: dict, now_utc: datetime) -> bool:
    """Return True when startup should run one catch-up backup for today's midnight."""
    if not settings.get('enabled'):
        return False

    timezone_name = _resolve_scheduler_timezone()
    local_now = now_utc.astimezone(ZoneInfo(timezone_name))
    if not _is_within_startup_catchup_window(local_now):
        return False

    return not DatabaseBackupService.has_auto_backup_for_local_date(local_now.date(), tz_name=timezone_name)


def _run_auto_backup_job(app, trigger: str = 'scheduled') -> bool:
    """Backup job runner for scheduled and startup catch-up flows."""
    with app.app_context():
        settings = DatabaseBackupService.get_auto_backup_settings()
        timezone_name = _resolve_scheduler_timezone()
        now_utc = datetime.now(timezone.utc)
        local_now = now_utc.astimezone(ZoneInfo(timezone_name))
        local_date = local_now.date()

        app.logger.info(
            'Auto backup job triggered at %s (trigger=%s, enabled=%s, retention_count=%s).',
            now_utc.isoformat(),
            trigger,
            settings['enabled'],
            settings['retention_count'],
        )
        if not settings['enabled']:
            app.logger.info('Auto backup skipped because automatic backup is disabled (trigger=%s).', trigger)
            return False

        if DatabaseBackupService.has_auto_backup_for_local_date(local_date, tz_name=timezone_name):
            app.logger.info(
                'Auto backup skipped because a successful backup already exists '
                '(trigger=%s, local_date=%s, timezone=%s).',
                trigger,
                local_date.isoformat(),
                timezone_name,
            )
            return False

        lock_path = _acquire_auto_backup_daily_lock(local_date, app, trigger, now_utc)
        if not lock_path:
            return False

        try:
            if DatabaseBackupService.has_auto_backup_for_local_date(local_date, tz_name=timezone_name):
                app.logger.info(
                    'Auto backup skipped after lock acquisition because backup exists '
                    '(trigger=%s, local_date=%s, timezone=%s).',
                    trigger,
                    local_date.isoformat(),
                    timezone_name,
                )
                return False

            backup = DatabaseBackupService.create_backup(source='auto')
            deleted = DatabaseBackupService.enforce_retention(
                retention_count=settings['retention_count'],
                source='auto',
            )
            DatabaseBackupService.mark_auto_backup_success(datetime.now(timezone.utc))
            app.logger.info(
                'Auto backup completed: %s (%s bytes). Retention removed %s file(s). trigger=%s',
                backup['filename'],
                backup['size'],
                len(deleted),
                trigger,
            )
            return True
        except BackupError as exc:
            app.logger.error('Auto backup failed (trigger=%s): %s', trigger, exc)
        except Exception as exc:
            app.logger.exception('Unexpected auto backup error (trigger=%s): %s', trigger, exc)
        finally:
            _release_auto_backup_daily_lock(lock_path, app)
    return False


def _run_startup_catchup_if_needed(app) -> None:
    """Run one startup catch-up backup if midnight was missed while the app was offline."""
    with app.app_context():
        now_utc = datetime.now(timezone.utc)
        settings = DatabaseBackupService.get_auto_backup_settings()
        timezone_name = _resolve_scheduler_timezone()
        local_now = now_utc.astimezone(ZoneInfo(timezone_name))
        within_window = _is_within_startup_catchup_window(local_now)
        has_backup_today = DatabaseBackupService.has_auto_backup_for_local_date(
            local_now.date(),
            tz_name=timezone_name,
        )
        should_run = _should_run_startup_catchup(settings, now_utc)

        app.logger.info(
            'Auto backup startup catch-up check '
            '(enabled=%s, local_date=%s, has_backup_today=%s, timezone=%s, '
            'within_window=%s, window_minutes=%s, should_run=%s).',
            settings.get('enabled'),
            local_now.date().isoformat(),
            has_backup_today,
            timezone_name,
            within_window,
            AUTO_BACKUP_STARTUP_CATCHUP_WINDOW_MINUTES,
            should_run,
        )

    if should_run:
        result = _run_auto_backup_job(app, trigger='startup_catchup')
        app.logger.info(
            'Auto backup startup catch-up result: %s.',
            'executed' if result else 'skipped_by_guard',
        )
    else:
        app.logger.info('Auto backup startup catch-up decision: skipped.')


def _shutdown_scheduler() -> None:
    """Stop scheduler cleanly on process shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def init_auto_backup_scheduler(app):
    """Initialize automatic backup scheduler with daily 12:00 AM trigger."""
    global _scheduler

    if not _can_start_scheduler(app):
        run_main = os.environ.get('WERKZEUG_RUN_MAIN')
        app.logger.info(
            'Auto backup scheduler not started in this process (debug=%s, WERKZEUG_RUN_MAIN=%s).',
            app.debug,
            run_main if run_main is not None else 'unset',
        )
        return None

    if _scheduler and _scheduler.running:
        app.logger.info('Auto backup scheduler already running; skipping re-initialization.')
        return _scheduler

    timezone_name = _resolve_scheduler_timezone()
    with app.app_context():
        local_now = datetime.now(timezone.utc).astimezone(ZoneInfo(timezone_name))
        _cleanup_stale_auto_backup_locks(app, local_now.date())

    _run_startup_catchup_if_needed(app)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: _run_auto_backup_job(app, trigger='scheduled'),
        trigger=CronTrigger(hour=0, minute=0, timezone=ZoneInfo(timezone_name)),
        id='auto_database_backup_job',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()

    _scheduler = scheduler
    atexit.register(_shutdown_scheduler)
    app.extensions['auto_backup_scheduler'] = scheduler
    app.logger.info('Auto backup scheduler started (daily at 12:00 AM, timezone=%s).', timezone_name)

    return scheduler
