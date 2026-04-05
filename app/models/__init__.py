"""
Models package - imports all models for easy access
"""
from app.models.user import User
from app.models.department import Department
from app.models.program import Program
from app.models.section import Section
from app.models.curriculum import Curriculum, YearLevel, Semester, Subject
from app.models.faculty import Faculty, FacultySubjectAssignment, FacultyAvailability
from app.models.building import Building, Room
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.schedule_snapshot import ScheduleSnapshot
from app.models.settings import AcademicSettings, InstitutionSettings
from app.models.archive import Archive
from app.models.activity_log import UserActivityLog
from app.models.login_history import LoginHistory
from app.models.system_config import SystemConfig
from app.models.trusted_device import TrustedDevice

__all__ = [
    'User',
    'Department',
    'Program',
    'Section',
    'Curriculum',
    'YearLevel',
    'Semester',
    'Subject',
    'Faculty',
    'FacultySubjectAssignment',
    'FacultyAvailability',
    'Building',
    'Room',
    'Schedule',
    'ExamSchedule',
    'ScheduleSnapshot',
    'AcademicSettings',
    'InstitutionSettings',
    'Archive',
    'UserActivityLog',
    'LoginHistory',
    'SystemConfig',
    'TrustedDevice',
]

