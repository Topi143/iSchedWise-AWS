"""
Data Generator Service — Generates realistic Filipino-context sample data
for iSchedWise. Designed for admin tools to populate the system with
artificial but realistic-looking programs, curricula, subjects,
faculty, sections, buildings, rooms, schedules, and exam schedules.

Safety:
    - Blocks generation if data already exists (per entity type)
    - All generated entities can be cleaned up by entity type
    - Uses current active academic settings for schedules
"""

import random
from datetime import datetime, time, date, timedelta
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.program import Program
from app.models.section import Section
from app.models.curriculum import Curriculum, YearLevel, Semester, Subject
from app.models.faculty import Faculty, FacultySubjectAssignment
from app.models.building import Building, Room
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.settings import AcademicSettings


# =========================================================================
# FILIPINO DATA POOLS
# =========================================================================

FILIPINO_FIRST_NAMES_MALE = [
    'Juan', 'Jose', 'Carlos', 'Miguel', 'Rafael', 'Antonio', 'Francisco',
    'Andres', 'Manuel', 'Ricardo', 'Gabriel', 'Marco', 'Diego', 'Fernando',
    'Eduardo', 'Roberto', 'Alejandro', 'Enrique', 'Lorenzo', 'Emilio',
    'Paolo', 'Jericho', 'Renz', 'Kyle', 'Jayson', 'Mark', 'John Paul',
    'Christian', 'Angelo', 'Patrick', 'Jerome', 'Kenneth', 'Ralph',
    'Vincent', 'Adrian', 'Nathaniel', 'Dominic', 'Cedric', 'Tristan',
    'Benedict', 'Elijah', 'Isaiah', 'Ronan', 'Joaquin', 'Mateo',
]

FILIPINO_FIRST_NAMES_FEMALE = [
    'Maria', 'Ana', 'Patricia', 'Isabella', 'Sofia', 'Gabriela',
    'Catalina', 'Teresa', 'Carmen', 'Rosa', 'Lucia', 'Elena',
    'Angelica', 'Bianca', 'Jasmine', 'Samantha', 'Nicole', 'Andrea',
    'Camille', 'Denise', 'Francesca', 'Hannah', 'Kristine', 'Leah',
    'Michelle', 'Princess', 'Rachel', 'Sarah', 'Trisha', 'Vanessa',
    'Yna', 'Zara', 'Abigail', 'Bea', 'Clarisse', 'Danielle',
    'Erica', 'Fatima', 'Graciel', 'Hazel', 'Ivy', 'Janelle',
    'Kimberly', 'Lyka', 'Mylene',
]

FILIPINO_LAST_NAMES = [
    'Santos', 'Reyes', 'Cruz', 'Bautista', 'Gonzales', 'Ramos',
    'Aquino', 'Garcia', 'Mendoza', 'Torres', 'Villanueva', 'Pascual',
    'Dela Cruz', 'Hernandez', 'Lopez', 'Martinez', 'Rivera', 'Perez',
    'Flores', 'Soriano', 'De Guzman', 'Castillo', 'Dimaculangan',
    'Manalo', 'Tolentino', 'Navarro', 'De Leon', 'Salazar', 'Aguilar',
    'Mercado', 'Santiago', 'Pineda', 'Roxas', 'Concepcion', 'Magno',
    'Lugtu', 'Valdez', 'Dizon', 'Pangilinan', 'Lim', 'Tan',
    'Chua', 'Ong', 'Sy', 'Co', 'Yu', 'Alvarez', 'Ilagan',
    'Enriquez', 'Padilla',
]


# =========================================================================
# PHILIPPINE HEI DEPARTMENT / PROGRAM TEMPLATES
# =========================================================================

