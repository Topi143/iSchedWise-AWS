"""
Department model — represents an academic department (e.g., College of Computing Studies).

Programs belong to a department; exports pull department_name and secretary_name from here.
Renamed from 'colleges' table for ERD clarity: Department = college-level grouping in Philippine HEIs.
"""
from app.extensions import db


class Department(db.Model):
    """Department entity for grouping programs and managing export branding"""

    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(255), nullable=False)
    department_code = db.Column(db.String(50), nullable=True)
    secretary_name = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())

    # Relationships
    programs = db.relationship('Program', backref='department', lazy=True)

    def __repr__(self):
        return f'<Department {self.department_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'department_name': self.department_name,
            'department_code': self.department_code,
            'secretary_name': self.secretary_name,
            'is_active': self.is_active,
            'program_count': len([p for p in self.programs if not p.is_archived]),
        }
