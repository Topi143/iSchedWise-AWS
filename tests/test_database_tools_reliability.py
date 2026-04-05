import pytest
from flask import Flask
from datetime import datetime, timezone
import os
from pathlib import Path

import app.services.auto_backup_scheduler as auto_backup_scheduler
from app.services.auto_backup_scheduler import _can_start_scheduler, _resolve_scheduler_timezone, _should_run_startup_catchup
from app.services.database_backup_service import BackupError, DatabaseBackupService


@pytest.fixture()
def app_context():
    app = Flask(__name__)
    with app.app_context():
        backups_dir = DatabaseBackupService.get_backups_dir()
        existing_files = {path.name for path in backups_dir.glob('ischedwise_backup_*.sql')}
        yield app

        for path in backups_dir.glob('ischedwise_backup_*.sql'):
            if path.name in existing_files:
                continue

            try:
                content = path.read_text(encoding='utf-8', errors='ignore').strip()
            except OSError:
                continue

            if content == '-- dummy backup' or content.startswith('-- test backup'):
                path.unlink(missing_ok=True)


def test_backup_filename_validation_blocks_non_sql(app_context):
    with pytest.raises(BackupError):
        DatabaseBackupService.get_backup_path('not-a-backup.txt')


def test_backup_filename_validation_supports_encoded_valid_name(app_context):
    filename = 'ischedwise_backup_20260321_101010.sql'
    encoded = 'ischedwise%5Fbackup%5F20260321%5F101010.sql'

    path = DatabaseBackupService.get_backup_path(encoded)
    assert path.name == filename


def test_collision_safe_filename_generation(app_context):
    backups_dir = DatabaseBackupService.get_backups_dir()
    filename1 = DatabaseBackupService._build_backup_filename()
    (backups_dir / filename1).write_text('-- dummy backup', encoding='utf-8')

    filename2 = DatabaseBackupService._build_backup_filename()

    assert filename2 != filename1
    assert filename2.endswith('.sql')
    assert filename2.startswith('ischedwise_backup_')


def test_schedule_label_uses_timezone(monkeypatch, app_context):
    from app.models import SystemConfig

    monkeypatch.setattr(SystemConfig, 'get', classmethod(lambda cls, key, default=None: default))
    # Auto-backup timezone is fixed to Asia/Manila regardless of display timezone settings.
    settings = DatabaseBackupService.get_auto_backup_settings()
    assert settings['schedule_label'] == 'Daily at 12:00 AM (Asia/Manila)'


def test_list_backups_excludes_known_dummy_files(app_context):
    backups_dir = DatabaseBackupService.get_backups_dir()
    dummy_name = DatabaseBackupService._build_backup_filename()
    (backups_dir / dummy_name).write_text('-- dummy backup', encoding='utf-8')

    valid_name = DatabaseBackupService._build_backup_filename()
    (backups_dir / valid_name).write_text('-- test backup\nCREATE TABLE sample(id INT);', encoding='utf-8')

    backups = DatabaseBackupService.list_backups()
    names = [entry['filename'] for entry in backups]

    assert valid_name in names
    assert dummy_name not in names
    assert not (backups_dir / dummy_name).exists()


def test_can_start_scheduler_debug_without_reloader_env_skips_start(monkeypatch):
    class App:
        debug = True

    monkeypatch.delenv('WERKZEUG_RUN_MAIN', raising=False)
    assert _can_start_scheduler(App()) is False


def test_can_start_scheduler_debug_parent_process(monkeypatch):
    class App:
        debug = True

    monkeypatch.setenv('WERKZEUG_RUN_MAIN', 'false')
    assert _can_start_scheduler(App()) is False


def test_can_start_scheduler_production(monkeypatch):
    class App:
        debug = False

    monkeypatch.setenv('WERKZEUG_RUN_MAIN', 'false')
    assert _can_start_scheduler(App()) is True