DEPARTMENT_TEMPLATES = [
    {
        'code': 'BSCS',
        'name': 'Computer Science',
        'full_name': 'Bachelor of Science in Computer Science',
        'year_levels': 4,
        'curriculum_code': 'BSCS-2024',
        'degree': 'Bachelor of Science in Computer Science',
        'subjects': {
            1: {
                1: [  # Year 1, Sem 1
                    ('CS 101', 'Introduction to Computing', 3, 0),
                    ('CS 102', 'Computer Programming 1', 2, 1),
                    ('GE 1', 'Understanding the Self', 3, 0),
                    ('GE 2', 'Readings in Philippine History', 3, 0),
                    ('GE 3', 'The Contemporary World', 3, 0),
                    ('MATH 101', 'Department Algebra', 3, 0),
                    ('PE 1', 'Physical Education 1', 2, 0),
                    ('NSTP 1', 'NSTP - CWTS 1', 3, 0),
                ],
                2: [  # Year 1, Sem 2
                    ('CS 103', 'Computer Programming 2', 2, 1),
                    ('CS 104', 'Discrete Mathematics', 3, 0),
                    ('GE 4', 'Mathematics in the Modern World', 3, 0),
                    ('GE 5', 'Purposive Communication', 3, 0),
                    ('GE 6', 'Art Appreciation', 3, 0),
                    ('MATH 102', 'Plane Trigonometry', 3, 0),
                    ('PE 2', 'Physical Education 2', 2, 0),
                    ('NSTP 2', 'NSTP - CWTS 2', 3, 0),
                ],
            },
            2: {
                1: [
                    ('CS 201', 'Data Structures and Algorithms', 2, 1),
                    ('CS 202', 'Object-Oriented Programming', 2, 1),
                    ('CS 203', 'Architecture and Organization', 3, 0),
                    ('GE 7', 'Science, Technology, and Society', 3, 0),
                    ('GE 8', 'Ethics', 3, 0),
                    ('MATH 201', 'Calculus 1', 3, 0),
                    ('PE 3', 'Physical Education 3', 2, 0),
                ],
                2: [
                    ('CS 204', 'Information Management', 2, 1),
                    ('CS 205', 'Algorithms and Complexity', 3, 0),
                    ('CS 206', 'Operating Systems', 2, 1),
                    ('CS 207', 'Software Engineering 1', 3, 0),
                    ('GE 9', 'The Life and Works of Rizal', 3, 0),
                    ('MATH 202', 'Calculus 2', 3, 0),
                    ('PE 4', 'Physical Education 4', 2, 0),
                ],
            },
            3: {
                1: [
                    ('CS 301', 'Automata Theory and Formal Languages', 3, 0),
                    ('CS 302', 'Programming Languages', 2, 1),
                    ('CS 303', 'Networks and Communications', 2, 1),
                    ('CS 304', 'Software Engineering 2', 2, 1),
                    ('CS 305', 'Human-Computer Interaction', 3, 0),
                    ('CS-E1', 'CS Elective 1', 3, 0),
                    ('FREE-E1', 'Free Elective 1', 3, 0),
                ],
                2: [
                    ('CS 306', 'Intelligent Systems', 2, 1),
                    ('CS 307', 'Parallel and Distributed Computing', 3, 0),
                    ('CS 308', 'Social Issues and Professional Practice', 3, 0),
                    ('CS 309', 'CS Thesis Writing 1', 3, 0),
                    ('CS-E2', 'CS Elective 2', 3, 0),
                    ('CS-E3', 'CS Elective 3', 3, 0),
                    ('FREE-E2', 'Free Elective 2', 3, 0),
                ],
            },
            4: {
                1: [
                    ('CS 401', 'CS Thesis Writing 2', 3, 0),
                    ('CS-E4', 'CS Elective 4', 3, 0),
                    ('CS-E5', 'CS Elective 5', 3, 0),
                    ('FREE-E3', 'Free Elective 3', 3, 0),
                    ('FREE-E4', 'Free Elective 4', 3, 0),
                ],
                2: [
                    ('CS 402', 'Practicum / OJT', 6, 0),
                ],
            },
        },
    },
    {
        'code': 'BSIT',
        'name': 'Information Technology',
        'full_name': 'Bachelor of Science in Information Technology',
        'year_levels': 4,
        'curriculum_code': 'BSIT-2024',
        'degree': 'Bachelor of Science in Information Technology',
        'subjects': {
            1: {
                1: [
                    ('IT 101', 'Introduction to Computing', 3, 0),
                    ('IT 102', 'Computer Programming 1', 2, 1),
                    ('GE 1', 'Understanding the Self', 3, 0),
                    ('GE 2', 'Readings in Philippine History', 3, 0),
                    ('GE 3', 'The Contemporary World', 3, 0),
                    ('MATH 101', 'Department Algebra', 3, 0),
                    ('PE 1', 'Physical Education 1', 2, 0),
                    ('NSTP 1', 'NSTP - CWTS 1', 3, 0),
                ],
                2: [
                    ('IT 103', 'Computer Programming 2', 2, 1),
                    ('IT 104', 'Discrete Mathematics', 3, 0),
                    ('GE 4', 'Mathematics in the Modern World', 3, 0),
                    ('GE 5', 'Purposive Communication', 3, 0),
                    ('GE 6', 'Art Appreciation', 3, 0),
                    ('MATH 102', 'Plane Trigonometry', 3, 0),
                    ('PE 2', 'Physical Education 2', 2, 0),
                    ('NSTP 2', 'NSTP - CWTS 2', 3, 0),
                ],
            },
            2: {
                1: [
                    ('IT 201', 'Data Structures and Algorithms', 2, 1),
                    ('IT 202', 'Object-Oriented Programming', 2, 1),
                    ('IT 203', 'Platform Technologies', 2, 1),
                    ('IT 204', 'Information Management', 2, 1),
                    ('GE 7', 'Science, Technology, and Society', 3, 0),
                    ('GE 8', 'Ethics', 3, 0),
                    ('PE 3', 'Physical Education 3', 2, 0),
                ],
                2: [
                    ('IT 205', 'Networking 1', 2, 1),
                    ('IT 206', 'Web Systems and Technologies', 2, 1),
                    ('IT 207', 'Quantitative Methods', 3, 0),
                    ('IT 208', 'Advanced Database Systems', 2, 1),
                    ('GE 9', 'The Life and Works of Rizal', 3, 0),
                    ('MATH 202', 'Probability and Statistics', 3, 0),
                    ('PE 4', 'Physical Education 4', 2, 0),
                ],
            },
            3: {
                1: [
                    ('IT 301', 'Networking 2', 2, 1),
                    ('IT 302', 'Systems Integration and Architecture', 2, 1),
                    ('IT 303', 'Information Assurance and Security', 3, 0),
                    ('IT 304', 'Applications Development', 2, 1),
                    ('IT-E1', 'IT Elective 1', 3, 0),
                    ('IT-E2', 'IT Elective 2', 3, 0),
                    ('FREE-E1', 'Free Elective 1', 3, 0),
                ],
                2: [
                    ('IT 305', 'System Administration and Maintenance', 2, 1),
                    ('IT 306', 'Social and Professional Issues in IT', 3, 0),
                    ('IT 307', 'Capstone Project 1', 3, 0),
                    ('IT-E3', 'IT Elective 3', 3, 0),
                    ('IT-E4', 'IT Elective 4', 3, 0),
                    ('FREE-E2', 'Free Elective 2', 3, 0),
                ],
            },
            4: {
                1: [
                    ('IT 401', 'Capstone Project 2', 3, 0),
                    ('IT-E5', 'IT Elective 5', 3, 0),
                    ('IT-E6', 'IT Elective 6', 3, 0),
                    ('FREE-E3', 'Free Elective 3', 3, 0),
                    ('FREE-E4', 'Free Elective 4', 3, 0),
                ],
                2: [
                    ('IT 402', 'Practicum / OJT', 6, 0),
                ],
            },
        },
    },
    {
        'code': 'BSBA',
        'name': 'Business Administration',
        'full_name': 'Bachelor of Science in Business Administration',
        'year_levels': 4,
        'curriculum_code': 'BSBA-2024',
        'degree': 'Bachelor of Science in Business Administration',
        'subjects': {
            1: {
                1: [
                    ('BA 101', 'Introduction to Business', 3, 0),
                    ('BA 102', 'Principles of Management', 3, 0),
                    ('GE 1', 'Understanding the Self', 3, 0),
                    ('GE 2', 'Readings in Philippine History', 3, 0),
                    ('GE 3', 'The Contemporary World', 3, 0),
                    ('MATH 101', 'Department Algebra', 3, 0),
                    ('PE 1', 'Physical Education 1', 2, 0),
                    ('NSTP 1', 'NSTP - CWTS 1', 3, 0),
                ],
                2: [
                    ('BA 103', 'Principles of Marketing', 3, 0),
                    ('BA 104', 'Microeconomics', 3, 0),
                    ('GE 4', 'Mathematics in the Modern World', 3, 0),
                    ('GE 5', 'Purposive Communication', 3, 0),
                    ('GE 6', 'Art Appreciation', 3, 0),
                    ('ACCT 101', 'Financial Accounting 1', 3, 0),
                    ('PE 2', 'Physical Education 2', 2, 0),
                    ('NSTP 2', 'NSTP - CWTS 2', 3, 0),
                ],
            },
            2: {
                1: [
                    ('BA 201', 'Human Resource Management', 3, 0),
                    ('BA 202', 'Macroeconomics', 3, 0),
                    ('BA 203', 'Business Law and Taxation', 3, 0),
                    ('ACCT 102', 'Financial Accounting 2', 3, 0),
                    ('GE 7', 'Science, Technology, and Society', 3, 0),
                    ('GE 8', 'Ethics', 3, 0),
                    ('PE 3', 'Physical Education 3', 2, 0),
                ],
                2: [
                    ('BA 204', 'Operations Management', 3, 0),
                    ('BA 205', 'Business Statistics', 3, 0),
                    ('BA 206', 'International Business', 3, 0),
                    ('ACCT 201', 'Managerial Accounting', 3, 0),
                    ('GE 9', 'The Life and Works of Rizal', 3, 0),
                    ('BA 207', 'Business Communication', 3, 0),
                    ('PE 4', 'Physical Education 4', 2, 0),
                ],
            },
            3: {
                1: [
                    ('BA 301', 'Financial Management 1', 3, 0),
                    ('BA 302', 'Strategic Management', 3, 0),
                    ('BA 303', 'Business Research Methods', 3, 0),
                    ('BA 304', 'Entrepreneurial Management', 3, 0),
                    ('BA-E1', 'BA Elective 1', 3, 0),
                    ('BA-E2', 'BA Elective 2', 3, 0),
                    ('FREE-E1', 'Free Elective 1', 3, 0),
                ],
                2: [
                    ('BA 305', 'Financial Management 2', 3, 0),
                    ('BA 306', 'Business Ethics and CSR', 3, 0),
                    ('BA 307', 'Thesis Writing 1', 3, 0),
                    ('BA-E3', 'BA Elective 3', 3, 0),
                    ('BA-E4', 'BA Elective 4', 3, 0),
                    ('FREE-E2', 'Free Elective 2', 3, 0),
                ],
            },
            4: {
                1: [
                    ('BA 401', 'Thesis Writing 2', 3, 0),
                    ('BA-E5', 'BA Elective 5', 3, 0),
                    ('BA-E6', 'BA Elective 6', 3, 0),
                    ('FREE-E3', 'Free Elective 3', 3, 0),
                    ('FREE-E4', 'Free Elective 4', 3, 0),
                ],
                2: [
                    ('BA 402', 'Practicum / OJT', 6, 0),
                ],
            },
        },
    },
    {
        'code': 'BEED',
        'name': 'Elementary Education',
        'full_name': 'Bachelor of Elementary Education',
        'year_levels': 4,
        'curriculum_code': 'BEED-2024',
        'degree': 'Bachelor of Elementary Education',
        'subjects': {
            1: {
                1: [
                    ('EDUC 101', 'The Teaching Profession', 3, 0),
                    ('EDUC 102', 'The Child and Adolescent Learner', 3, 0),
                    ('GE 1', 'Understanding the Self', 3, 0),
                    ('GE 2', 'Readings in Philippine History', 3, 0),
                    ('GE 3', 'The Contemporary World', 3, 0),
                    ('MATH 101', 'Department Algebra', 3, 0),
                    ('PE 1', 'Physical Education 1', 2, 0),
                    ('NSTP 1', 'NSTP - CWTS 1', 3, 0),
                ],
                2: [
                    ('EDUC 103', 'Facilitating Learner-Centered Teaching', 3, 0),
                    ('EDUC 104', 'Technology for Teaching and Learning 1', 2, 1),
                    ('GE 4', 'Mathematics in the Modern World', 3, 0),
                    ('GE 5', 'Purposive Communication', 3, 0),
                    ('GE 6', 'Art Appreciation', 3, 0),
                    ('FIL 101', 'Kontekstwalisadong Komunikasyon sa Filipino', 3, 0),
                    ('PE 2', 'Physical Education 2', 2, 0),
                    ('NSTP 2', 'NSTP - CWTS 2', 3, 0),
                ],
            },
            2: {
                1: [
                    ('EDUC 201', 'Assessment of Learning 1', 3, 0),
                    ('EDUC 202', 'The Teacher and the Community', 3, 0),
                    ('EDUC 203', 'Curriculum Development', 3, 0),
                    ('EDUC 204', 'Content and Pedagogy for Mother Tongue', 3, 0),
                    ('GE 7', 'Science, Technology, and Society', 3, 0),
                    ('GE 8', 'Ethics', 3, 0),
                    ('PE 3', 'Physical Education 3', 2, 0),
                ],
                2: [
                    ('EDUC 205', 'Assessment of Learning 2', 3, 0),
                    ('EDUC 206', 'Building and Enhancing Literacy', 3, 0),
                    ('EDUC 207', 'Technology for Teaching and Learning 2', 2, 1),
                    ('EDUC 208', 'Foundation of Special Education', 3, 0),
                    ('GE 9', 'The Life and Works of Rizal', 3, 0),
                    ('EDUC 209', 'Teaching Mathematics in Primary Grades', 3, 0),
                    ('PE 4', 'Physical Education 4', 2, 0),
                ],
            },
            3: {
                1: [
                    ('EDUC 301', 'Teaching Science in Elementary', 3, 0),
                    ('EDUC 302', 'Teaching Social Studies in Elementary', 3, 0),
                    ('EDUC 303', 'Teaching Filipino in Elementary', 3, 0),
                    ('EDUC 304', 'Teaching English in Elementary', 3, 0),
                    ('EDUC-E1', 'Education Elective 1', 3, 0),
                    ('EDUC-E2', 'Education Elective 2', 3, 0),
                    ('FREE-E1', 'Free Elective 1', 3, 0),
                ],
                2: [
                    ('EDUC 305', 'Teaching Math in Intermediate Grades', 3, 0),
                    ('EDUC 306', 'Field Study 1', 2, 1),
                    ('EDUC 307', 'Field Study 2', 2, 1),
                    ('EDUC 308', 'Research in Education 1', 3, 0),
                    ('EDUC-E3', 'Education Elective 3', 3, 0),
                    ('FREE-E2', 'Free Elective 2', 3, 0),
                ],
            },
            4: {
                1: [
                    ('EDUC 401', 'Research in Education 2', 3, 0),
                    ('EDUC 402', 'Practice Teaching 1', 6, 0),
                ],
                2: [
                    ('EDUC 403', 'Practice Teaching 2', 6, 0),
                ],
            },
        },
    },
]


