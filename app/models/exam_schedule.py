"""
Exam Schedule Model
"""
from app.extensions import db
from datetime import datetime, timedelta


# Lock timeout in minutes - after this time, lock is considered stale and can be overridden
EXAM_SCHEDULE_LOCK_TIMEOUT_MINUTES = 3


class ExamSchedule(db.Model):
    """Exam schedule model for exam scheduling with multi-user concurrency support"""
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
    schedule_type = db.Column(db.String(20), default='lecture')  # 'lecture', 'lab'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Concurrency control columns
    version = db.Column(db.Integer, default=1, nullable=False)  # Optimistic locking
    locked_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    section = db.relationship('Section', backref=db.backref('exam_schedules', lazy=True, cascade='all, delete-orphan'))
    subject = db.relationship('Subject', backref=db.backref('exam_schedules', lazy=True, cascade='all, delete-orphan', passive_deletes=True))
    faculty = db.relationship('Faculty', backref=db.backref('exam_schedules', lazy=True))
    room = db.relationship('Room', backref=db.backref('exam_schedules', lazy=True))
    locked_by_user = db.relationship('User', foreign_keys=[locked_by], backref=db.backref('locked_exam_schedules', lazy=True))

    def __repr__(self):
        return f'<ExamSchedule {self.id}: {self.exam_date} {self.start_time}-{self.end_time}>'

    def is_locked(self):
        """Check if this exam schedule is currently locked by another user"""
        if not self.locked_by or not self.locked_at:
            return False
        
        # Check if lock has expired
        lock_timeout = datetime.utcnow() - timedelta(minutes=EXAM_SCHEDULE_LOCK_TIMEOUT_MINUTES)
        if self.locked_at < lock_timeout:
            return False
        
        return True
    
    def is_locked_by_other(self, user_id):
        """Check if locked by a different user"""
        if not self.is_locked():
            return False
        return self.locked_by != user_id
    
    def acquire_lock(self, user_id):
        """Acquire edit lock for this exam schedule"""
        if self.is_locked_by_other(user_id):
            return False
        
        self.locked_by = user_id
        self.locked_at = datetime.utcnow()
        return True
    
    def release_lock(self, user_id=None):
        """Release edit lock (only if owned by user or force release)"""
        if user_id is None or self.locked_by == user_id:
            self.locked_by = None
            self.locked_at = None
            return True
        return False
    
    def get_lock_info(self):
        """Get information about current lock"""
        if not self.is_locked():
            return None
        
        return {
            'locked_by': self.locked_by,
            'locked_by_name': self.locked_by_user.full_name if self.locked_by_user else 'Unknown',
            'locked_at': self.locked_at.isoformat() if self.locked_at else None,
            'expires_at': (self.locked_at + timedelta(minutes=EXAM_SCHEDULE_LOCK_TIMEOUT_MINUTES)).isoformat() if self.locked_at else None
        }

    def has_archived_relationships(self):
        """Check if this exam schedule has any archived relationships"""
        # Check program (through section)
        if self.section and self.section.program and self.section.program.is_archived:
            return True
        
        # Check faculty
        if self.faculty and self.faculty.is_archived:
            return True
        
        # Check room and building (through room)
        if self.room:
            if not self.room.is_available:
                return True
            if self.room.building and self.room.building.is_archived:
                return True
        
        return False

    def to_dict(self):
        """Convert exam schedule to dictionary"""
        return {
            'id': self.id,
            'section_id': self.section_id,
            'section_name': self.section.section_name if self.section else None,
            'subject_id': self.subject_id,
            'subject_code': self.subject.subject_code if self.subject else None,
            'course_description': self.subject.course_description if self.subject else None,
            'curriculum_id': self.subject.semester.year_level.curriculum_id if self.subject and self.subject.semester and self.subject.semester.year_level else None,
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
            'schedule_type': self.schedule_type or 'lecture',
            'is_active': self.is_active,
            'version': self.version,
            'lock_info': self.get_lock_info()
        }
