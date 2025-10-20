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
