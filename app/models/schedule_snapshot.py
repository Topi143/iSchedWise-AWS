"""
Schedule Snapshot Model
Stores point-in-time snapshots of class/exam schedules as JSON for backup & restore.
"""
from app.extensions import db
from datetime import datetime
from sqlalchemy.dialects.mysql import LONGTEXT
import json


class ScheduleSnapshot(db.Model):
    """Snapshot of schedule data for a given semester, stored as JSON."""
    __tablename__ = 'schedule_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    snapshot_name = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    snapshot_scope = db.Column(db.String(20), nullable=False, default='class')  # 'class' or 'exam'
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id', ondelete='SET NULL'), nullable=True)
    schedule_data = db.Column(LONGTEXT, nullable=False)  # JSON array of schedule dicts
    schedule_count = db.Column(db.Integer, nullable=False, default=0)
    snapshot_type = db.Column(db.String(30), nullable=False, default='manual')  # manual, auto_pre_clear, auto_pre_restore
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    section = db.relationship('Section', backref=db.backref('schedule_snapshots', lazy=True))
    creator = db.relationship('User', foreign_keys=[created_by], backref=db.backref('schedule_snapshots', lazy=True))

    def __repr__(self):
        return f'<ScheduleSnapshot {self.id}: {self.snapshot_name} ({self.snapshot_scope})>'

    def get_schedule_data(self):
        """Parse and return the JSON schedule data."""
        if self.schedule_data:
            return json.loads(self.schedule_data)
        return []

    def to_dict(self):
        """Convert snapshot to dictionary for API responses."""
        return {
            'id': self.id,
            'snapshot_name': self.snapshot_name,
            'academic_year': self.academic_year,
            'semester': self.semester,
            'snapshot_scope': self.snapshot_scope,
            'section_id': self.section_id,
            'section_name': self.section.section_name if self.section else None,
            'full_section_name': self.section.full_section_name if self.section else 'All Sections',
            'schedule_count': self.schedule_count,
            'snapshot_type': self.snapshot_type,
            'created_by': self.created_by,
            'created_by_name': self.creator.full_name if self.creator else 'Unknown',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'notes': self.notes,
        }
