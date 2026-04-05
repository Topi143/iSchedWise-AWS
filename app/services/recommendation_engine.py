"""
Recommendation Engine Service
Generates smart schedule recommendations with workload balancing
"""
from datetime import time, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.services.conflict_detector import ConflictDetector


@dataclass
class Recommendation:
    """Represents a scheduling recommendation"""
    type: str  # 'time_slot', 'day', 'room', 'faculty', 'date'
    priority: int  # Lower = higher priority
    message: str
    options: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            'type': self.type,
            'priority': self.priority,
            'message': self.message,
            'title': self.message,  # Alias for JS compatibility
            'options': self.options
        }


class RecommendationEngine:
    """
    Generates smart schedule recommendations with workload awareness
    No AI API calls - pure algorithmic recommendations
    """
    
    # Workload limits (configurable)
    MAX_FACULTY_WEEKLY_UNITS = 21  # Maximum teaching units per week
    MAX_FACULTY_DAILY_HOURS = 6    # Maximum hours per day
    PREFERRED_DAILY_HOURS = 4      # Preferred max hours per day
    
    def __init__(self):
        self.conflict_detector = ConflictDetector()

    # ─── Score Normalization & Reason Generation (B3) ────────────

    def _normalize_score(self, raw_score: int, min_possible: int = 0, max_possible: int = 130) -> int:
        """Normalize a raw internal score to a 0-100 confidence percentage.

        Args:
            raw_score: The raw score from a scoring function
            min_possible: Worst-case score (maps to 0%)
            max_possible: Best-case score (maps to 100%)

        Returns:
            int in 0..100
        """
        if max_possible == min_possible:
            return 50
        normalized = ((raw_score - min_possible) / (max_possible - min_possible)) * 100
        return max(0, min(100, round(normalized)))

    def _generate_time_reason(self, time_score: int, workload_warning: bool, faculty_daily_hours: float, duration_hours: float) -> str:
        """Build a human-readable reason string for a time-slot recommendation."""
        parts = ['No conflicts']
        if time_score >= 90:
            parts.append('Preferred time slot')
        elif time_score >= 70:
            parts.append('Good time slot')
        else:
            parts.append('Less preferred time')
        if workload_warning:
            if (faculty_daily_hours + duration_hours) > self.MAX_FACULTY_DAILY_HOURS:
                parts.append('Exceeds daily limit')
            else:
                parts.append('Near daily limit')
        else:
            parts.append('Balanced workload')
        return ' \u2022 '.join(parts[:3])

    def _generate_day_reason(self, day_score: int, faculty_hours: float, duration_hours: float) -> str:
        """Build a reason string for a day recommendation."""
        parts = ['No conflicts']
        if faculty_hours == 0:
            parts.append('Fresh day for faculty')
        elif faculty_hours + duration_hours > self.MAX_FACULTY_DAILY_HOURS:
            parts.append('Exceeds daily limit')
        elif faculty_hours + duration_hours > self.PREFERRED_DAILY_HOURS:
            parts.append('Near daily limit')
        else:
            parts.append(f'{faculty_hours:.0f}h already scheduled')
        if day_score >= 90:
            parts.append('Preferred day')
        elif day_score < 70:
            parts.append('Weekend slot')
        return ' \u2022 '.join(parts[:3])

    def _generate_room_reason(self, same_type: bool, same_building: bool, room_type: str) -> str:
        """Build a reason string for a room recommendation."""
        parts = ['Available']
        if same_type:
            parts.append('Room type matches')
        else:
            parts.append(room_type + ' room')
        if same_building:
            parts.append('Same building')
        return ' \u2022 '.join(parts[:3])

    def _generate_faculty_reason(self, weekly_hours: float, daily_hours: float) -> str:
        """Build a reason string for a faculty recommendation."""
        parts = ['Available at this time']
        if weekly_hours >= self.MAX_FACULTY_WEEKLY_UNITS:
            parts.append('Overloaded')
        elif weekly_hours > self.MAX_FACULTY_WEEKLY_UNITS * 0.8:
            parts.append('High workload')
        elif weekly_hours < self.MAX_FACULTY_WEEKLY_UNITS * 0.5:
            parts.append('Light workload')
        else:
            parts.append(f'{weekly_hours:.0f}/{self.MAX_FACULTY_WEEKLY_UNITS} hrs/week')
        if daily_hours == 0:
            parts.append('Free this day')
        return ' \u2022 '.join(parts[:3])
    
    def generate_class_recommendations(
        self,
        schedule_data: Dict,
        conflicts: List,
        existing_schedules: List,
        subject = None,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Recommendation]:
        """
        Generate recommendations for class schedule conflicts
        
        Args:
            schedule_data: Current schedule form data
            conflicts: List of detected conflicts
            existing_schedules: All existing schedules
            subject: Subject object (for unit info)
            
        Returns:
            List of Recommendation objects sorted by priority
        """
        recommendations = []
        
        # Get conflict types present
        conflict_types = set(c.type.value if hasattr(c.type, 'value') else c.type for c in conflicts)
        
        # Always suggest alternative time slots
        alt_times = self._find_alternative_times(
            schedule_data,
            existing_schedules,
            subject,
            exclude_schedule_id=exclude_schedule_id
        )
        if alt_times:
            recommendations.append(Recommendation(
                type='time_slot',
                priority=1,
                message='Alternative time slots on the same day',
                options=alt_times
            ))
        
        # Suggest alternative days
        alt_days = self._find_alternative_days(
            schedule_data,
            existing_schedules,
            exclude_schedule_id=exclude_schedule_id
        )
        if alt_days:
            recommendations.append(Recommendation(
                type='day',
                priority=2,
                message='Alternative days with the same time',
                options=alt_days
            ))
        
        # Suggest alternative rooms if room conflict
        if 'room' in conflict_types:
            alt_rooms = self._find_alternative_rooms(
                schedule_data,
                existing_schedules,
                subject,
                exclude_schedule_id=exclude_schedule_id
            )
            if alt_rooms:
                recommendations.append(Recommendation(
                    type='room',
                    priority=3,
                    message='Available rooms for this time slot',
                    options=alt_rooms
                ))
        
        # Suggest alternative faculty if faculty conflict
        if 'faculty' in conflict_types:
            alt_faculty = self._find_alternative_faculty(
                schedule_data,
                existing_schedules,
                exclude_schedule_id=exclude_schedule_id
            )
            if alt_faculty:
                recommendations.append(Recommendation(
                    type='faculty',
                    priority=4,
                    message='Available faculty for this subject',
                    options=alt_faculty
                ))
        
        return sorted(recommendations, key=lambda r: r.priority)
    
    def generate_exam_recommendations(
        self,
        exam_data: Dict,
        conflicts: List,
        existing_exams: List
    ) -> List[Recommendation]:
        """
        Generate recommendations for exam schedule conflicts
        
        Args:
            exam_data: Current exam form data
            conflicts: List of detected conflicts
            existing_exams: All existing exam schedules
            
        Returns:
            List of Recommendation objects sorted by priority
        """
        recommendations = []
        
        # Check for duplicate conflict - no recommendations for duplicates
        has_duplicate = any(
            (c.type.value if hasattr(c.type, 'value') else c.type) == 'duplicate' 
            for c in conflicts
        )
        if has_duplicate:
            return []  # User should not create duplicate exams
        
        conflict_types = set(c.type.value if hasattr(c.type, 'value') else c.type for c in conflicts)
        
        # Suggest alternative time slots on same date
        alt_times = self._find_alternative_exam_times(
            exam_data,
            existing_exams
        )
        if alt_times:
            recommendations.append(Recommendation(
                type='time_slot',
                priority=1,
                message='Alternative time slots on the same date',
                options=alt_times
            ))
        
        # Suggest alternative dates
        alt_dates = self._find_alternative_exam_dates(
            exam_data,
            existing_exams
        )
        if alt_dates:
            recommendations.append(Recommendation(
                type='date',
                priority=2,
                message='Alternative dates for this exam',
                options=alt_dates
            ))
        
        # Suggest alternative rooms if room conflict
        if 'room' in conflict_types:
            alt_rooms = self._find_alternative_exam_rooms(
                exam_data,
                existing_exams
            )
            if alt_rooms:
                recommendations.append(Recommendation(
                    type='room',
                    priority=3,
                    message='Available rooms for this exam',
                    options=alt_rooms
                ))
        
        # Suggest alternative faculty if faculty conflict
        if 'faculty' in conflict_types:
            alt_faculty = self._find_alternative_exam_faculty(
                exam_data,
                existing_exams
            )
            if alt_faculty:
                recommendations.append(Recommendation(
                    type='faculty',
                    priority=4,
                    message='Available faculty to proctor',
                    options=alt_faculty
                ))
        
        return sorted(recommendations, key=lambda r: r.priority)
    
    def _find_alternative_times(
        self,
        schedule_data: Dict,
        existing_schedules: List,
        subject = None,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Dict]:
        """Find alternative time slots on the same day with workload awareness and faculty availability"""
        from app.models.settings import AcademicSettings
        from app.models.faculty import FacultyAvailability
        
        alternatives = []
        day = schedule_data.get('day_of_week')
        section_id = schedule_data.get('section_id')
        faculty_id = schedule_data.get('faculty_id')
        room_id = schedule_data.get('room_id')
        
        # Get time range from settings - MUST respect Schedule Time Range
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if current_settings:
            start_hour = (current_settings.schedule_start_time.hour if current_settings.schedule_start_time else 7)
            end_hour = (current_settings.schedule_end_time.hour if current_settings.schedule_end_time else 20)
            print(f"[RECOMMENDATIONS] Using settings time range: {start_hour}:00 - {end_hour}:00")
        else:
            # Fallback defaults if no settings found
            start_hour = 7
            end_hour = 20
            print("[RECOMMENDATIONS] No active settings found, using defaults 7:00 - 20:00")
        
        # Calculate required duration based on INPUTTED start and end time
        # This allows users to specify their preferred duration directly
        input_start_time = schedule_data.get('start_time')
        input_end_time = schedule_data.get('end_time')
        
        if input_start_time and input_end_time:
            # Parse times if they're strings
            if isinstance(input_start_time, str):
                input_start_time = datetime.strptime(input_start_time, '%H:%M').time()
            if isinstance(input_end_time, str):
                input_end_time = datetime.strptime(input_end_time, '%H:%M').time()
            
            # Calculate duration from inputted times (e.g., 3PM to 7PM = 4 hours = 240 minutes)
            input_start_dt = datetime.combine(datetime.today(), input_start_time)
            input_end_dt = datetime.combine(datetime.today(), input_end_time)
            required_minutes = int((input_end_dt - input_start_dt).seconds // 60)
        else:
            # Default: 90 minutes when no input times provided
            required_minutes = 90
        
        # Check if faculty is available on this day at all
        # If faculty is explicitly unavailable or not in their schedule, don't recommend any time slots
        if faculty_id and day:
            check_start = time(start_hour, 0)
            check_end = time(end_hour, 0)
            availability_result = FacultyAvailability.check_faculty_available_by_day(
                faculty_id, day, check_start, check_end
            )
            status = availability_result.get('status')
            if status in ('unavailable', 'not_in_schedule'):
                # Faculty is unavailable on this day, don't recommend any times
                return []
        
        # Calculate faculty's daily workload for this day
        faculty_daily_hours = 0
        if faculty_id:
            for sched in existing_schedules:
                if exclude_schedule_id and getattr(sched, 'id', None) == exclude_schedule_id:
                    continue
                if sched.faculty_id == faculty_id and sched.day_of_week == day:
                    duration = (datetime.combine(datetime.today(), sched.end_time) - 
                               datetime.combine(datetime.today(), sched.start_time)).seconds / 3600
                    faculty_daily_hours += duration
        
        # Generate time slots (30-minute intervals)
        current_dt = datetime.combine(datetime.today(), time(start_hour, 0))
        end_limit = datetime.combine(datetime.today(), time(end_hour, 0))
        
        while current_dt <= end_limit:
            slot_start = current_dt.time()
            slot_end_dt = current_dt + timedelta(minutes=required_minutes)
            
            # Check if slot END TIME fits within the configured schedule time range
            # Must compare datetime objects (not time) to handle midnight crossing correctly
            if slot_end_dt > end_limit:
                current_dt += timedelta(minutes=30)
                continue
            
            slot_end = slot_end_dt.time()
            
            # Check faculty availability for this specific time slot
            if faculty_id and day:
                availability_result = FacultyAvailability.check_faculty_available_by_day(
                    faculty_id, day, slot_start, slot_end
                )
                status = availability_result.get('status')
                if status in ('unavailable', 'not_in_schedule'):
                    # Skip this time slot - faculty is not available
                    current_dt += timedelta(minutes=30)
                    continue
            
            # Check for conflicts
            has_conflict = False
            for sched in existing_schedules:
                if exclude_schedule_id and getattr(sched, 'id', None) == exclude_schedule_id:
                    continue
                if sched.day_of_week != day:
                    continue
                
                if not self.conflict_detector.times_overlap(slot_start, slot_end, sched.start_time, sched.end_time):
                    continue
                
                if (sched.section_id == section_id or
                    (faculty_id and sched.faculty_id == faculty_id) or
                    (room_id and sched.room_id == room_id)):
                    has_conflict = True
                    break
            
            if not has_conflict:
                # Calculate slot score with workload awareness
                time_pref_score = self._calculate_time_slot_score(slot_start)
                base_score = time_pref_score
                
                # Penalize if faculty would exceed preferred daily hours
                duration_hours = required_minutes / 60
                workload_warning = False
                if faculty_id and (faculty_daily_hours + duration_hours) > self.PREFERRED_DAILY_HOURS:
                    base_score -= 20
                    workload_warning = True
                if faculty_id and (faculty_daily_hours + duration_hours) > self.MAX_FACULTY_DAILY_HOURS:
                    base_score -= 40
                
                alternatives.append({
                    'start_time': slot_start.strftime('%H:%M'),
                    'end_time': slot_end.strftime('%H:%M'),
                    'display': f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}",
                    'score': base_score,
                    'confidence': self._normalize_score(base_score, 10, 100),
                    'reason': self._generate_time_reason(time_pref_score, workload_warning, faculty_daily_hours, duration_hours),
                    'workload_warning': workload_warning
                })
            
            current_dt += timedelta(minutes=30)
        
        # Sort by score descending
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)[:5]
    
    def _find_alternative_days(
        self,
        schedule_data: Dict,
        existing_schedules: List,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Dict]:
        """Find alternative days with workload balancing and faculty availability filtering"""
        from app.models.faculty import FacultyAvailability
        
        alternatives = []
        from app.models.settings import AcademicSettings
        days = AcademicSettings.get_active_operation_days()
        
        current_day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        section_id = schedule_data.get('section_id')
        faculty_id = schedule_data.get('faculty_id')
        room_id = schedule_data.get('room_id')
        
        if not start_time or not end_time:
            return []
        
        # Calculate faculty's workload per day
        faculty_day_hours = {day: 0 for day in days}
        if faculty_id:
            for sched in existing_schedules:
                if exclude_schedule_id and getattr(sched, 'id', None) == exclude_schedule_id:
                    continue
                if sched.faculty_id == faculty_id:
                    duration = (datetime.combine(datetime.today(), sched.end_time) - 
                               datetime.combine(datetime.today(), sched.start_time)).seconds / 3600
                    faculty_day_hours[sched.day_of_week] = faculty_day_hours.get(sched.day_of_week, 0) + duration
        
        duration_hours = (datetime.combine(datetime.today(), end_time) - 
                         datetime.combine(datetime.today(), start_time)).seconds / 3600
        
        for day in days:
            if day == current_day:
                continue
            
            # Check faculty availability for this day FIRST
            if faculty_id:
                availability_result = FacultyAvailability.check_faculty_available_by_day(
                    faculty_id, day, start_time, end_time
                )
                # Skip days where faculty is explicitly unavailable OR not in their schedule
                status = availability_result.get('status')
                if status in ('unavailable', 'not_in_schedule'):
                    continue
            
            # Check if this day/time is free
            has_conflict = False
            for sched in existing_schedules:
                if exclude_schedule_id and getattr(sched, 'id', None) == exclude_schedule_id:
                    continue
                if sched.day_of_week != day:
                    continue
                
                if not self.conflict_detector.times_overlap(start_time, end_time, sched.start_time, sched.end_time):
                    continue
                
                if (sched.section_id == section_id or
                    (faculty_id and sched.faculty_id == faculty_id) or
                    (room_id and sched.room_id == room_id)):
                    has_conflict = True
                    break
            
            if not has_conflict:
                # Calculate day score with workload balancing
                base_score = self._calculate_day_score(day)
                
                # Bonus for days with less faculty workload (better distribution)
                current_hours = faculty_day_hours.get(day, 0) if faculty_id else 0
                if faculty_id:
                    if current_hours == 0:
                        base_score += 15  # Bonus for spreading across more days
                    elif current_hours + duration_hours <= self.PREFERRED_DAILY_HOURS:
                        base_score += 5
                    elif current_hours + duration_hours > self.MAX_FACULTY_DAILY_HOURS:
                        base_score -= 30  # Strong penalty for overloading
                
                alternatives.append({
                    'day': day,
                    'display': f"{day} ({start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')})",
                    'score': base_score,
                    'confidence': self._normalize_score(base_score, 10, 115),
                    'reason': self._generate_day_reason(self._calculate_day_score(day), current_hours, duration_hours),
                    'faculty_hours': current_hours if faculty_id else None
                })
        
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)[:4]
    
    def _find_alternative_rooms(
        self,
        schedule_data: Dict,
        existing_schedules: List,
        subject = None,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Dict]:
        """Find alternative available rooms with type matching and building preference"""
        from app.models.building import Room
        from app.models.curriculum import Subject
        
        alternatives = []
        day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        current_room_id = schedule_data.get('room_id')
        subject_id = schedule_data.get('subject_id')
        
        # Get the currently selected room to check its type and building
        current_room = Room.query.get(current_room_id) if current_room_id else None
        current_room_type = current_room.room_type if current_room else None
        current_building_id = current_room.building_id if current_room else None
        
        # Determine allowed room types based on subject
        allowed_types = ['Lecture']
        if subject_id and not subject:
            subject = Subject.query.get(subject_id)
        
        if subject:
            subject_code_lower = subject.subject_code.lower()
            subject_desc_lower = subject.course_description.lower()
            
            # PE/Sports check
            is_pe = any(kw in subject_code_lower for kw in ['pe', 'pathfit', 'p.e.']) or \
                    any(kw in subject_desc_lower for kw in ['physical education', 'sports', 'fitness'])
            
            if is_pe:
                allowed_types = ['Court/Gym']
            elif subject.lab_units > 0 and subject.lec_units > 0:
                allowed_types = ['Lecture', 'Laboratory']
            elif subject.lab_units > 0:
                allowed_types = ['Laboratory']
        
        # If current room is a Lab, allow both Lab and Lecture rooms in the SAME building
        prefer_same_building = False
        if current_room_type == 'Laboratory':
            allowed_types = ['Laboratory', 'Lecture']
            prefer_same_building = True
        
        # Get available rooms
        all_rooms = Room.query.filter(
            Room.is_available == True,
            Room.room_type.in_(allowed_types)
        ).all()
        
        for room in all_rooms:
            if room.id == current_room_id:
                continue
            
            # If we prefer same building (lab selected), only recommend rooms in same building
            if prefer_same_building and current_building_id:
                if room.building_id != current_building_id:
                    continue  # Skip rooms not in the same building
            
            # Check if room is free
            is_free = True
            for sched in existing_schedules:
                if exclude_schedule_id and getattr(sched, 'id', None) == exclude_schedule_id:
                    continue
                if sched.room_id != room.id or sched.day_of_week != day:
                    continue
                
                if self.conflict_detector.times_overlap(start_time, end_time, sched.start_time, sched.end_time):
                    is_free = False
                    break
            
            if is_free:
                # Calculate score - prioritize same room type, then same building
                score = 100
                same_type = bool(current_room_type and room.room_type == current_room_type)
                same_building = bool(current_building_id and room.building_id == current_building_id)
                if same_type:
                    score += 20  # Bonus for same room type
                if same_building:
                    score += 10  # Bonus for same building
                
                alternatives.append({
                    'room_id': room.id,
                    'display': f"{room.room_number} ({room.building.building_name if room.building else 'N/A'}) - {room.room_type}",
                    'room_type': room.room_type,
                    'building': room.building.building_name if room.building else 'Unknown',
                    'score': score,
                    'confidence': self._normalize_score(score, 80, 130),
                    'reason': self._generate_room_reason(same_type, same_building, room.room_type)
                })
        
        return sorted(alternatives, key=lambda x: (-x['score'], x['display']))[:6]
    
    def _find_alternative_faculty(
        self,
        schedule_data: Dict,
        existing_schedules: List,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Dict]:
        """Find alternative faculty with workload awareness"""
        from app.models.faculty import Faculty, FacultySubjectAssignment
        from app.models.settings import AcademicSettings
        
        alternatives = []
        day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        subject_id = schedule_data.get('subject_id')
        current_faculty_id = schedule_data.get('faculty_id')
        
        if not subject_id:
            return []
        
        # Get current settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return []
        
        # Get faculty assigned to this subject
        assignments = FacultySubjectAssignment.query.filter_by(
            subject_id=subject_id,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            is_active=True,
            is_archived=False
        ).all()
        
        faculty_ids = list(set(a.faculty_id for a in assignments))
        assigned_faculty = Faculty.query.filter(
            Faculty.id.in_(faculty_ids),
            Faculty.is_active == True,
            Faculty.is_archived == False
        ).all()
        
        for faculty in assigned_faculty:
            if faculty.id == current_faculty_id:
                continue
            
            # Check if faculty is free at this time
            is_free = True
            weekly_hours = 0
            daily_hours = 0
            
            for sched in existing_schedules:
                if exclude_schedule_id and getattr(sched, 'id', None) == exclude_schedule_id:
                    continue
                if sched.faculty_id != faculty.id:
                    continue
                
                # Calculate weekly hours
                duration = (datetime.combine(datetime.today(), sched.end_time) - 
                           datetime.combine(datetime.today(), sched.start_time)).seconds / 3600
                weekly_hours += duration
                
                # Calculate daily hours for this day
                if sched.day_of_week == day:
                    daily_hours += duration
                    
                    # Check time conflict
                    if self.conflict_detector.times_overlap(start_time, end_time, sched.start_time, sched.end_time):
                        is_free = False
            
            if is_free:
                # Calculate score based on workload
                score = 100
                
                # Prefer faculty with less workload
                if weekly_hours >= self.MAX_FACULTY_WEEKLY_UNITS:
                    score -= 50  # Strong penalty for overloaded faculty
                elif weekly_hours > self.MAX_FACULTY_WEEKLY_UNITS * 0.8:
                    score -= 20  # Moderate penalty
                else:
                    score += int((self.MAX_FACULTY_WEEKLY_UNITS - weekly_hours) / 2)  # Bonus for availability
                
                alternatives.append({
                    'faculty_id': faculty.id,
                    'display': f"{faculty.full_name} ({faculty.department.department_code if faculty.department else 'N/A'})",
                    'weekly_hours': weekly_hours,
                    'daily_hours': daily_hours,
                    'workload_info': f"{weekly_hours:.1f}/{self.MAX_FACULTY_WEEKLY_UNITS} hrs/week",
                    'score': score,
                    'confidence': self._normalize_score(score, 50, 110),
                    'reason': self._generate_faculty_reason(weekly_hours, daily_hours)
                })
        
        # Sort by score (prefer less loaded faculty)
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)[:5]
    
    def _find_alternative_exam_times(
        self,
        exam_data: Dict,
        existing_exams: List
    ) -> List[Dict]:
        """Find alternative exam time slots on the same date using settings and faculty availability"""
        from app.models.settings import AcademicSettings
        from app.models.faculty import FacultyAvailability
        
        alternatives = []
        exam_date = exam_data.get('exam_date')
        section_id = exam_data.get('section_id')
        faculty_id = exam_data.get('faculty_id')
        room_id = exam_data.get('room_id')
        
        # Get settings for exam hours, lunch break, and duration limit
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        if current_settings:
            exam_start_hour = (current_settings.exam_start_time.hour if current_settings.exam_start_time else 7)
            exam_end_hour = (current_settings.exam_end_time.hour if current_settings.exam_end_time else 17)
            duration_limit = getattr(current_settings, 'exam_duration_limit', 120) or 120
            lunch_start = current_settings.exam_lunch_start
            lunch_end = current_settings.exam_lunch_end
        else:
            # Fallback defaults
            exam_start_hour = 7
            exam_end_hour = 17
            duration_limit = 120
            lunch_start = time(12, 0)
            lunch_end = time(13, 0)
        
        # Convert lunch times to minutes for easier comparison
        lunch_start_mins = (lunch_start.hour * 60 + lunch_start.minute) if lunch_start else 720  # 12:00
        lunch_end_mins = (lunch_end.hour * 60 + lunch_end.minute) if lunch_end else 780  # 13:00
        
        # Generate dynamic exam sessions based on duration limit
        exam_sessions = []
        
        # Calculate time boundaries in minutes
        morning_start = exam_start_hour * 60
        morning_end = lunch_start_mins
        afternoon_start = lunch_end_mins
        afternoon_end = exam_end_hour * 60
        
        # Generate morning sessions
        current_time = morning_start
        session_num = 1
        while current_time + duration_limit <= morning_end:
            start_h, start_m = divmod(current_time, 60)
            end_time_mins = current_time + duration_limit
            end_h, end_m = divmod(end_time_mins, 60)
            
            exam_sessions.append({
                'start': time(start_h, start_m),
                'end': time(end_h, end_m),
                'name': f'Morning Session {session_num}'
            })
            session_num += 1
            current_time = end_time_mins + 15  # 15-minute gap between sessions
        
        # Generate afternoon sessions
        current_time = afternoon_start
        session_num = 1
        while current_time + duration_limit <= afternoon_end:
            start_h, start_m = divmod(current_time, 60)
            end_time_mins = current_time + duration_limit
            end_h, end_m = divmod(end_time_mins, 60)
            
            exam_sessions.append({
                'start': time(start_h, start_m),
                'end': time(end_h, end_m),
                'name': f'Afternoon Session {session_num}'
            })
            session_num += 1
            current_time = end_time_mins + 15  # 15-minute gap between sessions
        
        # If no sessions generated (edge case), create at least one based on input duration
        if not exam_sessions:
            input_start = exam_data.get('start_time')
            input_end = exam_data.get('end_time')
            if input_start and input_end:
                if isinstance(input_start, str):
                    input_start = datetime.strptime(input_start, '%H:%M').time()
                if isinstance(input_end, str):
                    input_end = datetime.strptime(input_end, '%H:%M').time()
                
                input_duration = (input_end.hour * 60 + input_end.minute) - (input_start.hour * 60 + input_start.minute)
                
                # Try morning slot
                if exam_start_hour * 60 + input_duration <= lunch_start_mins:
                    exam_sessions.append({
                        'start': time(exam_start_hour, 0),
                        'end': time(exam_start_hour + input_duration // 60, input_duration % 60),
                        'name': 'Morning Session'
                    })
                
                # Try afternoon slot
                if afternoon_start + input_duration <= afternoon_end:
                    start_h, start_m = divmod(afternoon_start, 60)
                    end_mins = afternoon_start + input_duration
                    end_h, end_m = divmod(end_mins, 60)
                    exam_sessions.append({
                        'start': time(start_h, start_m),
                        'end': time(end_h, end_m),
                        'name': 'Afternoon Session'
                    })
        
        # Get day of week from exam date for faculty availability check
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        exam_day_of_week = None
        if exam_date:
            if isinstance(exam_date, str):
                from datetime import datetime as dt
                exam_date_obj = dt.strptime(exam_date, '%Y-%m-%d').date()
            else:
                exam_date_obj = exam_date
            exam_day_of_week = day_names[exam_date_obj.weekday()]
        
        # Check if faculty is available on this day at all
        # Only block if faculty has set availability but NOT for this day ('not_in_schedule')
        # or is explicitly 'unavailable'. Allow 'available', 'preferred', and 'no_data' (no records)
        if faculty_id and exam_day_of_week:
            check_start = time(exam_start_hour, 0)
            check_end = time(exam_end_hour, 0)
            availability_result = FacultyAvailability.check_faculty_available_by_day(
                faculty_id, exam_day_of_week, check_start, check_end
            )
            status = availability_result.get('status')
            # Only block if explicitly unavailable or not in their configured schedule
            if status in ('unavailable', 'not_in_schedule'):
                # Faculty is unavailable on this day, don't recommend any times
                return []
        
        for session in exam_sessions:
            # Check faculty availability for this specific time slot
            # Only skip if faculty is explicitly unavailable or day not in their schedule
            if faculty_id and exam_day_of_week:
                availability_result = FacultyAvailability.check_faculty_available_by_day(
                    faculty_id, exam_day_of_week, session['start'], session['end']
                )
                status = availability_result.get('status')
                # Allow 'available', 'preferred', 'no_data'; block 'unavailable', 'not_in_schedule'
                if status in ('unavailable', 'not_in_schedule'):
                    continue  # Skip this session - faculty is not available
            
            has_conflict = False
            
            for exam in existing_exams:
                if exam.exam_date != exam_date:
                    continue
                
                if not self.conflict_detector.times_overlap(session['start'], session['end'], 
                                                           exam.start_time, exam.end_time):
                    continue
                
                if (exam.section_id == section_id or
                    (faculty_id and exam.faculty_id == faculty_id) or
                    (room_id and exam.room_id == room_id)):
                    has_conflict = True
                    break
            
            if not has_conflict:
                # Morning sessions score higher
                session_score = 90 if session['start'].hour < 12 else 75
                alternatives.append({
                    'start_time': session['start'].strftime('%H:%M'),
                    'end_time': session['end'].strftime('%H:%M'),
                    'display': f"{session['name']} ({session['start'].strftime('%I:%M %p').lstrip('0')} - {session['end'].strftime('%I:%M %p').lstrip('0')})",
                    'score': session_score,
                    'confidence': self._normalize_score(session_score, 50, 100),
                    'reason': 'No conflicts \u2022 ' + ('Morning session' if session['start'].hour < 12 else 'Afternoon session')
                })
        
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)
    
    def _find_alternative_exam_dates(
        self,
        exam_data: Dict,
        existing_exams: List
    ) -> List[Dict]:
        """Find alternative exam dates within the configured exam period with faculty availability"""
        from app.models.settings import AcademicSettings
        from app.models.faculty import FacultyAvailability
        
        alternatives = []
        current_date = exam_data.get('exam_date')
        section_id = exam_data.get('section_id')
        faculty_id = exam_data.get('faculty_id')  # Get faculty for availability check
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        
        # Day name lookup for faculty availability
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        if not current_date:
            return []
        
        # Get exam period date range from settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        
        exam_period_start = None
        exam_period_end = None
        if current_settings:
            exam_period_start = getattr(current_settings, 'exam_period_start', None)
            exam_period_end = getattr(current_settings, 'exam_period_end', None)
        
        # If exam period dates are configured, search within that range
        if exam_period_start and exam_period_end:
            # Search within the exam period range
            search_date = exam_period_start
            while search_date <= exam_period_end:
                # Skip if it's the current date being edited
                if search_date == current_date:
                    search_date += timedelta(days=1)
                    continue
                
                # Skip Sundays only (allow Monday-Saturday for exams)
                if search_date.weekday() == 6:  # Sunday
                    search_date += timedelta(days=1)
                    continue
                
                # Check faculty availability for this date
                if faculty_id:
                    search_day_of_week = day_names[search_date.weekday()]
                    availability_result = FacultyAvailability.check_faculty_available_by_day(
                        faculty_id, search_day_of_week, start_time, end_time
                    )
                    status = availability_result.get('status')
                    if status in ('unavailable', 'not_in_schedule'):
                        search_date += timedelta(days=1)
                        continue  # Skip this date - faculty is not available
                
                # Check for conflicts
                has_conflict = False
                for exam in existing_exams:
                    if exam.exam_date != search_date:
                        continue
                    
                    if not self.conflict_detector.times_overlap(start_time, end_time, 
                                                               exam.start_time, exam.end_time):
                        continue
                    
                    if exam.section_id == section_id:
                        has_conflict = True
                        break
                
                if not has_conflict:
                    # Calculate score based on proximity to current date
                    days_diff = abs((search_date - current_date).days)
                    score = max(100 - (days_diff * 5), 50)
                    proximity = 'Nearby date' if days_diff <= 3 else 'Further out'
                    
                    alternatives.append({
                        'exam_date': search_date.strftime('%Y-%m-%d'),
                        'display': search_date.strftime('%B %d, %Y (%A)'),
                        'score': score,
                        'confidence': self._normalize_score(score, 50, 100),
                        'reason': f'No conflicts \u2022 {proximity} \u2022 {days_diff} day{"s" if days_diff != 1 else ""} away'
                    })
                
                if len(alternatives) >= 5:
                    break
                    
                search_date += timedelta(days=1)
        else:
            # Fallback: Check next 14 days if no exam period configured
            for days_offset in range(1, 15):
                new_date = current_date + timedelta(days=days_offset)
                
                # Skip Sundays only (allow Monday-Saturday)
                if new_date.weekday() == 6:  # Sunday
                    continue
                
                # Check faculty availability for this date
                if faculty_id:
                    new_day_of_week = day_names[new_date.weekday()]
                    availability_result = FacultyAvailability.check_faculty_available_by_day(
                        faculty_id, new_day_of_week, start_time, end_time
                    )
                    status = availability_result.get('status')
                    if status in ('unavailable', 'not_in_schedule'):
                        continue  # Skip this date - faculty is not available
                
                # Check for conflicts
                has_conflict = False
                for exam in existing_exams:
                    if exam.exam_date != new_date:
                        continue
                    
                    if not self.conflict_detector.times_overlap(start_time, end_time, 
                                                               exam.start_time, exam.end_time):
                        continue
                    
                    if exam.section_id == section_id:
                        has_conflict = True
                        break
                
                if not has_conflict:
                    score = max(100 - (days_offset * 5), 50)
                    proximity = 'Nearby date' if days_offset <= 3 else 'Further out'
                    alternatives.append({
                        'exam_date': new_date.strftime('%Y-%m-%d'),
                        'display': new_date.strftime('%B %d, %Y (%A)'),
                        'score': score,
                        'confidence': self._normalize_score(score, 50, 100),
                        'reason': f'No conflicts \u2022 {proximity} \u2022 {days_offset} day{"s" if days_offset != 1 else ""} away'
                    })
                
                if len(alternatives) >= 5:
                    break
        
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)
    
    def _find_alternative_exam_rooms(
        self,
        exam_data: Dict,
        existing_exams: List
    ) -> List[Dict]:
        """Find alternative rooms for exam with building preference"""
        from app.models.building import Room
        
        alternatives = []
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        current_room_id = exam_data.get('room_id')
        
        # Get the currently selected room to check its type and building
        current_room = Room.query.get(current_room_id) if current_room_id else None
        current_room_type = current_room.room_type if current_room else None
        current_building_id = current_room.building_id if current_room else None
        
        # Determine allowed room types - if lab is selected, allow Lab and Lecture in same building
        allowed_types = ['Lecture', 'Laboratory']
        prefer_same_building = False
        
        if current_room_type == 'Laboratory':
            prefer_same_building = True
        
        # Get all available rooms
        all_rooms = Room.query.filter(
            Room.is_available == True,
            Room.room_type.in_(allowed_types)
        ).all()
        
        for room in all_rooms:
            if room.id == current_room_id:
                continue
            
            # If we prefer same building (lab selected), only recommend rooms in same building
            if prefer_same_building and current_building_id:
                if room.building_id != current_building_id:
                    continue  # Skip rooms not in the same building
            
            is_free = True
            for exam in existing_exams:
                if exam.exam_date != exam_date or exam.room_id != room.id:
                    continue
                
                if self.conflict_detector.times_overlap(start_time, end_time, exam.start_time, exam.end_time):
                    is_free = False
                    break
            
            if is_free:
                # Calculate score - prioritize same room type, then same building
                score = 100
                same_type = bool(current_room_type and room.room_type == current_room_type)
                same_building = bool(current_building_id and room.building_id == current_building_id)
                if same_type:
                    score += 20  # Bonus for same room type
                if same_building:
                    score += 10  # Bonus for same building
                
                alternatives.append({
                    'room_id': room.id,
                    'display': f"{room.room_number} ({room.building.building_name if room.building else 'N/A'}) - {room.room_type}",
                    'score': score,
                    'confidence': self._normalize_score(score, 80, 130),
                    'reason': self._generate_room_reason(same_type, same_building, room.room_type)
                })
        
        return sorted(alternatives, key=lambda x: (-x['score'], x['display']))[:5]
    
    def _find_alternative_exam_faculty(
        self,
        exam_data: Dict,
        existing_exams: List
    ) -> List[Dict]:
        """Find alternative faculty for exam proctoring with availability check"""
        from app.models.faculty import Faculty, FacultyAvailability
        
        alternatives = []
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        current_faculty_id = exam_data.get('faculty_id')
        
        # Get day of week from exam date for availability check
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        exam_day_of_week = None
        if exam_date:
            if isinstance(exam_date, str):
                from datetime import datetime as dt
                exam_date_obj = dt.strptime(exam_date, '%Y-%m-%d').date()
            else:
                exam_date_obj = exam_date
            exam_day_of_week = day_names[exam_date_obj.weekday()]
        
        # Get all active faculty
        all_faculty = Faculty.query.filter_by(is_active=True, is_archived=False).all()
        
        for faculty in all_faculty:
            if faculty.id == current_faculty_id:
                continue
            
            # Check faculty availability for this day/time
            if exam_day_of_week and start_time and end_time:
                availability_result = FacultyAvailability.check_faculty_available_by_day(
                    faculty.id, exam_day_of_week, start_time, end_time
                )
                status = availability_result.get('status')
                # Skip if faculty is unavailable or not in their configured schedule
                if status in ('unavailable', 'not_in_schedule'):
                    continue
            
            # Check if faculty is free from other exams at this time
            is_free = True
            for exam in existing_exams:
                if exam.exam_date != exam_date or exam.faculty_id != faculty.id:
                    continue
                
                if self.conflict_detector.times_overlap(start_time, end_time, exam.start_time, exam.end_time):
                    is_free = False
                    break
            
            if is_free:
                alternatives.append({
                    'faculty_id': faculty.id,
                    'display': faculty.full_name,
                    'score': 100,
                    'confidence': 80,
                    'reason': 'Available at this time \u2022 No exam conflicts'
                })
        
        return alternatives[:5]
    
    def _calculate_time_slot_score(self, start: time) -> int:
        """Calculate preference score for a time slot (prefer morning)"""
        hour = start.hour
        
        if 8 <= hour < 10:
            return 100  # Prime morning
        elif hour < 8:
            return 85   # Early morning
        elif 10 <= hour < 12:
            return 90   # Late morning
        elif 13 <= hour < 15:
            return 80   # Early afternoon
        elif 15 <= hour < 17:
            return 70   # Late afternoon
        elif 17 <= hour < 19:
            return 60   # Evening
        else:
            return 50   # Late evening
    
    def _calculate_day_score(self, day: str) -> int:
        """Calculate preference score for a day (prefer early week)"""
        scores = {
            'Monday': 100,
            'Tuesday': 95,
            'Wednesday': 90,
            'Thursday': 85,
            'Friday': 80,
            'Saturday': 60,
            'Sunday': 40
        }
        return scores.get(day, 50)


# Global instance
recommendation_engine = RecommendationEngine()
