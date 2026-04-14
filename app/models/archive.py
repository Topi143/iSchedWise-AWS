"""
Archive Model - Stores archived schedules
"""
from app.extensions import db
from datetime import datetime


class Archive(db.Model):
    """Archive model for storing inactive/archived schedules"""
    __tablename__ = 'archives'

    id = db.Column(db.Integer, primary_key=True)
    
    # Original schedule information
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id', ondelete='SET NULL'), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='SET NULL'), nullable=True)
    
    # Schedule details (stored as text for historical record)
    section_name = db.Column(db.String(100), nullable=True)
    subject_code = db.Column(db.String(50), nullable=True)
    course_description = db.Column(db.String(255), nullable=True)
    faculty_name = db.Column(db.String(100), nullable=True)
    room_number = db.Column(db.String(20), nullable=True)
    building_name = db.Column(db.String(100), nullable=True)
    program_name = db.Column(db.String(100), nullable=True)
    
    # Schedule timing - Modified to support both class and exam schedules
    day_of_week = db.Column(db.String(20), nullable=True)  # For class schedules
    exam_date = db.Column(db.Date, nullable=True)  # For exam schedules
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    semester = db.Column(db.String(50), nullable=True)
    academic_year = db.Column(db.String(20), nullable=True)
    schedule_type = db.Column(db.String(20), default='lecture')  # 'lecture', 'lab', 'exam'
    exam_period = db.Column(db.String(20), nullable=True)  # 'Prelim', 'Midterm', 'Final'
    
    # Archive metadata
    original_schedule_id = db.Column(db.Integer, nullable=True)  # Reference to original schedule
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    section = db.relationship('Section', backref=db.backref('archives', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('archives', lazy=True))
    faculty = db.relationship('Faculty', backref=db.backref('archives', lazy=True))
    room = db.relationship('Room', backref=db.backref('archives', lazy=True))
    user = db.relationship('User', backref=db.backref('archives', lazy=True), foreign_keys=[archived_by])

    def __repr__(self):
        return f'<Archive {self.id}: {self.section_name} - {self.subject_code}>'

    def to_dict(self):
        """Convert archive to dictionary"""
        # Get program_id from section relationship if available
        program_id = None
        if self.section and self.section.program:
            program_id = self.section.program_id

        # Get faculty department info if available
        faculty_department_id = None
        faculty_department_name = None
        if self.faculty and self.faculty.department:
            faculty_department_id = self.faculty.department_id
            faculty_department_name = self.faculty.department.department_name

        return {
            'id': self.id,
            'section_id': self.section_id,
            'faculty_id': self.faculty_id,
            'room_id': self.room_id,
            'program_id': program_id,
            'faculty_department_id': faculty_department_id,
            'faculty_department_name': faculty_department_name,
            'section_name': self.section_name,
            'subject_code': self.subject_code,
            'course_description': self.course_description,
            'faculty_name': self.faculty_name,
            'room_number': self.room_number,
            'building_name': self.building_name,
            'department_name': self.program_name,
            'program_name': self.program_name,
            'day_of_week': self.day_of_week,
            'exam_date': self.exam_date.strftime('%Y-%m-%d') if self.exam_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'schedule_type': self.schedule_type,
            'exam_period': self.exam_period,
            'archive_reason': self.archive_reason,
            'archived_at': self.archived_at.strftime('%Y-%m-%d %H:%M:%S') if self.archived_at else None,
            'archived_by_name': self.user.full_name if self.user else 'System'
        }
