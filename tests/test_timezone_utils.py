from datetime import datetime

from app.models.system_config import SystemConfig
from app.utils.timezone_utils import (
    DEFAULT_SYSTEM_TIMEZONE,
    format_in_system_timezone,
    resolve_timezone_name,
    to_utc_iso_z,
)


def test_format_in_system_timezone_converts_utc_to_manila():
    utc_value = datetime(2026, 3, 28, 14, 0, 0)

    formatted = format_in_system_timezone(
        utc_value,
        fmt='%b %d, %I:%M %p',
        timezone_name='Asia/Manila',
    )

    assert formatted == 'Mar 28, 10:00 PM'


def test_resolve_timezone_name_falls_back_when_config_invalid(monkeypatch):
    monkeypatch.setattr(
        SystemConfig,
        'get',
        classmethod(lambda cls, key, default=None: 'Invalid/Timezone'),
    )

    assert resolve_timezone_name() == DEFAULT_SYSTEM_TIMEZONE


def test_to_utc_iso_z_uses_assumed_timezone_for_naive_values():
    # Treat naive datetime as Asia/Manila local time and convert to UTC.
    local_value = datetime(2026, 3, 28, 10, 0, 0)

    iso_value = to_utc_iso_z(local_value, assume_timezone_name='Asia/Manila')

    assert iso_value == '2026-03-28T02:00:00Z'


def test_to_utc_iso_z_treats_naive_as_utc_without_assumption():
    utc_naive = datetime(2026, 3, 28, 14, 0, 0)

    iso_value = to_utc_iso_z(utc_naive)

    assert iso_value == '2026-03-28T14:00:00Z'
