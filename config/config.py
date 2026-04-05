"""
Application Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get the base directory (project root)
basedir = Path(__file__).resolve().parent.parent

# Load environment variables from .env file in project root
env_path = basedir / '.env'
load_dotenv(dotenv_path=env_path)

# Debug: Print if API key is loaded
api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    print(f"[OK] GEMINI_API_KEY loaded: {api_key[:10]}...")
else:
    print(f"[WARN] GEMINI_API_KEY not found in environment")
    print(f"   Looking for .env at: {env_path}")
    print(f"   .env exists: {env_path.exists()}")

class Config:
    """Base configuration class"""
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:@localhost/ischedwise_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }
    
    # Flask-Login configuration
    LOGIN_VIEW = 'auth.login'
    LOGIN_MESSAGE = 'Please log in to access this page.'
    LOGIN_MESSAGE_CATEGORY = 'info'

    # Session policy configuration
    SESSION_LOGOUT_POLICY = os.environ.get('SESSION_LOGOUT_POLICY', 'browser_close')
    
    # WTForms configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens
    
    # AI Configuration - Gemini API
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or None
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@ischedwise.com'
    
    # Password Reset Configuration
    PASSWORD_RESET_TOKEN_EXPIRY = 3600  # 1 hour in seconds

    # Two-Factor Authentication Configuration
    TWO_FACTOR_ISSUER = os.environ.get('TWO_FACTOR_ISSUER') or 'iSchedWise'
    TWO_FACTOR_PENDING_SECONDS = int(os.environ.get('TWO_FACTOR_PENDING_SECONDS') or 600)
    TWO_FACTOR_TRUST_DAYS = int(os.environ.get('TWO_FACTOR_TRUST_DAYS') or 1)
    TWO_FACTOR_TRUSTED_DEVICE_COOKIE = os.environ.get('TWO_FACTOR_TRUSTED_DEVICE_COOKIE') or 'isw_trusted_device'
    TWO_FACTOR_OTP_LENGTH = int(os.environ.get('TWO_FACTOR_OTP_LENGTH') or 6)
    TWO_FACTOR_OTP_EXPIRY_SECONDS = int(os.environ.get('TWO_FACTOR_OTP_EXPIRY_SECONDS') or 600)
    TWO_FACTOR_OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get('TWO_FACTOR_OTP_RESEND_COOLDOWN_SECONDS') or 60)
    TWO_FACTOR_OTP_MAX_ATTEMPTS = int(os.environ.get('TWO_FACTOR_OTP_MAX_ATTEMPTS') or 5)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Remove the @property decorator - SECRET_KEY must be a class attribute
    # Override the parent class SECRET_KEY
    def __init__(self):
        super().__init__()
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY must be set in production environment")
        self.SECRET_KEY = secret_key



class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SESSION_LOGOUT_POLICY = 'browser_close'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
