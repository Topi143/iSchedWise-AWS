"""
Department and Section models
"""
from app.extensions import db


class Department(db.Model):
    """Department model for organizing curricula and sections"""
    
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    department_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    department_name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_archived = db.Column(db.Boolean, default=False, index=True)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    archived_at = db.Column(db.DateTime)
    archive_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    # Relationships
    curricula = db.relationship('Curriculum', backref='department', lazy=True)
    sections = db.relationship('Section', backref='department', lazy=True, 
                              cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Department {self.department_code}>'
    
    def archive(self, user_id=None, reason=None):
        """Mark department as archived instead of deleting."""
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        from datetime import datetime
        self.archived_at = datetime.utcnow()
    
    def unarchive(self):
        """Restore an archived department."""
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
    
    def to_dict(self):
        """Convert department to dictionary for archive display"""
        return {
            'id': self.id,
            'department_code': self.department_code,
            'department_name': self.department_name,
            'sections_count': len(self.sections),
            'curricula_count': len(self.curricula),
            'is_active': self.is_active,
            'is_archived': self.is_archived,
            'archive_reason': self.archive_reason,
            'archived_at': self.archived_at.strftime('%Y-%m-%d %H:%M:%S') if self.archived_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Section(db.Model):
    """Section model for student groups"""
    
    __tablename__ = 'sections'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    section_name = db.Column(db.String(100), nullable=False)
    year_level = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    @property
    def full_section_name(self):
        """Returns the full section name format: DEPT-YEAR_LEVEL+SECTION_NAME (e.g., BSCS-1A)"""
        if self.department:
            return f"{self.department.department_code}-{self.year_level}{self.section_name}"
        return self.section_name
    
    def __repr__(self):
        return f'<Section {self.section_name}>'