# =========================================================================
# BUILDING AND ROOM TEMPLATES
# =========================================================================

BUILDING_TEMPLATES = [
    {
        'name': 'Academic Building',
        'rooms': [
            ('AB-101', 'Lecture'), ('AB-102', 'Lecture'), ('AB-103', 'Lecture'),
            ('AB-104', 'Lecture'), ('AB-201', 'Lecture'), ('AB-202', 'Lecture'),
            ('AB-203', 'Lecture'), ('AB-204', 'Lecture'), ('AB-301', 'Lecture'),
            ('AB-302', 'Lecture'),
        ],
    },
    {
        'name': 'Science and Technology Building',
        'rooms': [
            ('STB-101', 'Lecture'), ('STB-102', 'Laboratory'), ('STB-103', 'Laboratory'),
            ('STB-201', 'Lecture'), ('STB-202', 'Laboratory'), ('STB-203', 'Laboratory'),
            ('STB-301', 'Lecture'), ('STB-302', 'Laboratory'),
        ],
    },
    {
        'name': 'Engineering Building',
        'rooms': [
            ('EB-101', 'Lecture'), ('EB-102', 'Lecture'), ('EB-103', 'Laboratory'),
            ('EB-201', 'Lecture'), ('EB-202', 'Laboratory'), ('EB-203', 'Laboratory'),
        ],
    },
    {
        'name': 'Business and Arts Building',
        'rooms': [
            ('BAB-101', 'Lecture'), ('BAB-102', 'Lecture'), ('BAB-103', 'Lecture'),
            ('BAB-201', 'Lecture'), ('BAB-202', 'Lecture'), ('BAB-203', 'Lecture'),
            ('BAB-301', 'Lecture'), ('BAB-302', 'Lecture'),
        ],
    },
]


# =========================================================================
# SCHEDULE TIME SLOTS
# =========================================================================

DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']  # Default; overridden at runtime by get_operation_days()

def get_operation_days():
    """Get operation days from settings, falling back to default."""
    try:
        from app.models.settings import AcademicSettings
        return AcademicSettings.get_active_operation_days()
    except Exception:
        return DAYS_OF_WEEK

# Standard time slot templates (start_hour, start_min, end_hour, end_min)
# Lecture: minimum 3 hours
TIME_SLOTS_LECTURE = [
    (7, 0, 10, 0), (10, 0, 13, 0), (13, 0, 16, 0), (16, 0, 19, 0),
    (7, 30, 10, 30), (10, 30, 13, 30), (13, 30, 16, 30),
    (8, 0, 11, 0), (11, 0, 14, 0), (14, 0, 17, 0),
]

# Lab: minimum 2 hours
TIME_SLOTS_LAB = [
    (7, 0, 9, 0), (9, 0, 11, 0), (11, 0, 13, 0),
    (13, 0, 15, 0), (15, 0, 17, 0), (17, 0, 19, 0),
    (7, 30, 9, 30), (9, 30, 11, 30), (13, 30, 15, 30), (15, 30, 17, 30),
]


