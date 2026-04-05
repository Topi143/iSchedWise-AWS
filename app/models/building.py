"""
Building and Room models for facility management
"""
from app.extensions import db
from datetime import datetime


class Building(db.Model):
    """Building model for campus buildings"""
    
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    building_name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    # Relationships
    rooms = db.relationship('Room', backref='building', cascade='all, delete-orphan', lazy='dynamic')
    
    @property
    def room_count(self):
        """Count of rooms in this building"""
        return self.rooms.count()
    
    @property
    def sorted_rooms(self):
        """Return rooms sorted by type (Lecture first, then Lab, then others) then alphabetically by room number"""
        from sqlalchemy import case
        type_order = case(
            (Room.room_type == 'Lecture', 1),
            (Room.room_type == 'Laboratory', 2),
            else_=3
        )
        return self.rooms.order_by(type_order, Room.room_number).all()
    
    def archive(self, user_id=None, reason=None):
        """Mark building as archived instead of deleting."""
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        self.archived_at = datetime.utcnow()
    
    def unarchive(self):
        """Restore building from archive."""
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
    
    def to_dict(self):
        """Convert building to dictionary for API responses."""
        return {
            'id': self.id,
            'building_name': self.building_name,
            'room_count': self.room_count,
            'is_active': self.is_active,
            'is_archived': self.is_archived,
            'archived_by': self.archived_by,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'archive_reason': self.archive_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Building {self.building_name}>'


class Room(db.Model):
    """Room model for building rooms"""
    
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False)
    room_number = db.Column(db.String(50), nullable=False)
    room_type = db.Column(db.String(50), nullable=False, default='Lecture')
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Room {self.room_number}>'
