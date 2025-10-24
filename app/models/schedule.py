"""
Schedule Model
"""
from app.extensions import db
from datetime import datetime
from app.models.department import Section


class Schedule(db.Model):
    """Schedule model for class scheduling"""
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='SET NULL'), nullable=True)
    day_of_week = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    semester = db.Column(db.String(50), nullable=True)
    academic_year = db.Column(db.String(20), nullable=True)
    schedule_type = db.Column(db.String(20), default='lecture')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    section = db.relationship('Section', backref=db.backref('schedules', lazy=True, cascade='all, delete-orphan'))
    subject = db.relationship('Subject', backref=db.backref('schedules', lazy=True, cascade='all, delete-orphan', passive_deletes=True))
    faculty = db.relationship('Faculty', backref=db.backref('schedules', lazy=True))
    room = db.relationship('Room', backref=db.backref('schedules', lazy=True))

    def __repr__(self):
        return f'<Schedule {self.id}: {self.day_of_week} {self.start_time}-{self.end_time}>'

    def to_dict(self):
        """Convert schedule to dictionary"""
        return {
            'id': self.id,
            'section_id': self.section_id,
            'section_name': self.section.section_name if self.section else None,
            'subject_id': self.subject_id,
            'subject_code': self.subject.subject_code if self.subject else None,
            'course_description': self.subject.course_description if self.subject else None,
            'faculty_id': self.faculty_id,
            'faculty_name': self.faculty.full_name if self.faculty else 'TBA',
            'room_id': self.room_id,
            'room_number': self.room.room_number if self.room else 'TBA',
            'building_name': self.room.building.building_name if self.room and self.room.building else 'TBA',
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'schedule_type': self.schedule_type,
            'is_active': self.is_active
        }
