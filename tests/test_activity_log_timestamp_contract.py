from datetime import datetime

from app.models.activity_log import UserActivityLog


def test_activity_log_to_dict_includes_created_at_iso_and_legacy_created_at():
    log = UserActivityLog(
        user_id=1,
        action='created',
        entity_type='schedule',
        entity_id=99,
        entity_name='Test Schedule',
        details='sample',
        ip_address='127.0.0.1',
    )
    log.created_at = datetime(2026, 3, 28, 14, 0, 0)

    payload = log.to_dict()

    assert payload['created_at'] == '2026-03-28 14:00:00'
    assert payload['created_at_iso'] == '2026-03-28T14:00:00Z'
