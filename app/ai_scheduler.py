"""
AI-Powered Decision Support for Schedule Management
Uses Google Gemini API to provide intelligent scheduling recommendations

Refactored Architecture:
- ConflictDetector: Pure Python conflict checking (fast, no API)
- RecommendationEngine: Smart suggestions with workload balancing
- AISchedulerAssistant: Gemini AI explanations only
"""
import os
import google.generativeai as genai
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_
from app.models.schedule import Schedule
from app.models.faculty import Faculty
from app.models.building import Room
from app.models.section import Section
from app.models.curriculum import Subject
from app.models.settings import AcademicSettings

# Import new service layer
from app.services.conflict_detector import ConflictDetector, conflict_detector, ConflictSeverity, ConflictType
from app.services.recommendation_engine import RecommendationEngine, recommendation_engine


class AISchedulerAssistant:
    """
    AI-powered scheduling assistant using Google Gemini
    
    Now uses service layer for conflict detection and recommendations:
    - conflict_detector: Fast pure Python conflict checking
    - recommendation_engine: Workload-aware suggestions
    - This class: Gemini AI explanations only
    """
    
    def __init__(self):
        """Initialize Gemini AI"""
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key and api_key != 'your-api-key-here':
            genai.configure(api_key=api_key)
            # Use gemini-2.5-flash (fast, cost-effective)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.enabled = True
        else:
            self.model = None
            self.enabled = False
        
        # Use service layer instances
        self.conflict_detector = conflict_detector
        self.recommendation_engine = recommendation_engine
    
    def analyze_schedule_conflicts(self, schedule_data: Dict, existing_schedules: List, 
                                   exclude_schedule_id: Optional[int] = None) -> Dict:
        """
        Analyze potential conflicts and provide recommendations
        
        Uses new service layer architecture:
        1. ConflictDetector for fast conflict detection (no AI)
        2. RecommendationEngine for smart suggestions
        3. Gemini AI for natural language explanations only
        
        Args:
            schedule_data: Dictionary with section_id, subject_id, faculty_id, room_id, 
                          day_of_week, start_time, end_time
            existing_schedules: List of existing Schedule objects
            exclude_schedule_id: Schedule ID to exclude (for edit mode)
        
        Returns:
            Dictionary with conflicts, recommendations, and AI explanation
        """
        # Step 1: Detect conflicts using pure Python (fast, no API)
        conflicts = self.conflict_detector.detect_class_conflicts(
            schedule_data, 
            existing_schedules,
            exclude_schedule_id
        )
        
        # Step 2: Generate recommendations if conflicts exist
        recommendations = []
        ai_explanation = ""
        ai_fallback = not self.enabled
        ai_fallback_reason = (
            "AI guidance is disabled because Gemini API is not configured."
            if not self.enabled else None
        )
        
        if conflicts:
            # Get subject for workload-aware recommendations
            subject = None
            subject_id = schedule_data.get('subject_id')
            if subject_id:
                subject = Subject.query.get(subject_id)
            
            recommendations = self.recommendation_engine.generate_class_recommendations(
                schedule_data, 
                conflicts, 
                existing_schedules,
                subject,
                exclude_schedule_id=exclude_schedule_id
            )
            
            # Step 3: Get AI explanation (online or offline)
            if self.enabled:
                ai_explanation, ai_explanation_fallback, explanation_fallback_reason = self._get_ai_explanation_v2(
                    schedule_data,
                    conflicts,
                    recommendations
                )
                if ai_explanation_fallback:
                    ai_fallback = True
                    ai_fallback_reason = explanation_fallback_reason
            else:
                ai_explanation = self._get_offline_explanation(conflicts, recommendations)
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': [c.to_dict() for c in conflicts],
            'recommendations': [r.to_dict() for r in recommendations],
            'ai_explanation': ai_explanation,
            'ai_enabled': self.enabled,
            'ai_fallback': ai_fallback,
            'ai_fallback_reason': ai_fallback_reason
        }
    
    def _get_ai_explanation_v2(self, schedule_data: Dict, conflicts: List,
                               recommendations: List) -> Tuple[str, bool, Optional[str]]:
        """
        Generate AI explanation using Gemini (new version with service layer)
        
        Args:
            schedule_data: Schedule form data
            conflicts: List of Conflict objects from ConflictDetector
            recommendations: List of Recommendation objects from RecommendationEngine
            
        Returns:
            (explanation, used_fallback, fallback_reason)
        """
        if not self.enabled or not self.model:
            return "", True, "AI guidance is disabled because Gemini API is not configured."
        
        try:
            # Prepare conflict summary
            conflict_summary = "\n".join([
                f"- {c.severity.value.upper()} ({c.type.value}): {c.message}" 
                for c in conflicts
            ])
            
            # Prepare recommendation summary
            rec_summary = "\n".join([
                f"- {r.type.title()}: {len(r.options)} options available"
                for r in recommendations
            ]) if recommendations else "No alternatives found"
            
            prompt = f"""You are a university scheduling assistant. Be ultra-concise.

A user is scheduling a class:
- Day: {schedule_data.get('day_of_week')}
- Time: {schedule_data.get('start_time').strftime('%I:%M %p') if isinstance(schedule_data.get('start_time'), time) else schedule_data.get('start_time')} - {schedule_data.get('end_time').strftime('%I:%M %p') if isinstance(schedule_data.get('end_time'), time) else schedule_data.get('end_time')}

Conflicts detected:
{conflict_summary}

Available alternatives:
{rec_summary}

Provide a brief, helpful response (1-2 sentences max) that:
1. Identifies the main issue
2. Suggests the best resolution

Be direct and actionable. No markdown formatting."""

            response = self.model.generate_content(prompt)
            return response.text.strip(), False, None
            
        except Exception as e:
            print(f"AI explanation error: {str(e)}")
            return (
                "Conflicts detected. Review the suggestions below to resolve.",
                True,
                "AI guidance temporarily unavailable due to provider error."
            )
    
    # ========== LEGACY METHODS (kept for backward compatibility) ==========
    
    def _detect_conflicts(self, schedule_data: Dict, existing_schedules: List) -> List[Dict]:
        """Detect scheduling conflicts - LEGACY, use conflict_detector instead"""
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
                section_display = f"{schedule.section.program.program_code}-{schedule.section.year_level}{schedule.section.section_name}" if schedule.section and schedule.section.program else schedule.section.section_name if schedule.section else 'Unknown Section'
                conflicts.append({
                    'type': 'section',
                    'message': f'Section {section_display} already has a class at this time',
                    'schedule': schedule,
                    'severity': 'critical'
                })
            
            # Faculty conflict
            if faculty_id and schedule.faculty_id == faculty_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{schedule.section.program.program_code}-{schedule.section.year_level}{schedule.section.section_name}" if schedule.section and schedule.section.program else schedule.section.section_name if schedule.section else 'Unknown Section'
                conflicts.append({
                    'type': 'faculty',
                    'message': f'Faculty {schedule.faculty.full_name} is already teaching {section_display} ({schedule.subject.subject_code if schedule.subject else "N/A"})',
                    'schedule': schedule,
                    'severity': 'critical'
                })
            
            # Room conflict
            if room_id and schedule.room_id == room_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{schedule.section.program.program_code}-{schedule.section.year_level}{schedule.section.section_name}" if schedule.section and schedule.section.program else schedule.section.section_name if schedule.section else 'Unknown Section'
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
    
    def analyze_exam_conflicts(self, exam_data: Dict, existing_exams: List,
                               exclude_exam_id: Optional[int] = None) -> Dict:
        """
        Analyze potential conflicts for exam schedules
        
        Uses new service layer architecture for faster detection.
        
        Args:
            exam_data: Dictionary with section_id, subject_id, faculty_id, room_id, 
                      exam_date, start_time, end_time
            existing_exams: List of existing ExamSchedule objects
            exclude_exam_id: Exam ID to exclude (for edit mode)
        
        Returns:
            Dictionary with conflicts, recommendations, and AI explanation
        """
        # Step 1: Detect conflicts using pure Python (fast, no API)
        conflicts = self.conflict_detector.detect_exam_conflicts(
            exam_data,
            existing_exams,
            exclude_exam_id
        )
        
        # Step 2: Generate recommendations if conflicts exist
        recommendations = []
        ai_explanation = ""
        ai_fallback = not self.enabled
        ai_fallback_reason = (
            "AI guidance is disabled because Gemini API is not configured."
            if not self.enabled else None
        )
        
        if conflicts:
            recommendations = self.recommendation_engine.generate_exam_recommendations(
                exam_data,
                conflicts,
                existing_exams
            )
            
            # Step 3: Get AI explanation (online or offline)
            if self.enabled:
                ai_explanation, ai_explanation_fallback, explanation_fallback_reason = self._get_exam_ai_explanation_v2(
                    exam_data,
                    conflicts,
                    recommendations
                )
                if ai_explanation_fallback:
                    ai_fallback = True
                    ai_fallback_reason = explanation_fallback_reason
            else:
                ai_explanation = self._get_offline_explanation(conflicts, recommendations, is_exam=True)
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': [c.to_dict() for c in conflicts],
            'recommendations': [r.to_dict() for r in recommendations],
            'ai_explanation': ai_explanation,
            'ai_enabled': self.enabled,
            'ai_fallback': ai_fallback,
            'ai_fallback_reason': ai_fallback_reason
        }
    
    def _get_exam_ai_explanation_v2(self, exam_data: Dict, conflicts: List,
                                    recommendations: List) -> Tuple[str, bool, Optional[str]]:
        """
        Generate AI explanation for exam conflicts using Gemini (new version)
        
        Args:
            exam_data: Exam form data
            conflicts: List of Conflict objects from ConflictDetector
            recommendations: List of Recommendation objects from RecommendationEngine
            
        Returns:
            (explanation, used_fallback, fallback_reason)
        """
        if not self.enabled or not self.model:
            return "", True, "AI guidance is disabled because Gemini API is not configured."
        
        try:
            # Check for duplicate conflict - provide direct message without API call
            has_duplicate = any(c.type == ConflictType.DUPLICATE for c in conflicts)
            if has_duplicate:
                return (
                    "⚠️ This subject already has an exam scheduled. You cannot create duplicate exams for the same subject in the same section. Please review the existing exam schedule.",
                    False,
                    None
                )
            
            # Prepare conflict summary
            conflict_summary = "\n".join([
                f"- {c.severity.value.upper()} ({c.type.value}): {c.message}" 
                for c in conflicts
            ])
            
            # Prepare recommendation summary
            rec_summary = "\n".join([
                f"- {r.type.title()}: {len(r.options)} options available"
                for r in recommendations
            ]) if recommendations else "No alternatives found"
            
            prompt = f"""You are a university exam scheduling assistant. Be ultra-concise.

A user is scheduling an exam:
- Date: {exam_data.get('exam_date')}
- Time: {exam_data.get('start_time').strftime('%I:%M %p') if isinstance(exam_data.get('start_time'), time) else exam_data.get('start_time')} - {exam_data.get('end_time').strftime('%I:%M %p') if isinstance(exam_data.get('end_time'), time) else exam_data.get('end_time')}

Conflicts detected:
{conflict_summary}

Available alternatives:
{rec_summary}

Provide a brief, helpful response (1-2 sentences max) that:
1. Identifies the main issue
2. Suggests the best resolution

Be direct and actionable. No markdown formatting."""

            response = self.model.generate_content(prompt)
            return response.text.strip(), False, None
            
        except Exception as e:
            print(f"AI exam explanation error: {str(e)}")
            return (
                "Exam conflicts detected. Review the suggestions below to resolve.",
                True,
                "AI guidance temporarily unavailable due to provider error."
            )
    
    # ========== OFFLINE AI EXPLANATIONS (No Gemini Required) ==========
    
    def _get_offline_explanation(self, conflicts: List, recommendations: List,
                                 is_exam: bool = False) -> str:
        """
        Generate a rule-based offline explanation for conflicts.
        Works without any API key.
        """
        if not conflicts:
            return ""

        # Group conflicts by type
        conflict_types = {}
        for c in conflicts:
            ctype = c.type.value if hasattr(c.type, 'value') else str(c.type)
            if ctype not in conflict_types:
                conflict_types[ctype] = []
            conflict_types[ctype].append(c)

        parts = []
        entity_label = "exam" if is_exam else "class"

        # User-facing summary should stay concise and avoid technical severity wording.
        parts.append(f"Conflicts found for this {entity_label} schedule.")

        # Type-specific messages
        if 'duplicate' in conflict_types:
            parts.append(f"This subject already has a {entity_label} scheduled — duplicates are not allowed.")

        if 'section' in conflict_types:
            parts.append(f"The section already has a {entity_label} at the selected time.")

        if 'faculty' in conflict_types:
            parts.append("The faculty member is already assigned elsewhere at this time.")

        if 'room' in conflict_types:
            parts.append("The room is already occupied at this time.")

        if 'time_invalid' in conflict_types:
            parts.append("The selected time falls outside the allowed schedule hours.")

        if 'workload' in conflict_types:
            parts.append("Adding this would exceed the faculty member's maximum workload.")

        if 'proctor_unavailable' in conflict_types:
            parts.append("The proctor is marked as unavailable for this time slot.")

        # Recommendations hint
        if recommendations:
            total_options = sum(len(r.options) for r in recommendations if hasattr(r, 'options'))
            if total_options > 0:
                rec_types = [r.type for r in recommendations if r.options]
                hints = []
                for rt in rec_types:
                    if rt == 'time':
                        hints.append("alternative times")
                    elif rt == 'day':
                        hints.append("other days")
                    elif rt == 'room':
                        hints.append("available rooms")
                    elif rt == 'faculty':
                        hints.append("other faculty")
                    elif rt in ('exam_time', 'exam_date'):
                        hints.append("alternative slots")
                if hints:
                    parts.append(f"💡 Suggestions available: {', '.join(hints)}.")

        return " ".join(parts) if parts else f"Conflicts detected with this {entity_label}. Review suggestions below."

    # ========== LEGACY EXAM METHODS (kept for backward compatibility) ==========
    
    def _detect_exam_conflicts(self, exam_data: Dict, existing_exams: List) -> List[Dict]:
        """Detect exam scheduling conflicts - LEGACY, use conflict_detector instead"""
        conflicts = []
        
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        section_id = exam_data.get('section_id')
        subject_id = exam_data.get('subject_id')
        faculty_id = exam_data.get('faculty_id')
        room_id = exam_data.get('room_id')
        schedule_type = exam_data.get('schedule_type', 'lecture')
        
        for exam in existing_exams:
            # Check if same subject + section + schedule_type is already scheduled
            # This prevents double-booking the same exam type
            exam_type = getattr(exam, 'schedule_type', 'lecture') or 'lecture'
            if subject_id and exam.subject_id == subject_id and exam.section_id == section_id and exam_type == schedule_type:
                type_label = ' (Lab)' if schedule_type == 'lab' else ''
                conflicts.append({
                    'type': 'duplicate',
                    'message': f'Subject {exam.subject.subject_code}{type_label} is already scheduled for an exam on {exam.exam_date.strftime("%B %d, %Y")} at {exam.start_time.strftime("%I:%M %p")}',
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
                section_display = f"{exam.section.program.program_code}-{exam.section.year_level}{exam.section.section_name}" if exam.section and exam.section.program else exam.section.section_name if exam.section else 'Unknown Section'
                conflicts.append({
                    'type': 'section',
                    'message': f'Section {section_display} already has an exam scheduled for {exam.subject.subject_code}',
                    'schedule': exam,
                    'severity': 'high'
                })
            
            # Faculty conflict - same faculty cannot proctor multiple exams at the same time (across ANY section)
            if faculty_id and exam.faculty_id == faculty_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{exam.section.program.program_code}-{exam.section.year_level}{exam.section.section_name}" if exam.section and exam.section.program else exam.section.section_name if exam.section else 'Unknown Section'
                conflicts.append({
                    'type': 'faculty',
                    'message': f'Faculty {exam.faculty.full_name} is already proctoring an exam for {section_display} ({exam.subject.subject_code})',
                    'schedule': exam,
                    'severity': 'high'
                })
            
            # Room conflict - same room cannot host multiple exams at the same time (across ANY section)
            if room_id and exam.room_id == room_id:
                # Format section name as DEPTCODE-YEARLEVELSECTIONName
                section_display = f"{exam.section.program.program_code}-{exam.section.year_level}{exam.section.section_name}" if exam.section and exam.section.program else exam.section.section_name if exam.section else 'Unknown Section'
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
        from app.models.curriculum import Subject
        
        alternatives = []
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        current_room_id = exam_data.get('room_id')
        subject_id = exam_data.get('subject_id')
        
        # Determine allowed room types based on subject
        allowed_types = ['Lecture']
        if subject_id:
            subject = Subject.query.get(subject_id)
            if subject:
                # Check for PE/Sports
                subject_code_lower = subject.subject_code.lower()
                subject_desc_lower = subject.course_description.lower()
                is_pe = any(keyword in subject_code_lower for keyword in ['pe', 'pathfit', 'p.e.']) or \
                        any(keyword in subject_desc_lower for keyword in ['physical education', 'sports', 'fitness', 'gymnastics'])
                
                if is_pe:
                    allowed_types = ['Court/Gym']
                elif subject.lab_units > 0 and subject.lec_units > 0:
                    allowed_types = ['Lecture', 'Laboratory']
                elif subject.lab_units > 0:
                    allowed_types = ['Laboratory']
        
        # Get all available rooms of the allowed types
        all_rooms = Room.query.filter(Room.is_available==True, Room.room_type.in_(allowed_types)).all()
        
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
                    'display': f'{room.room_number} ({room.building.building_name if room.building else "N/A"}) - {room.room_type}',
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
    
    def suggest_rooms(
        self,
        subject_id: int,
        day: str,
        start_time: time,
        end_time: time,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Dict]:
        """Suggest appropriate rooms based on subject type and availability"""
        from app.models.building import Room
        from app.models.curriculum import Subject
        from app.models.schedule import Schedule
        from app.models.settings import AcademicSettings
        
        suggestions = []
        
        # Get subject to check type
        subject = Subject.query.get(subject_id)
        if not subject:
            return []
            
        is_lab = subject.lab_units > 0
        is_lecture = subject.lec_units > 0
        
        # Check for PE/Sports subject
        subject_code_lower = subject.subject_code.lower()
        subject_desc_lower = subject.course_description.lower()
        is_pe = any(keyword in subject_code_lower for keyword in ['pe', 'pathfit', 'p.e.']) or \
                any(keyword in subject_desc_lower for keyword in ['physical education', 'sports', 'fitness', 'gymnastics'])
        
        # Get current settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not current_settings:
            return []
            
        # Get all active rooms
        all_rooms = Room.query.filter_by(is_available=True).all()
        
        for room in all_rooms:
            # Check for conflicts
            conflicts = Schedule.query.filter(
                Schedule.room_id == room.id,
                Schedule.day_of_week == day,
                Schedule.is_active == True,
                Schedule.academic_year == current_settings.academic_year,
                Schedule.semester == current_settings.semester,
                or_(
                    and_(Schedule.start_time < end_time, Schedule.end_time > start_time)
                )
            )

            if exclude_schedule_id:
                conflicts = conflicts.filter(Schedule.id != exclude_schedule_id)

            conflicts = conflicts.count()
            
            if conflicts == 0:
                # Score the room
                score = 100
                room_name_lower = room.room_number.lower()
                room_type = getattr(room, 'room_type', 'Lecture')
                
                # Exclude Court/Gym rooms for non-PE subjects
                if room_type == 'Court/Gym' and not is_pe:
                    continue
                
                # PE Logic
                if is_pe:
                    if room_type == 'Court/Gym':
                        score += 100 # Perfect match
                    elif room_type == 'Laboratory':
                        score -= 80 # Strong penalty
                    else:
                        score -= 40 # Penalty for lecture rooms
                        
                    # Fallback name check
                    pe_facilities = ['gym', 'court', 'field', 'oval', 'covered', 'sports', 'plaza']
                    if any(facility in room_name_lower for facility in pe_facilities):
                        score += 20
                
                # Lab Logic
                elif is_lab:
                    if is_lecture: # Mixed subject
                        if room_type == 'Laboratory':
                            score += 100
                        elif room_type == 'Lecture':
                            score += 90 # Almost as good
                        elif room_type == 'Court/Gym':
                            score -= 80
                    else: # Pure Lab
                        if room_type == 'Laboratory':
                            score += 100 # Perfect match
                        elif room_type == 'Court/Gym':
                            score -= 80 # Strong penalty
                        else:
                            score -= 40 # Penalty for lecture rooms
                        
                    # Fallback name check
                    if 'lab' in room_name_lower or 'com' in room_name_lower:
                        score += 20
                
                # Lecture Logic
                else:
                    if room_type == 'Lecture':
                        score += 50 # Good match
                    elif room_type == 'Laboratory':
                        score -= 30 # Can use lab for lecture but not ideal
                    elif room_type == 'Court/Gym':
                        score -= 80 # Strong penalty
                    
                    # Fallback name check
                    if 'lab' in room_name_lower or 'com' in room_name_lower:
                        score -= 10
                
                suggestions.append({
                    'id': room.id,
                    'name': room.room_number,
                    'type': room_type,
                    'score': score,
                    'building': room.building.building_name if room.building else ""
                })
        
        # Sort by score
        return sorted(suggestions, key=lambda x: x['score'], reverse=True)

    def suggest_optimal_schedule(self, section: Section, subject: Subject, 
                                faculty: Optional[Faculty] = None) -> Dict:
        """
        Suggest optimal scheduling considering workload balance and patterns
        
        Returns:
            Dictionary with suggested day, time, and AI reasoning
        """
        # Core logic is pure Python — no Gemini needed
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
            'offline_mode': not self.enabled,
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
        from app.models.settings import AcademicSettings
        all_days = AcademicSettings.get_active_operation_days()
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
        start_hour = (current_settings.schedule_start_time.hour if current_settings and current_settings.schedule_start_time else 7)
        end_hour = (current_settings.schedule_end_time.hour if current_settings and current_settings.schedule_end_time else 20)
        
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
                               semester: str = None, program_name: str = None) -> Dict:
        """
        Generate a professional executive-style AI summary of the report statistics.
        
        Args:
            stats: Dictionary containing all report statistics
            academic_year: Current academic year
            semester: Current semester
            program_name: Specific program being analyzed (if filtered)
        
        Returns:
            Dictionary with summary text, severity-tagged insights, and prioritized recommendations
        """
        if not self.enabled or not self.model:
            return self._generate_offline_report_summary(stats, academic_year, semester, program_name)
        
        try:
            # Build scope context
            scope = f"PROGRAM: {program_name}\n" if program_name else "SCOPE: All Programs / Institution-wide\n"
            
            # Calculate utilization rates
            total_faculty = stats.get('total_faculty', 0)
            faculty_with_schedules = stats.get('faculty_with_schedules', 0)
            unassigned_faculty = stats.get('unassigned_faculty_count', total_faculty - faculty_with_schedules)
            faculty_utilization = round((faculty_with_schedules / total_faculty * 100), 1) if total_faculty > 0 else 0
            
            total_rooms = stats.get('total_rooms', 0)
            rooms_in_use = stats.get('rooms_in_use', 0)
            unused_rooms = stats.get('unused_rooms_count', total_rooms - rooms_in_use)
            room_usage_rate = round((rooms_in_use / total_rooms * 100), 1) if total_rooms > 0 else 0
            
            avg_room_utilization = stats.get('avg_room_utilization', 0)
            total_hours_used = stats.get('total_room_hours_used', 0)
            
            completion_rate = stats.get('schedule_completion_rate', 0)
            overloaded_count = stats.get('overloaded_faculty_count', 0)
            
            # Prepare context for AI with enhanced metrics
            context = f"""You are a scheduling operations analyst preparing an executive briefing for a university dean or administrator. Analyze the following scheduling data and provide a professional, data-driven assessment.

PERIOD: {academic_year or 'N/A'}, {semester or 'N/A'}
{scope}
=== OVERVIEW METRICS ===
- Total Class Schedules: {stats.get('total_schedules', 0)}
- Total Exam Schedules: {stats.get('total_exam_schedules', 0)}
- Schedule Types: {stats.get('lecture_count', 0)} lectures, {stats.get('lab_count', 0)} labs
- Active Sections: {stats.get('total_sections', 0)}
- Schedule Completion: {completion_rate:.1f}% of sections scheduled

=== FACULTY UTILIZATION ===
- Total Faculty: {total_faculty}
- Assigned (with schedules): {faculty_with_schedules} ({faculty_utilization}%)
- Unassigned (no schedules): {unassigned_faculty}
- Overloaded (exceed max units): {overloaded_count}
- At Warning Level (>80% load): {stats.get('warning_faculty_count', 0)}
- Average Utilization: {stats.get('avg_faculty_utilization', 0):.1f}%
{self._format_unassigned_by_dept(stats.get('unassigned_faculty_by_dept', {}))}

=== ROOM UTILIZATION ===
- Total Rooms: {total_rooms}
- Rooms in Use: {rooms_in_use} ({room_usage_rate}%)
- Unused Rooms: {unused_rooms}
- Average Room Utilization: {avg_room_utilization}% (based on weekly capacity)
- Total Hours Scheduled: {total_hours_used} hrs
{self._format_unused_by_type(stats.get('unused_rooms_by_type', {}))}

=== BUILDING UTILIZATION ===
{self._format_building_utilization(stats.get('room_utilization_by_building', {}))}

=== TOP FACULTY BY WORKLOAD ===
{self._format_faculty_workload(stats.get('faculty_workloads', [])[:5])}

=== TOP ROOMS BY USAGE ===
{self._format_room_utilization_hours(stats.get('room_utilizations', [])[:5])}

=== WEEKLY DISTRIBUTION ===
{self._format_weekly_distribution(stats.get('schedule_by_day', {}))}

---

Respond EXACTLY in this format (plain text only, no markdown):

EXECUTIVE SUMMARY
Write 2-3 sentences. State the overall scheduling health from completion, faculty load, and room utilization. Mention the single most critical issue and the strongest metric. Be precise with numbers.

KEY FINDINGS
Write exactly 5 bullet points. Each MUST start with a severity tag in square brackets:
- [CRITICAL] for issues requiring immediate action (conflicts, overloaded faculty, completion < 50%)
- [WARNING] for concerning trends needing attention (unused resources > 30%, unassigned faculty, imbalanced days)
- [INFO] for positive observations or neutral facts (strong metrics, balanced loads, good completion rates)
Format: [TAG] Finding text with specific numbers.

PRIORITY ACTIONS
Write exactly 4 bullet points. Each MUST start with a priority tag in square brackets:
- [HIGH] for actions addressing critical issues
- [MEDIUM] for optimization opportunities
- [LOW] for nice-to-have improvements
Format: [TAG] Action description — expected impact.

RULES:
- Be specific and cite actual numbers from the data
- {"Focus exclusively on " + program_name + " data." if program_name else "Consider institution-wide patterns."}
- DO NOT use any markdown formatting (no **, *, #, or _)
- DO NOT number the bullet points
- Each bullet point must start with a dash (-)
- Keep each bullet point to 1-2 sentences maximum
"""
            
            # Generate AI response
            response = self.model.generate_content(context)
            summary_text = response.text
            
            # Parse the response into structured sections
            insights = self._extract_tagged_bullets(summary_text, "Key Findings", "Priority Actions")
            if not insights:
                # Fallback to old markers
                insights = self._extract_tagged_bullets(summary_text, "Key Insights", "Recommendations")
                if not insights:
                    insights = self._extract_tagged_bullets(summary_text, "Insights", "Recommendations")
            
            recommendations = self._extract_tagged_bullets(summary_text, "Priority Actions", None)
            if not recommendations:
                recommendations = self._extract_tagged_bullets(summary_text, "Recommendations", None)
            
            # Extract main summary (everything before Key Findings / Key Insights)
            for marker in ["Key Findings", "KEY FINDINGS", "Key Insights", "KEY INSIGHTS", "Insights", "Recommendations"]:
                if marker in summary_text:
                    main_summary = summary_text.split(marker)[0].strip()
                    break
            else:
                main_summary = summary_text
            
            # Clean up markdown formatting and section headers from summary
            for remove_str in ['**', 'EXECUTIVE SUMMARY', 'Executive Summary:', 'Executive Summary', 'SUMMARY', 'Summary:', 'Summary']:
                main_summary = main_summary.replace(remove_str, '')
            main_summary = main_summary.lstrip(':- \n').strip()
            
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
    
    def _generate_offline_report_summary(self, stats: Dict, academic_year: str = None,
                                         semester: str = None, program_name: str = None) -> Dict:
        """
        Generate a rule-based offline report summary with severity-tagged insights.
        Works without Gemini API key. Matches the structured format of the AI version.
        """
        total_schedules = stats.get('total_schedules', 0)
        total_exams = stats.get('total_exam_schedules', 0)
        total_faculty = stats.get('total_faculty', 0)
        faculty_with_schedules = stats.get('faculty_with_schedules', 0)
        unassigned_count = stats.get('unassigned_faculty_count', total_faculty - faculty_with_schedules)
        total_rooms = stats.get('total_rooms', 0)
        rooms_in_use = stats.get('rooms_in_use', 0)
        unused_rooms_count = stats.get('unused_rooms_count', total_rooms - rooms_in_use)
        avg_room_util = stats.get('avg_room_utilization', 0)
        overloaded = stats.get('overloaded_faculty_count', 0)
        completion = stats.get('schedule_completion_rate', 0)

        scope = f"for {program_name}" if program_name else "across all programs"
        period = f"{academic_year}, {semester}" if academic_year else "the current period"

        # Build summary
        faculty_pct = round((faculty_with_schedules / total_faculty * 100), 1) if total_faculty > 0 else 0
        room_pct = round((rooms_in_use / total_rooms * 100), 1) if total_rooms > 0 else 0

        summary = (
            f"During {period} {scope}: {total_schedules} class schedules and {total_exams} exam "
            f"schedules are active. Faculty utilization is at {faculty_pct}% ({faculty_with_schedules}/{total_faculty}), "
            f"room usage is at {room_pct}% ({rooms_in_use}/{total_rooms}), "
            f"and schedule completion stands at {completion:.0f}%."
        )

        # Build severity-tagged insights
        insights = []
        
        if overloaded > 0:
            insights.append({'text': f'{overloaded} faculty member(s) exceed their maximum unit load — immediate rebalancing required.', 'severity': 'critical'})
        
        if completion < 50:
            insights.append({'text': f'Only {completion:.0f}% of sections are scheduled — significant scheduling work remains.', 'severity': 'critical'})
        elif completion < 80:
            insights.append({'text': f'Schedule completion at {completion:.0f}% — continued progress needed.', 'severity': 'warning'})
        elif completion >= 90:
            insights.append({'text': f'Schedule completion is strong at {completion:.0f}%.', 'severity': 'info'})
        
        if unassigned_count > 0:
            severity = 'warning' if unassigned_count <= 3 else 'critical'
            insights.append({'text': f'{unassigned_count} faculty member(s) have no schedules assigned — review subject assignments.', 'severity': severity})
        
        if unused_rooms_count > 0:
            unused_pct = round((unused_rooms_count / total_rooms * 100)) if total_rooms > 0 else 0
            by_type = stats.get('unused_rooms_by_type', {})
            type_info = ", ".join(f"{v} {k}" for k, v in by_type.items()) if by_type else f"{unused_rooms_count} room(s)"
            severity = 'warning' if unused_pct > 30 else 'info'
            insights.append({'text': f'{unused_rooms_count} rooms ({unused_pct}%) unused: {type_info}.', 'severity': severity})
        
        if avg_room_util < 30 and total_rooms > 0:
            insights.append({'text': f'Average room utilization is low at {avg_room_util:.1f}% — consider consolidating schedules.', 'severity': 'warning'})

        # Day distribution insight
        day_dist = stats.get('schedule_by_day', {})
        if day_dist:
            active_days = {d: c for d, c in day_dist.items() if c > 0}
            if len(active_days) >= 2:
                max_day = max(active_days, key=active_days.get)
                min_day = min(active_days, key=active_days.get)
                if active_days[max_day] > active_days[min_day] * 2:
                    insights.append({'text': f'Schedule imbalance: {max_day} has {active_days[max_day]} classes vs {min_day} with {active_days[min_day]}.', 'severity': 'warning'})

        if not insights:
            insights.append({'text': 'Scheduling metrics are within normal ranges.', 'severity': 'info'})

        # Build priority-tagged recommendations
        recommendations = []
        if overloaded > 0:
            recommendations.append({'text': 'Redistribute overloaded faculty schedules to maintain quality of instruction.', 'priority': 'high'})
        if unassigned_count > 0:
            recommendations.append({'text': 'Review unassigned faculty and ensure subject assignments are current.', 'priority': 'high'})
        if completion < 80:
            recommendations.append({'text': 'Use Auto-Generate Schedule to fill remaining unscheduled sections efficiently.', 'priority': 'high' if completion < 50 else 'medium'})
        if unused_rooms_count > 3:
            recommendations.append({'text': 'Consolidate class scheduling to reduce unused room overhead.', 'priority': 'medium'})
        if avg_room_util < 40 and total_rooms > 0:
            recommendations.append({'text': 'Use the auto-generate feature to optimize room allocation.', 'priority': 'medium'})
        
        if not recommendations:
            recommendations.append({'text': 'Continue monitoring utilization as the semester progresses.', 'priority': 'low'})

        return {
            'ai_enabled': False,
            'offline_mode': True,
            'summary': summary,
            'insights': insights[:5],
            'recommendations': recommendations[:4]
        }

    def _format_faculty_workload(self, faculty_list: List[Dict]) -> str:
        """Format faculty workload data for AI context"""
        if not faculty_list:
            return "No faculty data available"
        
        lines = []
        for i, faculty in enumerate(faculty_list, 1):
            dept = faculty.get('program', 'N/A')
            lines.append(
                f"{i}. {faculty['name']} ({dept}): {faculty['total_units']} units, {faculty['schedules']} classes ({faculty.get('lec_units', 0)} lec + {faculty.get('lab_units', 0)} lab)"
            )
        return "\n".join(lines)
    
    def _format_room_utilization(self, room_list: List[Dict]) -> str:
        """Format room utilization data for AI context (legacy)"""
        if not room_list:
            return "No room data available"
        
        lines = []
        for i, room in enumerate(room_list, 1):
            lines.append(
                f"{i}. {room['room']}: {room['total_usage']} uses"
            )
        return "\n".join(lines)
    
    def _format_room_utilization_hours(self, room_list: List[Dict]) -> str:
        """Format room utilization data with hours-based metrics"""
        if not room_list:
            return "No room data available"
        
        lines = []
        for i, room in enumerate(room_list, 1):
            building = room.get('building', 'N/A')
            room_type = room.get('type', 'N/A')
            total_hours = room.get('total_hours', 0)
            utilization = room.get('utilization_pct', 0)
            lines.append(
                f"{i}. {room['room']} ({building}, {room_type}): {total_hours} hrs/week, {utilization}% utilized"
            )
        return "\n".join(lines)
    
    def _format_unassigned_by_dept(self, unassigned_by_dept: Dict) -> str:
        """Format unassigned faculty by program"""
        if not unassigned_by_dept:
            return ""
        
        lines = ["  Unassigned by Program:"]
        for dept, count in unassigned_by_dept.items():
            lines.append(f"    - {dept}: {count} faculty")
        return "\n".join(lines)
    
    def _format_unused_by_type(self, unused_by_type: Dict) -> str:
        """Format unused rooms by type"""
        if not unused_by_type:
            return ""
        
        lines = ["  Unused by Room Type:"]
        for room_type, count in unused_by_type.items():
            lines.append(f"    - {room_type}: {count} rooms")
        return "\n".join(lines)
    
    def _format_building_utilization(self, building_util: Dict) -> str:
        """Format building-level utilization data"""
        if not building_util:
            return "No building data available"
        
        lines = []
        for building, data in building_util.items():
            total_rooms = data.get('total', 0)
            rooms_in_use = data.get('in_use', 0)
            total_hours = data.get('total_hours', 0)
            max_hours = data.get('max_hours', 0)
            utilization = data.get('utilization_pct', 0)
            lines.append(
                f"- {building}: {rooms_in_use}/{total_rooms} rooms active, {total_hours}/{max_hours} hrs ({utilization}% utilized)"
            )
        return "\n".join(lines) if lines else "No building data available"
    
    def _format_weekly_distribution(self, schedule_by_day: Dict) -> str:
        """Format weekly distribution for AI context with analysis hints"""
        if not schedule_by_day:
            return "No weekly data available"
        
        total = sum(schedule_by_day.values())
        if total == 0:
            return "No schedules recorded"
        
        lines = []
        max_day = max(schedule_by_day.items(), key=lambda x: x[1]) if schedule_by_day else (None, 0)
        min_day = min(schedule_by_day.items(), key=lambda x: x[1]) if schedule_by_day else (None, 0)
        
        for day, count in schedule_by_day.items():
            pct = round((count / total * 100), 1) if total > 0 else 0
            marker = " (PEAK)" if day == max_day[0] else " (LOW)" if day == min_day[0] else ""
            lines.append(f"- {day}: {count} schedules ({pct}%){marker}")
        
        return "\n".join(lines)
    
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
            
            return bullets[:5]  # Limit to 5 items
        except Exception:
            return []
    
    def _extract_tagged_bullets(self, text: str, start_marker: str,
                                end_marker: Optional[str]) -> List[Dict]:
        """Extract bullet points with severity/priority tags from AI response.
        
        Returns list of dicts: [{'text': '...', 'severity': 'critical|warning|info'}]
        or [{'text': '...', 'priority': 'high|medium|low'}] depending on section.
        Falls back to plain strings wrapped in dicts if no tags found.
        """
        import re
        try:
            # Case-insensitive search for the marker
            text_lower = text.lower()
            marker_lower = start_marker.lower()
            
            if marker_lower not in text_lower:
                return []
            
            start_idx = text_lower.index(marker_lower) + len(start_marker)
            
            if end_marker:
                end_lower = end_marker.lower()
                if end_lower in text_lower[start_idx:]:
                    end_idx = text_lower.index(end_lower, start_idx)
                    section = text[start_idx:end_idx]
                else:
                    section = text[start_idx:]
            else:
                section = text[start_idx:]
            
            lines = section.strip().split('\n')
            bullets = []
            for line in lines:
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                    
                # Check if line is a bullet point
                if not (line.startswith(('-', '*', '\u2022', '**')) or 
                       (len(line) > 2 and line[0].isdigit() and line[1] in '.)'))  :
                    continue
                
                # Clean leading bullet markers
                cleaned = line.lstrip('-*\u20220123456789.) ').strip()
                cleaned = cleaned.replace('**', '').replace('__', '').strip()
                
                if not cleaned or len(cleaned) < 10:
                    continue
                
                # Extract tag like [CRITICAL], [WARNING], [INFO], [HIGH], [MEDIUM], [LOW]
                tag_match = re.match(r'\[([A-Za-z]+)\]\s*(.*)', cleaned)
                if tag_match:
                    tag = tag_match.group(1).lower()
                    bullet_text = tag_match.group(2).strip()
                    # Remove any remaining markdown
                    bullet_text = bullet_text.replace('*', '').strip()
                    
                    if tag in ('critical', 'warning', 'info'):
                        bullets.append({'text': bullet_text, 'severity': tag})
                    elif tag in ('high', 'medium', 'low'):
                        bullets.append({'text': bullet_text, 'priority': tag})
                    else:
                        bullets.append({'text': bullet_text, 'severity': 'info'})
                else:
                    # No tag found — auto-classify as info/medium
                    cleaned = cleaned.replace('*', '').strip()
                    if any(k in start_marker.lower() for k in ('finding', 'insight')):
                        bullets.append({'text': cleaned, 'severity': 'info'})
                    else:
                        bullets.append({'text': cleaned, 'priority': 'medium'})
            
            return bullets[:5]
        except Exception:
            return []


# Global instance
ai_scheduler = AISchedulerAssistant()
