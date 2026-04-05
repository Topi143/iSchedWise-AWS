from app.services.conflict_resolver import ConflictResolver


def test_build_plan_counts_only_actionable_form_changes():
    resolver = ConflictResolver()

    result = {
        'remaining': 0,
        'form_changes': {
            'start_time': '10:00',
            'end_time': '11:00',
            '_room_display': 'Room 101',
        },
        'resolutions': [
            {
                'action': 'change_time',
                'description': 'Change time to 10:00 - 11:00',
                'confidence': 90,
                'details': {},
            }
        ],
    }
    conflict_dicts = [
        {'type': 'room', 'severity': 'high', 'message': 'Room overlap'},
        {'type': 'faculty', 'severity': 'high', 'message': 'Faculty overlap'},
    ]

    plan = resolver._build_plan(result, conflict_dicts)

    assert plan['stats']['total_conflicts'] == 2
    assert plan['stats']['auto_resolvable'] == 2
    assert plan['stats']['needs_manual'] == 0


def test_build_plan_deduplicates_resolution_cards_and_tracks_affected_conflicts():
    resolver = ConflictResolver()

    result = {
        'remaining': 0,
        'form_changes': {
            'day_of_week': 'Monday',
        },
        'resolutions': [
            {
                'action': 'change_day',
                'description': 'Change day to Monday',
                'confidence': 85,
                'details': {'day': 'Monday'},
            },
            {
                'action': 'change_day',
                'description': 'Change day to Monday',
                'confidence': 85,
                'details': {'day': 'Monday'},
            },
            {
                'action': 'change_day',
                'description': 'Change day to Monday',
                'confidence': 85,
                'details': {'day': 'Monday'},
            },
        ],
    }
    conflict_dicts = [
        {'type': 'section', 'severity': 'critical', 'message': 'Section overlap'},
        {'type': 'room', 'severity': 'high', 'message': 'Room overlap'},
        {'type': 'faculty', 'severity': 'high', 'message': 'Faculty overlap'},
    ]

    plan = resolver._build_plan(result, conflict_dicts)

    assert plan['stats']['total_conflicts'] == 3
    assert plan['stats']['auto_resolvable'] == 1
    assert len(plan['resolvable']) == 1
    assert plan['resolvable'][0]['affected_conflicts'] == 3
