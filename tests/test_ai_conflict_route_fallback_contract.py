import inspect

from flask import Flask

from app.routes import exam_schedule as exam_routes
from app.routes import schedule as schedule_routes


class DummyQuery:
    def filter_by(self, **_kwargs):
        return self

    def all(self):
        return []

    def first(self):
        return None


class DummyModel:
    query = DummyQuery()


class DummyConflict:
    def __init__(self, conflict_type='section'):
        self._conflict_type = conflict_type

    def to_dict(self):
        return {
            'type': self._conflict_type,
            'severity': 'critical',
            'message': 'dummy conflict',
            'details': {},
            'conflicting_schedule_id': 1,
        }


class DummyRecommendation:
    def __init__(self, rec_type='time'):
        self._rec_type = rec_type

    def to_dict(self):
        return {
            'type': self._rec_type,
            'priority': 1,
            'message': 'dummy rec',
            'options': [],
            'confidence': 0.5,
        }


def _unwrap(func):
    return inspect.unwrap(func)


def _install_schedule_stubs(monkeypatch):
    monkeypatch.setattr(schedule_routes, 'AcademicSettings', DummyModel)
    monkeypatch.setattr(schedule_routes, 'Schedule', DummyModel)


def _install_exam_stubs(monkeypatch):
    monkeypatch.setattr(exam_routes, 'AcademicSettings', DummyModel)
    monkeypatch.setattr(exam_routes, 'ExamSchedule', DummyModel)


def test_schedule_ai_route_includes_fallback_keys_ai_branch(monkeypatch):
    app = Flask(__name__)
    _install_schedule_stubs(monkeypatch)

    monkeypatch.setattr(
        'app.ai_scheduler.ai_scheduler.analyze_schedule_conflicts',
        lambda *_args, **_kwargs: {
            'has_conflicts': True,
            'conflicts': [DummyConflict('section').to_dict()],
            'recommendations': [DummyRecommendation('time').to_dict()],
            'ai_explanation': 'ai explanation',
            'ai_enabled': True,
            'ai_fallback': True,
            'ai_fallback_reason': 'AI guidance temporarily unavailable due to provider error.',
        }
    )

    payload = {
        'section_id': 1,
        'day_of_week': 'Monday',
        'start_time': '08:00',
        'end_time': '09:00',
        'use_ai': True,
    }

    with app.test_request_context('/schedule/ai-check-conflicts', method='POST', json=payload):
        response = _unwrap(schedule_routes.ai_check_conflicts)()

    data = response.get_json()
    assert 'ai_fallback' in data
    assert 'ai_fallback_reason' in data
    assert 'ai_fallback_message' in data
    assert data['ai_enabled'] is True
    assert data['ai_fallback'] is True
    assert data['ai_fallback_reason'] == 'AI guidance temporarily unavailable due to provider error.'
    assert data['ai_fallback_message'] == 'AI guidance temporarily unavailable due to provider error.'


def test_schedule_ai_route_includes_fallback_keys_manual_branch(monkeypatch):
    app = Flask(__name__)
    _install_schedule_stubs(monkeypatch)

    monkeypatch.setattr(
        'app.services.conflict_detector.conflict_detector.detect_class_conflicts',
        lambda *_args, **_kwargs: [DummyConflict('section')]
    )
    monkeypatch.setattr(
        'app.services.recommendation_engine.recommendation_engine.generate_class_recommendations',
        lambda *_args, **_kwargs: [DummyRecommendation('time')]
    )
    monkeypatch.setattr(
        'app.ai_scheduler.ai_scheduler._get_offline_explanation',
        lambda *_args, **_kwargs: 'offline explanation'
    )

    payload = {
        'section_id': 1,
        'day_of_week': 'Monday',
        'start_time': '08:00',
        'end_time': '09:00',
        'use_ai': False,
    }

    with app.test_request_context('/schedule/ai-check-conflicts', method='POST', json=payload):
        response = _unwrap(schedule_routes.ai_check_conflicts)()

    data = response.get_json()
    assert 'ai_fallback' in data
    assert 'ai_fallback_reason' in data
    assert 'ai_fallback_message' in data
    assert data['ai_enabled'] is False
    assert data['ai_fallback'] is False
    assert data['ai_fallback_reason'] is None
    assert data['ai_fallback_message'] == ''


