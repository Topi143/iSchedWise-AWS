"""Timezone helpers for consistent datetime display and API contracts."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


DEFAULT_SYSTEM_TIMEZONE = 'Asia/Manila'


def resolve_timezone_name(timezone_name: str | None = None) -> str:
    """Return a valid IANA timezone name, falling back to Asia/Manila."""
    candidate = timezone_name.strip() if isinstance(timezone_name, str) else ''

    if not candidate:
        try:
            from app.models.system_config import SystemConfig
            configured = SystemConfig.get('timezone', DEFAULT_SYSTEM_TIMEZONE)
            candidate = configured.strip() if isinstance(configured, str) else ''
        except Exception:
            candidate = ''

    if not candidate:
        return DEFAULT_SYSTEM_TIMEZONE

    try:
        ZoneInfo(candidate)
    except Exception:
        return DEFAULT_SYSTEM_TIMEZONE
    return candidate


def to_system_timezone(value: datetime | None, timezone_name: str | None = None) -> datetime | None:
    """Convert datetime to configured timezone, treating naive inputs as UTC."""
    if value is None:
        return None

    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.astimezone(ZoneInfo(resolve_timezone_name(timezone_name)))


def format_in_system_timezone(
    value: datetime | None,
    fmt: str = '%b %d, %I:%M %p',
    timezone_name: str | None = None,
) -> str:
    """Format datetime in configured timezone, returning empty string for missing values."""
    converted = to_system_timezone(value, timezone_name=timezone_name)
    if converted is None:
        return ''
    return converted.strftime(fmt)


def to_utc_iso_z(value: datetime | None, assume_timezone_name: str | None = None) -> str | None:
    """Return an ISO 8601 UTC string with Z suffix."""
    if value is None:
        return None

    if value.tzinfo is None:
        if assume_timezone_name:
            aware_value = value.replace(tzinfo=ZoneInfo(resolve_timezone_name(assume_timezone_name)))
            utc_value = aware_value.astimezone(timezone.utc)
        else:
            utc_value = value.replace(tzinfo=timezone.utc)
    else:
        utc_value = value.astimezone(timezone.utc)

    return utc_value.isoformat().replace('+00:00', 'Z')