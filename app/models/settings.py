"""
Settings Model
"""
from app.extensions import db
from datetime import datetime, time, date


class AcademicSettings(db.Model):
    """Academic settings model for managing academic year, semester, exam periods, and schedule time ranges"""
    __tablename__ = 'academic_settings'

    id = db.Column(db.Integer, primary_key=True)
    academic_year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    exam_period = db.Column(db.String(20), nullable=False)  # 'Prelim', 'Midterm', 'Final'
    exam_period_start = db.Column(db.Date, nullable=True)  # Start date of exam period
    exam_period_end = db.Column(db.Date, nullable=True)  # End date of exam period
    available_semesters = db.Column(db.String(100), nullable=False, default='1st Semester,2nd Semester')  # Comma-separated list
    schedule_start_hour = db.Column(db.Integer, nullable=False, default=7)  # Legacy class schedule start hour (0-23)
    schedule_end_hour = db.Column(db.Integer, nullable=False, default=20)  # Legacy class schedule end hour (0-23)
    exam_start_hour = db.Column(db.Integer, nullable=False, default=7)  # Legacy exam schedule start hour (0-23)
    exam_end_hour = db.Column(db.Integer, nullable=False, default=17)  # Legacy exam schedule end hour (0-23)
    schedule_start_time = db.Column(db.Time, nullable=False, default=time(7, 0))  # Class schedule start time (HH:MM)
    schedule_end_time = db.Column(db.Time, nullable=False, default=time(20, 0))  # Class schedule end time (HH:MM)
    exam_start_time = db.Column(db.Time, nullable=False, default=time(7, 0))  # Exam schedule start time (HH:MM)
    exam_end_time = db.Column(db.Time, nullable=False, default=time(17, 0))  # Exam schedule end time (HH:MM)
    exam_lunch_start = db.Column(db.Time, nullable=False, default=time(12, 0))  # Exam lunch break start
    exam_lunch_end = db.Column(db.Time, nullable=False, default=time(13, 0))  # Exam lunch break end
    exam_slot_duration = db.Column(db.Integer, nullable=False, default=30)  # Exam time slot duration in minutes
    exam_duration_limit = db.Column(db.Integer, nullable=False, default=120)  # Max exam duration in minutes (e.g., 120 = 2 hours)
    default_faculty_max_units = db.Column(db.Integer, nullable=False, default=24)  # Default max teaching units
    smart_max_backtracks_per_subject = db.Column(db.Integer, nullable=False, default=3)  # Smart scheduler per-subject backtrack limit
    smart_max_total_backtracks = db.Column(db.Integer, nullable=False, default=50)  # Smart scheduler total backtrack limit
    smart_timeout_seconds = db.Column(db.Integer, nullable=False, default=30)  # Smart scheduler timeout in seconds
    operation_days = db.Column(db.String(255), nullable=False, default='Monday,Tuesday,Wednesday,Thursday,Friday,Saturday')  # Comma-separated operation days
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
            'exam_period_start': self.exam_period_start.strftime('%Y-%m-%d') if self.exam_period_start else None,
            'exam_period_end': self.exam_period_end.strftime('%Y-%m-%d') if self.exam_period_end else None,
            'available_semesters': self.available_semesters,
            'schedule_start_hour': self.schedule_start_hour,
            'schedule_end_hour': self.schedule_end_hour,
            'exam_start_hour': self.exam_start_hour,
            'exam_end_hour': self.exam_end_hour,
            'schedule_start_time': self.schedule_start_time.strftime('%H:%M') if self.schedule_start_time else f"{int(self.schedule_start_hour or 7):02d}:00",
            'schedule_end_time': self.schedule_end_time.strftime('%H:%M') if self.schedule_end_time else f"{int(self.schedule_end_hour or 20):02d}:00",
            'exam_start_time': self.exam_start_time.strftime('%H:%M') if self.exam_start_time else f"{int(self.exam_start_hour or 7):02d}:00",
            'exam_end_time': self.exam_end_time.strftime('%H:%M') if self.exam_end_time else f"{int(self.exam_end_hour or 17):02d}:00",
            'exam_lunch_start': self.exam_lunch_start.strftime('%H:%M') if self.exam_lunch_start else '12:00',
            'exam_lunch_end': self.exam_lunch_end.strftime('%H:%M') if self.exam_lunch_end else '13:00',
            'exam_slot_duration': self.exam_slot_duration,
            'exam_duration_limit': self.exam_duration_limit,
            'default_faculty_max_units': self.default_faculty_max_units,
            'smart_max_backtracks_per_subject': self.smart_max_backtracks_per_subject,
            'smart_max_total_backtracks': self.smart_max_total_backtracks,
            'smart_timeout_seconds': self.smart_timeout_seconds,
            'operation_days': self.operation_days,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
    
    def get_operation_days_list(self):
        """Return operation days as a Python list"""
        if self.operation_days:
            return [d.strip() for d in self.operation_days.split(',') if d.strip()]
        return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    @staticmethod
    def get_active_operation_days():
        """Get the operation days list from active settings"""
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if active_settings:
            return active_settings.get_operation_days_list()
        return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    @staticmethod
    def get_default_faculty_max_units():
        """Get the default faculty max units from active settings"""
        active_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if active_settings:
            return active_settings.default_faculty_max_units
        return 24  # Fallback default


class InstitutionSettings(db.Model):
    """Institution settings model for managing institution name and logo (admin only)"""
    __tablename__ = 'institution_settings'

    id = db.Column(db.Integer, primary_key=True)
    institution_name = db.Column(db.String(255), nullable=False, default='Norzagaray College')
    system_name = db.Column(db.String(255), nullable=True)
    institution_logo = db.Column(db.String(255), nullable=True)  # Path to left logo image (institution seal)
    branding_logo = db.Column(db.String(255), nullable=True)  # Path to global app logo (sidebar/navbar/favicon)
    institution_logo_right = db.Column(db.String(255), nullable=True)  # Path to right logo image (e.g., Bagong Pilipinas)
    institution_head = db.Column(db.String(255), nullable=True)  # Name of institution head
    excel_header_line1 = db.Column(db.String(255), nullable=True, default='Republic of the Philippines')
    excel_header_line2 = db.Column(db.String(255), nullable=True, default='Municipality of Norzagaray')
    excel_schedule_color = db.Column(db.String(7), nullable=True, default='')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationship
    updater = db.relationship('User', backref='institution_updates', foreign_keys=[updated_by])

    def __repr__(self):
        return f'<InstitutionSettings {self.institution_name}>'

    def to_dict(self):
        """Convert settings to dictionary"""
        return {
            'id': self.id,
            'institution_name': self.institution_name,
            'system_name': self.system_name,
            'institution_logo': self.institution_logo,
            'branding_logo': self.branding_logo,
            'institution_logo_right': self.institution_logo_right,
            'institution_head': self.institution_head,
            'excel_header_line1': self.excel_header_line1 or 'Republic of the Philippines',
            'excel_header_line2': self.excel_header_line2 or 'Municipality of Norzagaray',
            'excel_schedule_color': self.excel_schedule_color or '',
            'updated_by': self.updated_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    @staticmethod
    def get_settings():
        """Get the current institution settings (creates default if none exists)"""
        settings = InstitutionSettings.query.first()
        if not settings:
            settings = InstitutionSettings(institution_name='Norzagaray College', system_name='iSchedWise')
            db.session.add(settings)
            db.session.commit()
        return settings
