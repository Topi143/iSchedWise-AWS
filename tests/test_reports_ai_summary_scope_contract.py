import inspect
from types import SimpleNamespace

from flask import Flask

from app.routes import reports as reports_routes


class _DummySettingsQuery:
    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return SimpleNamespace(
            academic_year='2025-2026',
            semester='1st Semester',
        )


class _DummyAcademicSettings:
    query = _DummySettingsQuery()


def _sample_stats():
    return {
        'schedule_completion_rate': 73,
        'sections_with_schedules': 8,
        'total_sections': 11,
        'avg_faculty_utilization': 60.7,
        'total_faculty': 25,
        'faculty_with_schedules': 25,
        'overloaded_faculty_count': 5,
        'warning_faculty_count': 0,
        'underutilized_faculty_count': 0,
        'unassigned_faculty_count': 0,
        'unassigned_faculty_by_dept': {},
        'unassigned_faculty': [],
        'unused_rooms_count': 28,
        'unused_rooms_by_type': {'Lecture': 12},
        'unused_rooms': [],
        'avg_room_utilization': 6.7,
        'total_room_hours_used': 229,
        'total_rooms': 14,
        'rooms_in_use': 14,
        'room_utilization_by_building': {'CS Building': {'utilization_pct': 28.6}},
    }


def _unwrap(func):
    return inspect.unwrap(func)


def test_normalize_program_scope_for_dean_and_admin():
    admin_scope = reports_routes._normalize_program_scope(None, None)
    assert admin_scope['is_dean_scope'] is False
    assert admin_scope['effective_program_ids'] is None

    dean_scope = reports_routes._normalize_program_scope([3, 4], 3)
    assert dean_scope['is_dean_scope'] is True
    assert dean_scope['selected_program_id'] == 3
    assert dean_scope['effective_program_ids'] == {3}

    dean_fallback_scope = reports_routes._normalize_program_scope([3, 4], 99)
    assert dean_fallback_scope['selected_program_id'] is None
    assert dean_fallback_scope['effective_program_ids'] == {3, 4}


def test_get_ai_summary_returns_scope_payload_and_section_metrics(monkeypatch):
    app = Flask(__name__)

    monkeypatch.setattr(reports_routes, 'AcademicSettings', _DummyAcademicSettings)
    monkeypatch.setattr(reports_routes, 'current_user', SimpleNamespace(get_program_ids=lambda: [7]))
    monkeypatch.setattr(reports_routes, 'calculate_statistics', lambda *_args, **_kwargs: _sample_stats())
    monkeypatch.setattr(
        reports_routes,
        '_resolve_scope_context',
        lambda *_args, **_kwargs: {
            'is_dean_scope': True,
            'scope_label': 'Analysis for Bachelor of Science in Computer Science',
            'selected_program_id': 7,
            'effective_program_ids': {7},
            'ai_program_name': 'Bachelor of Science in Computer Science (BSCS)',
            'unassigned_label': 'Unassigned Faculty in Your Department',
            'all_assigned_label': 'All faculty in your department assigned',
        },
    )
    monkeypatch.setattr(
        reports_routes,
        'ai_scheduler',
        SimpleNamespace(
            generate_report_summary=lambda *_args, **_kwargs: {
                'ai_enabled': False,
                'summary': 'Summary text',
                'insights': [],
                'recommendations': [],
            }
        ),
    )

    route_func = _unwrap(reports_routes.get_ai_summary)

    with app.test_request_context('/reports/api/ai-summary?program=7'):
        response = route_func()

    assert response.status_code == 200
    payload = response.get_json()

    assert payload['scope']['is_dean_scope'] is True
    assert payload['scope']['scope_label'] == 'Analysis for Bachelor of Science in Computer Science'
    assert payload['scope']['unassigned_label'] == 'Unassigned Faculty in Your Department'
    assert payload['scope']['all_assigned_label'] == 'All faculty in your department assigned'

    schedule_progress = payload['metrics']['schedule_progress']
    assert schedule_progress['scheduled'] == 8
    assert schedule_progress['total'] == 11
    assert schedule_progress['percentage'] == 73
