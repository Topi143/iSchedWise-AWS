"""
Application Factory
Creates and configures the Flask application
"""
import pymysql
from flask import Flask
from config import config
from app.extensions import db, login_manager, migrate, csrf, mail
from app.models import User

# Configure PyMySQL to work with SQLAlchemy
pymysql.install_as_MySQLdb()


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
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
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
    
    # Register blueprints
    from app.routes import main_bp, auth_bp, department_bp, curriculum_bp, faculty_bp, building_bp, schedule_bp, exam_schedule_bp, settings_bp, user_bp, archive_bp, reports_bp
    from app.routes.profile import profile_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(department_bp)
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
    
    # Add after_request handler for cache control
    @app.after_request
    def add_security_headers(response):
        """Add security headers to prevent caching of authenticated pages"""
        from flask_login import current_user
        
        if current_user.is_authenticated:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
