"""
Models package - imports all models for easy access
"""
from app.models.user import User
from app.models.department import Department, Section
from app.models.curriculum import Curriculum, YearLevel, Semester, Subject
from app.models.faculty import Faculty, FacultySubjectAssignment
from app.models.building import Building, Room
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.settings import AcademicSettings
from app.models.archive import Archive

__all__ = [
    'User',
    'Department',
    'Section',
    'Curriculum',
    'YearLevel',
    'Semester',
    'Subject',
    'Faculty',
    'FacultySubjectAssignment',
    'Building',
    'Room',
    'Schedule',
    'ExamSchedule',
    'AcademicSettings',
    'Archive',
    # FacultySubjectAssignmentArchive removed - using flag-based archiving on faculty_subject_assignments
]

