"""
AI-Powered Decision Support for Schedule Management
Uses Google Gemini API to provide intelligent scheduling recommendations
"""
import os
import google.generativeai as genai
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_
from app.models.schedule import Schedule
from app.models.faculty import Faculty
from app.models.building import Room
from app.models.department import Section
from app.models.curriculum import Subject
from app.models.settings import AcademicSettings


class AISchedulerAssistant:
    """AI-powered scheduling assistant using Google Gemini"""
    
    def __init__(self):
        """Initialize Gemini AI"""
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key and api_key != 'your-api-key-here':
            genai.configure(api_key=api_key)
            # Use gemini-2.0-flash-exp (latest experimental model with best performance)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.enabled = True
        else:
            self.model = None
            self.enabled = False
    
    def analyze_schedule_conflicts(self, schedule_data: Dict, existing_schedules: List) -> Dict:
        """
        Analyze potential conflicts and provide recommendations
        
        Args:
            schedule_data: Dictionary with section_id, subject_id, faculty_id, room_id, 
                          day_of_week, start_time, end_time
            existing_schedules: List of existing Schedule objects
        
        Returns:
            Dictionary with conflicts, recommendations, and AI explanation
        """
        if not self.enabled:
            return {
                'has_conflicts': False,
                'conflicts': [],
                'recommendations': [],
                'ai_enabled': False
            }
        
        # Detect conflicts
        conflicts = self._detect_conflicts(schedule_data, existing_schedules)
        
        # Get recommendations if conflicts exist
        recommendations = []
        ai_explanation = ""
        
        if conflicts:
            recommendations = self._generate_recommendations(schedule_data, conflicts, existing_schedules)
            ai_explanation = self._get_ai_explanation(schedule_data, conflicts, recommendations)
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts,
            'recommendations': recommendations,
            'ai_explanation': ai_explanation,
            'ai_enabled': True
        }
    
    def _detect_conflicts(self, schedule_data: Dict, existing_schedules: List) -> List[Dict]:
        """Detect scheduling conflicts"""
        conflicts = []
        
        day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        section_id = schedule_data.get('section_id')
        faculty_id = schedule_data.get('faculty_id')
        room_id = schedule_data.get('room_id')
        
        for schedule in existing_schedules:
            # Check if same day
            if schedule.day_of_week != day:
                continue
            
            # Check time overlap
            if not self._times_overlap(start_time, end_time, schedule.start_time, schedule.end_time):
                continue
            
            # Section conflict
            if schedule.section_id == section_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{schedule.section.department.department_code}-{schedule.section.year_level}{schedule.section.section_name}" if schedule.section and schedule.section.department else schedule.section.section_name if schedule.section else 'Unknown Section'
                conflicts.append({
                    'type': 'section',
                    'message': f'Section {section_display} already has a class at this time',
                    'schedule': schedule,
                    'severity': 'critical'
                })
            
            # Faculty conflict
            if faculty_id and schedule.faculty_id == faculty_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{schedule.section.department.department_code}-{schedule.section.year_level}{schedule.section.section_name}" if schedule.section and schedule.section.department else schedule.section.section_name if schedule.section else 'Unknown Section'
                conflicts.append({
                    'type': 'faculty',
                    'message': f'Faculty {schedule.faculty.full_name} is already teaching {section_display} ({schedule.subject.subject_code if schedule.subject else "N/A"})',
                    'schedule': schedule,
                    'severity': 'critical'
                })
            
            # Room conflict
            if room_id and schedule.room_id == room_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{schedule.section.department.department_code}-{schedule.section.year_level}{schedule.section.section_name}" if schedule.section and schedule.section.department else schedule.section.section_name if schedule.section else 'Unknown Section'
                conflicts.append({
                    'type': 'room',
                    'message': f'Room {schedule.room.room_number} is already occupied by {section_display} ({schedule.subject.subject_code if schedule.subject else "N/A"})',
                    'schedule': schedule,
                    'severity': 'critical'
                })
        
        return conflicts
    
    def _times_overlap(self, start1: time, end1: time, start2: time, end2: time) -> bool:
        """Check if two time ranges overlap"""
        return start1 < end2 and end1 > start2
    
    def analyze_exam_conflicts(self, exam_data: Dict, existing_exams: List) -> Dict:
        """
        Analyze potential conflicts for exam schedules
        
        Args:
            exam_data: Dictionary with section_id, subject_id, faculty_id, room_id, 
                      exam_date, start_time, end_time
            existing_exams: List of existing ExamSchedule objects
        
        Returns:
            Dictionary with conflicts, recommendations, and AI explanation
        """
        if not self.enabled:
            return {
                'has_conflicts': False,
                'conflicts': [],
                'recommendations': [],
                'ai_explanation': '',
                'ai_enabled': False
            }
        
        # Detect conflicts
        conflicts = self._detect_exam_conflicts(exam_data, existing_exams)
        
        # Get recommendations if conflicts exist
        recommendations = []
        ai_explanation = ""
        
        if conflicts:
            recommendations = self._generate_exam_recommendations(exam_data, conflicts, existing_exams)
            ai_explanation = self._get_exam_ai_explanation(exam_data, conflicts, recommendations)
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts,
            'recommendations': recommendations,
            'ai_explanation': ai_explanation,
            'ai_enabled': True
        }
    
    def _detect_exam_conflicts(self, exam_data: Dict, existing_exams: List) -> List[Dict]:
        """Detect exam scheduling conflicts"""
        conflicts = []
        
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        section_id = exam_data.get('section_id')
        subject_id = exam_data.get('subject_id')
        faculty_id = exam_data.get('faculty_id')
        room_id = exam_data.get('room_id')
        
        for exam in existing_exams:
            # Check if same subject is already scheduled for exam in the same section (regardless of date/time)
            # This prevents double-booking the same exam
            if subject_id and exam.subject_id == subject_id and exam.section_id == section_id:
                conflicts.append({
                    'type': 'duplicate',
                    'message': f'Subject {exam.subject.subject_code} is already scheduled for an exam on {exam.exam_date.strftime("%B %d, %Y")} at {exam.start_time.strftime("%I:%M %p")}',
                    'schedule': exam,
                    'severity': 'critical'
                })
                continue  # Skip other checks for this exam since it's a duplicate
            
            # Check if same date
            if exam.exam_date != exam_date:
                continue
            
            # Check time overlap
            if not self._times_overlap(start_time, end_time, exam.start_time, exam.end_time):
                continue
            
            # Section conflict - same section cannot have multiple exams at the same time
            if exam.section_id == section_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{exam.section.department.department_code}-{exam.section.year_level}{exam.section.section_name}" if exam.section and exam.section.department else exam.section.section_name if exam.section else 'Unknown Section'
                conflicts.append({
                    'type': 'section',
                    'message': f'Section {section_display} already has an exam scheduled for {exam.subject.subject_code}',
                    'schedule': exam,
                    'severity': 'high'
                })
            
            # Faculty conflict - same faculty cannot proctor multiple exams at the same time (across ANY section)
            if faculty_id and exam.faculty_id == faculty_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{exam.section.department.department_code}-{exam.section.year_level}{exam.section.section_name}" if exam.section and exam.section.department else exam.section.section_name if exam.section else 'Unknown Section'
                conflicts.append({
                    'type': 'faculty',
                    'message': f'Faculty {exam.faculty.full_name} is already proctoring an exam for {section_display} ({exam.subject.subject_code})',
                    'schedule': exam,
                    'severity': 'high'
                })
            
            # Room conflict - same room cannot host multiple exams at the same time (across ANY section)
            if room_id and exam.room_id == room_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{exam.section.department.department_code}-{exam.section.year_level}{exam.section.section_name}" if exam.section and exam.section.department else exam.section.section_name if exam.section else 'Unknown Section'
                conflicts.append({
                    'type': 'room',
                    'message': f'Room {exam.room.room_number} is already occupied by {section_display} ({exam.subject.subject_code})',
                    'schedule': exam,
                    'severity': 'high'  # Changed from 'medium' to 'high' - room conflicts are critical
                })
        
        return conflicts
    
    def _generate_exam_recommendations(self, exam_data: Dict, conflicts: List[Dict], 
                                      existing_exams: List) -> List[Dict]:
        """Generate recommendations to resolve exam conflicts"""
        from app.models.building import Room
        from app.models.faculty import Faculty
        from datetime import timedelta
        
        recommendations = []
        
        # Check if there's a duplicate exam conflict - if so, no recommendations needed
        has_duplicate = any(c['type'] == 'duplicate' for c in conflicts)
        if has_duplicate:
            # For duplicate exams, the only solution is to not create a duplicate
            # Return empty recommendations since the user should not create this exam at all
            return []
        
        # Recommend alternative time slots on same date
        alternative_times = self._find_alternative_exam_times(
            exam_data, 
            existing_exams,
            exam_data.get('exam_date')
        )
        
        if alternative_times:
            recommendations.append({
                'type': 'time',
                'priority': 1,
                'message': 'Alternative time slots available on the same date',
                'options': alternative_times
            })
        
        # Recommend alternative dates
        alternative_dates = self._find_alternative_exam_dates(exam_data, existing_exams)
        
        if alternative_dates:
            recommendations.append({
                'type': 'date',
                'priority': 2,
                'message': 'Alternative dates available',
                'options': alternative_dates
            })
        
        # Recommend alternative rooms (if room conflict)
        if any(c['type'] == 'room' for c in conflicts):
            alternative_rooms = self._find_alternative_exam_rooms(exam_data, existing_exams)
            if alternative_rooms:
                recommendations.append({
                    'type': 'room',
                    'priority': 3,
                    'message': 'Alternative rooms available',
                    'options': alternative_rooms
                })
        
        # Recommend alternative faculty (if faculty conflict)
        if any(c['type'] == 'faculty' for c in conflicts):
            alternative_faculty = self._find_alternative_exam_faculty(exam_data, existing_exams)
            if alternative_faculty:
                recommendations.append({
                    'type': 'faculty',
                    'priority': 4,
                    'message': 'Alternative faculty available',
                    'options': alternative_faculty
                })
        
        return sorted(recommendations, key=lambda x: x['priority'])
    
    def _find_alternative_exam_times(self, exam_data: Dict, existing_exams: List, 
                                    exam_date) -> List[Dict]:
        """Find alternative time slots on the same exam date"""
        from app.models.settings import AcademicSettings
        from datetime import time as dt_time
        
        alternatives = []
        
        # Get exam time ranges from settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return alternatives
        
        # Exam time ranges (typically morning and afternoon sessions)
        exam_sessions = [
            {'start': dt_time(8, 0), 'end': dt_time(11, 0), 'name': 'Morning Session'},
            {'start': dt_time(13, 0), 'end': dt_time(16, 0), 'name': 'Afternoon Session'},
        ]
        
        section_id = exam_data.get('section_id')
        faculty_id = exam_data.get('faculty_id')
        room_id = exam_data.get('room_id')
        
        for session in exam_sessions:
            # Check if this time slot has conflicts
            has_conflict = False
            
            for exam in existing_exams:
                if exam.exam_date != exam_date:
                    continue
                
                if not self._times_overlap(session['start'], session['end'], 
                                          exam.start_time, exam.end_time):
                    continue
                
                # Check for section, faculty, or room conflicts
                if (exam.section_id == section_id or
                    (faculty_id and exam.faculty_id == faculty_id) or
                    (room_id and exam.room_id == room_id)):
                    has_conflict = True
                    break
            
            if not has_conflict:
                alternatives.append({
                    'start_time': session['start'].strftime('%H:%M'),
                    'end_time': session['end'].strftime('%H:%M'),
                    'display': f"{session['name']} ({session['start'].strftime('%I:%M %p')} - {session['end'].strftime('%I:%M %p')})",
                    'score': 100
                })
        
        return alternatives[:3]  # Return top 3 alternatives
    
    def _find_alternative_exam_dates(self, exam_data: Dict, existing_exams: List) -> List[Dict]:
        """Find alternative exam dates"""
        from datetime import timedelta
        
        alternatives = []
        current_date = exam_data.get('exam_date')
        section_id = exam_data.get('section_id')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        
        # Check next 14 days
        for days_offset in range(1, 15):
            new_date = current_date + timedelta(days=days_offset)
            
            # Skip weekends
            if new_date.weekday() >= 5:  # Saturday=5, Sunday=6
                continue
            
            # Check if date has conflicts
            has_conflict = False
            
            for exam in existing_exams:
                if exam.exam_date != new_date:
                    continue
                
                if not self._times_overlap(start_time, end_time, 
                                          exam.start_time, exam.end_time):
                    continue
                
                # Check for section conflict
                if exam.section_id == section_id:
                    has_conflict = True
                    break
            
            if not has_conflict:
                alternatives.append({
                    'exam_date': new_date.strftime('%Y-%m-%d'),
                    'display': new_date.strftime('%B %d, %Y (%A)'),
                    'score': max(100 - (days_offset * 5), 50)
                })
            
            if len(alternatives) >= 5:
                break
        
        return alternatives
    
    def _find_alternative_exam_rooms(self, exam_data: Dict, existing_exams: List) -> List[Dict]:
        """Find alternative rooms for exam"""
        from app.models.building import Room
        
        alternatives = []
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        current_room_id = exam_data.get('room_id')
        
        # Get all available rooms
        all_rooms = Room.query.filter_by(is_available=True).all()
        
        for room in all_rooms:
            if room.id == current_room_id:
                continue
            
            # Check if room is available
            is_available = True
            
            for exam in existing_exams:
                if exam.exam_date != exam_date:
                    continue
                
                if exam.room_id != room.id:
                    continue
                
                if self._times_overlap(start_time, end_time, exam.start_time, exam.end_time):
                    is_available = False
                    break
            
            if is_available:
                alternatives.append({
                    'room_id': room.id,
                    'display': f'{room.room_number} ({room.building.building_name if room.building else "N/A"})',
                    'score': 100
                })
        
        # Sort by room number for consistency
        return sorted(alternatives, key=lambda x: x['display'])[:5]
    
    def _find_alternative_exam_faculty(self, exam_data: Dict, existing_exams: List) -> List[Dict]:
        """Find alternative faculty for exam proctoring"""
        from app.models.faculty import Faculty
        
        alternatives = []
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        subject_id = exam_data.get('subject_id')
        current_faculty_id = exam_data.get('faculty_id')
        
        # Get faculty who can proctor this subject's exam
        all_faculty = Faculty.query.filter_by(is_active=True).all()
        
        for faculty in all_faculty:
            if faculty.id == current_faculty_id:
                continue
            
            # Check if faculty is available
            is_available = True
            
            for exam in existing_exams:
                if exam.exam_date != exam_date:
                    continue
                
                if exam.faculty_id != faculty.id:
                    continue
                
                if self._times_overlap(start_time, end_time, exam.start_time, exam.end_time):
                    is_available = False
                    break
            
            if is_available:
                alternatives.append({
                    'faculty_id': faculty.id,
                    'display': faculty.full_name,
                    'score': 100
                })
        
        return alternatives[:5]
    
    def _get_exam_ai_explanation(self, exam_data: Dict, conflicts: List[Dict], 
                                recommendations: List[Dict]) -> str:
        """Generate AI explanation for exam conflicts using Gemini"""
        if not self.enabled or not self.model:
            return ""
        
        try:
            # Check if there's a duplicate exam conflict
            has_duplicate = any(c['type'] == 'duplicate' for c in conflicts)
            
            if has_duplicate:
                # For duplicate exams, provide a clear message without AI call
                duplicate_conflict = next(c for c in conflicts if c['type'] == 'duplicate')
                return f"⚠️ This subject is already scheduled for an exam. You cannot create duplicate exams for the same subject in the same section. Please review the existing exam schedule."
            
            # Prepare context for AI
            conflict_summary = "\n".join([
                f"- {c['type'].title()} Conflict: {c['message']}" 
                for c in conflicts
            ])
            
            recommendation_summary = "\n".join([
                f"- {r['type'].title()}: {len(r['options'])} options available"
                for r in recommendations
            ]) if recommendations else "No alternative recommendations available"
            
            prompt = f"""You are an intelligent scheduling assistant for a university. 
            
A user is trying to schedule an exam with the following details:
- Date: {exam_data.get('exam_date')}
- Time: {exam_data.get('start_time').strftime('%I:%M %p') if isinstance(exam_data.get('start_time'), time) else exam_data.get('start_time')} - {exam_data.get('end_time').strftime('%I:%M %p') if isinstance(exam_data.get('end_time'), time) else exam_data.get('end_time')}

The following conflicts were detected:
{conflict_summary}

Available recommendations:
{recommendation_summary}

Provide a brief, helpful explanation (1-2 sentences) that:
1. Identifies the main conflict
2. Suggests the best resolution

Keep your response ultra-concise and actionable."""

            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"AI explanation error: {e}")
            return ""
    
    def _generate_recommendations(self, schedule_data: Dict, conflicts: List[Dict], 
                                 existing_schedules: List) -> List[Dict]:
        """Generate recommendations to resolve conflicts"""
        recommendations = []
        
        # Recommend alternative time slots
        alternative_times = self._find_alternative_times(
            schedule_data, 
            existing_schedules,
            schedule_data.get('day_of_week')
        )
        
        if alternative_times:
            recommendations.append({
                'type': 'time_slot',
                'title': 'Alternative Time Slots',
                'options': alternative_times,
                'priority': 1
            })
        
        # Recommend alternative days
        alternative_days = self._find_alternative_days(schedule_data, existing_schedules)
        
        if alternative_days:
            recommendations.append({
                'type': 'day',
                'title': 'Alternative Days',
                'options': alternative_days,
                'priority': 2
            })
        
        # Recommend alternative rooms (if room conflict)
        if any(c['type'] == 'room' for c in conflicts):
            alternative_rooms = self._find_alternative_rooms(schedule_data, existing_schedules)
            if alternative_rooms:
                recommendations.append({
                    'type': 'room',
                    'title': 'Alternative Rooms',
                    'options': alternative_rooms,
                    'priority': 3
                })
        
        # Recommend alternative faculty (if faculty conflict)
        if any(c['type'] == 'faculty' for c in conflicts):
            alternative_faculty = self._find_alternative_faculty(schedule_data, existing_schedules)
            if alternative_faculty:
                recommendations.append({
                    'type': 'faculty',
                    'title': 'Alternative Faculty',
                    'options': alternative_faculty,
                    'priority': 4
                })
        
        return sorted(recommendations, key=lambda x: x['priority'])
    
    def _find_alternative_times(self, schedule_data: Dict, existing_schedules: List, 
                               day: str) -> List[Dict]:
        """Find alternative time slots on the same day based on schedule type (lecture/lab/both)"""
        alternatives = []
        
        # Get current academic settings for time range
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        start_hour = current_settings.schedule_start_hour if current_settings else 7
        end_hour = current_settings.schedule_end_hour if current_settings else 20
        
        # Get subject to determine required duration
        subject_id = schedule_data.get('subject_id')
        subject = Subject.query.get(subject_id) if subject_id else None
        
        # Get schedule type (lecture, lab, or both)
        schedule_type = schedule_data.get('schedule_type', 'lecture')
        
        # Calculate required duration based on schedule type and subject units
        # DYNAMIC: Duration matches the schedule type selection
        # For LECTURE: use lec_units (lecture hours only)
        # For LAB: use lab_units (lab hours only)
        # For BOTH: use total_units (lecture + lab combined)
        if subject:
            if schedule_type == 'lab':
                # Lab schedule: use lab_units directly (1 unit = 1 hour)
                required_hours = float(subject.lab_units) if subject.lab_units else 1.5
            elif schedule_type == 'both':
                # Both schedule: use total_units (lec + lab = total)
                required_hours = float(subject.total_units) if subject.total_units else 3.0
            else:
                # Lecture schedule: use lec_units (1 unit = 1 hour)
                required_hours = float(subject.lec_units) if subject.lec_units else 1.5
            # Convert hours to minutes for time calculation
            required_minutes = int(required_hours * 60)
        else:
            # Default: assume 1.5 hours (90 minutes)
            required_hours = 1.5
        
        # Generate time slots based on 30-minute intervals from configured start to end hour
        # This matches the dropdown options in the UI which are now dynamic
        time_slots = []
        
        # Use configured start and end hours from settings
        start_minute = 0
        
        # Generate all possible 30-minute interval start times
        current_datetime = datetime.combine(datetime.today(), time(start_hour, start_minute))
        end_limit = datetime.combine(datetime.today(), time(end_hour, 0))
        
        while current_datetime <= end_limit:
            current_time = current_datetime.time()
            
            # Calculate end time based on required duration
            end_datetime = current_datetime + timedelta(minutes=required_minutes)
            
            # Only include if end time is within configured end hour and on same day
            if end_datetime.time() <= time(end_hour, 0) and end_datetime.date() == current_datetime.date():
                time_slots.append((current_time, end_datetime.time()))
            
            # Increment by 30 minutes
            current_datetime = current_datetime + timedelta(minutes=30)
        
        section_id = schedule_data.get('section_id')
        faculty_id = schedule_data.get('faculty_id')
        room_id = schedule_data.get('room_id')
        
        for start, end in time_slots:
            # Check if this slot is free for all entities
            is_free = True
            
            for schedule in existing_schedules:
                if schedule.day_of_week != day:
                    continue
                
                if self._times_overlap(start, end, schedule.start_time, schedule.end_time):
                    if (schedule.section_id == section_id or 
                        (faculty_id and schedule.faculty_id == faculty_id) or
                        (room_id and schedule.room_id == room_id)):
                        is_free = False
                        break
            
            if is_free:
                # Calculate duration in hours for display
                duration_minutes = (datetime.combine(datetime.today(), end) - 
                                   datetime.combine(datetime.today(), start)).seconds // 60
                duration_hours = duration_minutes / 60
                
                # Build unit information string for display
                unit_info = ""
                if subject:
                    if schedule_type == 'lab':
                        unit_info = f" - Lab: {subject.lab_units} units"
                    elif schedule_type == 'both':
                        unit_info = f" - Both: {subject.total_units} units"
                    else:  # lecture
                        unit_info = f" - Lecture: {subject.lec_units} units"
                
                alternatives.append({
                    'start_time': start.strftime('%H:%M'),
                    'end_time': end.strftime('%H:%M'),
                    'display': f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} ({duration_hours:.1f} hrs{unit_info})",
                    'duration_hours': duration_hours,
                    'score': self._calculate_time_slot_score(start, end)
                })
        
        # Sort by score (prefer morning slots)
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)[:5]
    
    def _find_alternative_days(self, schedule_data: Dict, existing_schedules: List) -> List[Dict]:
        """Find alternative days for the schedule with subject-based duration"""
        alternatives = []
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        current_day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        section_id = schedule_data.get('section_id')
        faculty_id = schedule_data.get('faculty_id')
        room_id = schedule_data.get('room_id')
        
        # Calculate duration for display
        if start_time and end_time:
            duration_minutes = (datetime.combine(datetime.today(), end_time) - 
                               datetime.combine(datetime.today(), start_time)).seconds // 60
            duration_hours = duration_minutes / 60
        else:
            duration_hours = 1.5
        
        for day in days:
            if day == current_day:
                continue
            
            # Check if this day/time is free
            is_free = True
            
            for schedule in existing_schedules:
                if schedule.day_of_week != day:
                    continue
                
                if self._times_overlap(start_time, end_time, schedule.start_time, schedule.end_time):
                    if (schedule.section_id == section_id or 
                        (faculty_id and schedule.faculty_id == faculty_id) or
                        (room_id and schedule.room_id == room_id)):
                        is_free = False
                        break
            
            if is_free:
                alternatives.append({
                    'day': day,
                    'display': f"{day} at {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')} ({duration_hours:.1f} hrs)",
                    'duration_hours': duration_hours,
                    'score': self._calculate_day_score(day)
                })
        
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)[:3]
    
    def _find_alternative_rooms(self, schedule_data: Dict, existing_schedules: List) -> List[Dict]:
        """Find alternative available rooms"""
        from app.extensions import db
        
        alternatives = []
        day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        
        # Get all available rooms
        all_rooms = Room.query.filter_by(is_available=True).all()
        
        for room in all_rooms:
            # Check if room is free at this time
            is_free = True
            
            for schedule in existing_schedules:
                if (schedule.room_id == room.id and 
                    schedule.day_of_week == day and
                    self._times_overlap(start_time, end_time, schedule.start_time, schedule.end_time)):
                    is_free = False
                    break
            
            if is_free:
                alternatives.append({
                    'room_id': room.id,
                    'room_number': room.room_number,
                    'building': room.building.building_name if room.building else 'Unknown',
                    'display': f"{room.building.building_name if room.building else 'Unknown'} - {room.room_number}"
                })
        
        return alternatives[:5]
    
    def _find_alternative_faculty(self, schedule_data: Dict, existing_schedules: List) -> List[Dict]:
        """Find alternative available faculty assigned to this subject"""
        from app.extensions import db
        from app.models.faculty import FacultySubjectAssignment
        from app.models.settings import AcademicSettings
        
        alternatives = []
        day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        subject_id = schedule_data.get('subject_id')
        
        # Get subject to find assigned faculty
        subject = Subject.query.get(subject_id)
        if not subject:
            return []
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return []
        
        # Get faculty assignments for this subject and current academic period
        assignments = FacultySubjectAssignment.query.filter_by(
            subject_id=subject_id,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester,
            is_active=True,
            is_archived=False
        ).all()
        
        # Get unique faculty IDs assigned to this subject
        faculty_ids = list(set([assignment.faculty_id for assignment in assignments]))
        
        # Get faculty details
        assigned_faculty = Faculty.query.filter(
            Faculty.id.in_(faculty_ids),
            Faculty.is_active == True,
            Faculty.is_archived == False
        ).all()
        
        for faculty in assigned_faculty:
            # Check if faculty is free at this time
            is_free = True
            
            for schedule in existing_schedules:
                if (schedule.faculty_id == faculty.id and 
                    schedule.day_of_week == day and
                    self._times_overlap(start_time, end_time, schedule.start_time, schedule.end_time)):
                    is_free = False
                    break
            
            if is_free:
                # Calculate workload
                workload = len([s for s in existing_schedules if s.faculty_id == faculty.id])
                
                alternatives.append({
                    'faculty_id': faculty.id,
                    'name': faculty.full_name,
                    'department': faculty.department.department_name if faculty.department else 'Unknown',
                    'current_workload': workload,
                    'display': f"{faculty.full_name} ({faculty.department.department_code if faculty.department else 'N/A'}) - {workload} classes"
                })
        
        # Sort by workload (prefer less loaded faculty)
        return sorted(alternatives, key=lambda x: x['current_workload'])[:5]
    
    def _calculate_time_slot_score(self, start: time, end: time) -> int:
        """Calculate preference score for a time slot (prefer morning, works with any configured time range)"""
        hour = start.hour
        
        if hour <= 8:  # Early morning slots
            return 85
        elif 8 < hour < 10:  # Morning prime time
            return 100
        elif 10 <= hour < 12:  # Late morning
            return 90
        elif 13 <= hour < 15:  # Early afternoon
            return 80
        elif 15 <= hour < 17:  # Late afternoon
            return 70
        elif 17 <= hour < 19:  # Evening
            return 60
        else:  # Late evening/night
            return 50
    
    def _calculate_day_score(self, day: str) -> int:
        """Calculate preference score for a day (prefer early week)"""
        day_scores = {
            'Monday': 100,
            'Tuesday': 95,
            'Wednesday': 90,
            'Thursday': 85,
            'Friday': 80,
            'Saturday': 60
        }
        return day_scores.get(day, 50)
    
    def _get_ai_explanation(self, schedule_data: Dict, conflicts: List[Dict], 
                           recommendations: List[Dict]) -> str:
        """Get AI-generated explanation and guidance"""
        if not self.enabled or not self.model:
            return ""
        
        try:
            # Prepare context for AI
            conflict_summary = "\n".join([
                f"- {c['type'].title()} Conflict: {c['message']}" 
                for c in conflicts
            ])
            
            recommendation_summary = "\n".join([
                f"- {r['title']}: {len(r['options'])} options available"
                for r in recommendations
            ])
            
            prompt = f"""You are an intelligent scheduling assistant for a university. 
            
A user is trying to schedule a class with the following details:
- Day: {schedule_data.get('day_of_week')}
- Time: {schedule_data.get('start_time').strftime('%I:%M %p')} - {schedule_data.get('end_time').strftime('%I:%M %p')}

The following conflicts were detected:
{conflict_summary}

Available recommendations:
{recommendation_summary}

Provide a brief, helpful explanation (1-2 sentences) that:
1. Identifies the main conflict
2. Suggests the best resolution

Keep your response ultra-concise and actionable."""

            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"AI explanation error: {str(e)}")
            return "Unable to generate AI explanation at this time."
    
    def suggest_optimal_schedule(self, section: Section, subject: Subject, 
                                faculty: Optional[Faculty] = None) -> Dict:
        """
        Suggest optimal scheduling considering workload balance and patterns
        
        Returns:
            Dictionary with suggested day, time, and AI reasoning
        """
        if not self.enabled:
            return {'ai_enabled': False, 'suggestions': []}
        
        from app.extensions import db
        
        # Get current settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return {'ai_enabled': True, 'suggestions': []}
        
        # Get existing schedules for this semester
        existing_schedules = Schedule.query.filter_by(
            is_active=True,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester
        ).all()
        
        # Analyze patterns and suggest
        suggestions = self._analyze_and_suggest(section, subject, faculty, existing_schedules)
        
        return {
            'ai_enabled': True,
            'suggestions': suggestions
        }
    
    def _analyze_and_suggest(self, section: Section, subject: Subject, 
                            faculty: Optional[Faculty], existing_schedules: List) -> List[Dict]:
        """Analyze current schedules and suggest optimal slots"""
        suggestions = []
        
        # Get section's existing schedules
        section_schedules = [s for s in existing_schedules if s.section_id == section.id]
        
        # Analyze section's schedule pattern
        used_days = set(s.day_of_week for s in section_schedules)
        
        # Find free days
        all_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        free_days = [day for day in all_days if day not in used_days]
        
        # Prefer spreading classes across the week
        if free_days:
            for day in free_days[:3]:  # Top 3 free days
                # Find free time slots
                free_slots = self._find_free_time_slots_for_day(
                    day, section, faculty, existing_schedules
                )
                
                for slot in free_slots[:2]:  # Top 2 slots per day
                    suggestions.append({
                        'day': day,
                        'start_time': slot['start'],
                        'end_time': slot['end'],
                        'reason': f"Balances weekly schedule - {day} is currently free",
                        'score': slot['score']
                    })
        
        return sorted(suggestions, key=lambda x: x['score'], reverse=True)[:5]
    
    def _find_free_time_slots_for_day(self, day: str, section: Section, 
                                      faculty: Optional[Faculty], 
                                      existing_schedules: List) -> List[Dict]:
        """Find free time slots for a specific day using configured time range with 30-min intervals"""
        free_slots = []
        
        # Get current academic settings for time range
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        start_hour = current_settings.schedule_start_hour if current_settings else 7
        end_hour = current_settings.schedule_end_hour if current_settings else 20
        
        # Generate time slots dynamically based on configured time range (30-minute intervals)
        time_slots = []
        current_hour = start_hour
        
        # Create 1.5-hour time slots (matching typical class duration)
        while current_hour < end_hour:
            slot_start = time(current_hour, 0)
            # Calculate end time (1.5 hours = 90 minutes later)
            end_minutes = (current_hour * 60) + 90
            end_hour_calc = end_minutes // 60
            end_minute_calc = end_minutes % 60
            
            # Only add slot if it fits within the configured end hour
            if end_hour_calc <= end_hour or (end_hour_calc == end_hour and end_minute_calc == 0):
                slot_end = time(end_hour_calc, end_minute_calc)
                time_slots.append((slot_start, slot_end))
            
            # Move to next slot (advance by 30 minutes for more options)
            current_hour_float = current_hour + 0.5
            current_hour = int(current_hour_float) if current_hour_float % 1 == 0 else int(current_hour_float * 2) / 2
        
        for start, end in time_slots:
            is_free = True
            
            # Check section availability
            for schedule in existing_schedules:
                if (schedule.section_id == section.id and 
                    schedule.day_of_week == day and
                    self._times_overlap(start, end, schedule.start_time, schedule.end_time)):
                    is_free = False
                    break
            
            # Check faculty availability if provided
            if is_free and faculty:
                for schedule in existing_schedules:
                    if (schedule.faculty_id == faculty.id and 
                        schedule.day_of_week == day and
                        self._times_overlap(start, end, schedule.start_time, schedule.end_time)):
                        is_free = False
                        break
            
            if is_free:
                free_slots.append({
                    'start': start,
                    'end': end,
                    'score': self._calculate_time_slot_score(start, end)
                })
        
        return free_slots
    
    def generate_report_summary(self, stats: Dict, academic_year: str = None, 
                               semester: str = None, department_name: str = None) -> Dict:
        """
        Generate a comprehensive AI summary of the report statistics
        
        Args:
            stats: Dictionary containing all report statistics
            academic_year: Current academic year
            semester: Current semester
            department_name: Specific department being analyzed (if filtered)
        
        Returns:
            Dictionary with summary text and key insights
        """
        if not self.enabled or not self.model:
            return {
                'ai_enabled': False,
                'summary': 'AI summary is not available. Please configure the Gemini API key.',
                'insights': [],
                'recommendations': []
            }
        
        try:
            # Build scope context
            scope = f"DEPARTMENT: {department_name}\n" if department_name else "SCOPE: All Departments\n"
            
            # Prepare context for AI
            context = f"""
You are an educational data analyst providing a CONCISE analysis of scheduling data.

PERIOD: {academic_year or 'N/A'}, {semester or 'N/A'}
{scope}
KEY METRICS:
- Schedules: {stats.get('total_schedules', 0)} classes, {stats.get('total_exam_schedules', 0)} exams
- Faculty: {stats.get('faculty_with_schedules', 0)}/{stats.get('total_faculty', 0)} active
- Rooms: {stats.get('rooms_in_use', 0)}/{stats.get('total_rooms', 0)} in use
- Type: {stats.get('lecture_count', 0)} lectures, {stats.get('lab_count', 0)} labs

TOP FACULTY WORKLOAD:
{self._format_faculty_workload(stats.get('faculty_workloads', [])[:3])}

TOP ROOM USAGE:
{self._format_room_utilization(stats.get('room_utilizations', [])[:3])}

WEEKLY PATTERN:
{self._format_weekly_distribution(stats.get('schedule_by_day', {}))}

Provide a BRIEF analysis {"for " + department_name if department_name else "across all departments"}:
- Summary: 2-3 sentences highlighting overall status and utilization rates{"" if not department_name else " for this department"}
- Key Insights: 3-4 bullet points (one sentence each) about critical patterns{"" if not department_name else " specific to this department"}
- Recommendations: 3-4 bullet points (one sentence each) with specific actions{"" if not department_name else " for improving this department's scheduling"}

Be direct, specific, and actionable. Use numbers. No fluff.
{"Focus exclusively on " + department_name + " data." if department_name else "Consider department-level variations if relevant."}
DO NOT use markdown formatting (no **, *, or #). Use plain text only.
DO NOT number the sections (no "1.", "2.", "3."). Just use section headers."""
            
            # Generate AI response
            response = self.model.generate_content(context)
            summary_text = response.text
            
            # Parse the response to extract sections
            insights = self._extract_bullet_points(summary_text, "Key Insights", "Recommendations")
            if not insights:
                insights = self._extract_bullet_points(summary_text, "Insights", "Recommendations")
            
            recommendations = self._extract_bullet_points(summary_text, "Recommendations", None)
            
            # Extract main summary (everything before bullet points)
            main_summary = summary_text.split("Key Insights")[0].strip() if "Key Insights" in summary_text else summary_text.split("Insights")[0].strip() if "Insights" in summary_text else summary_text.split("Recommendations")[0].strip() if "Recommendations" in summary_text else summary_text
            
            # Clean up markdown formatting from summary
            main_summary = main_summary.replace('**', '').strip()
            
            return {
                'ai_enabled': True,
                'summary': main_summary,
                'insights': insights,
                'recommendations': recommendations,
                'full_text': summary_text
            }
            
        except Exception as e:
            print(f"Error generating AI report summary: {str(e)}")
            return {
                'ai_enabled': True,
                'error': str(e),
                'summary': 'Unable to generate AI summary at this time.',
                'insights': [],
                'recommendations': []
            }
    
    def _format_faculty_workload(self, faculty_list: List[Dict]) -> str:
        """Format faculty workload data for AI context"""
        if not faculty_list:
            return "None"
        
        lines = []
        for i, faculty in enumerate(faculty_list, 1):
            lines.append(
                f"{i}. {faculty['name']}: {faculty['total_units']} units ({faculty['schedules']} classes)"
            )
        return "\n".join(lines)
    
    def _format_room_utilization(self, room_list: List[Dict]) -> str:
        """Format room utilization data for AI context"""
        if not room_list:
            return "None"
        
        lines = []
        for i, room in enumerate(room_list, 1):
            lines.append(
                f"{i}. {room['room']}: {room['total_usage']} uses"
            )
        return "\n".join(lines)
    
    def _format_weekly_distribution(self, schedule_by_day: Dict) -> str:
        """Format weekly distribution for AI context"""
        if not schedule_by_day:
            return "None"
        
        lines = []
        for day, count in schedule_by_day.items():
            lines.append(f"{day}: {count}")
        return ", ".join(lines)
    
    def _extract_bullet_points(self, text: str, start_marker: str, 
                               end_marker: Optional[str]) -> List[str]:
        """Extract bullet points from AI response between markers"""
        try:
            # Find the section
            if start_marker not in text:
                return []
            
            start_idx = text.index(start_marker) + len(start_marker)
            
            if end_marker and end_marker in text[start_idx:]:
                end_idx = text.index(end_marker, start_idx)
                section = text[start_idx:end_idx]
            else:
                section = text[start_idx:]
            
            # Extract bullet points (lines starting with -, *, or numbers)
            lines = section.strip().split('\n')
            bullets = []
            for line in lines:
                line = line.strip()
                # Match lines starting with -, *, •, **, or 1., 2., etc.
                if line and (line.startswith(('-', '*', '•', '**')) or 
                           (len(line) > 2 and line[0].isdigit() and line[1] in '.)')):
                    # Clean up the bullet point
                    cleaned = line.lstrip('-*•0123456789.) ').strip()
                    # Remove all markdown formatting
                    cleaned = cleaned.replace('**', '').replace('*', '').replace('__', '').strip()
                    if cleaned and len(cleaned) > 10:  # Only include substantial points
                        bullets.append(cleaned)
            
            return bullets[:4]  # Limit to 4 items for conciseness
        except Exception:
            return []


# Global instance
ai_scheduler = AISchedulerAssistant()
