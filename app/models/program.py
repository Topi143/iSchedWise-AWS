"""
Program model — represents an academic program (e.g., BSCS, BSHM).

Renamed from 'departments' table for ERD clarity: Program = degree program offered under a Department.
"""
from app.extensions import db


class Program(db.Model):
    """Program model for organizing curricula and sections"""

    __tablename__ = 'programs'

    id = db.Column(db.Integer, primary_key=True)
    program_code = db.Column(db.String(20), nullable=False, index=True)
    program_name = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    program_logo = db.Column(db.String(255), nullable=True)
    year_levels = db.Column(db.Integer, nullable=False, default=4)
    shared_program_code = db.Column(db.String(50), nullable=True)
    shared_until_year = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_archived = db.Column(db.Boolean, default=False, index=True)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    archived_at = db.Column(db.DateTime)
    archive_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())

    # Relationships
    curricula = db.relationship('Curriculum', backref='program', lazy=True)
    sections = db.relationship('Section', backref='program', lazy=True,
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Program {self.program_code}>'

    def get_display_code(self, year_level):
        """
        Returns the display code based on year level.
        If program is shared with another program up to a certain year,
        returns combined code (e.g., 'BSCS/ACT') for those years.
        Otherwise returns just the program code (e.g., 'BSCS').
        """
        if self.shared_program_code and self.shared_until_year:
            if year_level <= self.shared_until_year:
                return f"{self.program_code}/{self.shared_program_code}"

        return self.program_code

    @property
    def display_code_with_shared(self):
        """
        Returns program code with shared program suffix if applicable.
        e.g., 'BSCS/ACT' if shared, otherwise just 'BSCS'.
        Use this for displaying program name in lists.
        """
        if self.shared_program_code:
            return f"{self.program_code}/{self.shared_program_code}"
        return self.program_code

    def archive(self, user_id=None, reason=None):
        """Mark program as archived instead of deleting."""
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        from datetime import datetime
        self.archived_at = datetime.utcnow()

    def unarchive(self):
        """Restore an archived program."""
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None

    def to_dict(self):
        """Convert program to dictionary for archive display"""
        return {
            'id': self.id,
            'program_code': self.program_code,
            'program_name': self.program_name,
            'department_id': self.department_id,
            'department_name': self.department.department_name if self.department else None,
            'secretary_name': (self.department.secretary_name if self.department else None) or None,
            'sections_count': len(self.sections),
            'curricula_count': len(self.curricula),
            'is_active': self.is_active,
            'is_archived': self.is_archived,
            'archive_reason': self.archive_reason,
            'archived_at': self.archived_at.strftime('%Y-%m-%d %H:%M:%S') if self.archived_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
