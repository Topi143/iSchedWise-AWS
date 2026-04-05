from datetime import datetime
from types import SimpleNamespace

import pytest
from flask import Flask

from app.extensions import db
from app.models.login_history import LoginHistory


class _QueryStub:
    def __init__(self, session):
        self._session = session
        self._filters = {}

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def first(self):
        if not self._session:
            return None
        if self._filters.get('id') != self._session.id:
            return None
        if self._filters.get('is_active') and not self._session.is_active:
            return None
        return self._session


@pytest.fixture()
def app_context():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        yield


def test_force_logout_deactivates_only_selected_session(monkeypatch, app_context):
    user = SimpleNamespace(force_logout_at=datetime(2026, 1, 1, 0, 0, 0))
    session = SimpleNamespace(
        id=123,
        is_active=True,
        logout_at=None,
        user=user,
    )

    monkeypatch.setattr(LoginHistory, 'query', _QueryStub(session), raising=False)

    assert LoginHistory.force_logout(123) is True
    assert session.is_active is False
    assert session.logout_at is not None
    # Targeted force logout must not mutate account-wide force flag.
    assert user.force_logout_at == datetime(2026, 1, 1, 0, 0, 0)


def test_force_logout_returns_false_for_missing_or_inactive_session(monkeypatch, app_context):
    monkeypatch.setattr(LoginHistory, 'query', _QueryStub(None), raising=False)
    assert LoginHistory.force_logout(999) is False
