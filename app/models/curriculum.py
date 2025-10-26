"""
Curriculum-related models: Curriculum, YearLevel, Semester, Subject
"""
from app.extensions import db


class Curriculum(db.Model):
    """Curriculum model for degree programs"""
    
    __tablename__ = 'curricula'
    
    id = db.Column(db.Integer, primary_key=True)
    curriculum_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    degree_program = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_archived = db.Column(db.Boolean, default=False, index=True)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    archived_at = db.Column(db.DateTime)
    archive_reason = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    # Relationships
    year_levels = db.relationship('YearLevel', backref='curriculum', lazy=True, 
                                 cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Curriculum {self.curriculum_code}>'
    
    def archive(self, user_id=None, reason=None):
        """Mark curriculum as archived instead of deleting."""
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        from datetime import datetime
        self.archived_at = datetime.utcnow()
    
    def unarchive(self):
        """Restore an archived curriculum."""
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
    
    def to_dict(self):
        """Convert curriculum to dictionary for archive display"""
        return {
            'id': self.id,
            'curriculum_code': self.curriculum_code,
            'degree_program': self.degree_program,
            'department_name': self.department.department_name if self.department else None,
            'year_levels_count': len(self.year_levels),
            'is_active': self.is_active,
            'is_archived': self.is_archived,
            'archive_reason': self.archive_reason,
            'archived_at': self.archived_at.strftime('%Y-%m-%d %H:%M:%S') if self.archived_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class YearLevel(db.Model):
    """Year level model (1st Year, 2nd Year, etc.)"""
    
    __tablename__ = 'year_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    curriculum_id = db.Column(db.Integer, db.ForeignKey('curricula.id'), nullable=False)
    year_number = db.Column(db.Integer, nullable=False)
    year_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    # Relationships
    semesters = db.relationship('Semester', backref='year_level', lazy=True, 
                               cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<YearLevel {self.year_name}>'


class Semester(db.Model):
    """Semester model (1st Semester, 2nd Semester)"""
    
    __tablename__ = 'semesters'
    
    id = db.Column(db.Integer, primary_key=True)
    year_level_id = db.Column(db.Integer, db.ForeignKey('year_levels.id'), nullable=False)
    semester_number = db.Column(db.Integer, nullable=False)
    semester_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    # Relationships
    subjects = db.relationship('Subject', backref='semester', lazy=True, 
                              cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Semester {self.semester_name}>'


class Subject(db.Model):
    """Subject/Course in a specific curriculum placement"""
    
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    subject_code = db.Column(db.String(50), nullable=False, index=True)
    course_description = db.Column(db.String(255), nullable=False)
    lec_units = db.Column(db.Numeric(3, 1), nullable=False, default=0.0)
    lab_units = db.Column(db.Numeric(3, 1), nullable=False, default=0.0)
    prerequisite = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    @property
    def total_units(self):
        """Calculate total units (lecture + laboratory)"""
        return float(self.lec_units) + float(self.lab_units)
    
    def __repr__(self):
        return f'<Subject {self.subject_code}>'
