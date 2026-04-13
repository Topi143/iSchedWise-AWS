import inspect
from types import SimpleNamespace

from flask import Flask

from app.routes import settings as settings_routes


def _unwrap(route_func):
    return inspect.unwrap(route_func)


def _response_and_status(result):
    if isinstance(result, tuple):
        response, status = result
        return response, status
    return result, result.status_code


def _build_app():
    app = Flask(__name__)
    app.config['TEXT_SIZE_MIN'] = 90
    app.config['TEXT_SIZE_MAX'] = 120
    app.config['TEXT_SIZE_DEFAULT'] = 100
    app.config['TEXT_SIZE_STEP'] = 5
    return app


def test_update_text_size_accepts_in_range_value(monkeypatch):
    app = _build_app()
    route = _unwrap(settings_routes.update_text_size)

    dummy_user = SimpleNamespace(text_size=100)
    commit_calls = {'count': 0}

    monkeypatch.setattr(settings_routes, 'current_user', dummy_user)
    monkeypatch.setattr(settings_routes.db.session, 'commit', lambda: commit_calls.__setitem__('count', commit_calls['count'] + 1))
    monkeypatch.setattr(settings_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context('/settings/text-size/update', method='POST', json={'text_size': 115}):
        result = route()

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 200
    assert payload['success'] is True
    assert payload['text_size'] == 115
    assert dummy_user.text_size == 115
    assert commit_calls['count'] == 1


def test_update_text_size_clamps_out_of_range_and_snaps_to_step(monkeypatch):
    app = _build_app()
    route = _unwrap(settings_routes.update_text_size)

    dummy_user = SimpleNamespace(text_size=100)
    monkeypatch.setattr(settings_routes, 'current_user', dummy_user)
    monkeypatch.setattr(settings_routes.db.session, 'commit', lambda: None)
    monkeypatch.setattr(settings_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context('/settings/text-size/update', method='POST', json={'text_size': 150}):
        result_high = route()

    response_high, status_high = _response_and_status(result_high)
    payload_high = response_high.get_json()

    assert status_high == 200
    assert payload_high['success'] is True
    assert payload_high['text_size'] == 120
    assert dummy_user.text_size == 120

    with app.test_request_context('/settings/text-size/update', method='POST', json={'text_size': 88}):
        result_low = route()

    response_low, status_low = _response_and_status(result_low)
    payload_low = response_low.get_json()

    assert status_low == 200
    assert payload_low['success'] is True
    assert payload_low['text_size'] == 90
    assert dummy_user.text_size == 90

    with app.test_request_context('/settings/text-size/update', method='POST', json={'text_size': 118}):
        result_step = route()

    response_step, status_step = _response_and_status(result_step)
    payload_step = response_step.get_json()

    assert status_step == 200
    assert payload_step['success'] is True
    assert payload_step['text_size'] == 120
    assert dummy_user.text_size == 120


def test_update_text_size_rejects_non_numeric_payload(monkeypatch):
    app = _build_app()
    route = _unwrap(settings_routes.update_text_size)

    dummy_user = SimpleNamespace(text_size=100)
    commit_calls = {'count': 0}

    monkeypatch.setattr(settings_routes, 'current_user', dummy_user)
    monkeypatch.setattr(settings_routes.db.session, 'commit', lambda: commit_calls.__setitem__('count', commit_calls['count'] + 1))
    monkeypatch.setattr(settings_routes.db.session, 'rollback', lambda: None)

    with app.test_request_context('/settings/text-size/update', method='POST', json={'text_size': 'not-a-number'}):
        result = route()

    response, status = _response_and_status(result)
    payload = response.get_json()

    assert status == 400
    assert payload['success'] is False
    assert payload['error'] == 'Invalid text_size value'
    assert dummy_user.text_size == 100
    assert commit_calls['count'] == 0
