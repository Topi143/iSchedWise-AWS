"""
SmartScheduler Service — Backtracking with Constraint Propagation

Provides an optimised alternative to AutoScheduler's greedy placement.
Uses the same scoring, conflict-detection, and result format so the UI
needs only a one-line change to switch between modes.

Algorithm:
  1. Build all valid (day, time, room) candidates per subject-slot
  2. Sort subjects by Most Constrained Variable (fewest candidates first)
  3. Backtracking search with forward-checking:
     – For each candidate (best-score-first), check hard constraints
     – Forward-check: would this placement leave a future subject with 0 options?
     – If yes → prune; if no → place & recurse
     – On dead-end → backtrack (undo) and try next candidate
  4. Return best complete (or partial) solution found

Safety:
  – Hard timeout (TIMEOUT_SECONDS)
  – Per-subject backtrack limit (MAX_BACKTRACKS_PER_SUBJECT)
  – Global backtrack limit (MAX_TOTAL_BACKTRACKS)
  – Graceful fallback to greedy on timeout/failure
"""

import time as time_module
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple


class SmartScheduler:
    """Backtracking scheduler with constraint propagation.

    Wraps an existing AutoScheduler instance and reuses its scoring,
    conflict-checking, and data-loading helpers.
    """

    MAX_BACKTRACKS_PER_SUBJECT = 3
    MAX_TOTAL_BACKTRACKS = 50
    TIMEOUT_SECONDS = 30

    MIN_BACKTRACKS_PER_SUBJECT = 1
    MAX_BACKTRACKS_PER_SUBJECT_LIMIT = 20
    MIN_TOTAL_BACKTRACKS = 10
    MAX_TOTAL_BACKTRACKS_LIMIT = 500
    MIN_TIMEOUT_SECONDS = 5
    MAX_TIMEOUT_SECONDS = 120

    def __init__(self, auto_scheduler, settings=None):
        """
        Args:
            auto_scheduler: An initialised AutoScheduler instance.
            settings: Optional active AcademicSettings instance.
        """
        self.auto = auto_scheduler
        self.conflict_detector = auto_scheduler.conflict_detector
        self._active_settings = settings

        self.max_backtracks_per_subject = self.MAX_BACKTRACKS_PER_SUBJECT
        self.max_total_backtracks = self.MAX_TOTAL_BACKTRACKS
        self.timeout_seconds = self.TIMEOUT_SECONDS

        self._apply_limit_settings(settings)

    @staticmethod
    def _clamp_int(value, min_value: int, max_value: int, fallback: int) -> int:
        """Safely coerce int values and clamp to configured safety bounds."""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = fallback
        return max(min_value, min(max_value, parsed))

    def _apply_limit_settings(self, settings):
        """Load smart-solver limits from AcademicSettings with safety clamps."""
        if not settings:
            return

        self.max_backtracks_per_subject = self._clamp_int(
            getattr(settings, 'smart_max_backtracks_per_subject', None),
            self.MIN_BACKTRACKS_PER_SUBJECT,
            self.MAX_BACKTRACKS_PER_SUBJECT_LIMIT,
            self.MAX_BACKTRACKS_PER_SUBJECT
        )
        self.max_total_backtracks = self._clamp_int(
            getattr(settings, 'smart_max_total_backtracks', None),
            self.MIN_TOTAL_BACKTRACKS,
            self.MAX_TOTAL_BACKTRACKS_LIMIT,
            self.MAX_TOTAL_BACKTRACKS
        )
        self.timeout_seconds = self._clamp_int(
            getattr(settings, 'smart_timeout_seconds', None),
            self.MIN_TIMEOUT_SECONDS,
            self.MAX_TIMEOUT_SECONDS,
            self.TIMEOUT_SECONDS
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_smart_preview(self, section_id: int,
                               curriculum_id: int = None,
                               preferred_building_id: int = None) -> Dict:
        """Generate an optimised batch schedule using backtracking search.

        Returns the *same dict shape* as AutoScheduler.generate_batch_preview()
        so the UI/route doesn't need changes.
        """
        from app.models.section import Section
        from app.models.settings import AcademicSettings
        from app.models.schedule import Schedule
        from app.models.building import Room

        # ── 1. Load data (reuse AutoScheduler helpers) ────────────
        section = Section.query.get(section_id)
        if not section:
            return {'success': False, 'error': 'Section not found'}

        settings = self._active_settings or AcademicSettings.query.filter_by(is_active=True).first()
        if not settings:
            return {'success': False, 'error': 'No active academic settings found'}
        self._active_settings = settings
        self._apply_limit_settings(settings)

        subjects = self.auto._get_section_subjects(section, settings,
                                                   curriculum_id=curriculum_id)
        if not subjects:
            return {
                'success': False,
                'error': "No subjects found for this section's curriculum and semester"
            }

        already_scheduled_ids = self.auto._get_already_scheduled_subject_ids(
            section_id, settings.academic_year, settings.semester
        )
        unscheduled = [s for s in subjects if s.id not in already_scheduled_ids]
        existing_list = self.auto._serialize_existing_schedules(section_id, settings)

        if not unscheduled:
            return {
                'success': True,
                'proposed': [],
                'unplaceable': [],
                'existing': existing_list,
                'section': {'id': section.id, 'name': section.full_section_name},
                'stats': {
                    'total_subjects': len(subjects),
                    'already_scheduled': len(already_scheduled_ids),
                    'scheduled': 0,
                    'unplaceable': 0
                },
                'message': 'All subjects are already scheduled for this section.'
            }

        existing_schedules = Schedule.query.filter_by(
            is_active=True,
            academic_year=settings.academic_year,
            semester=settings.semester
        ).all()

        all_rooms = Room.query.filter_by(is_available=True).join(Room.building).all()

        start_hour = (settings.schedule_start_time.hour if settings.schedule_start_time else 7)
        end_hour = (settings.schedule_end_time.hour if settings.schedule_end_time else 20)
        days = settings.get_operation_days_list() if hasattr(settings, 'get_operation_days_list') else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        # ── 2. Build candidate lists per slot ─────────────────────
        slot_entries = self._build_candidates(
            section, unscheduled, existing_schedules, all_rooms,
            settings, days, start_hour, end_hour, preferred_building_id
        )

        if not slot_entries:
            # Nothing to schedule — fallback
            return self.auto.generate_batch_preview(
                section_id, curriculum_id=curriculum_id,
                preferred_building_id=preferred_building_id
            )

        # ── 3. Sort by MCV (fewest candidates first) ─────────────
        slot_entries.sort(key=lambda x: len(x['candidates']))

        # ── 4. Backtracking search ───────────────────────────────
        self._total_backtracks = 0
        start_time = time_module.time()

        solution = self._backtrack(
            slot_entries, 0, [], list(existing_schedules),
            section, settings, start_time
        )

        if solution is None:
            # Complete failure — fall back to greedy
            return self.auto.generate_batch_preview(
                section_id, curriculum_id=curriculum_id,
                preferred_building_id=preferred_building_id
            )

        # ── 5. Build result in same format as greedy ──────────────
        proposed = []
        placed_subject_slot_keys = set()
        for cand in solution:
            proposed.append(self._candidate_to_proposed(cand))
            placed_subject_slot_keys.add(
                (cand['subject'].id, cand['schedule_type'])
            )

        # Determine unplaceable (slots that weren't in solution)
        unplaceable = []
        for entry in slot_entries:
            key = (entry['subject'].id, entry['slot']['type'])
            if key not in placed_subject_slot_keys:
                unplaceable.append({
                    'subject_id': entry['subject'].id,
                    'subject_code': entry['subject'].subject_code,
                    'course_description': entry['subject'].course_description or '',
                    'schedule_type': entry['slot']['type'],
                    'reason': 'No conflict-free time slot available'
                })

        return {
            'success': True,
            'proposed': proposed,
            'unplaceable': unplaceable,
            'existing': existing_list,
            'section': {'id': section.id, 'name': section.full_section_name},
            'stats': {
                'total_subjects': len(subjects),
                'already_scheduled': len(already_scheduled_ids),
                'scheduled': len(proposed),
                'unplaceable': len(unplaceable)
            },
            'mode': 'smart'
        }

    # ------------------------------------------------------------------
    # Candidate enumeration
    # ------------------------------------------------------------------

    def _build_candidates(self, section, subjects, existing_schedules,
                          all_rooms, settings, days, start_hour, end_hour,
                          preferred_building_id):
        """For each subject-slot, enumerate all valid (day, time, room) candidates."""
        result = []
        time_slots_cache = {}  # duration → [(start, end), ...]

        for subj in subjects:
            slots_needed = self.auto._determine_slots_needed(subj)
            for slot in slots_needed:
                duration = slot['duration']
                schedule_type = slot['type']

                # Get matching rooms for this subject/type
                matching_rooms = self.auto._get_matching_rooms(subj, schedule_type, all_rooms)
                if not matching_rooms:
                    # No rooms at all → will be unplaceable regardless
                    result.append({
                        'subject': subj,
                        'slot': slot,
                        'candidates': []
                    })
                    continue

                # Generate time windows (cached by duration)
                if duration not in time_slots_cache:
                    time_slots_cache[duration] = self.auto._generate_time_slots(
                        start_hour, end_hour, duration
                    )
                time_windows = time_slots_cache[duration]

                candidates = []
                for day in days:
                    for slot_start, slot_end in time_windows:
                        # Section conflict — hard constraint
                        if self.auto._has_section_conflict(
                            section.id, day, slot_start, slot_end,
                            existing_schedules
                        ):
                            continue

                        for room in matching_rooms:
                            # Room conflict — hard constraint
                            if self.auto._has_entity_conflict(
                                room.id, 'room_id', day, slot_start, slot_end,
                                existing_schedules
                            ):
                                continue

                            # Score this placement
                            score = self._score_placement(
                                section, subj, schedule_type,
                                day, slot_start, slot_end, room,
                                existing_schedules, settings,
                                preferred_building_id
                            )

                            candidates.append({
                                'day': day,
                                'start': slot_start,
                                'end': slot_end,
                                'room': room,
                                'score': score,
                                'subject': subj,
                                'schedule_type': schedule_type,
                                'duration': duration
                            })

                # Sort best-score-first
                candidates.sort(key=lambda c: c['score'], reverse=True)

                result.append({
                    'subject': subj,
                    'slot': slot,
                    'candidates': candidates
                })

        return result

    # ------------------------------------------------------------------
    # Scoring (mirrors _find_best_slot_batch inline scoring logic)
    # ------------------------------------------------------------------

    def _score_placement(self, section, subject, schedule_type,
                         day, slot_start, slot_end, room,
                         all_schedules, settings, preferred_building_id):
        """Score a candidate using the same factors as the greedy placer."""

        score = 0

        # ── Time preference ───────────────────────────────────────
        score += self.auto.TIME_PREFERENCE.get(slot_start.hour, 50)

        # ── Day preference ────────────────────────────────────────
        score += self.auto.DAY_PREFERENCE.get(day, 60)

        # ── Day-balancing ─────────────────────────────────────────
        days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday']
        day_counts = {d: 0 for d in days_list}
        for s in all_schedules:
            if getattr(s, 'section_id', None) == section.id:
                d = getattr(s, 'day_of_week', None)
                if d in day_counts:
                    day_counts[d] += 1
        min_day_count = min(day_counts.values()) if day_counts else 0
        day_excess = day_counts.get(day, 0) - min_day_count
        score -= day_excess * 50

        # ── Break / gap scoring ───────────────────────────────────
        same_day = [
            s for s in all_schedules
            if getattr(s, 'section_id', None) == section.id
            and getattr(s, 'day_of_week', None) == day
        ]
        if same_day:
            min_gap = float('inf')
            for s in same_day:
                s_start = s.start_time
                s_end = s.end_time
                if slot_end <= s_start:
                    gap = (s_start.hour * 60 + s_start.minute) - \
                          (slot_end.hour * 60 + slot_end.minute)
                elif slot_start >= s_end:
                    gap = (slot_start.hour * 60 + slot_start.minute) - \
                          (s_end.hour * 60 + s_end.minute)
                else:
                    gap = 0
                if gap < min_gap:
                    min_gap = gap
            if min_gap == 0:
                score -= 200
            elif 0 < min_gap < 30:
                score -= 150
            elif 30 <= min_gap <= 60:
                score += 80
            elif 60 < min_gap <= 120:
                score += 40

        # ── Lunch overlap penalty ─────────────────────────────────
        lunch_start_t = time(12, 0)
        lunch_end_t = time(13, 0)
        if self.auto._times_overlap(slot_start, slot_end, lunch_start_t, lunch_end_t):
            score -= 60

        # ── Room type match bonus ─────────────────────────────────
        is_pe = self.auto._is_pe_subject(subject.subject_code,
                                         subject.course_description)
        if is_pe and room.room_type == 'Court/Gym':
            score += 30
        elif schedule_type == 'lab' and room.room_type == 'Laboratory':
            score += 30
        elif schedule_type == 'lecture' and room.room_type == 'Lecture':
            score += 20

        # ── Preferred building bonus ──────────────────────────────
        if preferred_building_id and room.building_id == preferred_building_id:
            score += 40

        return score

    # ------------------------------------------------------------------
    # Backtracking core
    # ------------------------------------------------------------------

    def _backtrack(self, slot_entries, idx, current_solution,
                   current_schedules, section, settings, start_time):
        """Recursive backtracking search with forward checking.

        Returns a list of placed candidates (solution) or None on total failure.
        If a subject cannot be placed it is skipped (partial solution is OK).
        """

        # Timeout check
        if time_module.time() - start_time > self.timeout_seconds:
            return current_solution if current_solution else None

        # Base case — all slots processed
        if idx >= len(slot_entries):
            return current_solution[:]

        entry = slot_entries[idx]
        backtracks_here = 0

        for candidate in entry['candidates']:
            # ── Hard constraint: conflict against current state ────
            if self._conflicts_with_current(candidate, current_schedules, section):
                continue

            # ── Forward check ─────────────────────────────────────
            if self._forward_check_fails(
                candidate, slot_entries, idx + 1,
                current_schedules, section
            ):
                backtracks_here += 1
                self._total_backtracks += 1
                if (backtracks_here >= self.max_backtracks_per_subject or
                    self._total_backtracks >= self.max_total_backtracks):
                    break
                continue

            # ── Place candidate ───────────────────────────────────
            mock = self._to_mock_schedule(candidate, section, settings)
            current_schedules.append(mock)
            current_solution.append(candidate)

            # Recurse
            result = self._backtrack(
                slot_entries, idx + 1, current_solution,
                current_schedules, section, settings, start_time
            )
            if result is not None:
                return result

            # Backtrack: undo
            current_schedules.pop()
            current_solution.pop()
            backtracks_here += 1
            self._total_backtracks += 1

            if (backtracks_here >= self.max_backtracks_per_subject or
                    self._total_backtracks >= self.max_total_backtracks):
                break

        # Could not place this slot — skip it and continue
        return self._backtrack(
            slot_entries, idx + 1, current_solution,
            current_schedules, section, settings, start_time
        )

    # ------------------------------------------------------------------
    # Forward checking
    # ------------------------------------------------------------------

    def _forward_check_fails(self, candidate, all_entries, next_idx,
                             current_schedules, section):
        """Return True if placing *candidate* makes any future slot impossible.

        This is the key optimisation: prune branches that lead to dead ends
        before actually exploring them.
        """
        mock = self._to_mock_schedule_light(candidate, section)
        test_schedules = current_schedules + [mock]

        for i in range(next_idx, len(all_entries)):
            future = all_entries[i]
            has_valid = False
            for fc in future['candidates']:
                if not self._conflicts_with_current(fc, test_schedules, section):
                    has_valid = True
                    break
            if not has_valid:
                return True  # Dead end detected
        return False

    # ------------------------------------------------------------------
    # Conflict helpers
    # ------------------------------------------------------------------

    def _conflicts_with_current(self, candidate, schedules, section):
        """Check if candidate conflicts with any already-placed schedule."""
        day = candidate['day']
        start = candidate['start']
        end = candidate['end']
        room = candidate['room']

        if self.auto._has_section_conflict(section.id, day, start, end, schedules):
            return True
        if self.auto._has_entity_conflict(room.id, 'room_id', day, start, end, schedules):
            return True
        return False

    # ------------------------------------------------------------------
    # Mock schedule helpers
    # ------------------------------------------------------------------

    def _to_mock_schedule(self, candidate, section, settings):
        """Full mock schedule (for use in solution building)."""
        proposed = {
            'subject_id': candidate['subject'].id,
            'faculty_id': None,
            'room_id': candidate['room'].id,
            'day_of_week': candidate['day'],
            'start_time': candidate['start'].strftime('%H:%M'),
            'end_time': candidate['end'].strftime('%H:%M'),
            'schedule_type': candidate['schedule_type']
        }
        return self.auto._create_mock_schedule(proposed, section.id, settings)

    def _to_mock_schedule_light(self, candidate, section):
        """Lightweight mock for forward-checking (no settings needed)."""
        class _Mock:
            pass
        m = _Mock()
        m.id = None
        m.section_id = section.id
        m.subject_id = candidate['subject'].id
        m.faculty_id = None
        m.room_id = candidate['room'].id
        m.day_of_week = candidate['day']
        m.start_time = candidate['start']
        m.end_time = candidate['end']
        m.schedule_type = candidate['schedule_type']
        m.is_active = True
        return m

    # ------------------------------------------------------------------
    # Result formatting
    # ------------------------------------------------------------------

    def _candidate_to_proposed(self, candidate):
        """Convert an internal candidate dict to the same shape as greedy output."""
        subj = candidate['subject']
        room = candidate['room']
        return {
            'subject_id': subj.id,
            'subject_code': subj.subject_code,
            'course_description': subj.course_description or '',
            'faculty_id': None,
            'faculty_name': '',
            'room_id': room.id,
            'room_name': room.room_number,
            'room_type': room.room_type,
            'building_name': room.building.building_name if room.building else '',
            'day_of_week': candidate['day'],
            'start_time': candidate['start'].strftime('%H:%M'),
            'end_time': candidate['end'].strftime('%H:%M'),
            'start_time_display': candidate['start'].strftime('%I:%M %p'),
            'end_time_display': candidate['end'].strftime('%I:%M %p'),
            'schedule_type': candidate['schedule_type'],
            'score': candidate['score'],
            'lec_units': float(subj.lec_units or 0),
            'lab_units': float(subj.lab_units or 0),
            'total_units': float(subj.total_units or 0)
        }
