"""
Settings Model
"""
from app.extensions import db
from datetime import datetime


class AcademicSettings(db.Model):
    """Academic settings model for managing academic year, semester, exam periods, and schedule time ranges"""
    __tablename__ = 'academic_settings'

    id = db.Column(db.Integer, primary_key=True)
    academic_year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    exam_period = db.Column(db.String(20), nullable=False)  # 'Prelim', 'Midterm', 'Final'
    schedule_start_hour = db.Column(db.Integer, nullable=False, default=7)  # Start hour (0-23)
    schedule_end_hour = db.Column(db.Integer, nullable=False, default=20)  # End hour (0-23)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AcademicSettings {self.academic_year} - {self.semester}>'

    def to_dict(self):
        """Convert settings to dictionary"""
        return {
            'id': self.id,
            'academic_year': self.academic_year,
            'semester': self.semester,
            'exam_period': self.exam_period,
            'schedule_start_hour': self.schedule_start_hour,
            'schedule_end_hour': self.schedule_end_hour,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
