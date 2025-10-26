"""
Exam Schedule Model
"""
from app.extensions import db
from datetime import datetime


class ExamSchedule(db.Model):
    """Exam schedule model for exam scheduling"""
    __tablename__ = 'exam_schedules'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='SET NULL'), nullable=True)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    semester = db.Column(db.String(50), nullable=True)  # '1st Semester', '2nd Semester'
    academic_year = db.Column(db.String(20), nullable=True)  # e.g., '2024-2025'
    exam_period = db.Column(db.String(20), nullable=True)  # 'Prelim', 'Midterm', 'Final'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    section = db.relationship('Section', backref=db.backref('exam_schedules', lazy=True, cascade='all, delete-orphan'))
    subject = db.relationship('Subject', backref=db.backref('exam_schedules', lazy=True, cascade='all, delete-orphan', passive_deletes=True))
    faculty = db.relationship('Faculty', backref=db.backref('exam_schedules', lazy=True))
    room = db.relationship('Room', backref=db.backref('exam_schedules', lazy=True))

    def __repr__(self):
        return f'<ExamSchedule {self.id}: {self.exam_date} {self.start_time}-{self.end_time}>'

    def to_dict(self):
        """Convert exam schedule to dictionary"""
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
            'exam_date': self.exam_date.strftime('%Y-%m-%d') if self.exam_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'exam_period': self.exam_period,
            'is_active': self.is_active
        }
