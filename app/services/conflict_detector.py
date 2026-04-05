"""
Conflict Detection Service
Pure Python conflict checking - no AI dependencies
Fast, synchronous conflict detection for schedules and exams
"""
from datetime import time, datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ConflictSeverity(Enum):
    """Conflict severity levels for UI display"""
    CRITICAL = "critical"  # Blocks submission (duplicate exam, same section overlap)
    HIGH = "high"          # Strong warning (faculty/room double-booking)
    MEDIUM = "medium"      # Advisory (workload imbalance)
    LOW = "low"            # Informational


class ConflictType(Enum):
    """Types of scheduling conflicts"""
    DUPLICATE = "duplicate"
    SECTION = "section"
    FACULTY = "faculty"
    ROOM = "room"
    TIME_INVALID = "time_invalid"
    DATE_PAST = "date_past"
    WORKLOAD = "workload"
    PROCTOR_UNAVAILABLE = "proctor_unavailable"  # Proctor marked as unavailable for the time slot


@dataclass
class Conflict:
    """Represents a single conflict with all metadata"""
    type: ConflictType
    severity: ConflictSeverity
    message: str
    details: Dict
    conflicting_schedule_id: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON response"""
        return {
            'type': self.type.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'conflicting_schedule_id': self.conflicting_schedule_id
        }


class ConflictDetector:
    """
    Pure Python conflict detection - no AI API calls
    Fast synchronous checking for immediate feedback
    """
    
    @staticmethod
    def times_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
        """Check if two time ranges overlap"""
        return start1 < end2 and end1 > start2
    
    def detect_class_conflicts(
        self, 
        schedule_data: Dict,
        existing_schedules: List,
        exclude_schedule_id: Optional[int] = None
    ) -> List[Conflict]:
        """
        Detect conflicts for class schedules
        
        Args:
            schedule_data: Dict with section_id, faculty_id, room_id, day_of_week, start_time, end_time
            existing_schedules: List of existing Schedule objects
            exclude_schedule_id: ID to exclude (for edit mode)
            
        Returns:
            List of Conflict objects sorted by severity
        """
        conflicts = []
        
        day = schedule_data.get('day_of_week')
        start_time = schedule_data.get('start_time')
        end_time = schedule_data.get('end_time')
        section_id = schedule_data.get('section_id')
        faculty_id = schedule_data.get('faculty_id')
        room_id = schedule_data.get('room_id')
        
        # Validate time range first
        if start_time and end_time and start_time >= end_time:
            conflicts.append(Conflict(
                type=ConflictType.TIME_INVALID,
                severity=ConflictSeverity.CRITICAL,
                message="End time must be after start time",
                details={'start_time': str(start_time), 'end_time': str(end_time)}
            ))
            return conflicts  # Return early - invalid time
        
        for schedule in existing_schedules:
            # Skip excluded schedule (edit mode)
            if exclude_schedule_id and schedule.id == exclude_schedule_id:
                continue
            
            # Check if same day
            if schedule.day_of_week != day:
                continue
            
            # Check time overlap
            if not self.times_overlap(start_time, end_time, schedule.start_time, schedule.end_time):
                continue
            
            # Build section display name
            section_display = self._get_section_display(schedule.section)
            time_display = f"{schedule.start_time.strftime('%I:%M %p')} - {schedule.end_time.strftime('%I:%M %p')}"
            
            # Section conflict - same section, overlapping time
            if schedule.section_id == section_id:
                subject_code = schedule.subject.subject_code if schedule.subject else 'N/A'
                schedule_type_label = getattr(schedule, 'schedule_type', 'lecture') or 'lecture'
                type_tag = ' (Lab)' if schedule_type_label == 'lab' else ''
                conflicts.append(Conflict(
                    type=ConflictType.SECTION,
                    severity=ConflictSeverity.CRITICAL,
                    message=f"Conflicts with existing {subject_code}{type_tag} in {section_display} at {time_display}",
                    details={
                        'subject': subject_code,
                        'time': time_display,
                        'day': schedule.day_of_week,
                        'conflicting_section': section_display
                    },
                    conflicting_schedule_id=schedule.id
                ))
            
            # Faculty conflict - same faculty, overlapping time (cross-section)
            if faculty_id and schedule.faculty_id == faculty_id:
                faculty_name = schedule.faculty.full_name if schedule.faculty else 'Unknown'
                subject_code = schedule.subject.subject_code if schedule.subject else 'N/A'
                conflicts.append(Conflict(
                    type=ConflictType.FACULTY,
                    severity=ConflictSeverity.HIGH,
                    message=f"{faculty_name} is teaching {section_display} ({subject_code}) at {time_display}",
                    details={
                        'faculty': faculty_name,
                        'subject': subject_code,
                        'time': time_display,
                        'day': schedule.day_of_week,
                        'conflicting_section': section_display
                    },
                    conflicting_schedule_id=schedule.id
                ))
            
            # Room conflict - same room, overlapping time (cross-section)
            if room_id and schedule.room_id == room_id:
                room_number = schedule.room.room_number if schedule.room else 'Unknown'
                subject_code = schedule.subject.subject_code if schedule.subject else 'N/A'
                conflicts.append(Conflict(
                    type=ConflictType.ROOM,
                    severity=ConflictSeverity.HIGH,
                    message=f"Room {room_number} is occupied by {section_display} ({subject_code}) at {time_display}",
                    details={
                        'room': room_number,
                        'subject': subject_code,
                        'time': time_display,
                        'day': schedule.day_of_week,
                        'conflicting_section': section_display
                    },
                    conflicting_schedule_id=schedule.id
                ))
        
        # Sort by severity (critical first)
        severity_order = {
            ConflictSeverity.CRITICAL: 0,
            ConflictSeverity.HIGH: 1,
            ConflictSeverity.MEDIUM: 2,
            ConflictSeverity.LOW: 3
        }
        conflicts.sort(key=lambda c: severity_order[c.severity])
        
        return conflicts
    
    def detect_exam_conflicts(
        self,
        exam_data: Dict,
        existing_exams: List,
        exclude_exam_id: Optional[int] = None
    ) -> List[Conflict]:
        """
        Detect conflicts for exam schedules
        
        Args:
            exam_data: Dict with section_id, subject_id, faculty_id, room_id, exam_date, start_time, end_time
            existing_exams: List of existing ExamSchedule objects
            exclude_exam_id: ID to exclude (for edit mode)
            
        Returns:
            List of Conflict objects sorted by severity
        """
        conflicts = []
        
        exam_date = exam_data.get('exam_date')
        start_time = exam_data.get('start_time')
        end_time = exam_data.get('end_time')
        section_id = exam_data.get('section_id')
        subject_id = exam_data.get('subject_id')
        faculty_id = exam_data.get('faculty_id')
        room_id = exam_data.get('room_id')
        schedule_type = exam_data.get('schedule_type', 'lecture')
        
        # Validate time range
        if start_time and end_time and start_time >= end_time:
            conflicts.append(Conflict(
                type=ConflictType.TIME_INVALID,
                severity=ConflictSeverity.CRITICAL,
                message="End time must be after start time",
                details={'start_time': str(start_time), 'end_time': str(end_time)}
            ))
            return conflicts
        
        # Validate exam date is not in the past
        if exam_date and exam_date < datetime.now().date():
            conflicts.append(Conflict(
                type=ConflictType.DATE_PAST,
                severity=ConflictSeverity.CRITICAL,
                message="Cannot schedule exams in the past",
                details={'exam_date': str(exam_date)}
            ))
            return conflicts
        
        # Check proctor (faculty) availability if faculty is assigned
        if faculty_id and exam_date and start_time and end_time:
            proctor_conflict = self._check_proctor_availability(
                faculty_id, exam_date, start_time, end_time
            )
            if proctor_conflict:
                conflicts.append(proctor_conflict)
        
        for exam in existing_exams:
            # Skip excluded exam (edit mode)
            if exclude_exam_id and exam.id == exclude_exam_id:
                continue
            
            # Check if same date
            if exam.exam_date != exam_date:
                continue
            
            # Check time overlap
            if not self.times_overlap(start_time, end_time, exam.start_time, exam.end_time):
                continue
            
            section_display = self._get_section_display(exam.section)
            time_display = f"{exam.start_time.strftime('%I:%M %p')} - {exam.end_time.strftime('%I:%M %p')}"
            
            # Section conflict - same section, overlapping time
            if exam.section_id == section_id:
                subject_code = exam.subject.subject_code if exam.subject else 'N/A'
                conflicts.append(Conflict(
                    type=ConflictType.SECTION,
                    severity=ConflictSeverity.HIGH,
                    message=f"Section {section_display} has {subject_code} exam at {time_display}",
                    details={
                        'subject': subject_code,
                        'time': time_display,
                        'date': str(exam_date),
                        'conflicting_section': section_display
                    },
                    conflicting_schedule_id=exam.id
                ))
            
            # Faculty conflict - same faculty, overlapping time (cross-section)
            if faculty_id and exam.faculty_id == faculty_id:
                faculty_name = exam.faculty.full_name if exam.faculty else 'Unknown'
                subject_code = exam.subject.subject_code if exam.subject else 'N/A'
                conflicts.append(Conflict(
                    type=ConflictType.FACULTY,
                    severity=ConflictSeverity.HIGH,
                    message=f"{faculty_name} is proctoring {section_display} ({subject_code}) at {time_display}",
                    details={
                        'faculty': faculty_name,
                        'subject': subject_code,
                        'time': time_display,
                        'date': str(exam_date),
                        'conflicting_section': section_display
                    },
                    conflicting_schedule_id=exam.id
                ))
            
            # Room conflict - same room, overlapping time (cross-section)
            if room_id and exam.room_id == room_id:
                room_number = exam.room.room_number if exam.room else 'Unknown'
                subject_code = exam.subject.subject_code if exam.subject else 'N/A'
                conflicts.append(Conflict(
                    type=ConflictType.ROOM,
                    severity=ConflictSeverity.HIGH,
                    message=f"Room {room_number} is used by {section_display} ({subject_code}) at {time_display}",
                    details={
                        'room': room_number,
                        'subject': subject_code,
                        'time': time_display,
                        'date': str(exam_date),
                        'conflicting_section': section_display
                    },
                    conflicting_schedule_id=exam.id
                ))
        
        # Sort by severity
        severity_order = {
            ConflictSeverity.CRITICAL: 0,
            ConflictSeverity.HIGH: 1,
            ConflictSeverity.MEDIUM: 2,
            ConflictSeverity.LOW: 3
        }
        conflicts.sort(key=lambda c: severity_order[c.severity])
        
        return conflicts
    
    def preview_slot_conflicts(
        self,
        section_id: int,
        faculty_id: Optional[int],
        room_id: Optional[int],
        day_of_week: str,
        time_slots: List[Tuple[time, time]],
        existing_schedules: List
    ) -> Dict[str, List[str]]:
        """
        Quick preview of conflicts for multiple time slots (for hover preview)
        
        Args:
            section_id: Section ID to check
            faculty_id: Faculty ID (optional)
            room_id: Room ID (optional)
            day_of_week: Day to check
            time_slots: List of (start_time, end_time) tuples to check
            existing_schedules: List of existing Schedule objects
            
        Returns:
            Dict mapping time slot string to list of conflict types
        """
        result = {}
        
        for start_time, end_time in time_slots:
            slot_key = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
            slot_conflicts = []
            
            for schedule in existing_schedules:
                if schedule.day_of_week != day_of_week:
                    continue
                
                if not self.times_overlap(start_time, end_time, schedule.start_time, schedule.end_time):
                    continue
                
                if schedule.section_id == section_id:
                    slot_conflicts.append('section')
                if faculty_id and schedule.faculty_id == faculty_id:
                    slot_conflicts.append('faculty')
                if room_id and schedule.room_id == room_id:
                    slot_conflicts.append('room')
            
            result[slot_key] = list(set(slot_conflicts))  # Remove duplicates
        
        return result
    
    def _get_section_display(self, section) -> str:
        """Get formatted section display name"""
        if not section:
            return 'Unknown Section'
        
        if section.program:
            return f"{section.program.program_code}-{section.year_level}{section.section_name}"
        return section.section_name
    
    def _check_proctor_availability(
        self, 
        faculty_id: int, 
        exam_date, 
        start_time: time, 
        end_time: time
    ) -> Optional[Conflict]:
        """
        Check if a faculty member (proctor) is available for the given exam slot.
        
        Uses the FacultyAvailability model to check if the proctor has marked
        themselves as unavailable for this time slot.
        
        Args:
            faculty_id: The faculty ID to check
            exam_date: The exam date
            start_time: Start time of the exam
            end_time: End time of the exam
            
        Returns:
            Conflict object if proctor is unavailable, None otherwise
        """
        try:
            from app.models.faculty import FacultyAvailability, Faculty
            
            # Get faculty name for the message
            faculty = Faculty.query.get(faculty_id)
            faculty_name = faculty.full_name if faculty else 'Unknown Faculty'
            
            # Check availability using the existing model method
            availability_result = FacultyAvailability.check_faculty_available(
                faculty_id, exam_date, start_time, end_time
            )
            
            if availability_result['status'] == 'not_in_schedule':
                return Conflict(
                    type=ConflictType.PROCTOR_UNAVAILABLE,
                    severity=ConflictSeverity.MEDIUM,
                    message=f"{faculty_name} is not marked as available for this time slot",
                    details={
                        'faculty_id': faculty_id,
                        'faculty_name': faculty_name,
                        'date': str(exam_date),
                        'time': f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}",
                        'availability_status': 'not_in_schedule'
                    }
                )
            
            return None
            
        except Exception as e:
            # Log but don't fail the whole conflict check
            import logging
            logging.warning(f"Error checking proctor availability: {e}")
            return None


# Global instance for import
conflict_detector = ConflictDetector()