def test_exam_ai_route_includes_fallback_keys_ai_branch(monkeypatch):
    app = Flask(__name__)
    _install_exam_stubs(monkeypatch)

    monkeypatch.setattr(
        'app.ai_scheduler.ai_scheduler.analyze_exam_conflicts',
        lambda *_args, **_kwargs: {
            'has_conflicts': True,
            'conflicts': [DummyConflict('room').to_dict()],
            'recommendations': [DummyRecommendation('exam_time').to_dict()],
            'ai_explanation': 'ai explanation',
            'ai_enabled': True,
            'ai_fallback': True,
            'ai_fallback_reason': 'AI guidance temporarily unavailable due to provider error.',
        }
    )

    payload = {
        'section_id': 1,
        'exam_date': '2030-01-01',
        'start_time': '08:00',
        'end_time': '09:00',
        'use_ai': True,
    }

    with app.test_request_context('/exam-schedule/ai-check-conflicts', method='POST', json=payload):
        response = _unwrap(exam_routes.ai_check_exam_conflicts)()

    data = response.get_json()
    assert 'ai_fallback' in data
    assert 'ai_fallback_reason' in data
    assert 'ai_fallback_message' in data
    assert data['ai_enabled'] is True
    assert data['ai_fallback'] is True
    assert data['ai_fallback_reason'] == 'AI guidance temporarily unavailable due to provider error.'
    assert data['ai_fallback_message'] == 'AI guidance temporarily unavailable due to provider error.'


def test_exam_ai_route_includes_fallback_keys_manual_branch(monkeypatch):
    app = Flask(__name__)
    _install_exam_stubs(monkeypatch)

    monkeypatch.setattr(
        'app.services.conflict_detector.conflict_detector.detect_exam_conflicts',
        lambda *_args, **_kwargs: [DummyConflict('room')]
    )
    monkeypatch.setattr(
        'app.services.recommendation_engine.recommendation_engine.generate_exam_recommendations',
        lambda *_args, **_kwargs: [DummyRecommendation('exam_time')]
    )
    monkeypatch.setattr(
        'app.ai_scheduler.ai_scheduler._get_offline_explanation',
        lambda *_args, **_kwargs: 'offline explanation'
    )

    payload = {
        'section_id': 1,
        'exam_date': '2030-01-01',
        'start_time': '08:00',
        'end_time': '09:00',
        'use_ai': False,
    }

    with app.test_request_context('/exam-schedule/ai-check-conflicts', method='POST', json=payload):
        response = _unwrap(exam_routes.ai_check_exam_conflicts)()

    data = response.get_json()
    assert 'ai_fallback' in data
    assert 'ai_fallback_reason' in data
    assert 'ai_fallback_message' in data
    assert data['ai_enabled'] is False
    assert data['ai_fallback'] is False
    assert data['ai_fallback_reason'] is None
    assert data['ai_fallback_message'] == ''


def test_schedule_ai_route_no_conflicts_ai_success_has_no_fallback(monkeypatch):
    app = Flask(__name__)
    _install_schedule_stubs(monkeypatch)

    monkeypatch.setattr(
        'app.ai_scheduler.ai_scheduler.analyze_schedule_conflicts',
        lambda *_args, **_kwargs: {
            'has_conflicts': False,
            'conflicts': [],
            'recommendations': [],
            'ai_explanation': '',
            'ai_enabled': True,
            'ai_fallback': False,
            'ai_fallback_reason': None,
        }
    )

    payload = {
        'section_id': 1,
        'day_of_week': 'Monday',
        'start_time': '08:00',
        'end_time': '09:00',
        'use_ai': True,
    }

    with app.test_request_context('/schedule/ai-check-conflicts', method='POST', json=payload):
        response = _unwrap(schedule_routes.ai_check_conflicts)()

    data = response.get_json()
    assert data['has_conflicts'] is False
    assert data['ai_enabled'] is True
    assert data['ai_fallback'] is False
    assert data['ai_fallback_reason'] is None
    assert data['ai_fallback_message'] == ''


def test_exam_ai_route_no_conflicts_ai_success_has_no_fallback(monkeypatch):
    app = Flask(__name__)
    _install_exam_stubs(monkeypatch)

    monkeypatch.setattr(
        'app.ai_scheduler.ai_scheduler.analyze_exam_conflicts',
        lambda *_args, **_kwargs: {
            'has_conflicts': False,
            'conflicts': [],
            'recommendations': [],
            'ai_explanation': '',
            'ai_enabled': True,
            'ai_fallback': False,
            'ai_fallback_reason': None,
        }
    )

    payload = {
        'section_id': 1,
        'exam_date': '2030-01-01',
        'start_time': '08:00',
        'end_time': '09:00',
        'use_ai': True,
    }

    with app.test_request_context('/exam-schedule/ai-check-conflicts', method='POST', json=payload):
        response = _unwrap(exam_routes.ai_check_exam_conflicts)()

    data = response.get_json()
    assert data['has_conflicts'] is False
    assert data['ai_enabled'] is True
    assert data['ai_fallback'] is False
    assert data['ai_fallback_reason'] is None
    assert data['ai_fallback_message'] == ''
