"""
Application Factory
Creates and configures the Flask application
"""
import os
import time
from datetime import datetime
import pymysql
from flask import Flask, render_template, flash, redirect, url_for, jsonify
from config import config
from app.extensions import db, login_manager, csrf, mail, socketio
from app.models import User
from app.utils.timezone_utils import format_in_system_timezone, resolve_timezone_name

# Configure PyMySQL to work with SQLAlchemy
pymysql.install_as_MySQLdb()


def _has_session_idled_out(last_activity_iso, timeout_seconds, now_utc=None):
    """Minute-based inactivity timeout is disabled under browser-close session policy."""
    return False


def _is_password_change_enforcement_exempt(endpoint):
    """Return True when endpoint should bypass forced password-change gating."""
    if not endpoint:
        return False
    if endpoint == 'static' or endpoint.startswith('auth.'):
        return True
    return endpoint in {
        'profile.index',
        'profile.change_password',
    }


def _get_text_size_config(app_config):
    """Return sanitized text-size configuration values from app config."""
    min_size = int(app_config.get('TEXT_SIZE_MIN', 90))
    max_size = int(app_config.get('TEXT_SIZE_MAX', 120))
    default_size = int(app_config.get('TEXT_SIZE_DEFAULT', 100))
    step_size = int(app_config.get('TEXT_SIZE_STEP', 5))

    if min_size > max_size:
        min_size, max_size = max_size, min_size
    if step_size <= 0:
        step_size = 5

    default_size = max(min_size, min(max_size, default_size))
    return min_size, max_size, default_size, step_size


def _normalize_text_size(raw_value, min_size, max_size, default_size, step_size):
    """Normalize a raw text-size value into configured bounds and step."""
    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        parsed_value = default_size

    clamped_value = max(min_size, min(max_size, parsed_value))
    snapped_value = min_size + round((clamped_value - min_size) / step_size) * step_size
    return max(min_size, min(max_size, snapped_value))


