from types import SimpleNamespace

import pytest
from flask import Flask
from werkzeug.exceptions import Forbidden

import app.decorators as access_decorators
from app.routes import admin_tools as admin_tools_routes
from app.routes import main as main_routes


class _DummyUser:
    def __init__(self, is_authenticated, is_super_admin):
        self.is_authenticated = is_authenticated
        self.is_super_admin = is_super_admin


class _DashboardSentinelError(Exception):
    pass


class _NonSuperAdminUser:
    is_super_admin = False

    def get_program_ids(self):
        raise _DashboardSentinelError('existing dashboard flow reached')


def _build_test_app():
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    app.add_url_rule('/auth/login', endpoint='auth.login', view_func=lambda: 'login')
    app.add_url_rule('/admin/dashboard', endpoint='admin_tools.superadmin_dashboard', view_func=lambda: 'superadmin dashboard')
    return app


def test_superadmin_dashboard_decorator_redirects_unauthenticated_user(monkeypatch):
    app = _build_test_app()
    monkeypatch.setattr(access_decorators, 'current_user', _DummyUser(is_authenticated=False, is_super_admin=False), raising=False)

    route_func = admin_tools_routes.superadmin_dashboard.__wrapped__

    with app.test_request_context('/admin/dashboard'):
        response = route_func()

    assert response.status_code == 302
    assert response.location.endswith('/auth/login')


def test_superadmin_dashboard_decorator_blocks_non_super_admin(monkeypatch):
    app = _build_test_app()
    monkeypatch.setattr(access_decorators, 'current_user', _DummyUser(is_authenticated=True, is_super_admin=False), raising=False)

    route_func = admin_tools_routes.superadmin_dashboard.__wrapped__

    with app.test_request_context('/admin/dashboard'):
        with pytest.raises(Forbidden):
            route_func()


def test_superadmin_dashboard_route_renders_new_template(monkeypatch):
    app = _build_test_app()
    user_sentinel = object()
    monkeypatch.setattr(access_decorators, 'current_user', _DummyUser(is_authenticated=True, is_super_admin=True), raising=False)
    monkeypatch.setattr(admin_tools_routes, 'current_user', user_sentinel, raising=False)
    monkeypatch.setattr(
        admin_tools_routes,
        'render_template',
        lambda template, **ctx: {'template': template, 'ctx': ctx},
    )

    route_func = admin_tools_routes.superadmin_dashboard.__wrapped__

    with app.test_request_context('/admin/dashboard'):
        response = route_func()

    assert response['template'] == 'admin/superadmin_dashboard.html'
    assert response['ctx']['user'] is user_sentinel


def test_main_dashboard_redirects_super_admin_to_admin_dashboard(monkeypatch):
    app = _build_test_app()
    monkeypatch.setattr(main_routes, 'current_user', SimpleNamespace(is_super_admin=True), raising=False)
    monkeypatch.setattr(main_routes, 'url_for', lambda endpoint: '/admin/dashboard')

    route_func = main_routes.dashboard.__wrapped__

    with app.test_request_context('/dashboard'):
        response = route_func()

    assert response.status_code == 302
    assert response.location.endswith('/admin/dashboard')


def test_main_dashboard_non_super_admin_continues_existing_flow(monkeypatch):
    app = _build_test_app()
    monkeypatch.setattr(main_routes, 'current_user', _NonSuperAdminUser(), raising=False)
    monkeypatch.setattr(
        main_routes,
        'AcademicSettings',
        SimpleNamespace(
            query=SimpleNamespace(
                filter_by=lambda **kwargs: SimpleNamespace(
                    first=lambda: (_ for _ in ()).throw(_DashboardSentinelError('existing dashboard flow reached'))
                )
            )
        ),
        raising=False,
    )

    route_func = main_routes.dashboard.__wrapped__

    with app.test_request_context('/dashboard'):
        with pytest.raises(_DashboardSentinelError):
            route_func()