def test_init_auto_backup_scheduler_skips_when_guard_false(monkeypatch):
    app = Flask(__name__)
    app.debug = True

    monkeypatch.setattr(auto_backup_scheduler, '_can_start_scheduler', lambda _app: False)
    monkeypatch.setattr(auto_backup_scheduler, '_run_startup_catchup_if_needed', lambda _app: (_ for _ in ()).throw(AssertionError('startup catch-up should not run when scheduler start is skipped')))
    monkeypatch.setattr(auto_backup_scheduler, 'BackgroundScheduler', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('BackgroundScheduler should not be created when scheduler start is skipped')))
    monkeypatch.setattr(auto_backup_scheduler, '_scheduler', None)

    result = auto_backup_scheduler.init_auto_backup_scheduler(app)

    assert result is None
    assert 'auto_backup_scheduler' not in app.extensions


def test_scheduler_timezone_is_fixed_to_asia_manila():
    assert _resolve_scheduler_timezone() == 'Asia/Manila'


def test_startup_catchup_runs_when_no_backup_for_local_date(monkeypatch):
    settings = {'enabled': True, 'retention_count': 30}
    now_utc = datetime(2026, 3, 21, 16, 10, tzinfo=timezone.utc)

    monkeypatch.setattr(DatabaseBackupService, 'has_auto_backup_for_local_date', classmethod(lambda cls, local_date, tz_name=None: False))
    assert _should_run_startup_catchup(settings, now_utc) is True


def test_startup_catchup_skips_when_backup_exists_for_local_date(monkeypatch):
    settings = {'enabled': True, 'retention_count': 30}
    now_utc = datetime(2026, 3, 21, 16, 10, tzinfo=timezone.utc)

    monkeypatch.setattr(DatabaseBackupService, 'has_auto_backup_for_local_date', classmethod(lambda cls, local_date, tz_name=None: True))
    assert _should_run_startup_catchup(settings, now_utc) is False


def test_startup_catchup_skips_when_disabled(monkeypatch):
    settings = {'enabled': False, 'retention_count': 30}
    now_utc = datetime(2026, 3, 22, 4, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(DatabaseBackupService, 'has_auto_backup_for_local_date', classmethod(lambda cls, local_date, tz_name=None: False))
    assert _should_run_startup_catchup(settings, now_utc) is False


def test_startup_catchup_skips_outside_window(monkeypatch):
    settings = {'enabled': True, 'retention_count': 30}
    now_utc = datetime(2026, 3, 22, 4, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(DatabaseBackupService, 'has_auto_backup_for_local_date', classmethod(lambda cls, local_date, tz_name=None: False))
    assert _should_run_startup_catchup(settings, now_utc) is False


def test_auto_job_skips_when_backup_exists_for_local_date(monkeypatch):
    app = Flask(__name__)

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_auto_backup_settings',
        classmethod(lambda cls: {'enabled': True, 'retention_count': 30}),
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'has_auto_backup_for_local_date',
        classmethod(lambda cls, local_date, tz_name=None: True),
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'create_backup',
        classmethod(
            lambda cls, source='manual', initiated_by_user_id=None: (
                _ for _ in ()
            ).throw(AssertionError('create_backup should not run when same-day backup already exists'))
        ),
    )

    result = auto_backup_scheduler._run_auto_backup_job(app, trigger='test')

    assert result is False


def test_auto_job_skips_when_daily_lock_is_held(monkeypatch):
    app = Flask(__name__)

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_auto_backup_settings',
        classmethod(lambda cls: {'enabled': True, 'retention_count': 30}),
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'has_auto_backup_for_local_date',
        classmethod(lambda cls, local_date, tz_name=None: False),
    )
    monkeypatch.setattr(
        auto_backup_scheduler,
        '_acquire_auto_backup_daily_lock',
        lambda local_date, app, trigger, now_utc: None,
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'create_backup',
        classmethod(
            lambda cls, source='manual', initiated_by_user_id=None: (
                _ for _ in ()
            ).throw(AssertionError('create_backup should not run when daily lock is held'))
        ),
    )

    result = auto_backup_scheduler._run_auto_backup_job(app, trigger='test')

    assert result is False


