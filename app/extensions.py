"""
Flask extensions initialization
Extensions are initialized here and then attached to the app in the factory
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_socketio import SocketIO

# Initialize extensions (without app)
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
socketio = SocketIO()
