"""
iSchedWise V4 - School Scheduling System
Main application entry point using factory pattern
"""
import os
from app import create_app

# Get configuration from environment or default to development
config_name = os.environ.get('FLASK_ENV', 'development')

# Create application instance
app = create_app(config_name)

if __name__ == '__main__':
    # Run the application on local network
    # host='0.0.0.0' makes it accessible on local network
    # Use your machine's IP address to access from other devices
    app.run(host='0.0.0.0', port=5000, debug=True)