def test_auto_job_releases_lock_on_failure_path(monkeypatch):
    app = Flask(__name__)
    release_calls = []
    lock_path = Path('daily.lock')

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_auto_backup_settings',
        classmethod(lambda cls: {'enabled': True, 'retention_count': 30}),
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'has_auto_backup_for_local_date',
        classmethod(lambda cls, local_date, tz_name=None: False),
    )
    monkeypatch.setattr(
        auto_backup_scheduler,
        '_acquire_auto_backup_daily_lock',
        lambda local_date, app, trigger, now_utc: lock_path,
    )
    monkeypatch.setattr(
        auto_backup_scheduler,
        '_release_auto_backup_daily_lock',
        lambda path, app: release_calls.append(path),
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'create_backup',
        classmethod(
            lambda cls, source='manual', initiated_by_user_id=None: (
                _ for _ in ()
            ).throw(BackupError('forced backup failure'))
        ),
    )

    result = auto_backup_scheduler._run_auto_backup_job(app, trigger='test')

    assert result is False
    assert release_calls == [lock_path]


def test_startup_catchup_and_scheduled_same_date_only_one_create(monkeypatch):
    app = Flask(__name__)
    lock_path = Path('daily.lock')
    state = {
        'has_backup': False,
        'create_calls': 0,
        'mark_calls': 0,
    }

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_auto_backup_settings',
        classmethod(lambda cls: {'enabled': True, 'retention_count': 30}),
    )

    def _has_backup(cls, local_date, tz_name=None):
        return state['has_backup']

    def _create_backup(cls, source='manual', initiated_by_user_id=None):
        state['create_calls'] += 1
        return {
            'filename': 'ischedwise_backup_test.sql',
            'size': 128,
        }

    def _mark_success(cls, when_utc=None):
        state['mark_calls'] += 1
        state['has_backup'] = True

    monkeypatch.setattr(DatabaseBackupService, 'has_auto_backup_for_local_date', classmethod(_has_backup))
    monkeypatch.setattr(DatabaseBackupService, 'create_backup', classmethod(_create_backup))
    monkeypatch.setattr(DatabaseBackupService, 'mark_auto_backup_success', classmethod(_mark_success))
    monkeypatch.setattr(DatabaseBackupService, 'enforce_retention', classmethod(lambda cls, retention_count, source='auto', initiated_by_user_id=None: []))
    monkeypatch.setattr(
        auto_backup_scheduler,
        '_acquire_auto_backup_daily_lock',
        lambda local_date, app, trigger, now_utc: lock_path,
    )
    monkeypatch.setattr(auto_backup_scheduler, '_release_auto_backup_daily_lock', lambda path, app: None)

    first = auto_backup_scheduler._run_auto_backup_job(app, trigger='startup_catchup')
    second = auto_backup_scheduler._run_auto_backup_job(app, trigger='scheduled')

    assert first is True
    assert second is False
    assert state['create_calls'] == 1
    assert state['mark_calls'] == 1


def test_auto_job_happy_path_marks_success_and_runs_retention(monkeypatch):
    app = Flask(__name__)
    lock_path = Path('daily.lock')
    release_calls = []
    retention_calls = []
    mark_calls = []

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_auto_backup_settings',
        classmethod(lambda cls: {'enabled': True, 'retention_count': 30}),
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'has_auto_backup_for_local_date',
        classmethod(lambda cls, local_date, tz_name=None: False),
    )
    monkeypatch.setattr(
        auto_backup_scheduler,
        '_acquire_auto_backup_daily_lock',
        lambda local_date, app, trigger, now_utc: lock_path,
    )
    monkeypatch.setattr(
        auto_backup_scheduler,
        '_release_auto_backup_daily_lock',
        lambda path, app: release_calls.append(path),
    )
    monkeypatch.setattr(
        DatabaseBackupService,
        'create_backup',
        classmethod(
            lambda cls, source='manual', initiated_by_user_id=None: {
                'filename': 'ischedwise_backup_test.sql',
                'size': 256,
            }
        ),
    )

    def _retention(cls, retention_count, source='auto', initiated_by_user_id=None):
        retention_calls.append((retention_count, source))
        return ['old_backup.sql']

    def _mark_success(cls, when_utc=None):
        mark_calls.append(when_utc)

    monkeypatch.setattr(DatabaseBackupService, 'enforce_retention', classmethod(_retention))
    monkeypatch.setattr(DatabaseBackupService, 'mark_auto_backup_success', classmethod(_mark_success))

    result = auto_backup_scheduler._run_auto_backup_job(app, trigger='scheduled')

    assert result is True
    assert retention_calls == [(30, 'auto')]
    assert len(mark_calls) == 1
    assert isinstance(mark_calls[0], datetime)
    assert mark_calls[0].tzinfo == timezone.utc
    assert release_calls == [lock_path]


