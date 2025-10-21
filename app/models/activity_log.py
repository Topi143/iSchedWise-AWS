"""
User Activity Log model for tracking user actions
"""
from app.extensions import db
from datetime import datetime
import json


class UserActivityLog(db.Model):
    """User Activity Log model for audit trail"""
    
    __tablename__ = 'user_activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # created_schedule, edited_faculty, etc.
    entity_type = db.Column(db.String(50), nullable=False)  # schedule, faculty, building, etc.
    entity_id = db.Column(db.Integer, nullable=True)  # ID of affected entity
    entity_name = db.Column(db.String(255), nullable=True)  # Name/description of entity
    details = db.Column(db.Text, nullable=True)  # Additional details
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref='activity_logs')
    
    @staticmethod
    def log_action(user_id, action, entity_type, entity_id=None, entity_name=None, 
                   details=None, ip_address=None, user_agent=None):
        """
        Log a user action
        
        Args:
            user_id: ID of the user performing the action
            action: Action performed (e.g., 'created', 'edited', 'deleted', 'archived')
            entity_type: Type of entity (e.g., 'schedule', 'faculty', 'building')
            entity_id: ID of the affected entity (optional)
            entity_name: Name/description of the entity (optional)
            details: Additional details about the action (optional, can be dict or string)
            ip_address: User's IP address (optional)
            user_agent: User's browser/client info (optional)
        """
        # Convert details to JSON string if it's a dict
        if isinstance(details, dict):
            details = json.dumps(details)
        elif details is not None and not isinstance(details, str):
            details = str(details)
            
        log = UserActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log)
        # Don't commit here - let the calling function handle the transaction
        return log
    
    def to_dict(self):
        """Convert activity log to dictionary"""
        # Parse JSON details if it's a JSON string
        details_parsed = self.details
        if self.details:
            try:
                details_parsed = json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                details_parsed = self.details
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else 'Unknown',
            'user_role': self.user.role if self.user else 'Unknown',
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'details': details_parsed,
            'ip_address': self.ip_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
    
    def __repr__(self):
        return f'<UserActivityLog {self.id}: {self.user_id} {self.action} {self.entity_type}>'
