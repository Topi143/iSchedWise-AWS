"""
AutoScheduler Service - Batch Schedule Builder

Supports two modes:
1. Batch Preview: Finds all unscheduled subjects for a section, auto-assigns
   day/time/room (conflict-free) but leaves faculty blank for user to pick.
2. Batch Confirm: Validates and saves user-edited schedule rows with full
   conflict checking (section, faculty, room).
"""

import re
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from app.extensions import db
from app.services.conflict_detector import ConflictDetector


class AutoScheduler:
    """Batch schedule builder with greedy time/room placement."""

    # Scoring weights
    TIME_PREFERENCE = {
        7: 60, 8: 100, 9: 95, 10: 90, 11: 85,
        12: 80, 13: 82, 14: 80, 15: 78, 16: 70,
        17: 60, 18: 50, 19: 40
    }
    DAY_PREFERENCE = {
        'Monday': 90, 'Tuesday': 90, 'Wednesday': 90,
        'Thursday': 90, 'Friday': 90, 'Saturday': 90
    }

    SLOT_INTERVAL_MINUTES = 30  # Scan every 30 minutes
    DEFAULT_LECTURE_DURATION = 90  # 1.5 hours for 3-unit lecture
    DEFAULT_LAB_DURATION = 180  # 3 hours for lab

    # Regex for PE subject code detection (must be word-start 'PE' followed by digit/space/end)
    _PE_CODE_PATTERN = re.compile(r'^pe[\d\s]|^pe$|^pathfit|^p\.e\.', re.IGNORECASE)

    def __init__(self):
        self.conflict_detector = ConflictDetector()

    def _is_pe_subject(self, subject_code: str, course_description: str = '') -> bool:
        """Check if subject is a Physical Education / PATHFIT subject.
        Uses word-boundary matching so 'PERDEV' and 'PERSPECTIVE' are NOT matched.
        """
        code = (subject_code or '').strip()
        if self._PE_CODE_PATTERN.match(code):
            return True
        desc = (course_description or '').lower()
        return any(kw in desc for kw in ['physical education', 'sports', 'fitness'])

    def _serialize_existing_schedules(self, section_id: int, settings) -> List[Dict]:
        """Serialize already saved schedules for preview UI display rows."""
        from app.models.schedule import Schedule as ScheduleModel

        existing_rows = ScheduleModel.query.filter_by(
            section_id=section_id,
            academic_year=settings.academic_year,
            semester=settings.semester,
            is_active=True
        ).all()

        existing_list = []
        for sc in existing_rows:
            subj = sc.subject
            fac = sc.faculty
            rm = sc.room
            existing_list.append({
                'schedule_id': sc.id,
                'subject_id': sc.subject_id,
                'subject_code': subj.subject_code if subj else '',
                'course_description': subj.course_description if subj else '',
                'lec_units': float(subj.lec_units or 0) if subj else 0,
                'lab_units': float(subj.lab_units or 0) if subj else 0,
                'schedule_type': sc.schedule_type or 'lecture',
                'day_of_week': sc.day_of_week,
                'start_time': sc.start_time.strftime('%H:%M') if sc.start_time else '',
                'end_time': sc.end_time.strftime('%H:%M') if sc.end_time else '',
                'faculty_id': sc.faculty_id,
                'faculty_name': f"{fac.last_name}, {fac.first_name}" if fac else '',
                'room_id': sc.room_id,
                'room_name': rm.room_number if rm else '',
                'building_name': rm.building.building_name if rm and rm.building else '',
                'is_existing': True
            })

        return existing_list

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_unscheduled_subjects(self, section_id: int, curriculum_id: int = None,
                                  include_all: bool = False) -> Dict:
        """
        Get all unscheduled subjects for a section.
        Returns subject list with unit info for the batch builder.
        If include_all is True, returns ALL curriculum subjects (including already scheduled).
        """
        from app.models.section import Section
        from app.models.settings import AcademicSettings

        section = Section.query.get(section_id)
        if not section:
            return {'success': False, 'error': 'Section not found'}

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return {'success': False, 'error': 'No active academic settings found'}

        subjects = self._get_section_subjects(section, settings, curriculum_id=curriculum_id)
        if not subjects:
            return {'success': False, 'error': 'No subjects found for this section\'s curriculum and semester'}

        already_scheduled_keys = self._get_already_scheduled_subject_keys(
            section_id, settings.academic_year, settings.semester
        )

        subject_list = []
        for s in subjects:
            slots = self._determine_slots_needed(s)
            for slot in slots:
                slot_type = self._normalize_schedule_type(slot.get('type'))
                key = (s.id, slot_type)
                if not include_all and key in already_scheduled_keys:
                    continue
                subject_list.append({
                    'subject_id': s.id,
                    'subject_code': s.subject_code,
                    'course_description': s.course_description or '',
                    'lec_units': float(s.lec_units or 0),
                    'lab_units': float(s.lab_units or 0),
                    'total_units': float(s.total_units or 0),
                    'schedule_type': slot_type,
                    'duration_minutes': slot['duration']
                })

        return {
            'success': True,
            'subjects': subject_list,
            'all_subjects_count': len(subjects),
            'already_scheduled': len(already_scheduled_keys),
            'section': {'id': section.id, 'name': section.full_section_name}
        }

    def generate_batch_preview(self, section_id: int, curriculum_id: int = None,
                                preferred_building_id: int = None) -> Dict:
        """
        Generate a batch schedule preview for all unscheduled subjects.

        Auto-assigns day/time/room (conflict-free) but leaves faculty blank.
        The user picks faculty via the UI.

        Args:
            preferred_building_id: Soft preference — rooms in this building get a scoring bonus.

        Returns:
            {
                'success': bool,
                'proposed': [ { subject, day, time, room, faculty_id=null, ... } ],
                'unplaceable': [ { subject_code, reason } ],
                'section': { id, name },
                'stats': { total_subjects, scheduled, unplaceable, ... }
            }
        """
        from app.models.section import Section
        from app.models.settings import AcademicSettings

        section = Section.query.get(section_id)
        if not section:
            return {'success': False, 'error': 'Section not found'}

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return {'success': False, 'error': 'No active academic settings found'}

        # 1. Get subjects for this section
        subjects = self._get_section_subjects(section, settings, curriculum_id=curriculum_id)
        if not subjects:
            return {
                'success': False,
                'error': 'No subjects found for this section\'s curriculum and semester'
            }

        # 2. Get already-scheduled subjects
        already_scheduled_keys = self._get_already_scheduled_subject_keys(
            section_id, settings.academic_year, settings.semester
        )
        existing_list = self._serialize_existing_schedules(section_id, settings)

        # 3. Build slot-level unscheduled map so lecture/lab are accounted independently
        slot_overrides = {}
        unscheduled = []
        total_slots = 0

        for subject in subjects:
            slots = self._determine_slots_needed(subject)
            total_slots += len(slots)

            pending_slots = []
            for slot in slots:
                slot_type = self._normalize_schedule_type(slot.get('type'))
                key = (subject.id, slot_type)
                if key not in already_scheduled_keys:
                    pending_slots.append({
                        'type': slot_type,
                        'duration': slot.get('duration')
                    })

            if pending_slots:
                unscheduled.append(subject)
                slot_overrides[subject.id] = pending_slots

        if not unscheduled:
            return {
                'success': True,
                'proposed': [],
                'unplaceable': [],
                'existing': existing_list,
                'section': {'id': section.id, 'name': section.full_section_name},
                'stats': {
                    'total_subjects': total_slots,
                    'already_scheduled': len(already_scheduled_keys),
                    'scheduled': 0,
                    'unplaceable': 0
                },
                'message': 'All subjects are already scheduled for this section.'
            }

        # 4. Sort by total units descending (heaviest subjects first)
        unscheduled.sort(key=lambda s: float(s.total_units or 0), reverse=True)

        # 5. Load all existing schedules for conflict checking
        from app.models.schedule import Schedule
        existing_schedules = Schedule.query.filter_by(
            is_active=True,
            academic_year=settings.academic_year,
            semester=settings.semester
        ).all()

        # 6. Run greedy placement WITHOUT faculty
        proposed, unplaceable = self._greedy_place_batch(
            section, unscheduled, existing_schedules, settings,
            slot_overrides=slot_overrides,
            preferred_building_id=preferred_building_id
        )

        return {
            'success': True,
            'proposed': proposed,
            'unplaceable': unplaceable,
            'existing': existing_list,
            'section': {'id': section.id, 'name': section.full_section_name},
            'stats': {
                'total_subjects': total_slots,
                'already_scheduled': len(already_scheduled_keys),
                'scheduled': len(proposed),
                'unplaceable': len(unplaceable)
            }
        }

    def generate_section_schedule(self, section_id: int) -> Dict:
        """
        Legacy: Generate a proposed schedule with faculty auto-assigned.
        Now wraps generate_batch_preview for backward compatibility.
        """
        return self.generate_batch_preview(section_id)

    def confirm_schedule(self, section_id: int, proposed_items: List[Dict],
                         user_id: int = None) -> Dict:
        """
        Validate and save confirmed schedule items to the database.
        Performs full conflict checking (section, faculty, room) before saving.

        Args:
            section_id: Section ID
            proposed_items: List of proposed schedule dicts
            user_id: ID of the user confirming (for activity logging)

        Returns:
            { 'success': bool, 'created': int, 'errors': [...], 'row_errors': [...] }
        """
        from app.models.schedule import Schedule
        from app.models.faculty import Faculty, FacultySubjectAssignment
        from app.models.settings import AcademicSettings

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return {'success': False, 'error': 'No active academic settings'}

        # Load existing schedules for conflict detection
        existing_schedules = list(Schedule.query.filter_by(
            is_active=True,
            academic_year=settings.academic_year,
            semester=settings.semester
        ).all())

        created = 0
        updated = 0
        errors = []
        row_errors = []
        tentative = []  # Track already-confirmed rows for intra-batch conflicts

        for idx, item in enumerate(proposed_items):
            try:
                subject_code = item.get('subject_code', f'Row {idx+1}')
                start_time_val = item['start_time']
                end_time_val = item['end_time']

                # Parse time strings if needed
                if isinstance(start_time_val, str):
                    start_time_val = datetime.strptime(start_time_val, '%H:%M').time()
                if isinstance(end_time_val, str):
                    end_time_val = datetime.strptime(end_time_val, '%H:%M').time()

                day = item['day_of_week']
                faculty_id = item.get('faculty_id')
                faculty_name = item.get('faculty_name', '')
                room_id = item.get('room_id')
                schedule_id = item.get('schedule_id')

                existing_target = None
                if schedule_id not in (None, '', 'null', 'undefined'):
                    try:
                        schedule_id = int(schedule_id)
                    except (TypeError, ValueError):
                        row_errors.append({
                            'row': idx + 1,
                            'subject_code': subject_code,
                            'error': 'schedule_id is invalid'
                        })
                        continue

                    existing_target = Schedule.query.filter_by(
                        id=schedule_id,
                        is_active=True,
                        academic_year=settings.academic_year,
                        semester=settings.semester
                    ).first()

                    if not existing_target:
                        row_errors.append({
                            'row': idx + 1,
                            'subject_code': subject_code,
                            'error': f'Schedule #{schedule_id} not found for active term'
                        })
                        continue

                    if int(existing_target.section_id) != int(section_id):
                        row_errors.append({
                            'row': idx + 1,
                            'subject_code': subject_code,
                            'error': 'Schedule does not belong to this section'
                        })
                        continue

                try:
                    resolved_faculty_id, _ = self._resolve_faculty_for_confirm(
                        Faculty,
                        faculty_id,
                        faculty_name
                    )
                except ValueError as ve:
                    row_errors.append({
                        'row': idx + 1,
                        'subject_code': subject_code,
                        'error': str(ve)
                    })
                    continue

                faculty_id = resolved_faculty_id
                room_id = int(room_id) if room_id else None

                schedules_for_conflict = existing_schedules
                if existing_target:
                    schedules_for_conflict = [sc for sc in existing_schedules if int(getattr(sc, 'id', 0) or 0) != int(existing_target.id)]

                all_schedules = schedules_for_conflict + tentative
                conflict_found = False

                # Check section conflict
                if self._has_section_conflict(section_id, day, start_time_val, end_time_val, all_schedules):
                    row_errors.append({
                        'row': idx + 1,
                        'subject_code': subject_code,
                        'error': f'Section has a time conflict on {day} {start_time_val.strftime("%I:%M %p")}-{end_time_val.strftime("%I:%M %p")}'
                    })
                    conflict_found = True

                # Check faculty conflict
                if self._has_entity_conflict(faculty_id, 'faculty_id', day, start_time_val, end_time_val, all_schedules):
                    row_errors.append({
                        'row': idx + 1,
                        'subject_code': subject_code,
                        'error': f'Faculty has a time conflict on {day} {start_time_val.strftime("%I:%M %p")}-{end_time_val.strftime("%I:%M %p")}'
                    })
                    conflict_found = True

                # Check room conflict
                if room_id and self._has_entity_conflict(room_id, 'room_id', day, start_time_val, end_time_val, all_schedules):
                    row_errors.append({
                        'row': idx + 1,
                        'subject_code': subject_code,
                        'error': f'Room has a time conflict on {day} {start_time_val.strftime("%I:%M %p")}-{end_time_val.strftime("%I:%M %p")}'
                    })
                    conflict_found = True

                if conflict_found:
                    continue

                if existing_target:
                    existing_target.subject_id = item['subject_id']
                    existing_target.faculty_id = faculty_id
                    existing_target.room_id = room_id
                    existing_target.day_of_week = day
                    existing_target.start_time = start_time_val
                    existing_target.end_time = end_time_val
                    existing_target.schedule_type = item.get('schedule_type', 'lecture')
                    existing_target.version = (existing_target.version or 1) + 1
                    existing_target.updated_at = datetime.utcnow()
                    db.session.flush()
                    existing_schedules = [sc for sc in existing_schedules if int(getattr(sc, 'id', 0) or 0) != int(existing_target.id)]
                    updated += 1
                else:
                    # Check for soft-deleted schedule in the same slot (uk_section_slot)
                    existing_inactive = Schedule.query.filter_by(
                        section_id=section_id,
                        day_of_week=day,
                        start_time=start_time_val,
                        end_time=end_time_val,
                        academic_year=settings.academic_year,
                        semester=settings.semester,
                        is_active=False
                    ).first()

                    if existing_inactive:
                        # Reactivate and update the soft-deleted schedule
                        existing_inactive.subject_id = item['subject_id']
                        existing_inactive.faculty_id = faculty_id
                        existing_inactive.room_id = room_id
                        existing_inactive.schedule_type = item.get('schedule_type', 'lecture')
                        existing_inactive.is_active = True
                        existing_inactive.version = (existing_inactive.version or 1) + 1
                        existing_inactive.updated_at = datetime.utcnow()
                        db.session.flush()
                    else:
                        new_schedule = Schedule(
                            section_id=section_id,
                            subject_id=item['subject_id'],
                            faculty_id=faculty_id,
                            room_id=room_id,
                            day_of_week=day,
                            start_time=start_time_val,
                            end_time=end_time_val,
                            schedule_type=item.get('schedule_type', 'lecture'),
                            academic_year=settings.academic_year,
                            semester=settings.semester,
                            is_active=True
                        )
                        db.session.add(new_schedule)
                        db.session.flush()

                # Track as tentative for intra-batch conflict detection
                mock = self._create_mock_schedule(item, section_id, settings)
                mock.faculty_id = faculty_id
                mock.room_id = room_id
                tentative.append(mock)

                # Auto-create FacultySubjectAssignment
                if faculty_id and item.get('subject_id'):
                    existing = FacultySubjectAssignment.query.filter_by(
                        faculty_id=faculty_id,
                        subject_id=item['subject_id'],
                        academic_year=settings.academic_year,
                        semester=settings.semester
                    ).first()
                    if not existing:
                        assignment = FacultySubjectAssignment(
                            faculty_id=faculty_id,
                            subject_id=item['subject_id'],
                            academic_year=settings.academic_year,
                            semester=settings.semester,
                            is_active=True
                        )
                        db.session.add(assignment)

                if not existing_target:
                    created += 1

            except Exception as e:
                errors.append({
                    'row': idx + 1,
                    'subject_code': item.get('subject_code', f'Row {idx+1}'),
                    'error': str(e)
                })

        if (created + updated) > 0:
            try:
                # Log activity
                if user_id:
                    from app.models.activity_log import UserActivityLog
                    log = UserActivityLog(
                        user_id=user_id,
                        action='batch_schedule',
                        entity_type='schedule',
                        entity_id=section_id,
                        details=f'Batch schedule save: created {created}, updated {updated} for section',
                        ip_address='system'
                    )
                    db.session.add(log)

                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return {'success': False, 'error': f'Database commit failed: {str(e)}'}
        else:
            db.session.rollback()

        return {
            'success': (created + updated) > 0,
            'created': created,
            'updated': updated,
            'errors': errors,
            'row_errors': row_errors
        }

    @staticmethod
    def _normalize_faculty_name(value: str) -> str:
        return ' '.join(str(value or '').split()).strip().lower()

    def _resolve_faculty_for_confirm(self, FacultyModel, faculty_id, faculty_name):
        """Resolve and validate faculty assignment deterministically.

        Resolution policy:
        1) Valid numeric faculty_id for an active, non-archived faculty.
        2) If id missing, allow exact normalized full_name match only when unique.
        """
        if faculty_id not in (None, '', 'null', 'undefined'):
            try:
                candidate_id = int(faculty_id)
            except (TypeError, ValueError):
                raise ValueError('Faculty ID is invalid')

            faculty = FacultyModel.query.filter_by(
                id=candidate_id,
                is_active=True,
                is_archived=False
            ).first()
            if not faculty:
                raise ValueError(f'Faculty ID {candidate_id} is invalid or inactive')

            return faculty.id, faculty.full_name

        normalized_name = self._normalize_faculty_name(faculty_name)
        if not normalized_name:
            raise ValueError('Faculty is required')

        candidates = FacultyModel.query.filter_by(
            is_active=True,
            is_archived=False
        ).all()

        matches = [f for f in candidates if self._normalize_faculty_name(f.full_name) == normalized_name]
        if len(matches) == 1:
            return matches[0].id, matches[0].full_name
        if len(matches) > 1:
            raise ValueError('Faculty name is ambiguous; please select from dropdown again')

        raise ValueError('Faculty name does not match any active faculty')

    # ------------------------------------------------------------------
    # Internal: Subject discovery
    # ------------------------------------------------------------------

    def _get_section_subjects(self, section, settings, curriculum_id: int = None) -> List:
        """Get subjects for a section based on its curriculum and current semester.
        
        If curriculum_id is provided, only subjects from that curriculum are returned.
        Otherwise, subjects from all active curricula for the section's program are returned.
        """
        from app.models.curriculum import Curriculum, YearLevel, Semester, Subject
        from app.models.program import Program

        program = section.program
        if not program:
            return []

        year_level_num = section.year_level

        # Map settings.semester string to semester_number
        semester_number = self._parse_semester_number(settings.semester)

        # Find curricula for this program (or specific one if provided)
        if curriculum_id:
            curricula = Curriculum.query.filter_by(
                id=curriculum_id,
                is_active=True,
                is_archived=False
            ).all()
        else:
            curricula = Curriculum.query.filter_by(
                program_id=program.id,
                is_active=True,
                is_archived=False
            ).all()

        if not curricula:
            return []

        subjects = []
        for curriculum in curricula:
            # Find matching year level
            year_levels = YearLevel.query.filter_by(
                curriculum_id=curriculum.id,
                year_number=year_level_num
            ).all()

            for yl in year_levels:
                # Find matching semester
                semesters = Semester.query.filter_by(
                    year_level_id=yl.id,
                    semester_number=semester_number
                ).all()

                for sem in semesters:
                    sem_subjects = Subject.query.filter_by(
                        semester_id=sem.id
                    ).all()
                    subjects.extend(sem_subjects)

        # Deduplicate by subject id
        seen = set()
        unique = []
        for s in subjects:
            if s.id not in seen:
                seen.add(s.id)
                unique.append(s)
        return unique

    def _get_already_scheduled_subject_ids(self, section_id: int,
                                            academic_year: str,
                                            semester: str) -> set:
        """Get subject IDs that already have schedules for this section.

        Kept for backward compatibility with legacy callers.
        """
        keys = self._get_already_scheduled_subject_keys(section_id, academic_year, semester)
        return {subject_id for subject_id, _ in keys}

    def _get_already_scheduled_subject_keys(self, section_id: int,
                                            academic_year: str,
                                            semester: str) -> set:
        """Get (subject_id, schedule_type) keys already scheduled for this section."""
        from app.models.schedule import Schedule

        existing = Schedule.query.filter_by(
            section_id=section_id,
            academic_year=academic_year,
            semester=semester,
            is_active=True
        ).with_entities(Schedule.subject_id, Schedule.schedule_type).distinct().all()

        return {(row[0], self._normalize_schedule_type(row[1])) for row in existing}

    @staticmethod
    def _normalize_schedule_type(schedule_type: Optional[str]) -> str:
        """Normalize empty/unknown schedule_type values to lecture for stable keying."""
        normalized = (schedule_type or 'lecture').strip().lower()
        if normalized not in ('lecture', 'lab'):
            return 'lecture'
        return normalized

    def _parse_semester_number(self, semester_str: str) -> int:
        """Parse semester string to number. '1st Semester' → 1, '2nd Semester' → 2, etc."""
        if not semester_str:
            return 1
        s = semester_str.lower().strip()
        if '1st' in s or 'first' in s:
            return 1
        elif '2nd' in s or 'second' in s:
            return 2
        elif 'summer' in s or 'mid' in s or '3rd' in s:
            return 3
        return 1

    # ------------------------------------------------------------------
    # Internal: Sibling section LEC coordination
    # ------------------------------------------------------------------

    def _get_sibling_lec_slot(self, section, subject_id: int, academic_year: str,
                               semester: str, existing_schedules: List) -> Optional[Dict]:
        """
        Check if any sibling section (same program + year level) already has
        this LEC-only subject scheduled. If so, return the day+time slot so the
        current section can be aligned to the same slot.

        Returns dict with {day_of_week, start_time, end_time} or None.
        """
        from app.models.section import Section as SectionModel
        from app.models.schedule import Schedule

        # Find sibling sections (same program + year level, excluding self)
        sibling_sections = SectionModel.query.filter(
            SectionModel.program_id == section.program_id,
            SectionModel.year_level == section.year_level,
            SectionModel.id != section.id
        ).all()

        if not sibling_sections:
            return None

        sibling_ids = [s.id for s in sibling_sections]

        # Look for matching schedules in existing_schedules list first (faster)
        for sched in existing_schedules:
            if (getattr(sched, 'subject_id', None) == subject_id and
                getattr(sched, 'section_id', None) in sibling_ids and
                getattr(sched, 'schedule_type', 'lecture') == 'lecture'):
                return {
                    'day_of_week': sched.day_of_week,
                    'start_time': sched.start_time.strftime('%H:%M') if hasattr(sched.start_time, 'strftime') else str(sched.start_time),
                    'end_time': sched.end_time.strftime('%H:%M') if hasattr(sched.end_time, 'strftime') else str(sched.end_time)
                }

        # Fallback: query database directly
        match = Schedule.query.filter(
            Schedule.subject_id == subject_id,
            Schedule.section_id.in_(sibling_ids),
            Schedule.schedule_type == 'lecture',
            Schedule.academic_year == academic_year,
            Schedule.semester == semester,
            Schedule.is_active == True
        ).first()

        if match:
            return {
                'day_of_week': match.day_of_week,
                'start_time': match.start_time.strftime('%H:%M'),
                'end_time': match.end_time.strftime('%H:%M')
            }

        return None

    # ------------------------------------------------------------------
    # Internal: Greedy placement algorithm (batch - no faculty)
    # ------------------------------------------------------------------

    def _greedy_place_batch(self, section, subjects: List, existing_schedules: List,
                            settings, slot_overrides: Optional[Dict[int, List[Dict]]] = None,
                            preferred_building_id: int = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Greedy heuristic for batch mode: finds day×time×room combos only.
        Faculty is left blank (null) for the user to pick in the UI.
        Only checks section and room conflicts (no faculty conflicts).

        Args:
            preferred_building_id: Soft preference — rooms in this building get a scoring bonus.
        """
        from app.models.building import Room

        proposed = []
        unplaceable = []
        tentative = []

        start_hour = (settings.schedule_start_time.hour if settings.schedule_start_time else 7)
        end_hour = (settings.schedule_end_time.hour if settings.schedule_end_time else 20)
        days = settings.get_operation_days_list() if hasattr(settings, 'get_operation_days_list') else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        all_rooms = Room.query.filter_by(is_available=True).join(Room.building).all()

        for subject in subjects:
            slots_needed = slot_overrides.get(subject.id) if slot_overrides else self._determine_slots_needed(subject)
            slot_types = {self._normalize_schedule_type(slot.get('type')) for slot in slots_needed}
            has_both = slot_types == {'lecture', 'lab'}

            # Track the placed lecture so lab can follow on the same day
            placed_lecture = None

            for slot_info in slots_needed:
                schedule_type = self._normalize_schedule_type(slot_info.get('type'))
                duration_minutes = slot_info['duration']

                matching_rooms = self._get_matching_rooms(subject, schedule_type, all_rooms)
                if not matching_rooms:
                    unplaceable.append({
                        'subject_id': subject.id,
                        'subject_code': subject.subject_code,
                        'course_description': subject.course_description or '',
                        'schedule_type': schedule_type,
                        'reason': f'No available {schedule_type} rooms found'
                    })
                    continue

                # If this is the lab part of a LEC+LAB subject, constrain to same day
                # immediately after lecture (back-to-back, zero gap)
                forced_day = None
                after_time = None
                lab_forced_start = None
                is_lec_lab_pair = has_both and schedule_type == 'lab' and placed_lecture
                if is_lec_lab_pair:
                    forced_day = placed_lecture['day_of_week']
                    lab_forced_start = placed_lecture['end_time']  # Lab must start exactly when LEC ends

                # ── Year-level LEC alignment ──────────────────────────
                # For LEC-only subjects (no lab), try to match the same
                # day+time as sibling sections (same dept + year level).
                sibling_slot = None
                is_lec_only = not has_both and schedule_type == 'lecture'
                if is_lec_only:
                    sibling_slot = self._get_sibling_lec_slot(
                        section, subject.id,
                        settings.academic_year, settings.semester,
                        existing_schedules + tentative
                    )

                best = None

                # If a sibling slot exists, try to use that exact day+time first
                if sibling_slot and is_lec_only:
                    best = self._find_best_slot_batch(
                        section=section,
                        subject=subject,
                        schedule_type=schedule_type,
                        duration_minutes=duration_minutes,
                        matching_rooms=matching_rooms,
                        existing_schedules=existing_schedules,
                        tentative=tentative,
                        days=days,
                        start_hour=start_hour,
                        end_hour=end_hour,
                        forced_day=sibling_slot['day_of_week'],
                        after_time=None,
                        forced_start_time=sibling_slot['start_time'],
                        preferred_building_id=preferred_building_id
                    )

                # LEC+LAB pair: try back-to-back first (lab starts exactly when lecture ends)
                if not best and is_lec_lab_pair:
                    best = self._find_best_slot_batch(
                        section=section,
                        subject=subject,
                        schedule_type=schedule_type,
                        duration_minutes=duration_minutes,
                        matching_rooms=matching_rooms,
                        existing_schedules=existing_schedules,
                        tentative=tentative,
                        days=days,
                        start_hour=start_hour,
                        end_hour=end_hour,
                        forced_day=forced_day,
                        after_time=None,
                        forced_start_time=lab_forced_start,
                        is_lec_lab_follow=True,
                        preferred_building_id=preferred_building_id
                    )

                # Fallback: normal best-slot search (with sibling bonus scoring)
                # For LEC+LAB pair: if exact back-to-back failed, allow lab anywhere after lecture
                if not best:
                    best = self._find_best_slot_batch(
                        section=section,
                        subject=subject,
                        schedule_type=schedule_type,
                        duration_minutes=duration_minutes,
                        matching_rooms=matching_rooms,
                        existing_schedules=existing_schedules,
                        tentative=tentative,
                        days=days,
                        start_hour=start_hour,
                        end_hour=end_hour,
                        forced_day=forced_day,
                        after_time=lab_forced_start if is_lec_lab_pair else after_time,
                        sibling_slot=sibling_slot,
                        is_lec_lab_follow=is_lec_lab_pair,
                        preferred_building_id=preferred_building_id
                    )

                if best:
                    proposed.append(best)
                    mock = self._create_mock_schedule(best, section.id, settings)
                    tentative.append(mock)
                    # Remember placed lecture for lab constraint
                    if has_both and schedule_type == 'lecture':
                        placed_lecture = best
                else:
                    unplaceable.append({
                        'subject_id': subject.id,
                        'subject_code': subject.subject_code,
                        'course_description': subject.course_description or '',
                        'schedule_type': schedule_type,
                        'reason': 'No conflict-free time slot available'
                    })

        return proposed, unplaceable

    def _find_best_slot_batch(self, section, subject, schedule_type: str,
                               duration_minutes: int, matching_rooms: List,
                               existing_schedules: List, tentative: List,
                               days: List, start_hour: int, end_hour: int,
                               forced_day: str = None, after_time: str = None,
                               forced_start_time: str = None,
                               sibling_slot: Dict = None,
                               preferred_building_id: int = None,
                               is_lec_lab_follow: bool = False) -> Optional[Dict]:
        """
        Find best day×time×room combo (no faculty). Uses section + room conflict checks only.
        Applies day-balancing so subjects are evenly spread across the week.

        If forced_day is set, only consider that day (used for LEC+LAB same-day).
        If after_time is set ('HH:MM'), only consider slots starting >= that time.
        If forced_start_time is set ('HH:MM'), only consider slots starting at that exact time.
        If sibling_slot is set, add a large scoring bonus for matching day+time.
        If preferred_building_id is set, rooms from that building get a scoring bonus (+40).
        If is_lec_lab_follow is True, this is a LAB slot immediately following its LEC
            — exempt from break penalties and rewarded for back-to-back placement.
        """
        best_candidate = None
        best_score = -1

        time_slots = self._generate_time_slots(start_hour, end_hour, duration_minutes)
        all_schedules = existing_schedules + tentative

        # Parse after_time constraint if provided
        after_time_obj = None
        if after_time:
            parts = after_time.split(':')
            after_time_obj = time(int(parts[0]), int(parts[1]))

        # Parse forced_start_time constraint if provided (exact match)
        forced_start_obj = None
        if forced_start_time:
            parts = forced_start_time.split(':')
            forced_start_obj = time(int(parts[0]), int(parts[1]))

        # Parse sibling_slot for scoring bonus
        sibling_day = None
        sibling_start = None
        if sibling_slot:
            sibling_day = sibling_slot.get('day_of_week')
            st_str = sibling_slot.get('start_time', '')
            if st_str:
                parts = st_str.split(':')
                sibling_start = time(int(parts[0]), int(parts[1]))

        # If forced to a specific day, only use that day
        search_days = [forced_day] if forced_day else days

        # Count how many classes this section already has on each day
        # (existing + tentatively placed so far) for day-balancing
        day_counts = {d: 0 for d in days}
        for s in all_schedules:
            if getattr(s, 'section_id', None) == section.id:
                d = getattr(s, 'day_of_week', None)
                if d in day_counts:
                    day_counts[d] += 1

        min_day_count = min(day_counts.values()) if day_counts else 0

        for day in search_days:
            for slot_start, slot_end in time_slots:
                # If after_time constraint, skip slots that start before it
                if after_time_obj and slot_start < after_time_obj:
                    continue

                # If forced_start_time, only allow exact match
                if forced_start_obj and slot_start != forced_start_obj:
                    continue

                # Section conflict check
                if self._has_section_conflict(section.id, day, slot_start, slot_end, all_schedules):
                    continue

                for room in matching_rooms:
                    # Room conflict check
                    if self._has_entity_conflict(room.id, 'room_id', day, slot_start, slot_end, all_schedules):
                        continue

                    # Score this candidate (time + day + room match only)
                    score = self.TIME_PREFERENCE.get(slot_start.hour, 50)
                    score += self.DAY_PREFERENCE.get(day, 60)

                    # Day-balancing: penalize days that already have more classes
                    # Heavy penalty per extra class above the minimum day count
                    day_excess = day_counts[day] - min_day_count
                    score -= day_excess * 50

                    # ── Natural break / gap scoring ───────────────────
                    # Enforce 30-60 min breaks between classes on the
                    # same day.  LEC→LAB pairs are exempt and rewarded
                    # for back-to-back (zero gap) placement.
                    same_day_schedules = [
                        s for s in all_schedules
                        if getattr(s, 'section_id', None) == section.id
                        and getattr(s, 'day_of_week', None) == day
                    ]
                    if same_day_schedules:
                        # Compute the smallest gap (in minutes) between
                        # this candidate and any existing section class
                        min_gap = float('inf')
                        for s in same_day_schedules:
                            s_start = s.start_time
                            s_end = s.end_time
                            if slot_end <= s_start:
                                gap = (s_start.hour * 60 + s_start.minute) - (slot_end.hour * 60 + slot_end.minute)
                            elif slot_start >= s_end:
                                gap = (slot_start.hour * 60 + slot_start.minute) - (s_end.hour * 60 + s_end.minute)
                            else:
                                gap = 0  # overlapping (conflict check should have caught this)
                            if gap < min_gap:
                                min_gap = gap

                        if is_lec_lab_follow:
                            # LEC→LAB pair: reward back-to-back, no break needed
                            if min_gap == 0:
                                score += 50   # ideal: LAB starts right when LEC ends
                            elif 0 < min_gap <= 30:
                                score += 20   # acceptable small gap
                        else:
                            # Regular classes: enforce 30-60 min breaks
                            if min_gap == 0:
                                score -= 200  # near-prohibitive: no back-to-back
                            elif 0 < min_gap < 30:
                                score -= 150  # strong penalty: gap too short (< 30 min)
                            elif 30 <= min_gap <= 60:
                                score += 80   # ideal: 30-60 min break
                            elif 60 < min_gap <= 120:
                                score += 40   # good: 1-2 hour break
                            # gaps > 2 hr get no bonus (neutral)

                    # ── Lunch overlap penalty ─────────────────────────
                    # Avoid scheduling through 12:00-1:00 PM
                    lunch_start_t = time(12, 0)
                    lunch_end_t = time(13, 0)
                    if self._times_overlap(slot_start, slot_end, lunch_start_t, lunch_end_t):
                        # If the class completely spans lunch, penalise
                        score -= 60

                    # Sibling slot bonus: strongly prefer matching day+time
                    if sibling_day and sibling_start:
                        if day == sibling_day and slot_start == sibling_start:
                            score += 500  # Very strong preference for exact match
                        elif day == sibling_day:
                            score += 100  # Moderate bonus for same day

                    # Room type match bonus
                    is_pe = self._is_pe_subject(subject.subject_code, subject.course_description)
                    if is_pe and room.room_type == 'Court/Gym':
                        score += 30
                    elif schedule_type == 'lab' and room.room_type == 'Laboratory':
                        score += 30
                    elif schedule_type == 'lecture' and room.room_type == 'Lecture':
                        score += 20

                    # Preferred building bonus (soft preference)
                    if preferred_building_id and room.building_id == preferred_building_id:
                        score += 40

                    if score > best_score:
                        best_score = score
                        best_candidate = {
                            'subject_id': subject.id,
                            'subject_code': subject.subject_code,
                            'course_description': subject.course_description or '',
                            'faculty_id': None,
                            'faculty_name': '',
                            'room_id': room.id,
                            'room_name': room.room_number,
                            'room_type': room.room_type,
                            'building_name': room.building.building_name if room.building else '',
                            'day_of_week': day,
                            'start_time': slot_start.strftime('%H:%M'),
                            'end_time': slot_end.strftime('%H:%M'),
                            'start_time_display': slot_start.strftime('%I:%M %p'),
                            'end_time_display': slot_end.strftime('%I:%M %p'),
                            'schedule_type': schedule_type,
                            'score': score,
                            'lec_units': float(subject.lec_units or 0),
                            'lab_units': float(subject.lab_units or 0),
                            'total_units': float(subject.total_units or 0)
                        }

        return best_candidate

    def get_available_rooms(self, day: str, start_time_str: str, end_time_str: str,
                            schedule_type: str = 'lecture',
                            subject_id: int = None,
                            preferred_building_id: int = None,
                            exclude_schedule_id: int = None) -> List[Dict]:
        """
        Get rooms available (no conflicts) at a specific day/time slot.
        Used by the batch builder to refresh room options when user edits time.

        Args:
            subject_id: If provided, enables PE-aware filtering (Lecture + Court/Gym for PE).
            preferred_building_id: If provided, rooms from this building are listed first.
        """
        from app.models.building import Room
        from app.models.schedule import Schedule
        from app.models.settings import AcademicSettings
        from app.models.curriculum import Subject

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return []

        start_time_val = datetime.strptime(start_time_str, '%H:%M').time()
        end_time_val = datetime.strptime(end_time_str, '%H:%M').time()

        existing_schedules = Schedule.query.filter_by(
            is_active=True,
            academic_year=settings.academic_year,
            semester=settings.semester
        ).all()

        all_rooms = Room.query.filter_by(is_available=True).join(Room.building).all()

        # Use subject-aware room filtering if subject_id is provided
        if subject_id:
            subject = Subject.query.get(subject_id)
            if subject:
                matching_rooms = self._get_matching_rooms(subject, schedule_type, all_rooms)
            else:
                matching_rooms = self._get_matching_rooms_by_type(schedule_type, all_rooms)
        else:
            matching_rooms = self._get_matching_rooms_by_type(schedule_type, all_rooms)

        rooms_with_status = []
        for room in matching_rooms:
            conflict_schedule = None
            for sc in existing_schedules:
                if exclude_schedule_id and getattr(sc, 'id', None) == exclude_schedule_id:
                    continue
                if getattr(sc, 'room_id', None) == room.id and getattr(sc, 'day_of_week', None) == day:
                    if self._times_overlap(start_time_val, end_time_val, sc.start_time, sc.end_time):
                        conflict_schedule = sc
                        break

            section_name = ''
            subject_code = ''
            conflict_start = ''
            conflict_end = ''
            occupied_note = ''
            if conflict_schedule:
                if conflict_schedule.section:
                    section_name = conflict_schedule.section.full_section_name or conflict_schedule.section.section_name or 'Unknown Section'
                else:
                    section_name = 'Unknown Section'
                subject_code = conflict_schedule.subject.subject_code if conflict_schedule.subject else 'Unknown Subject'
                conflict_start = conflict_schedule.start_time.strftime('%H:%M') if conflict_schedule.start_time else ''
                conflict_end = conflict_schedule.end_time.strftime('%H:%M') if conflict_schedule.end_time else ''
                occupied_note = f"Used by {section_name} ({subject_code})"

            rooms_with_status.append({
                'id': room.id,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'building_id': room.building_id,
                'building_name': room.building.building_name if room.building else '',
                'capacity': room.capacity if hasattr(room, 'capacity') else None,
                'is_occupied': bool(conflict_schedule),
                'occupied_note': occupied_note,
                'occupied_by': {
                    'section_name': section_name,
                    'subject_code': subject_code,
                    'day_of_week': conflict_schedule.day_of_week if conflict_schedule else '',
                    'start_time': conflict_start,
                    'end_time': conflict_end,
                } if conflict_schedule else None
            })

        # Sort: preferred building first, then by room_number
        if preferred_building_id:
            rooms_with_status.sort(key=lambda r: (0 if r['building_id'] == preferred_building_id else 1, r['is_occupied'], r['room_number']))
        else:
            rooms_with_status.sort(key=lambda r: (r['is_occupied'], r['room_number']))

        return rooms_with_status

    def _get_matching_rooms_by_type(self, schedule_type: str, all_rooms: List) -> List:
        """Filter rooms by schedule type without subject context.
        Lab sessions can use Laboratory rooms (preferred) or Lecture rooms.
        """
        if schedule_type == 'lab':
            allowed_types = ['Laboratory', 'Lecture']
        else:
            # Lecture type: only Lecture rooms (no gym unless PE — handled by _get_matching_rooms)
            allowed_types = ['Lecture']
        return [r for r in all_rooms if r.room_type in allowed_types]

    # ------------------------------------------------------------------
    # Internal: Greedy placement algorithm (legacy with faculty)
    # ------------------------------------------------------------------

    def _greedy_place(self, section, subjects: List, existing_schedules: List,
                      settings) -> Tuple[List[Dict], List[Dict]]:
        """
        Greedy heuristic: for each subject, try all day×time×room×faculty combos,
        pick the highest-scoring conflict-free slot.

        Maintains a 'tentative' list so subsequent subjects see already-proposed schedules.
        """
        from app.models.schedule import Schedule
        from app.models.building import Room
        from app.models.faculty import Faculty, FacultySubjectAssignment, FacultyAvailability
        from app.models.curriculum import Subject

        proposed = []
        unplaceable = []

        # Tentative schedules (mock Schedule objects for conflict detection)
        tentative = []

        start_hour = (settings.schedule_start_time.hour if settings.schedule_start_time else 7)
        end_hour = (settings.schedule_end_time.hour if settings.schedule_end_time else 20)
        days = settings.get_operation_days_list() if hasattr(settings, 'get_operation_days_list') else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        # Preload available rooms
        all_rooms = Room.query.filter_by(is_available=True).join(
            Room.building
        ).all()

        for subject in subjects:
            # Determine what needs to be scheduled for this subject
            slots_needed = self._determine_slots_needed(subject)
            has_both = len(slots_needed) == 2 and slots_needed[0]['type'] == 'lecture' and slots_needed[1]['type'] == 'lab'

            # Track the placed lecture so lab can follow on the same day
            placed_lecture = None

            placed_all = True
            for slot_info in slots_needed:
                schedule_type = slot_info['type']  # 'lecture' or 'lab'
                duration_minutes = slot_info['duration']

                # Get eligible faculty
                eligible_faculty = self._get_eligible_faculty(
                    subject, settings, existing_schedules + tentative
                )

                if not eligible_faculty:
                    placed_all = False
                    unplaceable.append({
                        'subject_id': subject.id,
                        'subject_code': subject.subject_code,
                        'course_description': subject.course_description,
                        'schedule_type': schedule_type,
                        'reason': 'No eligible faculty assigned to this subject'
                    })
                    continue

                # Get matching rooms
                matching_rooms = self._get_matching_rooms(
                    subject, schedule_type, all_rooms
                )

                if not matching_rooms:
                    placed_all = False
                    unplaceable.append({
                        'subject_id': subject.id,
                        'subject_code': subject.subject_code,
                        'course_description': subject.course_description,
                        'schedule_type': schedule_type,
                        'reason': f'No available {schedule_type} rooms found'
                    })
                    continue

                # If this is the lab part of a LEC+LAB subject, constrain to same day after lecture
                forced_day = None
                after_time = None
                if has_both and schedule_type == 'lab' and placed_lecture:
                    forced_day = placed_lecture['day_of_week']
                    after_time = placed_lecture['end_time']

                # Find best slot across all combos
                best = self._find_best_slot(
                    section=section,
                    subject=subject,
                    schedule_type=schedule_type,
                    duration_minutes=duration_minutes,
                    eligible_faculty=eligible_faculty,
                    matching_rooms=matching_rooms,
                    existing_schedules=existing_schedules,
                    tentative=tentative,
                    days=days,
                    start_hour=start_hour,
                    end_hour=end_hour,
                    settings=settings,
                    forced_day=forced_day,
                    after_time=after_time
                )

                if best:
                    proposed.append(best)
                    # Create a mock schedule object for subsequent conflict checks
                    mock = self._create_mock_schedule(best, section.id, settings)
                    tentative.append(mock)
                    # Remember placed lecture for lab constraint
                    if has_both and schedule_type == 'lecture':
                        placed_lecture = best
                else:
                    placed_all = False
                    unplaceable.append({
                        'subject_id': subject.id,
                        'subject_code': subject.subject_code,
                        'course_description': subject.course_description,
                        'schedule_type': schedule_type,
                        'reason': 'No conflict-free time slot available'
                    })

        return proposed, unplaceable

    def _determine_slots_needed(self, subject) -> List[Dict]:
        """
        Determine how many schedule slots a subject needs.
        - Lecture-only: 1 slot
        - Lab-only: 1 slot
        - Both lecture + lab: 2 slots
        """
        slots = []
        lec_units = float(subject.lec_units or 0)
        lab_units = float(subject.lab_units or 0)
        has_both = lec_units > 0 and lab_units > 0

        if lec_units > 0:
            if has_both:
                # Subject has both LEC and LAB: 2 units = 3hrs, 1 unit = 2hrs
                duration = 180 if lec_units >= 2 else 120
            else:
                # LEC-only subject: always 3hrs
                duration = 180
            slots.append({'type': 'lecture', 'duration': duration})

        if lab_units > 0:
            if has_both:
                # Subject has both LEC and LAB: 2 units = 3hrs, 1 unit = 2hrs
                duration = 180 if lab_units >= 2 else 120
            else:
                # LAB-only subject: use unit-based calculation
                duration = int(lab_units * 60)
                duration = max(60, min(duration, 240))
            slots.append({'type': 'lab', 'duration': duration})

        # If subject has no units specified, default to a 1.5hr lecture
        if not slots:
            slots.append({'type': 'lecture', 'duration': 90})

        return slots

    def _get_eligible_faculty(self, subject, settings, all_schedules: List) -> List:
        """Get faculty assigned to this subject who still have capacity."""
        from app.models.faculty import Faculty, FacultySubjectAssignment

        assignments = FacultySubjectAssignment.query.filter_by(
            subject_id=subject.id,
            academic_year=settings.academic_year,
            semester=settings.semester,
            is_active=True,
            is_archived=False
        ).all()

        faculty_ids = list(set(a.faculty_id for a in assignments))
        if not faculty_ids:
            return []

        faculty_list = Faculty.query.filter(
            Faculty.id.in_(faculty_ids),
            Faculty.is_active == True,
            Faculty.is_archived == False
        ).all()

        # Sort by current load ascending → prefer less-loaded faculty
        def _load_sort_key(f):
            load_info = f.get_load_status(settings.academic_year, settings.semester)
            current = load_info[0] if load_info else 0
            return float(current)

        faculty_list.sort(key=_load_sort_key)
        return faculty_list

    def _get_matching_rooms(self, subject, schedule_type: str,
                            all_rooms: List) -> List:
        """Filter rooms that match the subject/schedule type.
        PE subjects prefer Court/Gym but fall back to Lecture rooms if none available.
        Lab subjects can use Laboratory OR Lecture rooms (lab rooms get a scoring bonus).
        """
        is_pe = self._is_pe_subject(subject.subject_code, subject.course_description)

        if is_pe:
            # PE subjects can use Court/Gym AND Lecture rooms; scoring prefers gym
            return [r for r in all_rooms if r.room_type in ('Court/Gym', 'Lecture')]
        elif schedule_type == 'lab':
            # Lab can use Laboratory rooms (preferred via scoring bonus) or Lecture rooms
            return [r for r in all_rooms if r.room_type in ('Laboratory', 'Lecture')]
        else:
            return [r for r in all_rooms if r.room_type == 'Lecture']

    def _find_best_slot(self, section, subject, schedule_type: str,
                        duration_minutes: int, eligible_faculty: List,
                        matching_rooms: List, existing_schedules: List,
                        tentative: List, days: List, start_hour: int,
                        end_hour: int, settings,
                        forced_day: str = None, after_time: str = None) -> Optional[Dict]:
        """
        Scan all day × time × faculty × room combos and return the best
        conflict-free option with highest score.

        If forced_day is set, only consider that day (used for LEC+LAB same-day).
        If after_time is set ('HH:MM'), only consider slots starting >= that time.
        """
        from app.models.faculty import FacultyAvailability

        best_candidate = None
        best_score = -1

        # Generate time slots for the given duration
        time_slots = self._generate_time_slots(start_hour, end_hour, duration_minutes)

        all_schedules = existing_schedules + tentative

        # Parse after_time constraint if provided
        after_time_obj = None
        if after_time:
            parts = after_time.split(':')
            after_time_obj = time(int(parts[0]), int(parts[1]))

        # If forced to a specific day, only use that day
        search_days = [forced_day] if forced_day else days

        for day in search_days:
            for slot_start, slot_end in time_slots:
                # If after_time constraint, skip slots that start before it
                if after_time_obj and slot_start < after_time_obj:
                    continue

                for faculty in eligible_faculty:
                    # Quick check: faculty availability
                    avail = FacultyAvailability.check_faculty_available_by_day(
                        faculty.id, day, slot_start, slot_end
                    )
                    if avail['status'] in ('unavailable',):
                        continue

                    # Quick check: section time conflict
                    if self._has_section_conflict(section.id, day, slot_start, slot_end, all_schedules):
                        continue

                    # Quick check: faculty time conflict
                    if self._has_entity_conflict(faculty.id, 'faculty_id', day, slot_start, slot_end, all_schedules):
                        continue

                    for room in matching_rooms:
                        # Quick check: room time conflict
                        if self._has_entity_conflict(room.id, 'room_id', day, slot_start, slot_end, all_schedules):
                            continue

                        # Score this candidate
                        score = self._score_candidate(
                            day, slot_start, faculty, room, subject,
                            schedule_type, all_schedules, settings,
                            section=section
                        )

                        if score > best_score:
                            best_score = score
                            best_candidate = {
                                'subject_id': subject.id,
                                'subject_code': subject.subject_code,
                                'course_description': subject.course_description,
                                'faculty_id': faculty.id,
                                'faculty_name': faculty.full_name,
                                'room_id': room.id,
                                'room_name': room.room_number,
                                'room_type': room.room_type,
                                'building_name': room.building.building_name if room.building else '',
                                'day_of_week': day,
                                'start_time': slot_start.strftime('%H:%M'),
                                'end_time': slot_end.strftime('%H:%M'),
                                'start_time_display': slot_start.strftime('%I:%M %p'),
                                'end_time_display': slot_end.strftime('%I:%M %p'),
                                'schedule_type': schedule_type,
                                'score': score,
                                'lec_units': float(subject.lec_units or 0),
                                'lab_units': float(subject.lab_units or 0),
                                'total_units': float(subject.total_units or 0)
                            }

        return best_candidate

    def _generate_time_slots(self, start_hour: int, end_hour: int,
                              duration_minutes: int) -> List[Tuple[time, time]]:
        """Generate all possible (start, end) time slots for a duration."""
        slots = []
        current_min = start_hour * 60

        while current_min + duration_minutes <= end_hour * 60:
            s_h, s_m = divmod(current_min, 60)
            e_min = current_min + duration_minutes
            e_h, e_m = divmod(e_min, 60)

            if e_h < 24:
                slots.append((time(s_h, s_m), time(e_h, e_m)))

            current_min += self.SLOT_INTERVAL_MINUTES

        return slots

    def _has_section_conflict(self, section_id: int, day: str,
                               start: time, end: time,
                               schedules: List) -> bool:
        """Check if section has a schedule at this day/time."""
        for s in schedules:
            if s.section_id == section_id and s.day_of_week == day:
                if self._times_overlap(start, end, s.start_time, s.end_time):
                    return True
        return False

    def _has_entity_conflict(self, entity_id: int, field: str, day: str,
                              start: time, end: time,
                              schedules: List) -> bool:
        """Check if entity (faculty/room) has a conflict at this day/time."""
        for s in schedules:
            if getattr(s, field, None) == entity_id and s.day_of_week == day:
                if self._times_overlap(start, end, s.start_time, s.end_time):
                    return True
        return False

    @staticmethod
    def _times_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
        return start1 < end2 and end1 > start2

    def _score_candidate(self, day: str, start: time, faculty, room,
                          subject, schedule_type: str, all_schedules: List,
                          settings, section=None) -> int:
        """
        Score a candidate placement. Higher = better.
        Factors: time preference, day preference, workload balance, room match,
        day-balancing (even spread across the week).
        """
        score = 0

        # Time preference (morning classes preferred)
        score += self.TIME_PREFERENCE.get(start.hour, 50)

        # Day preference
        score += self.DAY_PREFERENCE.get(day, 60)

        # Day-balancing: penalize days that already have more section classes
        if section is not None:
            days_list = settings.get_operation_days_list() if hasattr(settings, 'get_operation_days_list') else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            day_counts = {d: 0 for d in days_list}
            for s in all_schedules:
                if getattr(s, 'section_id', None) == section.id:
                    d = getattr(s, 'day_of_week', None)
                    if d in day_counts:
                        day_counts[d] += 1
            min_day_count = min(day_counts.values()) if day_counts else 0
            day_excess = day_counts.get(day, 0) - min_day_count
            score -= day_excess * 50

        # Faculty workload balance
        faculty_day_hours = 0
        faculty_weekly_hours = 0
        for s in all_schedules:
            if getattr(s, 'faculty_id', None) == faculty.id:
                dur = self._duration_hours(s.start_time, s.end_time)
                faculty_weekly_hours += dur
                if s.day_of_week == day:
                    faculty_day_hours += dur

        # Penalty for overloaded faculty
        max_units = float(faculty.get_max_units() or 24)
        if faculty_weekly_hours >= max_units:
            score -= 100  # Heavy penalty
        elif faculty_weekly_hours > max_units * 0.8:
            score -= 30
        else:
            # Bonus for spreading load
            score += int((max_units - faculty_weekly_hours) * 2)

        # Penalty for too many hours in one day (prefer 4-6h max)
        if faculty_day_hours > 6:
            score -= 40
        elif faculty_day_hours > 4:
            score -= 10
        elif faculty_day_hours == 0:
            score += 15  # Bonus for using a new day (spread across week)

        # ── Section break / gap scoring (legacy mode) ─────────────
        # Encourage 30-60 min breaks between section classes.
        if section is not None:
            same_day = [
                s for s in all_schedules
                if getattr(s, 'section_id', None) == section.id
                and getattr(s, 'day_of_week', None) == day
            ]
            if same_day:
                end_t = start  # slot start is the `start` param
                # Calculate slot end from start + subject duration
                dur_min = self._duration_hours(start, start) * 60  # placeholder
                min_gap = float('inf')
                for s in same_day:
                    s_start = s.start_time
                    s_end = s.end_time
                    # We only know the candidate start; estimate gap from neighbours
                    gap_after = (start.hour * 60 + start.minute) - (s_end.hour * 60 + s_end.minute)
                    gap_before = (s_start.hour * 60 + s_start.minute) - (start.hour * 60 + start.minute)
                    if gap_after >= 0 and gap_after < min_gap:
                        min_gap = gap_after
                    if gap_before >= 0 and gap_before < min_gap:
                        min_gap = gap_before
                if min_gap != float('inf'):
                    if min_gap == 0:
                        score -= 200  # near-prohibitive: no back-to-back
                    elif 0 < min_gap < 30:
                        score -= 150  # strong penalty: gap too short
                    elif 30 <= min_gap <= 60:
                        score += 80   # ideal: 30-60 min break
                    elif 60 < min_gap <= 120:
                        score += 40   # good: 1-2 hour break

        # Room type match bonus
        is_pe = self._is_pe_subject(subject.subject_code, getattr(subject, 'course_description', ''))

        if is_pe and room.room_type == 'Court/Gym':
            score += 30
        elif schedule_type == 'lab' and room.room_type == 'Laboratory':
            score += 30
        elif schedule_type == 'lecture' and room.room_type == 'Lecture':
            score += 20

        return score

    @staticmethod
    def _duration_hours(start: time, end: time) -> float:
        """Calculate duration in hours between two time objects."""
        start_min = start.hour * 60 + start.minute
        end_min = end.hour * 60 + end.minute
        return (end_min - start_min) / 60

    def _create_mock_schedule(self, proposed: Dict, section_id: int, settings) -> object:
        """
        Create a lightweight mock object that looks enough like a Schedule
        for conflict detection purposes.
        """
        start = proposed['start_time']
        end = proposed['end_time']
        if isinstance(start, str):
            start = datetime.strptime(start, '%H:%M').time()
        if isinstance(end, str):
            end = datetime.strptime(end, '%H:%M').time()

        class MockSchedule:
            pass

        mock = MockSchedule()
        mock.id = None
        mock.section_id = int(section_id) if section_id else None
        mock.subject_id = int(proposed['subject_id']) if proposed.get('subject_id') else None
        mock.faculty_id = proposed['faculty_id']
        mock.room_id = proposed['room_id']
        mock.day_of_week = proposed['day_of_week']
        mock.start_time = start
        mock.end_time = end
        mock.schedule_type = proposed.get('schedule_type', 'lecture')
        mock.academic_year = settings.academic_year
        mock.semester = settings.semester
        mock.is_active = True
        return mock

    # ==================================================================
    # EXAM BATCH BUILDER
    # ==================================================================

    def generate_exam_batch_preview(self, section_id: int, curriculum_id: int = None,
                                     preferred_building_id: int = None) -> Dict:
        """
        Generate a batch exam preview for all unexamined subjects.
        Auto-assigns exam_date/time/room across the exam period, leaves faculty (proctor) blank.

        Returns:
            {
                'success': bool,
                'proposed': [ { subject, exam_date, start_time, end_time, room, faculty_id=null, ... } ],
                'unplaceable': [ { subject_code, reason } ],
                'section': { id, name },
                'stats': { total_subjects, already_examined, scheduled, unplaceable }
            }
        """
        from app.models.section import Section
        from app.models.settings import AcademicSettings
        from app.models.exam_schedule import ExamSchedule
        from app.models.building import Room
        from datetime import date as date_class

        section = Section.query.get(section_id)
        if not section:
            return {'success': False, 'error': 'Section not found'}

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return {'success': False, 'error': 'No active academic settings found'}

        # Validate exam period dates are configured
        exam_period_start = getattr(settings, 'exam_period_start', None)
        exam_period_end = getattr(settings, 'exam_period_end', None)
        if not exam_period_start or not exam_period_end:
            return {'success': False, 'error': 'Exam period dates are not configured in academic settings'}

        # 1. Get subjects for this section
        subjects = self._get_section_subjects(section, settings, curriculum_id=curriculum_id)
        if not subjects:
            return {'success': False, 'error': "No subjects found for this section's curriculum and semester"}

        # 2. Get already-examined subjects (returns set of (subject_id, schedule_type) tuples)
        already_examined_pairs = self._get_already_examined_subject_ids(
            section_id, settings.academic_year, settings.semester, settings.exam_period
        )

        # 3. Build exam slots: split subjects with lab units into lecture + lab entries
        exam_slots = []
        for s in subjects:
            lec_units = float(s.lec_units or 0)
            lab_units = float(s.lab_units or 0)

            if lec_units > 0 and (s.id, 'lecture') not in already_examined_pairs:
                exam_slots.append({'subject': s, 'schedule_type': 'lecture'})
            if lab_units > 0 and (s.id, 'lab') not in already_examined_pairs:
                exam_slots.append({'subject': s, 'schedule_type': 'lab'})
            # If no units specified, default to lecture
            if lec_units == 0 and lab_units == 0 and (s.id, 'lecture') not in already_examined_pairs:
                exam_slots.append({'subject': s, 'schedule_type': 'lecture'})

        already_examined_subject_ids = {pair[0] for pair in already_examined_pairs}

        if not exam_slots:
            # Build existing exam data so frontend can display them
            existing_exams_list = ExamSchedule.query.filter_by(
                section_id=section_id,
                academic_year=settings.academic_year,
                semester=settings.semester,
                exam_period=settings.exam_period,
                is_active=True
            ).all()
            existing_list = []
            for ex in existing_exams_list:
                subj = ex.subject
                fac = ex.faculty
                rm = ex.room
                existing_list.append({
                    'exam_schedule_id': ex.id,
                    'subject_id': ex.subject_id,
                    'subject_code': subj.subject_code if subj else '',
                    'course_description': subj.course_description if subj else '',
                    'schedule_type': ex.schedule_type or 'lecture',
                    'exam_date': ex.exam_date.strftime('%Y-%m-%d') if ex.exam_date else '',
                    'start_time': ex.start_time.strftime('%H:%M') if ex.start_time else '',
                    'end_time': ex.end_time.strftime('%H:%M') if ex.end_time else '',
                    'faculty_id': ex.faculty_id,
                    'faculty_name': f"{fac.last_name}, {fac.first_name}" if fac else '',
                    'room_id': ex.room_id,
                    'room_name': rm.room_number if rm else '',
                    'building_name': rm.building.building_name if rm and rm.building else '',
                    'is_existing': True
                })
            return {
                'success': True,
                'proposed': [],
                'unplaceable': [],
                'existing': existing_list,
                'section': {'id': section.id, 'name': section.full_section_name},
                'stats': {
                    'total_subjects': len(subjects),
                    'already_examined': len(already_examined_subject_ids),
                    'scheduled': 0,
                    'unplaceable': 0
                },
                'message': 'All subjects already have exams scheduled for this period.'
            }

        # 4. Sort alphabetically by subject code for predictable ordering
        exam_slots.sort(key=lambda x: (x['subject'].subject_code or '', x['schedule_type']))

        # 5. Load existing exam schedules for conflict checking
        existing_exams = ExamSchedule.query.filter_by(
            is_active=True,
            academic_year=settings.academic_year,
            semester=settings.semester,
            exam_period=settings.exam_period
        ).all()

        # 6. Run greedy exam placement
        proposed, unplaceable = self._greedy_place_exam_batch(
            section, exam_slots, existing_exams, settings,
            preferred_building_id=preferred_building_id
        )

        return {
            'success': True,
            'proposed': proposed,
            'unplaceable': unplaceable,
            'section': {'id': section.id, 'name': section.full_section_name},
            'stats': {
                'total_subjects': len(subjects),
                'already_examined': len(already_examined_subject_ids),
                'scheduled': len(proposed),
                'unplaceable': len(unplaceable)
            }
        }

    def get_unscheduled_exam_subjects(self, section_id: int, curriculum_id: int = None,
                                       include_all: bool = False) -> Dict:
        """Get subjects that don't yet have an exam for the current exam period.
        If include_all is True, returns ALL curriculum subjects (including already examined).
        """
        from app.models.section import Section
        from app.models.settings import AcademicSettings

        section = Section.query.get(section_id)
        if not section:
            return {'success': False, 'error': 'Section not found'}

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return {'success': False, 'error': 'No active academic settings found'}

        subjects = self._get_section_subjects(section, settings, curriculum_id=curriculum_id)
        if not subjects:
            return {'success': False, 'error': "No subjects found for this section's curriculum and semester"}

        already_examined_pairs = self._get_already_examined_subject_ids(
            section_id, settings.academic_year, settings.semester, settings.exam_period
        )

        # Build exam entries splitting subjects with lab units into lecture + lab
        subject_list = []
        for s in subjects:
            lec_units = float(s.lec_units or 0)
            lab_units = float(s.lab_units or 0)

            if lec_units > 0 and (include_all or (s.id, 'lecture') not in already_examined_pairs):
                subject_list.append({
                    'subject_id': s.id,
                    'subject_code': s.subject_code,
                    'course_description': s.course_description or '',
                    'lec_units': lec_units,
                    'lab_units': lab_units,
                    'total_units': float(s.total_units or 0),
                    'schedule_type': 'lecture',
                })
            if lab_units > 0 and (include_all or (s.id, 'lab') not in already_examined_pairs):
                subject_list.append({
                    'subject_id': s.id,
                    'subject_code': s.subject_code,
                    'course_description': s.course_description or '',
                    'lec_units': lec_units,
                    'lab_units': lab_units,
                    'total_units': float(s.total_units or 0),
                    'schedule_type': 'lab',
                })
            # If subject has no units specified, default to lecture
            if lec_units == 0 and lab_units == 0 and (include_all or (s.id, 'lecture') not in already_examined_pairs):
                subject_list.append({
                    'subject_id': s.id,
                    'subject_code': s.subject_code,
                    'course_description': s.course_description or '',
                    'lec_units': 0,
                    'lab_units': 0,
                    'total_units': float(s.total_units or 0),
                    'schedule_type': 'lecture',
                })

        already_examined_subject_ids = {pair[0] for pair in already_examined_pairs}

        return {
            'success': True,
            'subjects': subject_list,
            'all_subjects_count': len(subjects),
            'already_examined': len(already_examined_subject_ids),
            'section': {'id': section.id, 'name': section.full_section_name}
        }

    def confirm_exam_schedule(self, section_id: int, proposed_items: List[Dict],
                               user_id: int = None) -> Dict:
        """
        Validate and save confirmed exam schedule items to the database.
        Performs full conflict checking (section, faculty, room, duplicate) before saving.
        """
        from app.models.exam_schedule import ExamSchedule
        from app.models.settings import AcademicSettings
        from app.models.faculty import FacultySubjectAssignment

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return {'success': False, 'error': 'No active academic settings'}

        # Ensure section_id is an integer for reliable comparisons
        section_id = int(section_id)

        existing_exams = list(ExamSchedule.query.filter_by(
            is_active=True,
            academic_year=settings.academic_year,
            semester=settings.semester,
            exam_period=settings.exam_period
        ).all())

        created = 0
        updated = 0
        skipped = 0  # Already-scheduled subjects (from previous partial save or re-confirm)
        errors = []
        row_errors = []
        tentative = []  # Track confirmed rows for intra-batch conflicts

        for idx, item in enumerate(proposed_items):
            try:
                subject_code = item.get('subject_code', f'Row {idx+1}')
                faculty_id = item.get('faculty_id')
                room_id = item.get('room_id')
                exam_date_str = item.get('exam_date')
                start_time_str = item.get('start_time')
                end_time_str = item.get('end_time')
                exam_schedule_id = item.get('exam_schedule_id')

                existing_target_exam = None
                if exam_schedule_id not in (None, '', 'null', 'undefined'):
                    try:
                        exam_schedule_id = int(exam_schedule_id)
                    except (TypeError, ValueError):
                        row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'exam_schedule_id is invalid'})
                        continue

                    existing_target_exam = ExamSchedule.query.filter_by(
                        id=exam_schedule_id,
                        is_active=True,
                        academic_year=settings.academic_year,
                        semester=settings.semester,
                        exam_period=settings.exam_period
                    ).first()

                    if not existing_target_exam:
                        row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': f'Exam schedule #{exam_schedule_id} not found for active term'})
                        continue

                    if int(existing_target_exam.section_id) != int(section_id):
                        row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'Exam schedule does not belong to this section'})
                        continue

                # Validate required fields
                if not faculty_id:
                    row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'Proctor is required'})
                    continue
                if not room_id:
                    row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'Room is required'})
                    continue
                if not exam_date_str:
                    row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'Exam date is required'})
                    continue
                if not start_time_str or not end_time_str:
                    row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'Start and end time are required'})
                    continue

                faculty_id = int(faculty_id)
                room_id = int(room_id)
                exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
                start_time_val = datetime.strptime(start_time_str, '%H:%M').time()
                end_time_val = datetime.strptime(end_time_str, '%H:%M').time()

                if start_time_val >= end_time_val:
                    row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'End time must be after start time'})
                    continue

                exams_for_conflict = existing_exams
                if existing_target_exam:
                    exams_for_conflict = [ex for ex in existing_exams if int(getattr(ex, 'id', 0) or 0) != int(existing_target_exam.id)]

                all_exams = exams_for_conflict + tentative
                conflict_found = False
                item_schedule_type = item.get('schedule_type', 'lecture')
                item_subject_id = int(item.get('subject_id', 0)) if item.get('subject_id') else None

                # Duplicate check: same subject + same section + same schedule_type
                # For update rows, allow keeping the same record identity.
                if item_subject_id and not existing_target_exam:
                    for ex in all_exams:
                        ex_type = getattr(ex, 'schedule_type', 'lecture') or 'lecture'
                        ex_subject_id = int(ex.subject_id) if ex.subject_id else None
                        ex_section_id = int(ex.section_id) if ex.section_id else None
                        if (ex_subject_id == item_subject_id
                                and ex_section_id == section_id
                                and ex_type == item_schedule_type):
                            # Already scheduled — skip silently instead of erroring
                            skipped += 1
                            conflict_found = True
                            break

                if conflict_found:
                    continue

                # Section conflict (same section, same date, overlapping time)
                if self._has_exam_entity_conflict(section_id, 'section_id', exam_date, start_time_val, end_time_val, all_exams):
                    row_errors.append({
                        'row': idx + 1, 'subject_code': subject_code,
                        'error': f'Section conflict on {exam_date.strftime("%b %d")} {start_time_val.strftime("%I:%M %p")}-{end_time_val.strftime("%I:%M %p")}'
                    })
                    conflict_found = True

                # Faculty conflict
                if self._has_exam_entity_conflict(faculty_id, 'faculty_id', exam_date, start_time_val, end_time_val, all_exams):
                    row_errors.append({
                        'row': idx + 1, 'subject_code': subject_code,
                        'error': f'Proctor conflict on {exam_date.strftime("%b %d")} {start_time_val.strftime("%I:%M %p")}-{end_time_val.strftime("%I:%M %p")}'
                    })
                    conflict_found = True

                # Room conflict
                if self._has_exam_entity_conflict(room_id, 'room_id', exam_date, start_time_val, end_time_val, all_exams):
                    row_errors.append({
                        'row': idx + 1, 'subject_code': subject_code,
                        'error': f'Room conflict on {exam_date.strftime("%b %d")} {start_time_val.strftime("%I:%M %p")}-{end_time_val.strftime("%I:%M %p")}'
                    })
                    conflict_found = True

                if conflict_found:
                    continue

                subject_id = item.get('subject_id')
                if not subject_id:
                    row_errors.append({'row': idx + 1, 'subject_code': subject_code, 'error': 'Subject is required'})
                    continue

                if existing_target_exam:
                    existing_target_exam.subject_id = subject_id
                    existing_target_exam.faculty_id = faculty_id
                    existing_target_exam.room_id = room_id
                    existing_target_exam.exam_date = exam_date
                    existing_target_exam.start_time = start_time_val
                    existing_target_exam.end_time = end_time_val
                    existing_target_exam.schedule_type = item.get('schedule_type', 'lecture')
                    existing_target_exam.version = (existing_target_exam.version or 1) + 1
                    existing_target_exam.updated_at = datetime.utcnow()
                    db.session.flush()
                    existing_exams = [ex for ex in existing_exams if int(getattr(ex, 'id', 0) or 0) != int(existing_target_exam.id)]
                    updated += 1
                else:
                    # Check for soft-deleted exam in the same slot (uk_exam_section_slot)
                    existing_inactive_exam = ExamSchedule.query.filter_by(
                        section_id=section_id,
                        exam_date=exam_date,
                        start_time=start_time_val,
                        end_time=end_time_val,
                        academic_year=settings.academic_year,
                        semester=settings.semester,
                        exam_period=settings.exam_period,
                        is_active=False
                    ).first()

                    if existing_inactive_exam:
                        # Reactivate and update the soft-deleted exam schedule
                        existing_inactive_exam.subject_id = subject_id
                        existing_inactive_exam.faculty_id = faculty_id
                        existing_inactive_exam.room_id = room_id
                        existing_inactive_exam.schedule_type = item.get('schedule_type', 'lecture')
                        existing_inactive_exam.is_active = True
                        existing_inactive_exam.version = (existing_inactive_exam.version or 1) + 1
                        existing_inactive_exam.updated_at = datetime.utcnow()
                        db.session.flush()
                    else:
                        new_exam = ExamSchedule(
                            section_id=section_id,
                            subject_id=subject_id,
                            faculty_id=faculty_id,
                            room_id=room_id,
                            exam_date=exam_date,
                            start_time=start_time_val,
                            end_time=end_time_val,
                            academic_year=settings.academic_year,
                            semester=settings.semester,
                            exam_period=settings.exam_period,
                            schedule_type=item.get('schedule_type', 'lecture'),
                            is_active=True
                        )
                        db.session.add(new_exam)
                        db.session.flush()

                # Track as tentative for intra-batch detection
                mock = self._create_mock_exam(item, section_id, settings)
                mock.faculty_id = faculty_id
                mock.room_id = room_id
                tentative.append(mock)

                # Auto-create FacultySubjectAssignment
                if faculty_id and item.get('subject_id'):
                    existing_assignment = FacultySubjectAssignment.query.filter_by(
                        faculty_id=faculty_id,
                        subject_id=item['subject_id'],
                        academic_year=settings.academic_year,
                        semester=settings.semester
                    ).first()
                    if not existing_assignment:
                        assignment = FacultySubjectAssignment(
                            faculty_id=faculty_id,
                            subject_id=item['subject_id'],
                            academic_year=settings.academic_year,
                            semester=settings.semester,
                            is_active=True
                        )
                        db.session.add(assignment)

                if not existing_target_exam:
                    created += 1

            except Exception as e:
                errors.append({
                    'row': idx + 1,
                    'subject_code': item.get('subject_code', f'Row {idx+1}'),
                    'error': str(e)
                })

        if (created + updated) > 0:
            try:
                if user_id:
                    from app.models.activity_log import UserActivityLog
                    log = UserActivityLog(
                        user_id=user_id,
                        action='batch_exam_schedule',
                        entity_type='exam_schedule',
                        entity_id=section_id,
                        details=f'Batch exam save: created {created}, updated {updated} for section',
                        ip_address='system'
                    )
                    db.session.add(log)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return {'success': False, 'error': f'Database commit failed: {str(e)}'}
        else:
            db.session.rollback()

        result = {
            'success': (created + updated) > 0 or (skipped > 0 and len(row_errors) == 0 and len(errors) == 0),
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'errors': errors,
            'row_errors': row_errors
        }

        # Provide a summary error message when nothing new was saved
        if created == 0 and skipped == 0 and (row_errors or errors):
            all_issues = row_errors + errors
            first_err = all_issues[0].get('error', 'Unknown error')
            if len(all_issues) == 1:
                result['error'] = f'{all_issues[0].get("subject_code", "Row")}: {first_err}'
            else:
                result['error'] = f'{len(all_issues)} row(s) failed. First: {first_err}'
        elif created == 0 and skipped > 0 and (row_errors or errors):
            all_issues = row_errors + errors
            first_err = all_issues[0].get('error', 'Unknown error')
            result['error'] = f'{len(all_issues)} row(s) failed ({skipped} already scheduled). First: {first_err}'
        elif created == 0 and skipped > 0:
            result['message'] = f'All {skipped} exam(s) were already scheduled.'

        return result

    # ------------------------------------------------------------------
    # Exam Batch: Internal helpers
    # ------------------------------------------------------------------

    def _get_already_examined_subject_ids(self, section_id: int, academic_year: str,
                                           semester: str, exam_period: str) -> set:
        """Get subject IDs that already have exams for this section/period.
        
        Returns a set of (subject_id, schedule_type) tuples so that
        lecture and lab exams are tracked independently.
        """
        from app.models.exam_schedule import ExamSchedule

        existing = ExamSchedule.query.filter_by(
            section_id=section_id,
            academic_year=academic_year,
            semester=semester,
            exam_period=exam_period,
            is_active=True
        ).with_entities(ExamSchedule.subject_id, ExamSchedule.schedule_type).all()

        return {(row[0], row[1] or 'lecture') for row in existing}

    def _greedy_place_exam_batch(self, section, exam_slots: List[Dict], existing_exams: List,
                                  settings, preferred_building_id: int = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Greedy exam placement: finds date×time×room combos across the exam period.
        Faculty (proctor) is left blank for user to pick.
        Only checks section and room conflicts.

        Args:
            exam_slots: List of dicts with 'subject' (Subject obj) and 'schedule_type' ('lecture'/'lab').

        Sibling-sync rule: subjects shared by sections in the same year level
        and program are placed at the SAME date & time (different rooms).
        If a sibling section already has an exam for a subject, we reuse that
        date/time and only search for an available room.
        """
        from app.models.building import Room
        from app.models.section import Section as SectionModel
        from datetime import timedelta as td

        proposed = []
        unplaceable = []
        tentative = []

        exam_start_hour = (settings.exam_start_time.hour if settings.exam_start_time else 7)
        exam_end_hour = (settings.exam_end_time.hour if settings.exam_end_time else 17)
        exam_duration = settings.exam_duration_limit or 120  # minutes

        exam_period_start = settings.exam_period_start
        exam_period_end = settings.exam_period_end

        # Generate valid exam dates (weekdays only)
        exam_dates = []
        current_date = exam_period_start
        while current_date <= exam_period_end:
            if current_date.weekday() < 6:  # Mon-Sat (0-5)
                exam_dates.append(current_date)
            current_date += td(days=1)

        if not exam_dates:
            return [], [{'subject_id': slot['subject'].id, 'subject_code': slot['subject'].subject_code,
                         'course_description': slot['subject'].course_description or '',
                         'schedule_type': slot['schedule_type'],
                         'reason': 'No valid exam dates in configured period'}
                        for slot in exam_slots]

        # Generate time slots
        time_slots = self._generate_time_slots(exam_start_hour, exam_end_hour, exam_duration)
        if not time_slots:
            return [], [{'subject_id': slot['subject'].id, 'subject_code': slot['subject'].subject_code,
                         'course_description': slot['subject'].course_description or '',
                         'schedule_type': slot['schedule_type'],
                         'reason': 'No valid time slots in configured exam hours'}
                        for slot in exam_slots]

        # Load rooms - use lab rooms for lab exams, lecture rooms for lecture exams
        all_rooms = Room.query.filter_by(is_available=True).join(Room.building).all()
        lecture_rooms = [r for r in all_rooms if r.room_type == 'Lecture']
        lab_rooms = [r for r in all_rooms if r.room_type == 'Laboratory']
        if not lecture_rooms:
            lecture_rooms = all_rooms  # Fallback to any room
        if not lab_rooms:
            lab_rooms = all_rooms  # Fallback to any room

        # Sort rooms with preferred building first
        if preferred_building_id:
            lecture_rooms.sort(key=lambda r: (0 if r.building_id == preferred_building_id else 1, r.room_number))
            lab_rooms.sort(key=lambda r: (0 if r.building_id == preferred_building_id else 1, r.room_number))

        # ── Sibling-section sync ──────────────────────────────────────────
        # Find sibling sections (same program + same year level)
        sibling_sections = SectionModel.query.filter(
            SectionModel.program_id == section.program_id,
            SectionModel.year_level == section.year_level,
            SectionModel.id != section.id
        ).all()
        sibling_ids = {s.id for s in sibling_sections}

        # Build (subject_id, schedule_type) → (exam_date, start_time, end_time) lookup
        # from existing exams of sibling sections in the same academic period.
        sibling_slots = {}  # (subject_id, schedule_type) → (date, start_time, end_time)
        if sibling_ids:
            for ex in existing_exams:
                ex_type = getattr(ex, 'schedule_type', 'lecture') or 'lecture'
                key = (ex.subject_id, ex_type)
                if ex.section_id in sibling_ids and key not in sibling_slots:
                    sibling_slots[key] = (ex.exam_date, ex.start_time, ex.end_time)

        # Split exam_slots: anchored (sibling already scheduled) vs fresh
        anchored_slots = [slot for slot in exam_slots if (slot['subject'].id, slot['schedule_type']) in sibling_slots]
        fresh_slots = [slot for slot in exam_slots if (slot['subject'].id, slot['schedule_type']) not in sibling_slots]

        # ── Phase 1: Place anchored slots (reuse sibling date/time) ────
        for slot in anchored_slots:
            subject = slot['subject']
            schedule_type = slot['schedule_type']
            rooms = lab_rooms if schedule_type == 'lab' else lecture_rooms
            anchor_date, anchor_start, anchor_end = sibling_slots[(subject.id, schedule_type)]
            all_exams = existing_exams + tentative

            # Check section conflict at the anchor slot
            section_busy = self._has_exam_entity_conflict(
                section.id, 'section_id', anchor_date, anchor_start, anchor_end, all_exams
            )

            placed = False
            if not section_busy:
                # Find an available room at the anchor date/time
                for room in rooms:
                    if not self._has_exam_entity_conflict(
                        room.id, 'room_id', anchor_date, anchor_start, anchor_end, all_exams
                    ):
                        best = self._build_exam_candidate(
                            subject, room, anchor_date, anchor_start, anchor_end,
                            preferred_building_id=preferred_building_id,
                            schedule_type=schedule_type
                        )
                        proposed.append(best)
                        mock = self._create_mock_exam(best, section.id, settings)
                        tentative.append(mock)
                        placed = True
                        break

            if not placed:
                # Fallback: normal greedy search if anchor slot unavailable
                best = self._find_best_exam_slot(
                    section=section, subject=subject,
                    exam_dates=exam_dates, time_slots=time_slots,
                    rooms=rooms, existing_exams=existing_exams,
                    tentative=tentative, settings=settings,
                    preferred_building_id=preferred_building_id,
                    schedule_type=schedule_type
                )
                if best:
                    proposed.append(best)
                    mock = self._create_mock_exam(best, section.id, settings)
                    tentative.append(mock)
                else:
                    type_label = ' (Lab)' if schedule_type == 'lab' else ''
                    unplaceable.append({
                        'subject_id': subject.id,
                        'subject_code': subject.subject_code,
                        'course_description': (subject.course_description or '') + type_label,
                        'schedule_type': schedule_type,
                        'reason': 'No conflict-free date/time/room available'
                    })

        # ── Phase 2: Place fresh slots (normal greedy) ─────────────────
        for slot in fresh_slots:
            subject = slot['subject']
            schedule_type = slot['schedule_type']
            rooms = lab_rooms if schedule_type == 'lab' else lecture_rooms
            best = self._find_best_exam_slot(
                section=section,
                subject=subject,
                exam_dates=exam_dates,
                time_slots=time_slots,
                rooms=rooms,
                existing_exams=existing_exams,
                tentative=tentative,
                settings=settings,
                preferred_building_id=preferred_building_id,
                schedule_type=schedule_type
            )

            if best:
                proposed.append(best)
                mock = self._create_mock_exam(best, section.id, settings)
                tentative.append(mock)
            else:
                type_label = ' (Lab)' if schedule_type == 'lab' else ''
                unplaceable.append({
                    'subject_id': subject.id,
                    'subject_code': subject.subject_code,
                    'course_description': (subject.course_description or '') + type_label,
                    'schedule_type': schedule_type,
                    'reason': 'No conflict-free date/time/room available'
                })

        return proposed, unplaceable

    def _find_best_exam_slot(self, section, subject, exam_dates: List,
                              time_slots: List, rooms: List,
                              existing_exams: List, tentative: List,
                              settings, preferred_building_id: int = None,
                              schedule_type: str = 'lecture') -> Optional[Dict]:
        """
        Find best date×time×room combo for an exam. Uses section + room conflict checks.
        Scoring: earlier dates preferred, morning times preferred.
        If preferred_building_id is set, rooms from that building get a scoring bonus (+40).
        """
        # Scoring preferences
        DATE_ORDER_BONUS = 50  # decreases as dates go further
        all_exams = existing_exams + tentative

        best_candidate = None
        best_score = -1

        for date_idx, exam_date in enumerate(exam_dates):
            for slot_start, slot_end in time_slots:
                # Section conflict check (same section, same date, overlapping time)
                if self._has_exam_entity_conflict(section.id, 'section_id', exam_date,
                                                   slot_start, slot_end, all_exams):
                    continue

                for room in rooms:
                    # Room conflict check
                    if self._has_exam_entity_conflict(room.id, 'room_id', exam_date,
                                                      slot_start, slot_end, all_exams):
                        continue

                    # Score: earlier date + morning time + room type
                    score = max(0, DATE_ORDER_BONUS - date_idx * 2)
                    score += self.TIME_PREFERENCE.get(slot_start.hour, 50)
                    score += self.DAY_PREFERENCE.get(self._weekday_name(exam_date), 80)

                    # Lunch overlap penalty
                    lunch_start = getattr(settings, 'exam_lunch_start', None)
                    lunch_end = getattr(settings, 'exam_lunch_end', None)
                    if lunch_start and lunch_end:
                        if self._times_overlap(slot_start, slot_end, lunch_start, lunch_end):
                            score -= 30

                    # Preferred building bonus
                    if preferred_building_id and room.building_id == preferred_building_id:
                        score += 40

                    if score > best_score:
                        best_score = score
                        best_candidate = {
                            'subject_id': subject.id,
                            'subject_code': subject.subject_code,
                            'course_description': subject.course_description or '',
                            'faculty_id': None,
                            'faculty_name': '',
                            'room_id': room.id,
                            'room_name': room.room_number,
                            'room_type': room.room_type,
                            'building_name': room.building.building_name if room.building else '',
                            'exam_date': exam_date.strftime('%Y-%m-%d'),
                            'exam_date_display': exam_date.strftime('%b %d, %Y (%a)'),
                            'start_time': slot_start.strftime('%H:%M'),
                            'end_time': slot_end.strftime('%H:%M'),
                            'start_time_display': slot_start.strftime('%I:%M %p'),
                            'end_time_display': slot_end.strftime('%I:%M %p'),
                            'score': score,
                            'schedule_type': schedule_type,
                            'lec_units': float(subject.lec_units or 0),
                            'lab_units': float(subject.lab_units or 0),
                            'total_units': float(subject.total_units or 0)
                        }

        return best_candidate

    def _build_exam_candidate(self, subject, room, exam_date, start_time, end_time,
                               preferred_building_id: int = None,
                               schedule_type: str = 'lecture') -> Dict:
        """Build a proposed exam candidate dict (used by sibling-sync placement)."""
        from datetime import date as date_class
        score = 100  # anchored slots get a solid base score
        if preferred_building_id and room.building_id == preferred_building_id:
            score += 40

        if isinstance(exam_date, str):
            exam_date = datetime.strptime(exam_date, '%Y-%m-%d').date()

        return {
            'subject_id': subject.id,
            'subject_code': subject.subject_code,
            'course_description': subject.course_description or '',
            'faculty_id': None,
            'faculty_name': '',
            'room_id': room.id,
            'room_name': room.room_number,
            'room_type': room.room_type,
            'building_name': room.building.building_name if room.building else '',
            'exam_date': exam_date.strftime('%Y-%m-%d') if hasattr(exam_date, 'strftime') else str(exam_date),
            'exam_date_display': exam_date.strftime('%b %d, %Y (%a)') if hasattr(exam_date, 'strftime') else str(exam_date),
            'start_time': start_time.strftime('%H:%M') if hasattr(start_time, 'strftime') else str(start_time),
            'end_time': end_time.strftime('%H:%M') if hasattr(end_time, 'strftime') else str(end_time),
            'start_time_display': start_time.strftime('%I:%M %p') if hasattr(start_time, 'strftime') else str(start_time),
            'end_time_display': end_time.strftime('%I:%M %p') if hasattr(end_time, 'strftime') else str(end_time),
            'score': score,
            'schedule_type': schedule_type,
            'lec_units': float(subject.lec_units or 0),
            'lab_units': float(subject.lab_units or 0),
            'total_units': float(subject.total_units or 0)
        }

    @staticmethod
    def _weekday_name(d) -> str:
        """Convert a date to weekday name string."""
        names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return names[d.weekday()]

    def _has_exam_entity_conflict(self, entity_id, field: str, exam_date,
                                   start: time, end: time, exams: List) -> bool:
        """Check if entity (section/faculty/room) has an exam conflict on a given date/time."""
        for ex in exams:
            if getattr(ex, field, None) == entity_id and ex.exam_date == exam_date:
                if self._times_overlap(start, end, ex.start_time, ex.end_time):
                    return True
        return False

    def _create_mock_exam(self, proposed: Dict, section_id: int, settings) -> object:
        """Create a mock ExamSchedule object for intra-batch conflict detection."""
        start = proposed['start_time']
        end = proposed['end_time']
        exam_date = proposed.get('exam_date')

        if isinstance(start, str):
            start = datetime.strptime(start, '%H:%M').time()
        if isinstance(end, str):
            end = datetime.strptime(end, '%H:%M').time()
        if isinstance(exam_date, str):
            exam_date = datetime.strptime(exam_date, '%Y-%m-%d').date()

        class MockExam:
            pass

        mock = MockExam()
        mock.id = None
        mock.section_id = int(section_id) if section_id else None
        mock.subject_id = int(proposed['subject_id']) if proposed.get('subject_id') else None
        mock.faculty_id = proposed.get('faculty_id')
        mock.room_id = proposed.get('room_id')
        mock.exam_date = exam_date
        mock.start_time = start
        mock.end_time = end
        mock.academic_year = settings.academic_year
        mock.semester = settings.semester
        mock.exam_period = settings.exam_period
        mock.schedule_type = proposed.get('schedule_type', 'lecture')
        mock.is_active = True
        return mock

    def get_available_exam_rooms(self, exam_date_str: str, start_time_str: str,
                                  end_time_str: str,
                                  preferred_building_id: int = None) -> List[Dict]:
        """Get rooms available (no exam conflicts) at a specific date/time.

        Args:
            preferred_building_id: If provided, rooms from this building are listed first.
        """
        from app.models.building import Room
        from app.models.exam_schedule import ExamSchedule
        from app.models.settings import AcademicSettings

        settings = AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return []

        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
        start_time_val = datetime.strptime(start_time_str, '%H:%M').time()
        end_time_val = datetime.strptime(end_time_str, '%H:%M').time()

        existing_exams = ExamSchedule.query.filter_by(
            is_active=True,
            academic_year=settings.academic_year,
            semester=settings.semester,
            exam_period=settings.exam_period
        ).all()

        all_rooms = Room.query.filter_by(is_available=True).join(Room.building).all()

        rooms_with_status = []
        for room in all_rooms:
            conflict_exam = None
            for ex in existing_exams:
                if getattr(ex, 'room_id', None) == room.id and getattr(ex, 'exam_date', None) == exam_date:
                    if self._times_overlap(start_time_val, end_time_val, ex.start_time, ex.end_time):
                        conflict_exam = ex
                        break

            section_name = ''
            subject_code = ''
            conflict_start = ''
            conflict_end = ''
            occupied_note = ''
            if conflict_exam:
                if conflict_exam.section:
                    section_name = conflict_exam.section.full_section_name or conflict_exam.section.section_name or 'Unknown Section'
                else:
                    section_name = 'Unknown Section'
                subject_code = conflict_exam.subject.subject_code if conflict_exam.subject else 'Unknown Subject'
                conflict_start = conflict_exam.start_time.strftime('%H:%M') if conflict_exam.start_time else ''
                conflict_end = conflict_exam.end_time.strftime('%H:%M') if conflict_exam.end_time else ''
                occupied_note = f"Used by {section_name} ({subject_code})"

            rooms_with_status.append({
                'id': room.id,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'building_id': room.building_id,
                'building_name': room.building.building_name if room.building else '',
                'capacity': room.capacity if hasattr(room, 'capacity') else None,
                'is_occupied': bool(conflict_exam),
                'occupied_note': occupied_note,
                'occupied_by': {
                    'section_name': section_name,
                    'subject_code': subject_code,
                    'exam_date': conflict_exam.exam_date.strftime('%Y-%m-%d') if conflict_exam and conflict_exam.exam_date else '',
                    'start_time': conflict_start,
                    'end_time': conflict_end,
                } if conflict_exam else None
            })

        # Sort: preferred building first, then by room_number.
        if preferred_building_id:
            rooms_with_status.sort(key=lambda r: (0 if r['building_id'] == preferred_building_id else 1, r['is_occupied'], r['room_number']))
        else:
            rooms_with_status.sort(key=lambda r: (r['is_occupied'], r['room_number']))

        return rooms_with_status
