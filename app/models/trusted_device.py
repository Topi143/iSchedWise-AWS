"""
Trusted device model for optional 2FA bypass tokens.
"""
import hashlib
from datetime import datetime, timedelta
from app.extensions import db


class TrustedDevice(db.Model):
    """Stores hashed trusted-device tokens scoped to a user."""

    __tablename__ = 'trusted_devices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('trusted_devices', lazy='dynamic', cascade='all, delete-orphan'))

    @staticmethod
    def hash_token(raw_token):
        """Hash a raw trusted-device token before persistence or comparison."""
        if not raw_token:
            return None
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @staticmethod
    def _normalize_days_valid(days_valid, fallback=1):
        """Normalize trusted-device validity window to a safe minimum."""
        try:
            parsed_value = int(days_valid)
        except Exception:
            parsed_value = fallback
        return max(1, parsed_value)

    @classmethod
    def issue_for_user(cls, user_id, raw_token, days_valid=1, label=None, ip_address=None, user_agent=None):
        """Create a trusted-device record for a user."""
        now = datetime.utcnow()
        resolved_days = cls._normalize_days_valid(days_valid)
        device = cls(
            user_id=user_id,
            token_hash=cls.hash_token(raw_token),
            label=label,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + timedelta(days=resolved_days),
            last_used_at=now,
        )
        db.session.add(device)
        return device

    @classmethod
    def find_valid_for_user(cls, user_id, raw_token, extend_days=None):
        """Return valid trusted device row if token matches and is not expired."""
        token_hash = cls.hash_token(raw_token)
        if not token_hash:
            return None

        now = datetime.utcnow()
        device = cls.query.filter_by(user_id=user_id, token_hash=token_hash).first()
        if not device:
            return None

        if device.expires_at <= now:
            db.session.delete(device)
            db.session.flush()
            return None

        device.last_used_at = now
        if extend_days is not None:
            device.expires_at = now + timedelta(days=cls._normalize_days_valid(extend_days))
        db.session.flush()
        return device

    @classmethod
    def revoke_all_for_user(cls, user_id):
        """Delete all trusted devices for a user and return revoked row count."""
        return cls.query.filter_by(user_id=user_id).delete(synchronize_session=False)

    @classmethod
    def revoke_one_for_user(cls, user_id, device_id):
        """Delete one trusted device for a user and return deleted row count."""
        return cls.query.filter_by(user_id=user_id, id=device_id).delete(synchronize_session=False)

    @classmethod
    def active_for_user(cls, user_id):
        """List active (non-expired) trusted devices for a user."""
        now = datetime.utcnow()
        return cls.query.filter(
            cls.user_id == user_id,
            cls.expires_at > now,
        ).order_by(cls.created_at.desc()).all()

    def to_dict(self):
        """Serialize trusted device metadata for profile UI."""
        return {
            'id': self.id,
            'label': self.label,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }

    def __repr__(self):
        return f'<TrustedDevice {self.id} user={self.user_id}>'
