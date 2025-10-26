"""
User model for authentication
"""
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer
from app.extensions import db


# Junction table for many-to-many relationship between users and departments
user_departments = db.Table('user_departments',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False),
    db.Column('created_at', db.DateTime, default=db.func.current_timestamp()),
    db.UniqueConstraint('user_id', 'department_id', name='user_department_unique')
)


class User(UserMixin, db.Model):
    """User model for admin and dean roles"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'dean'
    full_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_login = db.Column(db.DateTime)
    
    # Relationships - many-to-many with departments
    departments = db.relationship('Department', secondary=user_departments, backref='users', lazy='dynamic')
    
    @property
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == 'admin'
    
    @property
    def is_dean(self):
        """Check if user is a dean"""
        return self.role == 'dean'
    
    def get_department_ids(self):
        """Get list of department IDs assigned to this user"""
        if self.is_admin:
            # Admins have access to all departments
            return None
        return [dept.id for dept in self.departments.all()]
    
    def has_department_access(self, department_id):
        """Check if user has access to a specific department"""
        if self.is_admin:
            return True
        if not department_id:
            return True  # Allow access to records without department
        return department_id in self.get_department_ids()
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_temporary_user(self):
        """
        Check if this is a temporary auto-generated user account.
        Temporary users have usernames like user001, user002, etc.
        and STILL have the default password 'ischedwise'
        """
        # Check if username matches the pattern user###
        if self.username.startswith('user') and len(self.username) == 7:
            try:
                # Check if the last 3 characters are digits
                int(self.username[4:])
                # Also check if they still have the default password
                if self.check_password('ischedwise'):
                    return True
            except ValueError:
                pass
        return False
    
    def is_expired_temporary_account(self):
        """
        Check if this temporary account has expired (24 hours without configuration).
        Returns True if:
        - Account is a temporary user (user### with default password)
        - Account was created more than 24 hours ago
        """
        if not self.is_temporary_user():
            return False
        
        # Check if account is older than 24 hours
        from datetime import datetime, timedelta
        if self.created_at:
            expiry_time = self.created_at + timedelta(hours=24)
            if datetime.utcnow() > expiry_time:
                return True
        
        return False
    
    def check_and_disable_if_expired(self):
        """
        Check if temporary account has expired and disable it if needed.
        Returns True if account was disabled, False otherwise.
        """
        if self.is_expired_temporary_account() and self.is_active:
            self.is_active = False
            return True
        return False
    
    def generate_reset_token(self):
        """Generate a password reset token"""
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})
    
    @staticmethod
    def verify_reset_token(token, expiration=3600):
        """
        Verify a password reset token
        
        Args:
            token: The reset token to verify
            expiration: Token expiration time in seconds (default 1 hour)
            
        Returns:
            User object if token is valid, None otherwise
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
            user_id = data.get('user_id')
            if user_id:
                return User.query.get(user_id)
        except:
            return None
        return None
    
    def __repr__(self):
        return f'<User {self.username}>'