def create_app(config_name='default'):
    """
    Application factory pattern
    
    Args:
        config_name: Configuration to use ('development', 'production', 'testing')
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Initialize SocketIO for real-time updates
    # cors_allowed_origins allows connections from the same origin
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        ping_interval=25,
        ping_timeout=60,
        logger=False,
        engineio_logger=False
    )
    
    # Configure login manager
    login_manager.login_view = app.config.get('LOGIN_VIEW', 'auth.login')
    login_manager.login_message = app.config.get('LOGIN_MESSAGE', 'Please log in to access this page.')
    login_manager.login_message_category = app.config.get('LOGIN_MESSAGE_CATEGORY', 'info')
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        return User.query.get(int(user_id))
    
    # Add context processor to make current_user available as 'user' in templates
    @app.context_processor
    def inject_user():
        """Inject current_user as 'user' into all templates"""
        from flask_login import current_user
        return dict(user=current_user)
    
    # Add context processor to inject institution settings into all templates
    @app.context_processor
    def inject_institution_settings():
        """Inject institution settings into all templates for sidebar/header display"""
        try:
            from app.models.settings import InstitutionSettings
            settings = InstitutionSettings.query.first()
            if settings:
                institution_display_name = (settings.institution_name or '').strip() or 'Norzagaray College'
                app_brand_name = (settings.system_name or '').strip() or 'iSchedWise'
                display_logo = settings.branding_logo or settings.institution_logo
                return dict(
                    # Backward-compatible alias used by many templates.
                    institution_name=institution_display_name,
                    institution_display_name=institution_display_name,
                    app_brand_name=app_brand_name,
                    institution_logo=display_logo
                )
        except Exception:
            pass
        # Return defaults if no settings or error
        return dict(
            institution_name='Norzagaray College',
            institution_display_name='Norzagaray College',
            app_brand_name='iSchedWise',
            institution_logo=None
        )
    
    # Add context processor to inject user display preferences into all templates
    @app.context_processor
    def inject_user_preferences():
        """Inject user display preferences (text_size, dark_mode) into all templates"""
        from flask_login import current_user

        text_size_min, text_size_max, text_size_default, text_size_step = _get_text_size_config(app.config)
        if current_user.is_authenticated:
            normalized_text_size = _normalize_text_size(
                current_user.text_size,
                text_size_min,
                text_size_max,
                text_size_default,
                text_size_step,
            )
            return dict(
                user_text_size=normalized_text_size,
                user_dark_mode=bool(current_user.dark_mode),
                text_size_min=text_size_min,
                text_size_max=text_size_max,
                text_size_default=text_size_default,
                text_size_step=text_size_step,
            )
        return dict(
            user_text_size=text_size_default,
            user_dark_mode=False,
            text_size_min=text_size_min,
            text_size_max=text_size_max,
            text_size_default=text_size_default,
            text_size_step=text_size_step,
        )

    @app.context_processor
    def inject_system_timezone():
        """Inject configured timezone for shared JS/template formatting."""
        return dict(system_timezone=resolve_timezone_name())

    @app.template_filter('format_system_datetime')
    def format_system_datetime(value, fmt='%b %d, %I:%M %p'):
        """Render a datetime in configured system timezone."""
        return format_in_system_timezone(value, fmt=fmt)
    
    # Force logout enforcement: invalidate sessions that have been force-logged-out by super admin
    @app.before_request
    def check_force_logout():
        """Log out users whose sessions have been force-terminated by an admin"""
        from flask_login import current_user, logout_user
        from flask import session as flask_session, request as req
        from app.models.login_history import LoginHistory
        # Skip for static files and auth routes
        if _is_password_change_enforcement_exempt(req.endpoint):
            return
        try:
            if not current_user.is_authenticated:
                return

            # Session-scoped enforcement: if the current login token no longer has an active
            # login_history row, terminate only this browser session.
            current_session_token = flask_session.get('_login_session_token')
            if current_session_token:
                active_session = LoginHistory.query.filter_by(
                    user_id=current_user.id,
                    session_id=current_session_token,
                    is_active=True
                ).first()
                if not active_session:
                    logout_user()
                    flask_session.clear()
                    flash('Your session has been terminated by an administrator.', 'warning')
                    return redirect(url_for('auth.login'))

            # Account-wide enforcement used by force-logout-all.
            if getattr(current_user, 'force_logout_at', None):
                from datetime import datetime
                login_time_str = flask_session.get('_login_time')
                if login_time_str:
                    login_time = datetime.fromisoformat(login_time_str)
                    if current_user.force_logout_at > login_time:
                        logout_user()
                        flask_session.clear()
                        flash('Your session has been terminated by an administrator.', 'warning')
                        return redirect(url_for('auth.login'))
                else:
                    # No login time in session — session predates the force-logout feature.
                    logout_user()
                    flask_session.clear()
                    flash('Your session has been terminated by an administrator.', 'warning')
                    return redirect(url_for('auth.login'))
        except Exception:
            pass

    @app.before_request
    def enforce_password_change():
        """Restrict flagged users to password-change flow until reset is completed."""
        from flask_login import current_user
        from flask import request as req

        if req.endpoint and (
            req.endpoint == 'static' or
            req.endpoint.startswith('auth.')
        ):
            return

        if not current_user.is_authenticated:
            return

        if not getattr(current_user, 'needs_password_change', False):
            return

        if _is_password_change_enforcement_exempt(req.endpoint):
            return

        if req.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Password reset required before accessing this endpoint.'
            }), 403

        flash('You must change your password before continuing.', 'warning')
        return redirect(url_for('profile.index'))

    @app.before_request
    def enforce_text_size_bounds():
        """Normalize persisted text-size preferences into configured safe bounds."""
        from flask_login import current_user
        from flask import request as req

        if req.endpoint and req.endpoint == 'static':
            return

        if not current_user.is_authenticated:
            return

        text_size_min, text_size_max, text_size_default, text_size_step = _get_text_size_config(app.config)
        normalized_text_size = _normalize_text_size(
            current_user.text_size,
            text_size_min,
            text_size_max,
            text_size_default,
            text_size_step,
        )

        if current_user.text_size == normalized_text_size:
            return

        try:
            current_user.text_size = normalized_text_size
            db.session.commit()
        except Exception:
            db.session.rollback()

    @app.before_request
    def check_inactivity_timeout():
        """Apply account-status session enforcement for authenticated users."""
        from flask_login import current_user, logout_user
        from flask import session as flask_session, request as req

        if req.endpoint and (
            req.endpoint == 'static' or
            req.endpoint.startswith('auth.')
        ):
            return

        if not current_user.is_authenticated:
            return

        # Immediately terminate sessions for deactivated or archived users.
        if not getattr(current_user, 'is_active', True) or getattr(current_user, 'is_archived', False):
            try:
                from app.models.login_history import LoginHistory
                current_session_token = flask_session.get('_login_session_token')
                if current_session_token:
                    LoginHistory.record_logout(session_id=current_session_token)
                else:
                    LoginHistory.record_logout(user_id=current_user.id)
                db.session.commit()
            except Exception:
                db.session.rollback()

            logout_user()
            flask_session.clear()
            flash('Your account is inactive. Please contact the administrator.', 'warning')
            return redirect(url_for('auth.login'))

        # Minute-based inactivity auto-logout is intentionally disabled.
        # Sessions are browser-session scoped and end when the browser closes.
    
    # Maintenance mode: block non-super_admin users when maintenance_mode is enabled
    @app.before_request
    def check_maintenance_mode():
        """Redirect non-super_admin users to maintenance page when maintenance mode is on"""
        from flask_login import current_user
        from flask import request as req
        # Allow static files, auth routes, and the maintenance page itself
        if req.endpoint and (
            req.endpoint == 'static' or
            req.endpoint.startswith('auth.') or
            req.endpoint == 'admin_tools.maintenance_page'
        ):
            return
        try:
            from app.models.system_config import SystemConfig
            if SystemConfig.get('maintenance_mode', False):
                if not current_user.is_authenticated or not getattr(current_user, 'is_super_admin', False):
                    maintenance_msg = SystemConfig.get('maintenance_message', '') or 'The system is currently under maintenance. Please try again later.'
                    return render_template('maintenance.html', message=maintenance_msg), 503
        except Exception:
            pass
    
    # Cache-busting for static files: append file modification time as version query param
    # This ensures browsers always load the latest JS/CSS after code changes
    @app.url_defaults
    def cache_busting_static(endpoint, values):
        if endpoint == 'static':
            filename = values.get('filename')
            if filename:
                filepath = os.path.join(app.static_folder, filename)
                try:
                    values['v'] = int(os.path.getmtime(filepath))
                except OSError:
                    pass
    
    # Register blueprints
    from app.routes import main_bp, auth_bp, program_bp, curriculum_bp, faculty_bp, building_bp, schedule_bp, exam_schedule_bp, settings_bp, user_bp, archive_bp, reports_bp
    from app.routes.profile import profile_bp
    from app.routes.admin_tools import admin_tools_bp
    from app.routes.data_generator import data_generator_bp
    
    # Import socket events to register handlers
    from app.routes import socket_events  # noqa: F401
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(program_bp)
    app.register_blueprint(curriculum_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(building_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(exam_schedule_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_tools_bp)
    app.register_blueprint(data_generator_bp)
    
    # Add after_request handler for cache control
    @app.after_request
    def add_security_headers(response):
        """Add security headers for authenticated pages.
        
        Uses 'private, no-cache' instead of 'no-store' to allow:
        - bfcache (instant back/forward navigation)
        - Speculative link prefetching
        - View Transitions API cross-document support
        While still requiring revalidation so users always get fresh data.
        """
        from flask_login import current_user
        
        if current_user.is_authenticated:
            response.headers['Cache-Control'] = 'private, no-cache, max-age=0, must-revalidate'
            response.headers['Expires'] = '0'
        return response
    
    # Create database tables
    with app.app_context():
        db.create_all()
        try:
            from app.models.system_config import SystemConfig
            configured_policy = SystemConfig.get('session_logout_policy', 'browser_close')
            logout_policy = 'browser_close' if configured_policy != 'browser_close' else configured_policy
            app.config['SESSION_LOGOUT_POLICY'] = logout_policy

            # Seed missing key to keep system settings and runtime config in sync.
            policy_key = SystemConfig.query.filter_by(config_key='session_logout_policy').first()
            if not policy_key:
                SystemConfig.set('session_logout_policy', logout_policy)
                db.session.commit()
        except Exception:
            db.session.rollback()
            pass

    # Initialize automatic database backup scheduler (non-blocking on failure)
    try:
        from app.services.auto_backup_scheduler import init_auto_backup_scheduler
        init_auto_backup_scheduler(app)
    except Exception as exc:
        app.logger.warning('Auto backup scheduler initialization skipped: %s', exc)
    
    return app
