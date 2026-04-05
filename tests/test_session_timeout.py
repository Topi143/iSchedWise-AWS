from datetime import UTC, datetime, timedelta

from app import _has_session_idled_out
from config.config import TestingConfig


def test_idle_timeout_not_exceeded_returns_false():
    now = datetime.now(UTC).replace(tzinfo=None)
    last_activity = (now - timedelta(minutes=30)).isoformat()

    assert _has_session_idled_out(last_activity, 3600, now_utc=now) is False


def test_idle_timeout_exceeded_returns_false_when_feature_disabled():
    now = datetime.now(UTC).replace(tzinfo=None)
    last_activity = (now - timedelta(minutes=61)).isoformat()

    assert _has_session_idled_out(last_activity, 3600, now_utc=now) is False


def test_idle_timeout_invalid_timestamp_returns_false_when_feature_disabled():
    assert _has_session_idled_out('not-an-iso-timestamp', 3600, now_utc=datetime.now(UTC).replace(tzinfo=None)) is False


def test_idle_timeout_missing_timestamp_returns_false():
    assert _has_session_idled_out(None, 3600, now_utc=datetime.now(UTC).replace(tzinfo=None)) is False


def test_idle_timeout_disabled_when_non_positive():
    now = datetime.now(UTC).replace(tzinfo=None)
    old_activity = (now - timedelta(hours=24)).isoformat()

    assert _has_session_idled_out(old_activity, 0, now_utc=now) is False
    assert _has_session_idled_out(old_activity, -1, now_utc=now) is False


def test_testing_config_uses_browser_close_policy():
    assert TestingConfig.SESSION_LOGOUT_POLICY == 'browser_close'
