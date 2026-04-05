"""
Routes package - registers all blueprints
"""
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.program import program_bp
from app.routes.curriculum import curriculum_bp
from app.routes.faculty import faculty_bp
from app.routes.building import building_bp
from app.routes.schedule import schedule_bp
from app.routes.exam_schedule import exam_schedule_bp
from app.routes.settings import settings_bp
from app.routes.user import user_bp
from app.routes.archive import archive_bp
from app.routes.reports import reports_bp
from app.routes.profile import profile_bp
from app.routes.admin_tools import admin_tools_bp
from app.routes.data_generator import data_generator_bp

__all__ = ['main_bp', 'auth_bp', 'program_bp', 'curriculum_bp', 'faculty_bp', 'building_bp', 'schedule_bp', 'exam_schedule_bp', 'settings_bp', 'user_bp', 'archive_bp', 'reports_bp', 'profile_bp', 'admin_tools_bp', 'data_generator_bp']
