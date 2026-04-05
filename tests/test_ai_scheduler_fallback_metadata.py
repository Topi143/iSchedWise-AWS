import datetime as dt

from app.ai_scheduler import AISchedulerAssistant
from app.services.conflict_detector import Conflict, ConflictSeverity, ConflictType


class DummyRecommendation:
    def __init__(self, rec_type='time'):
        self.type = rec_type
        self.options = [{'start_time': '08:00', 'end_time': '09:00'}]

    def to_dict(self):
        return {
            'type': self.type,
            'priority': 1,
            'message': 'dummy',
            'options': self.options,
            'confidence': 0.8,
        }


def test_schedule_analysis_has_fallback_metadata_without_api_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)

    assistant = AISchedulerAssistant()
    assistant.conflict_detector.detect_class_conflicts = lambda *_args, **_kwargs: []

    result = assistant.analyze_schedule_conflicts(
        {
            'section_id': 1,
            'day_of_week': 'Monday',
            'start_time': dt.time(8, 0),
            'end_time': dt.time(9, 0),
        },
        []
    )

    assert 'ai_fallback' in result
    assert 'ai_fallback_reason' in result
    assert result['ai_enabled'] is False
    assert result['ai_fallback'] is True
    assert isinstance(result['ai_fallback_reason'], str)


def test_schedule_analysis_sets_provider_error_fallback_reason(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')

    class FailingModel:
        def generate_content(self, _prompt):
            raise RuntimeError('provider down')

    monkeypatch.setattr('app.ai_scheduler.genai.configure', lambda **_kwargs: None)
    monkeypatch.setattr('app.ai_scheduler.genai.GenerativeModel', lambda *_args, **_kwargs: FailingModel())

    assistant = AISchedulerAssistant()

    conflicts = [
        Conflict(
            type=ConflictType.SECTION,
            severity=ConflictSeverity.CRITICAL,
            message='conflict',
            details={}
        )
    ]

    assistant.conflict_detector.detect_class_conflicts = lambda *_args, **_kwargs: conflicts
    assistant.recommendation_engine.generate_class_recommendations = (
        lambda *_args, **_kwargs: [DummyRecommendation('time')]
    )

    result = assistant.analyze_schedule_conflicts(
        {
            'section_id': 1,
            'day_of_week': 'Monday',
            'start_time': dt.time(8, 0),
            'end_time': dt.time(9, 0),
        },
        []
    )

    assert result['ai_enabled'] is True
    assert result['ai_fallback'] is True
    assert result['ai_fallback_reason'] == 'AI guidance temporarily unavailable due to provider error.'


def test_exam_analysis_has_fallback_metadata_without_api_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)

    assistant = AISchedulerAssistant()
    assistant.conflict_detector.detect_exam_conflicts = lambda *_args, **_kwargs: []

    result = assistant.analyze_exam_conflicts(
        {
            'section_id': 1,
            'exam_date': dt.date.today(),
            'start_time': dt.time(8, 0),
            'end_time': dt.time(9, 0),
        },
        []
    )

    assert 'ai_fallback' in result
    assert 'ai_fallback_reason' in result
    assert result['ai_enabled'] is False
    assert result['ai_fallback'] is True
    assert isinstance(result['ai_fallback_reason'], str)


def test_exam_analysis_sets_provider_error_fallback_reason(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')

    class FailingModel:
        def generate_content(self, _prompt):
            raise RuntimeError('provider down')

    monkeypatch.setattr('app.ai_scheduler.genai.configure', lambda **_kwargs: None)
    monkeypatch.setattr('app.ai_scheduler.genai.GenerativeModel', lambda *_args, **_kwargs: FailingModel())

    assistant = AISchedulerAssistant()

    conflicts = [
        Conflict(
            type=ConflictType.ROOM,
            severity=ConflictSeverity.HIGH,
            message='room conflict',
            details={}
        )
    ]

    assistant.conflict_detector.detect_exam_conflicts = lambda *_args, **_kwargs: conflicts
    assistant.recommendation_engine.generate_exam_recommendations = (
        lambda *_args, **_kwargs: [DummyRecommendation('exam_time')]
    )

    result = assistant.analyze_exam_conflicts(
        {
            'section_id': 1,
            'exam_date': dt.date.today(),
            'start_time': dt.time(8, 0),
            'end_time': dt.time(9, 0),
        },
        []
    )

    assert result['ai_enabled'] is True
    assert result['ai_fallback'] is True
    assert result['ai_fallback_reason'] == 'AI guidance temporarily unavailable due to provider error.'


def test_schedule_analysis_no_conflicts_ai_enabled_has_no_fallback(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')

    class DummyModel:
        def generate_content(self, _prompt):
            return None

    monkeypatch.setattr('app.ai_scheduler.genai.configure', lambda **_kwargs: None)
    monkeypatch.setattr('app.ai_scheduler.genai.GenerativeModel', lambda *_args, **_kwargs: DummyModel())

    assistant = AISchedulerAssistant()
    assistant.conflict_detector.detect_class_conflicts = lambda *_args, **_kwargs: []

    result = assistant.analyze_schedule_conflicts(
        {
            'section_id': 1,
            'day_of_week': 'Monday',
            'start_time': dt.time(8, 0),
            'end_time': dt.time(9, 0),
        },
        []
    )

    assert result['ai_enabled'] is True
    assert result['has_conflicts'] is False
    assert result['ai_fallback'] is False
    assert result['ai_fallback_reason'] is None


def test_exam_analysis_no_conflicts_ai_enabled_has_no_fallback(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')

    class DummyModel:
        def generate_content(self, _prompt):
            return None

    monkeypatch.setattr('app.ai_scheduler.genai.configure', lambda **_kwargs: None)
    monkeypatch.setattr('app.ai_scheduler.genai.GenerativeModel', lambda *_args, **_kwargs: DummyModel())

    assistant = AISchedulerAssistant()
    assistant.conflict_detector.detect_exam_conflicts = lambda *_args, **_kwargs: []

    result = assistant.analyze_exam_conflicts(
        {
            'section_id': 1,
            'exam_date': dt.date.today(),
            'start_time': dt.time(8, 0),
            'end_time': dt.time(9, 0),
        },
        []
    )

    assert result['ai_enabled'] is True
    assert result['has_conflicts'] is False
    assert result['ai_fallback'] is False
    assert result['ai_fallback_reason'] is None
