from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.routes import settings as settings_routes


def _row(academic_year, semester, exam_period, start=None, end=None):
    return SimpleNamespace(
        academic_year=academic_year,
        semester=semester,
        exam_period=exam_period,
        exam_period_start=start,
        exam_period_end=end,
    )


def test_build_exam_period_date_memory_prefers_latest_non_empty_per_period():
    rows = [
        _row('2025-2026', '1st Semester', 'Prelim', None, None),
        _row('2025-2026', '1st Semester', 'Prelim', date(2025, 1, 1), date(2025, 1, 6)),
        _row('2025-2026', '1st Semester', 'Midterm', date(2025, 3, 3), date(2025, 3, 8)),
        _row('2025-2026', '1st Semester', 'Finals', date(2025, 5, 5), date(2025, 5, 10)),
    ]

    memory = settings_routes._build_exam_period_date_memory_map(rows)
    term = memory['2025-2026|1st Semester']

    assert term['Prelim'] == {'start': '2025-01-01', 'end': '2025-01-06'}
    assert term['Midterm'] == {'start': '2025-03-03', 'end': '2025-03-08'}
    assert term['Final'] == {'start': '2025-05-05', 'end': '2025-05-10'}


def test_build_exam_period_date_memory_keeps_empty_for_missing_periods():
    rows = [
        _row('2026-2027', '2nd Semester', 'Prelim', date(2026, 2, 2), date(2026, 2, 7)),
    ]

    memory = settings_routes._build_exam_period_date_memory_map(rows)
    term = memory['2026-2027|2nd Semester']

    assert term['Prelim'] == {'start': '2026-02-02', 'end': '2026-02-07'}
    assert term['Midterm'] == {'start': '', 'end': ''}
    assert term['Final'] == {'start': '', 'end': ''}


def test_should_reset_exam_period_dates_only_on_term_change():
    assert settings_routes._should_reset_exam_period_dates(True) is True
    assert settings_routes._should_reset_exam_period_dates(False) is False


def test_normalize_exam_period_strips_and_maps_aliases():
    assert settings_routes._normalize_exam_period(' Prelim ') == 'Prelim'
    assert settings_routes._normalize_exam_period(' Midterm ') == 'Midterm'
    assert settings_routes._normalize_exam_period(' Finals ') == 'Final'
    assert settings_routes._normalize_exam_period('Unknown') is None


def test_settings_template_has_standalone_exam_period_memory_payload_tag():
    template_path = Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'settings.html'
    template_content = template_path.read_text(encoding='utf-8')

    assert '<script id="settingsExamPeriodDateMemory" type="application/json">{{ exam_period_date_memory|tojson }}</script>' in template_content
    assert 'id="settingsRouteData"' in template_content
    assert 'id="settingsRouteData"\n<script id="settingsExamPeriodDateMemory"' not in template_content
