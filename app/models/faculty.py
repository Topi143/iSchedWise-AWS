"""
Faculty model for faculty management and subject assignments
"""
from app.extensions import db


class Faculty(db.Model):
    """Faculty model for instructors/professors"""
    
    __tablename__ = 'faculty'
    
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_initial = db.Column(db.String(5), nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # 'Male' or 'Female' for salutation (Mr./Ms.)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    max_units = db.Column(db.Integer, nullable=True)  # NULL means use system default
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
    def full_name(self):
        """Computed full name in 'Lastname, Firstname M.' format"""
        if self.middle_initial:
            mi = self.middle_initial.strip()
            # Add period if not already present and it's a single letter
            if len(mi) == 1:
                mi = f"{mi}."
            return f"{self.last_name}, {self.first_name} {mi}"
        return f"{self.last_name}, {self.first_name}"

    @property
    def assigned_subjects_count(self):
        """Count of assigned subjects"""
        return self.subject_assignments.count()
    
    def get_max_units(self):
        """
        Get the maximum units for this faculty.
        Returns individual max_units if set, otherwise returns system default.
        """
        if self.max_units is not None:
            return self.max_units
        # Import here to avoid circular imports
        from app.models.settings import AcademicSettings
        return AcademicSettings.get_default_faculty_max_units()
    
    def get_current_load(self, academic_year=None, semester=None):
        """
        Calculate the current teaching load (total units) for this faculty.
        
        This calculates based on SCHEDULES - each class/section counts separately.
        A faculty teaching the same subject to 3 sections gets 3x the units.
        
        Args:
            academic_year: Filter by academic year (optional, uses active settings if not provided)
            semester: Filter by semester (optional, uses active settings if not provided)
            
        Returns:
            Total units from all scheduled classes (units per section)
        """
        from app.models.settings import AcademicSettings
        from app.models.schedule import Schedule
        
        # Get current academic period if not specified
        if academic_year is None or semester is None:
            active_settings = AcademicSettings.query.filter_by(is_active=True).first()
            if active_settings:
                academic_year = academic_year or active_settings.academic_year
                semester = semester or active_settings.semester
        
        # Get all active schedules for this faculty (each class counts)
        schedules = Schedule.query.filter_by(
            faculty_id=self.id,
            is_active=True,
            academic_year=academic_year,
            semester=semester
        ).all()
        
        total_units = 0
        for schedule in schedules:
            if schedule.subject and schedule.subject.total_units:
                total_units += float(schedule.subject.total_units)
        
        return total_units
    
    def get_load_status(self, academic_year=None, semester=None):
        """
        Get the faculty's current load status.
        
        Args:
            academic_year: Filter by academic year (optional)
            semester: Filter by semester (optional)
            
        Returns:
            Tuple of (current_load, max_units, percentage, status)
            status: 'normal', 'warning' (>80%), 'exceeded' (>=100%)
        """
        current_load = self.get_current_load(academic_year, semester)
        max_units = self.get_max_units()
        
        if max_units > 0:
            percentage = (current_load / max_units) * 100
        else:
            percentage = 0
        
        if percentage >= 100:
            status = 'exceeded'
        elif percentage >= 80:
            status = 'warning'
        else:
            status = 'normal'
        
        return (current_load, max_units, percentage, status)
    
    def can_add_units(self, units_to_add, academic_year=None, semester=None):
        """
        Check if faculty can take on additional units.
        
        Args:
            units_to_add: Number of units to add
            academic_year: Filter by academic year (optional)
            semester: Filter by semester (optional)
            
        Returns:
            Tuple of (can_add, new_total, max_units, would_exceed)
        """
        current_load = self.get_current_load(academic_year, semester)
        max_units = self.get_max_units()
        new_total = current_load + units_to_add
        would_exceed = new_total > max_units
        
        return (not would_exceed, new_total, max_units, would_exceed)
    
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
        current_load, max_units, percentage, status = self.get_load_status()
        return {
            'id': self.id,
            'last_name': self.last_name,
            'first_name': self.first_name,
            'middle_initial': self.middle_initial,
            'full_name': self.full_name,
            'department_name': self.department.department_name if self.department else None,
            'department_code': self.department.department_code if self.department else None,
            'max_units': self.max_units,
            'effective_max_units': max_units,
            'current_load': current_load,
            'load_percentage': round(percentage, 1),
            'load_status': status,
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


class FacultyAvailability(db.Model):
    """
    Tracks proctor/faculty weekly availability for exam scheduling.
    
    Faculty can set their recurring weekly availability (e.g., available every Monday 8AM-12PM).
    This helps exam schedulers identify which proctors are available for specific time slots.
    """
    
    __tablename__ = 'faculty_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='CASCADE'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=True)  # 'Monday', 'Tuesday', etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    academic_year = db.Column(db.String(20), nullable=True)
    semester = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=db.func.current_timestamp())
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    faculty = db.relationship('Faculty', backref=db.backref('availability_slots', lazy='dynamic', cascade='all, delete-orphan'))
    creator = db.relationship('User', foreign_keys=[created_by])
    
    # Valid days of week
    VALID_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    def __repr__(self):
        return f'<FacultyAvailability {self.faculty_id} {self.day_of_week} {self.start_time}-{self.end_time}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'faculty_id': self.faculty_id,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'academic_year': self.academic_year,
            'semester': self.semester,
            'is_active': self.is_active
        }
    
    @staticmethod
    def check_faculty_available(faculty_id, check_date, start_time, end_time):
        """
        Check if a faculty member is available at a specific date/time.
        
        Args:
            faculty_id: The faculty ID to check
            check_date: The date to check (datetime.date)
            start_time: Start time to check (datetime.time)
            end_time: End time to check (datetime.time)
            
        Returns:
            dict with keys:
                - available: bool
                - status: 'available', 'not_in_schedule', or 'no_data'
        """
        # Get day of week from date
        day_name = check_date.strftime('%A')  # 'Monday', 'Tuesday', etc.
        
        # Check recurring day_of_week availability records for this day
        day_records = FacultyAvailability.query.filter_by(
            faculty_id=faculty_id,
            day_of_week=day_name,
            is_active=True
        ).all()
        
        # If there's an overlapping slot, faculty is available
        for record in day_records:
            if FacultyAvailability._times_overlap(record.start_time, record.end_time, start_time, end_time):
                return {'available': True, 'status': 'available'}
        
        # Check if faculty has ANY availability defined
        has_any_availability = FacultyAvailability.query.filter_by(
            faculty_id=faculty_id,
            is_active=True
        ).first() is not None
        
        if has_any_availability:
            return {
                'available': False,
                'status': 'not_in_schedule',
                'reason': f'Faculty is not marked as available on {day_name} at this time'
            }
        
        # No availability data at all — assume available by default
        return {'available': True, 'status': 'no_data'}
    
    @staticmethod
    def check_faculty_available_by_day(faculty_id, day_of_week, start_time, end_time):
        """
        Check if a faculty member is available at a specific day/time (for class scheduling).
        
        Args:
            faculty_id: The faculty ID to check
            day_of_week: Day name string ('Monday', 'Tuesday', etc.)
            start_time: Start time to check (datetime.time)
            end_time: End time to check (datetime.time)
            
        Returns:
            dict with keys:
                - available: bool
                - status: 'available', 'not_in_schedule', or 'no_data'
        """
        # Check recurring day_of_week availability records for this day
        day_records = FacultyAvailability.query.filter_by(
            faculty_id=faculty_id,
            day_of_week=day_of_week,
            is_active=True
        ).all()
        
        # If there's an overlapping slot, faculty is available
        for record in day_records:
            if FacultyAvailability._times_overlap(record.start_time, record.end_time, start_time, end_time):
                return {'available': True, 'status': 'available'}
        
        # Check if faculty has ANY availability defined
        has_any_availability = FacultyAvailability.query.filter_by(
            faculty_id=faculty_id,
            is_active=True
        ).first() is not None
        
        if has_any_availability:
            return {
                'available': False,
                'status': 'not_in_schedule',
                'reason': f'Faculty is not marked as available on {day_of_week} at this time'
            }
        
        # No availability data at all — assume available by default
        return {'available': True, 'status': 'no_data'}

    @staticmethod
    def _times_overlap(start1, end1, start2, end2):
        """Check if two time ranges overlap"""
        return start1 < end2 and start2 < end1
    
    @staticmethod
    def get_faculty_weekly_availability(faculty_id):
        """
        Get all recurring weekly availability for a faculty member.
        Availability is global — not tied to a specific semester or academic year.
        
        Returns dict keyed by day of week with list of time slots.
        """
        records = FacultyAvailability.query.filter_by(
            faculty_id=faculty_id,
            is_active=True
        ).filter(
            FacultyAvailability.day_of_week.isnot(None)
        ).order_by(FacultyAvailability.day_of_week, FacultyAvailability.start_time).all()
        
        result = {day: [] for day in FacultyAvailability.VALID_DAYS}
        for record in records:
            if record.day_of_week in result:
                result[record.day_of_week].append(record.to_dict())
        
        return result
    
    @staticmethod
    def get_available_proctors_for_slot(exam_date, start_time, end_time, department_id=None):
        """
        Get list of faculty members available for a specific exam slot.
        
        Returns list of faculty with their availability status.
        """
        from app.models.faculty import Faculty
        
        query = Faculty.query.filter_by(is_archived=False, is_active=True)
        
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        faculty_list = query.order_by(Faculty.last_name, Faculty.first_name).all()
        
        result = []
        for faculty in faculty_list:
            availability = FacultyAvailability.check_faculty_available(
                faculty.id, exam_date, start_time, end_time
            )
            result.append({
                'faculty': {
                    'id': faculty.id,
                    'full_name': faculty.full_name,
                    'department_id': faculty.department_id,
                    'department_name': faculty.department.department_name if faculty.department else None
                },
                'availability': availability
            })
        
        # Sort: preferred first, then available, then unavailable
        status_order = {'preferred': 0, 'available': 1, 'no_data': 2, 'unavailable': 3}
        result.sort(key=lambda x: (status_order.get(x['availability']['status'], 2), x['faculty']['full_name']))
        
        return result