def test_daily_lock_helpers_acquire_release_and_reacquire(monkeypatch, tmp_path):
    app = Flask(__name__)
    local_date = datetime(2026, 3, 22, tzinfo=timezone.utc).date()
    now_utc = datetime(2026, 3, 22, 4, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_backups_dir',
        classmethod(lambda cls: tmp_path),
    )

    first_lock = auto_backup_scheduler._acquire_auto_backup_daily_lock(local_date, app, 'test', now_utc)

    assert first_lock is not None
    assert first_lock.exists()
    assert first_lock.name == '.auto_backup_lock_20260322.lock'

    second_lock = auto_backup_scheduler._acquire_auto_backup_daily_lock(local_date, app, 'test', now_utc)
    assert second_lock is None

    auto_backup_scheduler._release_auto_backup_daily_lock(first_lock, app)
    assert not first_lock.exists()

    third_lock = auto_backup_scheduler._acquire_auto_backup_daily_lock(local_date, app, 'test', now_utc)
    assert third_lock is not None
    assert third_lock.exists()


def test_daily_lock_acquire_recovers_from_stale_lock(monkeypatch, tmp_path):
    app = Flask(__name__)
    local_date = datetime(2026, 3, 22, tzinfo=timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_backups_dir',
        classmethod(lambda cls: tmp_path),
    )

    stale_lock_path = tmp_path / '.auto_backup_lock_20260322.lock'
    stale_lock_path.write_text('stale lock', encoding='utf-8')

    stale_epoch = now_utc.timestamp() - auto_backup_scheduler.AUTO_BACKUP_LOCK_STALE_SECONDS - 30
    os.utime(stale_lock_path, (stale_epoch, stale_epoch))

    lock_path = auto_backup_scheduler._acquire_auto_backup_daily_lock(local_date, app, 'test', now_utc)

    assert lock_path == stale_lock_path
    assert lock_path.exists()
    content = lock_path.read_text(encoding='utf-8')
    assert 'trigger=test' in content
    assert 'created_at_utc=' in content


def test_cleanup_stale_locks_removes_only_old_dates(monkeypatch, tmp_path):
    app = Flask(__name__)
    today = datetime(2026, 3, 22, tzinfo=timezone.utc).date()

    monkeypatch.setattr(
        DatabaseBackupService,
        'get_backups_dir',
        classmethod(lambda cls: tmp_path),
    )

    (tmp_path / '.auto_backup_lock_20260322.lock').write_text('today', encoding='utf-8')
    (tmp_path / '.auto_backup_lock_20260321.lock').write_text('yesterday', encoding='utf-8')
    old_lock = tmp_path / '.auto_backup_lock_20260320.lock'
    old_lock.write_text('old', encoding='utf-8')

    removed_count = auto_backup_scheduler._cleanup_stale_auto_backup_locks(app, today)

    assert removed_count == 1
    assert not old_lock.exists()
    assert (tmp_path / '.auto_backup_lock_20260322.lock').exists()
    assert (tmp_path / '.auto_backup_lock_20260321.lock').exists()
