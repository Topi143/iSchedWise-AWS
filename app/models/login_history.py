"""
LoginHistory model - tracks user login sessions
"""
from datetime import datetime, timezone
from app.extensions import db


def _utcnow_naive():
    """Return UTC now as a naive datetime to match existing DB column types."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LoginHistory(db.Model):
    """Tracks user login/logout sessions for security monitoring"""
    __tablename__ = 'login_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    login_at = db.Column(db.DateTime, nullable=False, default=_utcnow_naive)
    logout_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(128), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='login_sessions')

    @property
    def duration_seconds(self):
        """Get session duration in seconds"""
        end = self.logout_at or _utcnow_naive()
        return int((end - self.login_at).total_seconds())

    @property
    def duration_display(self):
        """Get human-readable session duration"""
        secs = self.duration_seconds
        if secs < 60:
            return f'{secs}s'
        elif secs < 3600:
            return f'{secs // 60}m'
        else:
            hours = secs // 3600
            mins = (secs % 3600) // 60
            return f'{hours}h {mins}m'

    @classmethod
    def record_login(cls, user_id, ip_address=None, user_agent=None, session_id=None):
        """Record a new login session"""
        entry = cls(
            user_id=user_id,
            login_at=_utcnow_naive(),
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            is_active=True
        )
        db.session.add(entry)
        return entry

    @classmethod
    def record_logout(cls, session_id=None, user_id=None):
        """Record logout for a session"""
        query = cls.query.filter_by(is_active=True)
        if session_id:
            query = query.filter_by(session_id=session_id)
        elif user_id:
            query = query.filter_by(user_id=user_id)
        else:
            return

        sessions = query.all()
        for session in sessions:
            session.is_active = False
            session.logout_at = _utcnow_naive()

    @classmethod
    def force_logout(cls, session_id):
        """Force logout a specific login_history row (single session only)."""
        session = cls.query.filter_by(id=session_id, is_active=True).first()
        if session:
            session.is_active = False
            session.logout_at = _utcnow_naive()
            return True
        return False

    @classmethod
    def force_logout_all(cls, except_user_id=None):
        """Force logout all active sessions, optionally except a specific user"""
        from app.models.user import User
        query = cls.query.filter_by(is_active=True)
        if except_user_id:
            query = query.filter(cls.user_id != except_user_id)
        sessions = query.all()
        count = 0
        affected_user_ids = set()
        now = _utcnow_naive()
        for session in sessions:
            session.is_active = False
            session.logout_at = now
            affected_user_ids.add(session.user_id)
            count += 1
        # Invalidate Flask sessions for all affected users
        if affected_user_ids:
            User.query.filter(User.id.in_(affected_user_ids)).update(
                {User.force_logout_at: now}, synchronize_session='fetch'
            )
        return count

    @classmethod
    def get_active_sessions(cls):
        """Get all currently active sessions with user info"""
        return cls.query.filter_by(is_active=True)\
            .options(db.joinedload(cls.user))\
            .order_by(cls.login_at.desc()).all()

    @classmethod
    def get_active_session_count(cls):
        """Get count of active sessions"""
        return cls.query.filter_by(is_active=True).count()

    def to_dict(self):
        """Serialize login history to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else 'Unknown',
            'user_role': self.user.role if self.user else None,
            'login_at': (self.login_at.isoformat() + 'Z') if self.login_at else None,
            'logout_at': (self.logout_at.isoformat() + 'Z') if self.logout_at else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'is_active': self.is_active,
            'duration': self.duration_display,
        }

    def to_admin_dict(self):
        """Serialize login history for admin monitoring without account-identifying fields."""
        return {
            'id': self.id,
            'user_role': self.user.role if self.user else None,
            'login_at': (self.login_at.isoformat() + 'Z') if self.login_at else None,
            'logout_at': (self.logout_at.isoformat() + 'Z') if self.logout_at else None,
            'is_active': self.is_active,
            'duration': self.duration_display,
        }

    def __repr__(self):
        return f'<LoginHistory {self.id}: user={self.user_id} active={self.is_active}>'