class DataGenerator:
    """
    Generates realistic sample data for the iSchedWise scheduling system.
    Designed for Philippine HEI context with Filipino names and programs.
    """

    # Marker prefix for generated data — used for cleanup identification
    GENERATED_MARKER = '[Generated]'

    def __init__(self):
        self.results = {
            'programs': 0, 'curricula': 0, 'year_levels': 0,
            'semesters': 0, 'subjects': 0, 'sections': 0,
            'faculty': 0, 'buildings': 0, 'rooms': 0,
            'faculty_assignments': 0, 'schedules': 0, 'exam_schedules': 0,
            'conflict_schedules': 0, 'conflict_exams': 0,
        }
        self.errors = []
        self._generated_departments = []
        self._generated_faculty = []
        self._generated_sections = []
        self._generated_rooms_by_type = {'Lecture': [], 'Laboratory': []}
        self._generated_subjects_by_dept = {}
        self._used_names = set()

    # =====================================================================
    # STATUS / SAFETY CHECK
    # =====================================================================

    @staticmethod
    def get_entity_counts():
        """Return counts of existing data per entity type for safety checks."""
        return {
            'programs': Program.query.filter_by(is_archived=False).count(),
            'curricula': Curriculum.query.filter_by(is_archived=False).count(),
            'faculty': Faculty.query.filter_by(is_archived=False).count(),
            'sections': Section.query.count(),
            'buildings': Building.query.filter_by(is_archived=False).count(),
            'rooms': Room.query.count(),
            'schedules': Schedule.query.filter_by(is_active=True).count(),
            'exam_schedules': ExamSchedule.query.filter_by(is_active=True).count(),
            'subjects': Subject.query.count(),
        }

    @staticmethod
    def has_existing_data(entity_type):
        """Check if an entity type has existing data."""
        counts = DataGenerator.get_entity_counts()
        return counts.get(entity_type, 0) > 0

    # =====================================================================
    # FULL GENERATION PIPELINE
    # =====================================================================

    def generate_all(self, config):
        """
        Main entry point. Generate all requested entities based on config.

        Args:
            config: dict with keys like:
                {
                    'programs': {'enabled': True, 'count': 4},
                    'faculty': {'enabled': True, 'per_department': 12},
                    'sections': {'enabled': True, 'per_year': 2},
                    'buildings': {'enabled': True, 'count': 3},
                    'schedules': {'enabled': True},
                    'exams': {'enabled': True, 'per_section': 5},
                }
        Returns:
            dict with 'success', 'results', 'errors'
        """
        try:
            # Phase 1: Foundation entities
            if config.get('programs', {}).get('enabled'):
                dept_count = config['programs'].get('count', 4)
                self._generate_departments(dept_count)

            # Phase 2: Dependent entities
            if config.get('faculty', {}).get('enabled'):
                per_dept = config['faculty'].get('per_department', 12)
                self._generate_faculty(per_dept)

            if config.get('sections', {}).get('enabled'):
                per_year = config['sections'].get('per_year', 2)
                self._generate_sections(per_year)

            if config.get('buildings', {}).get('enabled'):
                bldg_count = config['buildings'].get('count', 3)
                self._generate_buildings(bldg_count)

            # Phase 3: Schedules (depend on sections, faculty, rooms, subjects)
            if config.get('schedules', {}).get('enabled'):
                self._generate_schedules()

            if config.get('exams', {}).get('enabled'):
                per_section = config['exams'].get('per_section', 5)
                self._generate_exam_schedules(per_section)

            # Phase 4: Conflict test data (intentionally conflicting schedules)
            if config.get('conflict_schedules', {}).get('enabled'):
                count = config['conflict_schedules'].get('count', 6)
                self._generate_conflict_schedules(count)

            if config.get('conflict_exams', {}).get('enabled'):
                count = config['conflict_exams'].get('count', 4)
                self._generate_conflict_exams(count)

            db.session.commit()

            return {
                'success': True,
                'results': self.results,
                'errors': self.errors,
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'results': self.results,
                'errors': self.errors + [str(e)],
            }

    # =====================================================================
    # DEPARTMENT + CURRICULUM + SUBJECTS GENERATION
    # =====================================================================

    def _generate_departments(self, count):
        """Generate programs with full curriculum trees (year levels, semesters, subjects)."""
        templates = DEPARTMENT_TEMPLATES[:count]

        for tmpl in templates:
            try:
                # Check for duplicate program code
                existing = Program.query.filter_by(program_code=tmpl['code']).first()
                if existing:
                    self.errors.append(f"Program {tmpl['code']} already exists, skipping")
                    # Still track it for downstream generation
                    self._generated_departments.append(existing)
                    continue

                dept = Program(
                    program_code=tmpl['code'],
                    program_name=tmpl['name'],
                    year_levels=tmpl['year_levels'],
                    is_active=True,
                    is_archived=False,
                )
                db.session.add(dept)
                db.session.flush()  # Get dept.id
                self.results['programs'] += 1
                self._generated_departments.append(dept)

                # Create curriculum
                curr = Curriculum(
                    curriculum_code=tmpl['curriculum_code'],
                    curriculum_name=f"{tmpl['degree']} Curriculum",
                    program_id=dept.id,
                    degree_program=tmpl['degree'],
                    is_active=True,
                    is_archived=False,
                )
                db.session.add(curr)
                db.session.flush()
                self.results['curricula'] += 1

                # Create year levels, semesters, subjects
                dept_subjects = []
                for yr_num in range(1, tmpl['year_levels'] + 1):
                    yl = YearLevel(
                        curriculum_id=curr.id,
                        year_number=yr_num,
                        year_name=f"{self._ordinal(yr_num)} Year",
                    )
                    db.session.add(yl)
                    db.session.flush()
                    self.results['year_levels'] += 1

                    yr_subjects = tmpl['subjects'].get(yr_num, {})
                    for sem_num in (1, 2):
                        sem = Semester(
                            year_level_id=yl.id,
                            semester_number=sem_num,
                            semester_name=f"{self._ordinal(sem_num)} Semester",
                        )
                        db.session.add(sem)
                        db.session.flush()
                        self.results['semesters'] += 1

                        sem_subjects = yr_subjects.get(sem_num, [])
                        for code, desc, lec, lab in sem_subjects:
                            # Make subject code unique per program
                            unique_code = f"{code}"
                            subj = Subject(
                                semester_id=sem.id,
                                subject_code=unique_code,
                                course_description=desc,
                                lec_units=lec,
                                lab_units=lab,
                            )
                            db.session.add(subj)
                            db.session.flush()
                            self.results['subjects'] += 1
                            dept_subjects.append(subj)

                self._generated_subjects_by_dept[dept.id] = dept_subjects

            except Exception as e:
                self.errors.append(f"Error creating program {tmpl['code']}: {str(e)}")

    # =====================================================================
    # FACULTY GENERATION
    # =====================================================================

    def _generate_faculty(self, per_department):
        """Generate realistic Filipino faculty members per program."""
        programs = self._generated_departments or Program.query.filter_by(
            is_archived=False).all()

        for dept in programs:
            for i in range(per_department):
                try:
                    gender = random.choice(['Male', 'Female'])
                    first_name, last_name, middle_initial = self._generate_unique_name_parts(gender)
                    max_units = random.choice([18, 21, 24, 24, 24, 27])

                    fac = Faculty(
                        last_name=last_name,
                        first_name=first_name,
                        middle_initial=middle_initial,
                        gender=gender,
                        department_id=dept.department_id,
                        max_units=max_units,
                        is_active=True,
                        is_archived=False,
                    )
                    db.session.add(fac)
                    db.session.flush()
                    self.results['faculty'] += 1
                    self._generated_faculty.append(fac)

                except Exception as e:
                    self.errors.append(f"Error creating faculty for {dept.program_code}: {str(e)}")

    def _generate_unique_name_parts(self, gender):
        """Generate unique Filipino name parts (first_name, last_name, middle_initial)."""
        pool = FILIPINO_FIRST_NAMES_MALE if gender == 'Male' else FILIPINO_FIRST_NAMES_FEMALE
        for _ in range(100):
            first = random.choice(pool)
            last = random.choice(FILIPINO_LAST_NAMES)
            full = f"{last}, {first}"
            if full not in self._used_names:
                self._used_names.add(full)
                return (first, last, None)
        # Fallback with middle initial
        first = random.choice(pool)
        middle = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + '.'
        last = random.choice(FILIPINO_LAST_NAMES)
        full = f"{last}, {first} {middle}"
        self._used_names.add(full)
        return (first, last, middle)

    def _generate_unique_name(self, gender):
        """Generate a unique Filipino full name (backward compatibility)."""
        first, last, mi = self._generate_unique_name_parts(gender)
        if mi:
            return f"{last}, {first} {mi}"
        return f"{last}, {first}"

    # =====================================================================
    # SECTIONS GENERATION
    # =====================================================================

    def _generate_sections(self, per_year):
        """Generate sections (e.g., BSCS-1A, BSCS-1B) per program per year level."""
        programs = self._generated_departments or Program.query.filter_by(
            is_archived=False).all()

        section_letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        for dept in programs:
            yr_levels = dept.year_levels or 4
            for yr in range(1, yr_levels + 1):
                for s in range(per_year):
                    try:
                        letter = section_letters[s] if s < len(section_letters) else str(s + 1)
                        section = Section(
                            program_id=dept.id,
                            section_name=letter,
                            year_level=yr,
                        )
                        db.session.add(section)
                        db.session.flush()
                        self.results['sections'] += 1
                        self._generated_sections.append(section)

                    except Exception as e:
                        self.errors.append(
                            f"Error creating section for {dept.program_code} Y{yr}: {str(e)}")

    # =====================================================================
    # BUILDINGS + ROOMS GENERATION
    # =====================================================================

    def _generate_buildings(self, count):
        """Generate buildings with rooms."""
        templates = BUILDING_TEMPLATES[:count]

        for tmpl in templates:
            try:
                existing = Building.query.filter_by(building_name=tmpl['name']).first()
                if existing:
                    self.errors.append(f"Building '{tmpl['name']}' already exists, skipping")
                    # Still track rooms for downstream
                    for room in existing.rooms:
                        rtype = room.room_type or 'Lecture'
                        self._generated_rooms_by_type.setdefault(rtype, []).append(room)
                    continue

                bldg = Building(
                    building_name=tmpl['name'],
                    is_active=True,
                    is_archived=False,
                )
                db.session.add(bldg)
                db.session.flush()
                self.results['buildings'] += 1

                for room_num, room_type in tmpl['rooms']:
                    room = Room(
                        building_id=bldg.id,
                        room_number=room_num,
                        room_type=room_type,
                        is_available=True,
                    )
                    db.session.add(room)
                    db.session.flush()
                    self.results['rooms'] += 1
                    self._generated_rooms_by_type.setdefault(room_type, []).append(room)

            except Exception as e:
                self.errors.append(f"Error creating building '{tmpl['name']}': {str(e)}")

    # =====================================================================
    # SCHEDULE GENERATION
    # =====================================================================

    def _generate_schedules(self):
        """
        Generate class schedules for each section based on their year level
        and the matching curriculum's subjects for the active semester.
        Also creates faculty subject assignments.
        """
        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            self.errors.append("No active academic settings found — cannot generate schedules")
            return

        academic_year = settings.academic_year
        semester = settings.semester

        # Determine semester number from name
        if '1st' in semester.lower():
            sem_num = 1
        elif '2nd' in semester.lower():
            sem_num = 2
        else:
            sem_num = 1

        sections = self._generated_sections or Section.query.all()
        all_lecture_rooms = self._generated_rooms_by_type.get('Lecture', [])
        all_lab_rooms = self._generated_rooms_by_type.get('Laboratory', [])

        if not all_lecture_rooms:
            all_lecture_rooms = Room.query.filter_by(room_type='Lecture', is_available=True).all()
        if not all_lab_rooms:
            all_lab_rooms = Room.query.filter_by(room_type='Laboratory', is_available=True).all()

        if not all_lecture_rooms:
            self.errors.append("No lecture rooms available for scheduling")
            return

        # Build a faculty pool per program
        faculty_by_dept = {}
        all_faculty = self._generated_faculty or Faculty.query.filter_by(
            is_archived=False, is_active=True).all()
        for f in all_faculty:
            faculty_by_dept.setdefault(f.department_id, []).append(f)

        # Track occupied slots: (entity_id, day) -> [(start_minutes, end_minutes), ...]
        room_slots = {}
        faculty_slots = {}
        section_slots = {}

        # Track faculty unit loads for this generation
        faculty_load = {}

        assigned_pairs = set()  # Track (faculty_id, subject_id) for assignments

        for section in sections:
            dept = section.program
            if not dept:
                continue

            # Find curriculum for this program
            curriculum = Curriculum.query.filter_by(
                program_id=dept.id, is_archived=False, is_active=True
            ).first()
            if not curriculum:
                continue

            # Find year level
            year_level = YearLevel.query.filter_by(
                curriculum_id=curriculum.id,
                year_number=section.year_level,
            ).first()
            if not year_level:
                continue

            # Find the matching semester
            sem = Semester.query.filter_by(
                year_level_id=year_level.id,
                semester_number=sem_num,
            ).first()
            if not sem:
                continue

            # Get subjects for this semester
            subjects = Subject.query.filter_by(semester_id=sem.id).all()
            dept_faculty = faculty_by_dept.get(dept.department_id, [])

            if not dept_faculty:
                self.errors.append(f"No faculty for dept {dept.program_code}, skipping schedules")
                continue

            for subj in subjects:
                try:
                    has_lec = float(subj.lec_units or 0) > 0
                    has_lab = float(subj.lab_units or 0) > 0

                    # Build list of slots to schedule for this subject
                    slots_to_schedule = []
                    if has_lec:
                        slots_to_schedule.append(('lecture', TIME_SLOTS_LECTURE, all_lecture_rooms))
                    if has_lab:
                        slots_to_schedule.append(('lab', TIME_SLOTS_LAB, all_lab_rooms))
                    if not slots_to_schedule:
                        # Fallback: treat as lecture
                        slots_to_schedule.append(('lecture', TIME_SLOTS_LECTURE, all_lecture_rooms))

                    # Pick a faculty member (round-robin by load) — same faculty for all slots
                    faculty = self._pick_faculty(dept_faculty, faculty_load, subj)
                    if not faculty:
                        continue

                    all_slots_placed = True
                    for schedule_type, time_slots, available_rooms in slots_to_schedule:
                        if not available_rooms:
                            all_slots_placed = False
                            continue

                        # Find an available slot
                        slot = self._find_available_slot(
                            section.id, faculty.id, available_rooms, time_slots,
                            room_slots, faculty_slots, section_slots,
                        )
                        if not slot:
                            self.errors.append(
                                f"No {schedule_type} slot for {subj.subject_code} in {dept.program_code}-{section.year_level}{section.section_name}")
                            all_slots_placed = False
                            continue

                        day, start_t, end_t, room = slot

                        sched = Schedule(
                            section_id=section.id,
                            subject_id=subj.id,
                            faculty_id=faculty.id,
                            room_id=room.id,
                            day_of_week=day,
                            start_time=start_t,
                            end_time=end_t,
                            semester=semester,
                            academic_year=academic_year,
                            schedule_type=schedule_type,
                            is_active=True,
                            version=1,
                        )
                        db.session.add(sched)
                        self.results['schedules'] += 1

                        # Mark slots as occupied
                        self._occupy_slot(room.id, faculty.id, section.id,
                                          day, start_t, end_t,
                                          room_slots, faculty_slots, section_slots)

                    # Track loads (once per subject regardless of slot count)
                    total_units = float(subj.lec_units or 0) + float(subj.lab_units or 0)
                    faculty_load[faculty.id] = faculty_load.get(faculty.id, 0) + total_units

                    # Faculty subject assignment
                    pair_key = (faculty.id, subj.id)
                    if pair_key not in assigned_pairs:
                        assigned_pairs.add(pair_key)
                        existing_assign = FacultySubjectAssignment.query.filter_by(
                            faculty_id=faculty.id,
                            subject_id=subj.id,
                            academic_year=academic_year,
                            semester=semester,
                        ).first()
                        if not existing_assign:
                            assign = FacultySubjectAssignment(
                                faculty_id=faculty.id,
                                subject_id=subj.id,
                                academic_year=academic_year,
                                semester=semester,
                                is_active=True,
                                is_archived=False,
                            )
                            db.session.add(assign)
                            self.results['faculty_assignments'] += 1

                except Exception as e:
                    self.errors.append(f"Error scheduling {subj.subject_code}: {str(e)}")

    def _pick_faculty(self, dept_faculty, faculty_load, subject):
        """Pick a faculty member with the lowest current load that can take more units."""
        total_units = float(subject.lec_units) + float(subject.lab_units)
        candidates = []
        for f in dept_faculty:
            current = faculty_load.get(f.id, 0)
            max_u = f.max_units or 24
            if current + total_units <= max_u:
                candidates.append((current, f))

        if not candidates:
            # Allow overload if no one has capacity
            candidates = [(faculty_load.get(f.id, 0), f) for f in dept_faculty]

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1] if candidates else None

    @staticmethod
    def _to_minutes(t):
        """Convert a time object to minutes since midnight."""
        return t.hour * 60 + t.minute

    def _has_overlap(self, entity_id, day, start_min, end_min, slot_dict):
        """Check if an entity has any overlapping interval on a given day."""
        intervals = slot_dict.get((entity_id, day), [])
        for occ_start, occ_end in intervals:
            if start_min < occ_end and end_min > occ_start:
                return True
        return False

    def _find_available_slot(self, section_id, faculty_id, rooms, time_slots,
                             room_slots, faculty_slots, section_slots):
        """Find an available day/time/room combination with real overlap checking."""
        days = list(get_operation_days())
        random.shuffle(days)
        shuffled_slots = list(time_slots)
        random.shuffle(shuffled_slots)
        shuffled_rooms = list(rooms)
        random.shuffle(shuffled_rooms)

        for day in days:
            for (sh, sm, eh, em) in shuffled_slots:
                start_t = time(sh, sm)
                end_t = time(eh, em)
                start_min = self._to_minutes(start_t)
                end_min = self._to_minutes(end_t)

                # Check section availability (no overlap)
                if self._has_overlap(section_id, day, start_min, end_min, section_slots):
                    continue

                # Check faculty availability (no overlap)
                if self._has_overlap(faculty_id, day, start_min, end_min, faculty_slots):
                    continue

                # Check room availability (no overlap)
                for room in shuffled_rooms:
                    if not self._has_overlap(room.id, day, start_min, end_min, room_slots):
                        return (day, start_t, end_t, room)

        return None

    def _occupy_slot(self, room_id, faculty_id, section_id,
                     day, start_t, end_t,
                     room_slots, faculty_slots, section_slots):
        """Mark a time slot as occupied for room, faculty, and section."""
        start_min = self._to_minutes(start_t)
        end_min = self._to_minutes(end_t)
        room_slots.setdefault((room_id, day), []).append((start_min, end_min))
        faculty_slots.setdefault((faculty_id, day), []).append((start_min, end_min))
        section_slots.setdefault((section_id, day), []).append((start_min, end_min))

    # =====================================================================
    # EXAM SCHEDULE GENERATION
    # =====================================================================

    def _generate_exam_schedules(self, per_section):
        """Generate exam schedules for sections using their scheduled subjects."""
        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            self.errors.append("No active academic settings — cannot generate exams")
            return

        academic_year = settings.academic_year
        semester = settings.semester
        exam_period = settings.exam_period or 'Midterm'

        # Calculate exam dates: use exam_period_start/end or generate 5 weekdays starting next Monday
        if settings.exam_period_start and settings.exam_period_end:
            exam_dates = self._get_weekdays_between(settings.exam_period_start, settings.exam_period_end)
        else:
            # Generate 5 weekdays starting from tomorrow
            today = date.today()
            exam_dates = self._generate_weekdays(today + timedelta(days=1), 10)

        if not exam_dates:
            self.errors.append("Could not determine exam dates")
            return

        sections = self._generated_sections or Section.query.all()
        all_rooms = Room.query.filter(Room.is_available == True).all()
        if not all_rooms:
            self.errors.append("No available rooms for exams")
            return

        # Exam time slots (2-hour blocks)
        exam_time_slots = [
            (7, 0, 9, 0), (9, 0, 11, 0), (11, 0, 13, 0),
            (13, 0, 15, 0), (15, 0, 17, 0),
        ]

        # Track occupied: (room_id, date, start_time) -> True
        exam_room_slots = {}
        exam_faculty_slots = {}
        exam_section_slots = {}

        for section in sections:
            # Get active schedules for this section to find subjects + faculty
            schedules = Schedule.query.filter_by(
                section_id=section.id,
                academic_year=academic_year,
                semester=semester,
                is_active=True,
            ).all()

            subjects_faculty = []
            seen = set()
            for s in schedules:
                key = (s.subject_id, s.faculty_id)
                if key not in seen and s.subject_id and s.faculty_id:
                    seen.add(key)
                    subjects_faculty.append((s.subject_id, s.faculty_id, s.schedule_type))

            # Limit to per_section exams
            selected = subjects_faculty[:per_section]

            for subj_id, fac_id, sched_type in selected:
                try:
                    slot = self._find_exam_slot(
                        section.id, fac_id, all_rooms, exam_dates, exam_time_slots,
                        exam_room_slots, exam_faculty_slots, exam_section_slots,
                    )
                    if not slot:
                        continue

                    exam_date, start_t, end_t, room = slot

                    exam = ExamSchedule(
                        section_id=section.id,
                        subject_id=subj_id,
                        faculty_id=fac_id,
                        room_id=room.id,
                        exam_date=exam_date,
                        start_time=start_t,
                        end_time=end_t,
                        semester=semester,
                        academic_year=academic_year,
                        exam_period=exam_period,
                        schedule_type=sched_type,
                        is_active=True,
                        version=1,
                    )
                    db.session.add(exam)
                    self.results['exam_schedules'] += 1

                    # Occupy slot
                    key = (exam_date.isoformat(), start_t.isoformat())
                    exam_room_slots[(room.id,) + key] = True
                    exam_faculty_slots[(fac_id,) + key] = True
                    exam_section_slots[(section.id,) + key] = True

                except Exception as e:
                    self.errors.append(f"Error creating exam for subject {subj_id}: {str(e)}")

    def _find_exam_slot(self, section_id, faculty_id, rooms, dates, time_slots,
                        room_slots, faculty_slots, section_slots):
        """Find an available exam date/time/room combination."""
        random.shuffle(dates)
        shuffled_slots = list(time_slots)
        random.shuffle(shuffled_slots)
        shuffled_rooms = list(rooms)
        random.shuffle(shuffled_rooms)

        for d in dates:
            for (sh, sm, eh, em) in shuffled_slots:
                start_t = time(sh, sm)
                end_t = time(eh, em)
                key = (d.isoformat(), start_t.isoformat())

                if (section_id,) + key in section_slots:
                    continue
                if (faculty_id,) + key in faculty_slots:
                    continue

                for room in shuffled_rooms:
                    if (room.id,) + key not in room_slots:
                        return (d, start_t, end_t, room)

        return None

    @staticmethod
    def _get_weekdays_between(start_date, end_date):
        """Get list of weekdays between two dates."""
        days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 6:  # Mon-Sat
                days.append(current)
            current += timedelta(days=1)
        return days

    @staticmethod
    def _generate_weekdays(start_date, count):
        """Generate a list of weekday dates starting from start_date."""
        days = []
        current = start_date
        while len(days) < count:
            if current.weekday() < 6:  # Mon-Sat
                days.append(current)
            current += timedelta(days=1)
        return days

    # =====================================================================
    # CONFLICT TEST DATA — Intentionally creates conflicting schedules
    # =====================================================================

    def _generate_conflict_schedules(self, count):
        """
        Generate class schedules with deliberate conflicts for testing the
        conflict detection and resolution system.

        Creates pairs of schedules that share the same room, faculty, or
        section at overlapping times so every generated record has at least
        one detectable conflict.

        Uses :15/:45 minute offsets that never appear in the clean schedule
        generator's TIME_SLOTS, guaranteeing no uk_section_slot collisions
        with Phase 3 data.
        """
        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            self.errors.append("No active academic settings — cannot generate conflict schedules")
            return

        academic_year = settings.academic_year
        semester = settings.semester

        # Gather existing entities to build conflicts from
        sections = Section.query.limit(10).all()
        faculty_list = Faculty.query.filter_by(is_archived=False, is_active=True).limit(10).all()
        lecture_rooms = Room.query.filter_by(room_type='Lecture', is_available=True).limit(6).all()

        if len(sections) < 3 or len(faculty_list) < 3 or len(lecture_rooms) < 2:
            self.errors.append("Not enough sections/faculty/rooms to generate conflict schedules. Need at least 3 sections, 3 faculty, 2 rooms.")
            return

        all_subjects = Subject.query.limit(20).all()
        if len(all_subjects) < 3:
            self.errors.append("Not enough subjects found — generate programs first")
            return

        # Build a set of already-occupied unique keys so we can verify before insert
        existing_slots = set()
        existing_scheds = Schedule.query.filter_by(
            academic_year=academic_year, semester=semester, is_active=True
        ).with_entities(
            Schedule.section_id, Schedule.day_of_week,
            Schedule.start_time, Schedule.end_time
        ).all()
        for s in existing_scheds:
            existing_slots.add((s.section_id, s.day_of_week, str(s.start_time), str(s.end_time)))

        # Conflict scenario definitions — uses :15 times that never appear in clean generation
        # Each scenario uses a UNIQUE day to avoid cross-scenario section collisions.
        conflict_scenarios = [
            {
                'name': 'Room double-book',
                'desc': 'Two different sections in the same room at the same time',
                'day': 'Monday',
                'slots': [
                    # (section_key, start, end) — section_key: 'a' or 'b'
                    ('a', time(7, 15), time(10, 15)),
                    ('b', time(7, 15), time(10, 15)),
                ],
                'shared': 'room',
            },
            {
                'name': 'Faculty double-book',
                'desc': 'Same faculty assigned to two sections at the same time',
                'day': 'Tuesday',
                'slots': [
                    ('a', time(7, 15), time(10, 15)),
                    ('b', time(7, 15), time(10, 15)),
                ],
                'shared': 'faculty',
            },
            {
                'name': 'Section time overlap',
                'desc': 'Same section has two subjects at overlapping (but different) times',
                'day': 'Wednesday',
                'slots': [
                    ('a', time(7, 15), time(10, 15)),
                    ('a', time(8, 45), time(11, 45)),  # overlaps but different unique key
                ],
                'shared': 'section',
            },
            {
                'name': 'Room + Faculty clash',
                'desc': 'Same room AND faculty assigned to two sections',
                'day': 'Thursday',
                'slots': [
                    ('a', time(7, 15), time(10, 15)),
                    ('b', time(7, 15), time(10, 15)),
                ],
                'shared': 'room_and_faculty',
            },
            {
                'name': 'Partial time overlap (room)',
                'desc': 'Two sections in same room with partial time overlap',
                'day': 'Friday',
                'slots': [
                    ('a', time(7, 15), time(10, 15)),
                    ('b', time(8, 45), time(11, 45)),  # partial overlap
                ],
                'shared': 'room_partial',
            },
            {
                'name': 'Triple conflict',
                'desc': 'Three schedules sharing the same room at the same time',
                'day': 'Saturday',
                'slots': [
                    ('a', time(7, 15), time(10, 15)),
                    ('b', time(7, 15), time(10, 15)),
                    ('c', time(7, 15), time(10, 15)),
                ],
                'shared': 'room_triple',
            },
        ]

        used_scenarios = conflict_scenarios[:count]

        for i, scenario in enumerate(used_scenarios):
            try:
                shared = scenario['shared']
                day = scenario['day']

                # Pick distinct sections, faculty, rooms, subjects for this scenario
                sec_a = sections[(i * 3) % len(sections)]
                sec_b = sections[(i * 3 + 1) % len(sections)]
                sec_c = sections[(i * 3 + 2) % len(sections)]
                # Ensure sec_b != sec_a
                if sec_b.id == sec_a.id:
                    sec_b = sections[(i * 3 + 2) % len(sections)]
                if sec_c.id == sec_a.id or sec_c.id == sec_b.id:
                    for s in sections:
                        if s.id != sec_a.id and s.id != sec_b.id:
                            sec_c = s
                            break

                fac_a = faculty_list[(i * 2) % len(faculty_list)]
                fac_b = faculty_list[(i * 2 + 1) % len(faculty_list)]
                room = lecture_rooms[i % len(lecture_rooms)]
                room_b = lecture_rooms[(i + 1) % len(lecture_rooms)]
                subj_a = all_subjects[(i * 3) % len(all_subjects)]
                subj_b = all_subjects[(i * 3 + 1) % len(all_subjects)]
                subj_c = all_subjects[(i * 3 + 2) % len(all_subjects)]

                sec_map = {'a': sec_a, 'b': sec_b, 'c': sec_c}
                fac_map_by_shared = {
                    'room':             [fac_a, fac_b],
                    'faculty':          [fac_a, fac_a],        # same faculty
                    'section':          [fac_a, fac_b],
                    'room_and_faculty': [fac_a, fac_a],        # same faculty + room
                    'room_partial':     [fac_a, fac_b],
                    'room_triple':      [fac_a, fac_b, faculty_list[(i * 2 + 2) % len(faculty_list)]],
                }
                room_map_by_shared = {
                    'room':             [room, room],          # same room
                    'faculty':          [room, room_b],
                    'section':          [room, room_b],
                    'room_and_faculty': [room, room],          # same room
                    'room_partial':     [room, room],          # same room
                    'room_triple':      [room, room, room],    # same room
                }
                subj_list = [subj_a, subj_b, subj_c]

                fac_list = fac_map_by_shared[shared]
                rm_list = room_map_by_shared[shared]

                schedules_to_add = []
                slot_ok = True
                for idx, (sec_key, start_t, end_t) in enumerate(scenario['slots']):
                    sec = sec_map[sec_key]
                    slot_tuple = (sec.id, day, str(start_t), str(end_t))
                    if slot_tuple in existing_slots:
                        self.errors.append(
                            f"Skipped '{scenario['name']}' slot {idx + 1}: section {sec.id} already has {day} {start_t}-{end_t}")
                        slot_ok = False
                        break
                    sched = self._make_test_schedule(
                        sec, subj_list[idx % len(subj_list)],
                        fac_list[idx % len(fac_list)],
                        rm_list[idx % len(rm_list)],
                        day, start_t, end_t, semester, academic_year)
                    schedules_to_add.append(sched)

                if not slot_ok:
                    continue

                for sched in schedules_to_add:
                    try:
                        db.session.begin_nested()
                        db.session.add(sched)
                        db.session.flush()
                        self.results['conflict_schedules'] += 1
                        # Track so later scenarios don't collide
                        existing_slots.add((sched.section_id, sched.day_of_week,
                                            str(sched.start_time), str(sched.end_time)))
                    except IntegrityError:
                        db.session.rollback()
                        self.errors.append(f"Skipped duplicate in '{scenario['name']}' (slot already exists)")

            except Exception as e:
                self.errors.append(f"Error creating conflict scenario '{scenario['name']}': {str(e)}")

    def _generate_conflict_exams(self, count):
        """
        Generate exam schedules with deliberate conflicts for testing.
        Creates pairs of exams that share room, faculty, or section at
        overlapping times on the same date.

        Uses :15/:45 minute offsets to avoid uk_exam_section_slot collisions
        with clean exam data from Phase 3.
        """
        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            self.errors.append("No active academic settings — cannot generate conflict exams")
            return

        academic_year = settings.academic_year
        semester = settings.semester
        exam_period = settings.exam_period or 'Midterm'

        # Pick an exam date (use exam_period_start or tomorrow)
        if settings.exam_period_start:
            exam_date = settings.exam_period_start
        else:
            exam_date = date.today() + timedelta(days=1)
            while exam_date.weekday() >= 6:
                exam_date += timedelta(days=1)

        sections = Section.query.limit(10).all()
        faculty_list = Faculty.query.filter_by(is_archived=False, is_active=True).limit(10).all()
        rooms = Room.query.filter_by(is_available=True).limit(6).all()
        all_subjects = Subject.query.limit(20).all()

        if len(sections) < 3 or len(faculty_list) < 3 or len(rooms) < 2:
            self.errors.append("Not enough data to generate conflict exams. Need at least 3 sections, 3 faculty, 2 rooms.")
            return

        if len(all_subjects) < 3:
            self.errors.append("Not enough subjects — generate programs first")
            return

        # Build existing occupied exam slots
        existing_exam_slots = set()
        existing_exams = ExamSchedule.query.filter_by(
            academic_year=academic_year, semester=semester,
            exam_period=exam_period, is_active=True
        ).with_entities(
            ExamSchedule.section_id, ExamSchedule.exam_date,
            ExamSchedule.start_time, ExamSchedule.end_time
        ).all()
        for e in existing_exams:
            existing_exam_slots.add((e.section_id, str(e.exam_date), str(e.start_time), str(e.end_time)))

        # Use different exam dates for each scenario to avoid cross-scenario collisions
        exam_dates = [exam_date + timedelta(days=d) for d in range(7)]
        exam_dates = [d for d in exam_dates if d.weekday() < 5]
        if len(exam_dates) < 4:
            exam_dates.extend([exam_date + timedelta(days=d) for d in range(7, 14)
                               if (exam_date + timedelta(days=d)).weekday() < 5])

        conflict_scenarios = [
            {
                'name': 'Exam room clash',
                'desc': 'Two exams in same room at same time',
                'slots': [
                    ('a', time(7, 15), time(9, 15)),
                    ('b', time(7, 15), time(9, 15)),
                ],
                'shared': 'room',
            },
            {
                'name': 'Proctor double-book',
                'desc': 'Same proctor assigned to two exams at same time',
                'slots': [
                    ('a', time(10, 15), time(12, 15)),
                    ('b', time(10, 15), time(12, 15)),
                ],
                'shared': 'faculty',
            },
            {
                'name': 'Section exam overlap',
                'desc': 'Same section has two exams at overlapping times',
                'slots': [
                    ('a', time(13, 15), time(15, 15)),
                    ('a', time(14, 15), time(16, 15)),
                ],
                'shared': 'section',
            },
            {
                'name': 'Room + Proctor clash',
                'desc': 'Same room AND proctor for two exams at same time',
                'slots': [
                    ('a', time(7, 45), time(9, 45)),
                    ('b', time(7, 45), time(9, 45)),
                ],
                'shared': 'room_and_faculty',
            },
        ]

        used = conflict_scenarios[:count]

        for i, scenario in enumerate(used):
            try:
                shared = scenario['shared']
                e_date = exam_dates[i % len(exam_dates)]

                sec_a = sections[(i * 3) % len(sections)]
                sec_b = sections[(i * 3 + 1) % len(sections)]
                if sec_b.id == sec_a.id:
                    sec_b = sections[(i * 3 + 2) % len(sections)]

                fac_a = faculty_list[(i * 2) % len(faculty_list)]
                fac_b = faculty_list[(i * 2 + 1) % len(faculty_list)]
                room_a = rooms[i % len(rooms)]
                room_b = rooms[(i + 1) % len(rooms)]

                sec_map = {'a': sec_a, 'b': sec_b}
                fac_map = {
                    'room':             [fac_a, fac_b],
                    'faculty':          [fac_a, fac_a],
                    'section':          [fac_a, fac_b],
                    'room_and_faculty': [fac_a, fac_a],
                }
                rm_map = {
                    'room':             [room_a, room_a],
                    'faculty':          [room_a, room_b],
                    'section':          [room_a, room_b],
                    'room_and_faculty': [room_a, room_a],
                }

                fac_list = fac_map[shared]
                rm_list = rm_map[shared]

                exams_to_add = []
                slot_ok = True
                for idx, (sec_key, start_t, end_t) in enumerate(scenario['slots']):
                    sec = sec_map[sec_key]
                    slot_tuple = (sec.id, str(e_date), str(start_t), str(end_t))
                    if slot_tuple in existing_exam_slots:
                        self.errors.append(
                            f"Skipped '{scenario['name']}' slot {idx + 1}: section {sec.id} already has exam at {e_date} {start_t}-{end_t}")
                        slot_ok = False
                        break
                    exam = self._make_test_exam(
                        sec, all_subjects[(i * 3 + idx) % len(all_subjects)],
                        fac_list[idx % len(fac_list)],
                        rm_list[idx % len(rm_list)],
                        e_date, start_t, end_t,
                        semester, academic_year, exam_period)
                    exams_to_add.append(exam)

                if not slot_ok:
                    continue

                for exam in exams_to_add:
                    try:
                        db.session.begin_nested()
                        db.session.add(exam)
                        db.session.flush()
                        self.results['conflict_exams'] += 1
                        existing_exam_slots.add((exam.section_id, str(exam.exam_date),
                                                 str(exam.start_time), str(exam.end_time)))
                    except IntegrityError:
                        db.session.rollback()
                        self.errors.append(f"Skipped duplicate in '{scenario['name']}' (exam slot already exists)")

            except Exception as e:
                self.errors.append(f"Error creating exam conflict '{scenario['name']}': {str(e)}")

    @staticmethod
    def _make_test_schedule(section, subject, faculty, room, day, start_t, end_t,
                            semester, academic_year):
        """Create a Schedule object for conflict testing."""
        return Schedule(
            section_id=section.id,
            subject_id=subject.id,
            faculty_id=faculty.id,
            room_id=room.id,
            day_of_week=day,
            start_time=start_t,
            end_time=end_t,
            semester=semester,
            academic_year=academic_year,
            schedule_type='lecture',
            is_active=True,
            version=1,
        )

    @staticmethod
    def _make_test_exam(section, subject, faculty, room, exam_date, start_t, end_t,
                        semester, academic_year, exam_period):
        """Create an ExamSchedule object for conflict testing."""
        return ExamSchedule(
            section_id=section.id,
            subject_id=subject.id,
            faculty_id=faculty.id,
            room_id=room.id,
            exam_date=exam_date,
            start_time=start_t,
            end_time=end_t,
            semester=semester,
            academic_year=academic_year,
            exam_period=exam_period,
            schedule_type='lecture',
            is_active=True,
            version=1,
        )

    @staticmethod
    def _ordinal(n):
        """Return ordinal string for a number: 1st, 2nd, 3rd, 4th."""
        if n == 1:
            return '1st'
        elif n == 2:
            return '2nd'
        elif n == 3:
            return '3rd'
        else:
            return f'{n}th'

    # =====================================================================
    # CLEANUP — Remove generated data by entity type
    # =====================================================================

    @staticmethod
    def clear_entity(entity_type, academic_year=None, semester=None):
        """
        Clear all data for a given entity type. Cascading deletes handle children.

        Args:
            entity_type: 'schedules', 'exam_schedules', 'faculty_assignments',
                         'faculty', 'sections', 'buildings', 'programs'
            academic_year: filter for schedule-based entities
            semester: filter for schedule-based entities

        Returns:
            dict with 'success', 'deleted'
        """
        try:
            deleted = 0

            if entity_type == 'schedules':
                q = Schedule.query
                if academic_year:
                    q = q.filter_by(academic_year=academic_year)
                if semester:
                    q = q.filter_by(semester=semester)
                deleted = q.delete()

            elif entity_type == 'exam_schedules':
                q = ExamSchedule.query
                if academic_year:
                    q = q.filter_by(academic_year=academic_year)
                if semester:
                    q = q.filter_by(semester=semester)
                deleted = q.delete()

            elif entity_type == 'faculty_assignments':
                q = FacultySubjectAssignment.query
                if academic_year:
                    q = q.filter_by(academic_year=academic_year)
                if semester:
                    q = q.filter_by(semester=semester)
                deleted = q.delete()

            elif entity_type == 'faculty':
                deleted = Faculty.query.delete()

            elif entity_type == 'sections':
                deleted = Section.query.delete()

            elif entity_type == 'rooms':
                deleted = Room.query.delete()

            elif entity_type == 'buildings':
                # Cascade deletes rooms
                deleted = Building.query.delete()

            elif entity_type == 'programs':
                # Delete curricula first (cascade drops year_levels → semesters → subjects)
                Curriculum.query.delete()
                deleted = Program.query.delete()

            else:
                return {'success': False, 'error': f'Unknown entity type: {entity_type}'}

            db.session.commit()
            return {'success': True, 'deleted': deleted}

        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
