"""
Faculty model for faculty management and subject assignments
"""
from app.extensions import db


class Faculty(db.Model):
    """Faculty model for instructors/professors"""
    
    __tablename__ = 'faculty'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False, index=True)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=True, default=None, onupdate=db.func.current_timestamp())
    
    # Relationships
    department = db.relationship('Department', backref=db.backref('faculty_members', lazy='dynamic'))
    subject_assignments = db.relationship('FacultySubjectAssignment', 
                                         backref='faculty', 
                                         cascade='all, delete-orphan', 
                                         passive_deletes=True,
                                         lazy='dynamic')
    # Note: schedules relationship is defined in Schedule model with backref='schedules'
    
    @property
    def assigned_subjects_count(self):
        """Count of assigned subjects"""
        return self.subject_assignments.count()
    
    def archive(self, user_id=None, reason=None):
        """Mark faculty as archived instead of deleting."""
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        from datetime import datetime
        self.archived_at = datetime.utcnow()
    
    def unarchive(self):
        """Restore an archived faculty."""
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
    
    def to_dict(self):
        """Convert faculty to dictionary for archive display"""
        return {
            'id': self.id,
            'full_name': self.full_name,
            'department_name': self.department.department_name if self.department else None,
            'is_active': self.is_active,
            'is_archived': self.is_archived,
            'archive_reason': self.archive_reason,
            'archived_at': self.archived_at.strftime('%Y-%m-%d %H:%M:%S') if self.archived_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'assigned_subjects_count': self.assigned_subjects_count
        }
    
    def __repr__(self):
        return f'<Faculty {self.id} - {self.full_name}>'


class FacultySubjectAssignment(db.Model):
    """Faculty to Subject assignment"""
    
    __tablename__ = 'faculty_subject_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)  # e.g., '2024-2025'
    semester = db.Column(db.String(20), nullable=False)  # e.g., '1st Semester', '2nd Semester'
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=True, default=None, onupdate=db.func.current_timestamp())
    
    # Relationships
    subject = db.relationship('Subject', 
                             backref=db.backref('faculty_assignments', 
                                              cascade='all, delete-orphan', 
                                              passive_deletes=True))
    
    @property
    def display_name(self):
        """Get display name for the assignment"""
        if self.subject:
            # Get curriculum context
            semester = self.subject.semester
            year_level = semester.year_level if semester else None
            curriculum = year_level.curriculum if year_level else None
            
            context = ""
            if curriculum:
                context = f" [{curriculum.curriculum_code} - {year_level.year_name}, {semester.semester_name}]"
            
            return f"{self.subject.subject_code} - {self.subject.course_description}{context}"
        return "Unknown Assignment"
    
    @property
    def subject_code(self):
        """Get the subject code"""
        return self.subject.subject_code if self.subject else "N/A"
    
    @property
    def course_description(self):
        """Get the course description"""
        return self.subject.course_description if self.subject else ""
    
    @property
    def total_units(self):
        """Get total units"""
        return self.subject.total_units if self.subject else 0.0
    
    def __repr__(self):
        return f'<FacultySubjectAssignment Faculty:{self.faculty_id} Subject:{self.subject_id}>'

    def archive(self, user_id=None, reason=None):
        """Mark this assignment as archived instead of deleting."""
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        from datetime import datetime
        self.archived_at = datetime.utcnow()

    def unarchive(self):
        """Restore an archived assignment."""
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
