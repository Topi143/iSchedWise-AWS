"""
iSchedWise V4 - School Scheduling System
Main application entry point using factory pattern
"""
import os
from app import create_app
from app.extensions import socketio

# Get configuration from environment or default to development
config_name = os.environ.get('FLASK_ENV', 'development')

# Create application instance
app = create_app(config_name)

if __name__ == '__main__':
    # Use Socket.IO runner so /socket.io requests are served by Flask-SocketIO.
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True
    )
