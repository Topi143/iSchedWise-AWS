"""
Conflict Chain Resolver

Takes a list of detected conflicts and the current schedule form data,
generates a resolution plan by applying top recommendations sequentially
while checking for cascading conflicts.

Uses RecommendationEngine to generate alternatives, then simulates
each to find the minimal change set that eliminates all conflicts.
"""
from datetime import date, time, datetime, timedelta
from typing import Dict, List, Optional, Set
from app.services.conflict_detector import ConflictDetector, Conflict, ConflictType, ConflictSeverity
from app.services.recommendation_engine import RecommendationEngine


class ConflictResolver:
    """
    Resolves multiple schedule conflicts by finding optimal form field changes.

    Strategy priority (class schedules):
    1. Change time slot
    2. Change day
    3. Change room only
    4. Change faculty only
    5. Combined 2-field changes (room+faculty, time+room, time+faculty, day+room, day+faculty)
    6. Combined 3-field changes (time+room+faculty, day+room+faculty)
    7. Iterative fallback: apply best partial fix, re-run for remaining
    """

    MAX_OPTIONS_TO_TRY = 5  # Max alternatives to simulate per category
    MAX_COMBO_PER_AXIS = 3  # Max options per axis in combined strategies
    MAX_ITERATIONS = 3      # Max iterative resolution rounds

    def __init__(self):
        self.conflict_detector = ConflictDetector()
        self.recommendation_engine = RecommendationEngine()

    # ── Public API ────────────────────────────────────────────────

    def generate_resolution_plan(
        self,
        schedule_data: Dict,
        conflicts: List[Dict],
        existing_schedules: List,
        subject=None,
        exclude_schedule_id: Optional[int] = None
    ) -> Dict:
        """
        Generate a resolution plan for all detected conflicts.

        Returns:
            {
                'resolvable': [{conflict, resolution}, ...],
                'unresolvable': [{conflict, reason}, ...],
                'form_changes': {field: new_value, ...},
                'stats': {total_conflicts, auto_resolvable, needs_manual}
            }
        """
        if not conflicts:
            return self._empty_plan()

        conflict_dicts = [self._normalise_conflict(c) for c in conflicts]
        total = len(conflict_dicts)

        best = self._find_best_class_resolution(
            schedule_data, conflict_dicts, existing_schedules,
            subject, exclude_schedule_id
        )

        # ── Iterative fallback: apply partial fix, re-run ────────
        if best and best['remaining'] > 0:
            merged = dict(best)
            working_data = dict(schedule_data)
            for iteration in range(self.MAX_ITERATIONS):
                # Apply current best form_changes to a copy
                for k, v in merged['form_changes'].items():
                    if k.startswith('_'):
                        continue
                    if k in ('start_time', 'end_time'):
                        working_data[k] = self._parse_time(v)
                    else:
                        working_data[k] = v

                # Re-detect remaining conflicts
                remaining_conflicts = self.conflict_detector.detect_class_conflicts(
                    working_data, existing_schedules, exclude_schedule_id
                )
                remaining_crit = [
                    c for c in remaining_conflicts
                    if c.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.HIGH)
                ]
                if not remaining_crit:
                    merged['remaining'] = 0
                    break

                remaining_dicts = [c.to_dict() for c in remaining_crit]
                next_best = self._find_best_class_resolution(
                    working_data, remaining_dicts, existing_schedules,
                    subject, exclude_schedule_id
                )
                if not next_best or next_best['remaining'] >= len(remaining_crit):
                    break  # No further improvement

                # Merge form_changes and resolutions
                for k, v in next_best['form_changes'].items():
                    merged['form_changes'][k] = v
                merged['resolutions'].extend(next_best.get('resolutions', []))
                merged['remaining'] = next_best['remaining']
                if merged['remaining'] == 0:
                    break

        if best:
            return self._build_plan(best if not best.get('remaining') else merged, conflict_dicts)

        return {
            'resolvable': [],
            'unresolvable': [
                {'conflict': c, 'reason': 'No conflict-free alternative found within constraints'}
                for c in conflict_dicts
            ],
            'form_changes': {},
            'stats': {'total_conflicts': total, 'auto_resolvable': 0, 'needs_manual': total}
        }

    def generate_exam_resolution_plan(
        self,
        exam_data: Dict,
        conflicts: List[Dict],
        existing_exams: List,
        exclude_exam_id: Optional[int] = None
    ) -> Dict:
        """
        Generate a resolution plan for exam schedule conflicts.
        Similar to class resolution but uses exam-specific detection and fields.
        """
        if not conflicts:
            return self._empty_plan()

        conflict_dicts = [self._normalise_conflict(c) for c in conflicts]
        total = len(conflict_dicts)

        best = self._find_best_exam_resolution(
            exam_data, conflict_dicts, existing_exams, exclude_exam_id
        )

        # ── Iterative fallback ───────────────────────────────────
        if best and best['remaining'] > 0:
            merged = dict(best)
            working_data = dict(exam_data)
            for iteration in range(self.MAX_ITERATIONS):
                for k, v in merged['form_changes'].items():
                    if k.startswith('_'):
                        continue
                    if k in ('start_time', 'end_time'):
                        working_data[k] = self._parse_time(v)
                    elif k == 'exam_date':
                        working_data[k] = self._parse_date(v)
                    else:
                        working_data[k] = v

                remaining_conflicts = self.conflict_detector.detect_exam_conflicts(
                    working_data, existing_exams, exclude_exam_id
                )
                remaining_crit = [
                    c for c in remaining_conflicts
                    if c.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.HIGH)
                ]
                if not remaining_crit:
                    merged['remaining'] = 0
                    break

                remaining_dicts = [c.to_dict() for c in remaining_crit]
                next_best = self._find_best_exam_resolution(
                    working_data, remaining_dicts, existing_exams, exclude_exam_id
                )
                if not next_best or next_best['remaining'] >= len(remaining_crit):
                    break

                for k, v in next_best['form_changes'].items():
                    merged['form_changes'][k] = v
                merged['resolutions'].extend(next_best.get('resolutions', []))
                merged['remaining'] = next_best['remaining']
                if merged['remaining'] == 0:
                    break

        if best:
            return self._build_plan(best if not best.get('remaining') else merged, conflict_dicts)

        return {
            'resolvable': [],
            'unresolvable': [
                {'conflict': c, 'reason': 'No conflict-free alternative found within constraints'}
                for c in conflict_dicts
            ],
            'form_changes': {},
            'stats': {'total_conflicts': total, 'auto_resolvable': 0, 'needs_manual': total}
        }

    # ── Resolution search (class) ────────────────────────────────

    def _find_best_class_resolution(self, schedule_data, conflict_dicts,
                                     existing_schedules, subject,
                                     exclude_schedule_id):
        """Try all strategies and return best result for class schedules."""
        conflict_objs = self._dicts_to_conflict_objs(conflict_dicts)
        recommendations = self.recommendation_engine.generate_class_recommendations(
            schedule_data,
            conflict_objs,
            existing_schedules,
            subject,
            exclude_schedule_id=exclude_schedule_id
        )

        time_options = self._extract_options(recommendations, 'time_slot')
        day_options = self._extract_options(recommendations, 'day')
        room_options = self._extract_options(recommendations, 'room')
        faculty_options = self._extract_options(recommendations, 'faculty')

        best = None

        # Strategy 1: Single-field changes
        for strategy in [
            self._try_time_changes(schedule_data, conflict_dicts, existing_schedules, time_options, exclude_schedule_id),
            self._try_day_changes(schedule_data, conflict_dicts, existing_schedules, day_options, exclude_schedule_id),
            self._try_room_changes(schedule_data, conflict_dicts, existing_schedules, room_options, exclude_schedule_id),
            self._try_faculty_changes(schedule_data, conflict_dicts, existing_schedules, faculty_options, exclude_schedule_id),
        ]:
            best = self._try_better(best, strategy)
            if best and best['remaining'] == 0:
                return best

        # Strategy 2: All 2-field combinations
        two_field_combos = [
            (room_options, faculty_options, 'room_faculty'),
            (time_options, room_options, 'time_room'),
            (time_options, faculty_options, 'time_faculty'),
            (day_options, room_options, 'day_room'),
            (day_options, faculty_options, 'day_faculty'),
        ]
        for opts_a, opts_b, combo_type in two_field_combos:
            result = self._try_two_field_combo(
                schedule_data, conflict_dicts, existing_schedules,
                opts_a, opts_b, combo_type, exclude_schedule_id
            )
            best = self._try_better(best, result)
            if best and best['remaining'] == 0:
                return best

        # Strategy 3: 3-field combinations
        three_field_combos = [
            (time_options, room_options, faculty_options, 'time_room_faculty'),
            (day_options, room_options, faculty_options, 'day_room_faculty'),
        ]
        for opts_a, opts_b, opts_c, combo_type in three_field_combos:
            result = self._try_three_field_combo(
                schedule_data, conflict_dicts, existing_schedules,
                opts_a, opts_b, opts_c, combo_type, exclude_schedule_id
            )
            best = self._try_better(best, result)
            if best and best['remaining'] == 0:
                return best

        return best

    # ── Resolution search (exam) ─────────────────────────────────

    def _find_best_exam_resolution(self, exam_data, conflict_dicts,
                                    existing_exams, exclude_exam_id):
        """Try all strategies and return best result for exam schedules."""
        conflict_objs = self._dicts_to_conflict_objs(conflict_dicts)
        recommendations = self.recommendation_engine.generate_exam_recommendations(
            exam_data, conflict_objs, existing_exams
        )

        time_options = self._extract_options(recommendations, 'time_slot')
        date_options = self._extract_options(recommendations, 'date')
        room_options = self._extract_options(recommendations, 'room')
        faculty_options = self._extract_options(recommendations, 'faculty')

        best = None

        # Strategy 1: Single-field changes
        for strategy in [
            self._try_exam_time_changes(exam_data, conflict_dicts, existing_exams, time_options, exclude_exam_id),
            self._try_exam_date_changes(exam_data, conflict_dicts, existing_exams, date_options, exclude_exam_id),
            self._try_exam_room_changes(exam_data, conflict_dicts, existing_exams, room_options, exclude_exam_id),
            self._try_exam_faculty_changes(exam_data, conflict_dicts, existing_exams, faculty_options, exclude_exam_id),
        ]:
            best = self._try_better(best, strategy)
            if best and best['remaining'] == 0:
                return best

        # Strategy 2: 2-field combinations
        two_field_combos = [
            (room_options, faculty_options, 'room_faculty'),
            (time_options, room_options, 'time_room'),
            (time_options, faculty_options, 'time_faculty'),
            (date_options, room_options, 'date_room'),
            (date_options, faculty_options, 'date_faculty'),
        ]
        for opts_a, opts_b, combo_type in two_field_combos:
            result = self._try_exam_two_field_combo(
                exam_data, conflict_dicts, existing_exams,
                opts_a, opts_b, combo_type, exclude_exam_id
            )
            best = self._try_better(best, result)
            if best and best['remaining'] == 0:
                return best

        # Strategy 3: 3-field combinations
        three_field_combos = [
            (time_options, room_options, faculty_options, 'time_room_faculty'),
            (date_options, room_options, faculty_options, 'date_room_faculty'),
        ]
        for opts_a, opts_b, opts_c, combo_type in three_field_combos:
            result = self._try_exam_three_field_combo(
                exam_data, conflict_dicts, existing_exams,
                opts_a, opts_b, opts_c, combo_type, exclude_exam_id
            )
            best = self._try_better(best, result)
            if best and best['remaining'] == 0:
                return best

        return best

    # ── Single-change strategies (class) ──────────────────────────

    def _try_time_changes(self, schedule_data, conflict_dicts, existing_schedules,
                          options, exclude_id):
        """Try each alternative time slot, return best (prefer remaining==0)."""
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(schedule_data)
            test['start_time'] = self._parse_time(opt['start_time'])
            test['end_time'] = self._parse_time(opt['end_time'])
            remaining = self._count_real_conflicts(test, existing_schedules, exclude_id)
            if remaining == 0:
                return {
                    'remaining': 0,
                    'form_changes': {'start_time': opt['start_time'], 'end_time': opt['end_time']},
                    'resolutions': [self._make_resolution('change_time',
                        f"Change time to {opt.get('display', opt['start_time'] + ' - ' + opt['end_time'])}", opt)]
                }
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'start_time': opt['start_time'], 'end_time': opt['end_time']},
                    'resolutions': [self._make_resolution('change_time',
                        f"Change time to {opt.get('display', opt['start_time'] + ' - ' + opt['end_time'])}", opt)]
                }
        return best

    def _try_day_changes(self, schedule_data, conflict_dicts, existing_schedules,
                         options, exclude_id):
        """Try each alternative day, return best (prefer remaining==0)."""
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(schedule_data)
            test['day_of_week'] = opt['day']
            remaining = self._count_real_conflicts(test, existing_schedules, exclude_id)
            if remaining == 0:
                return {
                    'remaining': 0,
                    'form_changes': {'day_of_week': opt['day']},
                    'resolutions': [self._make_resolution('change_day',
                        f"Change day to {opt.get('display', opt['day'])}", opt)]
                }
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'day_of_week': opt['day']},
                    'resolutions': [self._make_resolution('change_day',
                        f"Change day to {opt.get('display', opt['day'])}", opt)]
                }
        return best

    def _try_room_changes(self, schedule_data, conflict_dicts, existing_schedules,
                          options, exclude_id):
        """Try each alternative room, return best (prefer remaining==0)."""
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(schedule_data)
            test['room_id'] = opt['room_id']
            remaining = self._count_real_conflicts(test, existing_schedules, exclude_id)
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'room_id': opt['room_id'], '_room_display': opt.get('display', '')},
                    'resolutions': [self._make_resolution('change_room',
                        f"Use {opt.get('display', 'Room ' + str(opt['room_id']))} instead", opt)]
                }
                if remaining == 0:
                    return best
        return best

    def _try_faculty_changes(self, schedule_data, conflict_dicts, existing_schedules,
                             options, exclude_id):
        """Try each alternative faculty, return best (prefer remaining==0)."""
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(schedule_data)
            test['faculty_id'] = opt['faculty_id']
            remaining = self._count_real_conflicts(test, existing_schedules, exclude_id)
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'faculty_id': opt['faculty_id'], '_faculty_display': opt.get('display', '')},
                    'resolutions': [self._make_resolution('change_faculty',
                        f"Assign to {opt.get('display', 'Faculty #' + str(opt['faculty_id']))}", opt)]
                }
                if remaining == 0:
                    return best
        return best

    # ── Single-change strategies (exam) ───────────────────────────

    def _try_exam_time_changes(self, exam_data, conflict_dicts, existing_exams,
                               options, exclude_id):
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(exam_data)
            test['start_time'] = self._parse_time(opt['start_time'])
            test['end_time'] = self._parse_time(opt['end_time'])
            remaining = self._count_exam_conflicts(test, existing_exams, exclude_id)
            if remaining == 0:
                return {
                    'remaining': 0,
                    'form_changes': {'start_time': opt['start_time'], 'end_time': opt['end_time']},
                    'resolutions': [self._make_resolution('change_time',
                        f"Change time to {opt.get('display', opt['start_time'] + ' - ' + opt['end_time'])}", opt)]
                }
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'start_time': opt['start_time'], 'end_time': opt['end_time']},
                    'resolutions': [self._make_resolution('change_time',
                        f"Change time to {opt.get('display', opt['start_time'] + ' - ' + opt['end_time'])}", opt)]
                }
        return best

    def _try_exam_date_changes(self, exam_data, conflict_dicts, existing_exams,
                               options, exclude_id):
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(exam_data)
            date_val = opt.get('date') or opt.get('exam_date', '')
            test['exam_date'] = self._parse_date(date_val)
            remaining = self._count_exam_conflicts(test, existing_exams, exclude_id)
            if remaining == 0:
                return {
                    'remaining': 0,
                    'form_changes': {'exam_date': date_val},
                    'resolutions': [self._make_resolution('change_date',
                        f"Change date to {opt.get('display', date_val)}", opt)]
                }
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'exam_date': date_val},
                    'resolutions': [self._make_resolution('change_date',
                        f"Change date to {opt.get('display', date_val)}", opt)]
                }
        return best

    def _try_exam_room_changes(self, exam_data, conflict_dicts, existing_exams,
                               options, exclude_id):
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(exam_data)
            test['room_id'] = opt['room_id']
            remaining = self._count_exam_conflicts(test, existing_exams, exclude_id)
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'room_id': opt['room_id'], '_room_display': opt.get('display', '')},
                    'resolutions': [self._make_resolution('change_room',
                        f"Use {opt.get('display', 'Room ' + str(opt['room_id']))} instead", opt)]
                }
                if remaining == 0:
                    return best
        return best

    def _try_exam_faculty_changes(self, exam_data, conflict_dicts, existing_exams,
                                  options, exclude_id):
        best = None
        for opt in options[:self.MAX_OPTIONS_TO_TRY]:
            test = dict(exam_data)
            test['faculty_id'] = opt['faculty_id']
            remaining = self._count_exam_conflicts(test, existing_exams, exclude_id)
            original = len(conflict_dicts)
            if original - remaining > 0 and (not best or remaining < best['remaining']):
                best = {
                    'remaining': remaining,
                    'form_changes': {'faculty_id': opt['faculty_id'], '_faculty_display': opt.get('display', '')},
                    'resolutions': [self._make_resolution('change_faculty',
                        f"Assign to {opt.get('display', 'Faculty #' + str(opt['faculty_id']))}", opt)]
                }
                if remaining == 0:
                    return best
        return best

    # ── 2-field combination strategies ────────────────────────────

    def _apply_combo_fields(self, base_data, opt_a, opt_b, combo_type, is_exam=False):
        """Apply two option dicts to a copy of schedule data based on combo_type."""
        test = dict(base_data)
        form_changes = {}
        resolutions = []
        field_map = self._combo_field_map(is_exam)

        for opt, axis in [(opt_a, combo_type.split('_')[0]), (opt_b, combo_type.split('_')[1])]:
            cfg = field_map.get(axis)
            if not cfg:
                continue
            for fk, ok in cfg['fields'].items():
                val = opt.get(ok)
                if val is not None:
                    if fk in ('start_time', 'end_time'):
                        test[fk] = self._parse_time(val)
                    elif fk == 'exam_date':
                        test[fk] = self._parse_date(val)
                    else:
                        test[fk] = val
                    form_changes[fk] = val
            # Display keys
            for dk in cfg.get('display_keys', []):
                form_changes[dk] = opt.get('display', '')
            resolutions.append(self._make_resolution(
                cfg['action'], cfg['desc_fn'](opt), opt))

        return test, form_changes, resolutions

    def _try_two_field_combo(self, schedule_data, conflict_dicts, existing_schedules,
                             opts_a, opts_b, combo_type, exclude_id):
        best = None
        limit = self.MAX_COMBO_PER_AXIS
        for a in opts_a[:limit]:
            for b in opts_b[:limit]:
                test, form_changes, resolutions = self._apply_combo_fields(
                    schedule_data, a, b, combo_type, is_exam=False)
                remaining = self._count_real_conflicts(test, existing_schedules, exclude_id)
                original = len(conflict_dicts)
                if original - remaining > 0 and (not best or remaining < best['remaining']):
                    best = {'remaining': remaining, 'form_changes': form_changes, 'resolutions': resolutions}
                    if remaining == 0:
                        return best
        return best

    def _try_exam_two_field_combo(self, exam_data, conflict_dicts, existing_exams,
                                  opts_a, opts_b, combo_type, exclude_id):
        best = None
        limit = self.MAX_COMBO_PER_AXIS
        for a in opts_a[:limit]:
            for b in opts_b[:limit]:
                test, form_changes, resolutions = self._apply_combo_fields(
                    exam_data, a, b, combo_type, is_exam=True)
                remaining = self._count_exam_conflicts(test, existing_exams, exclude_id)
                original = len(conflict_dicts)
                if original - remaining > 0 and (not best or remaining < best['remaining']):
                    best = {'remaining': remaining, 'form_changes': form_changes, 'resolutions': resolutions}
                    if remaining == 0:
                        return best
        return best

    # ── 3-field combination strategies ────────────────────────────

    def _try_three_field_combo(self, schedule_data, conflict_dicts, existing_schedules,
                               opts_a, opts_b, opts_c, combo_type, exclude_id):
        best = None
        limit = self.MAX_COMBO_PER_AXIS
        parts = combo_type.split('_')  # e.g. ['time','room','faculty']
        field_map = self._combo_field_map(is_exam=False)
        for a in opts_a[:limit]:
            for b in opts_b[:limit]:
                for c in opts_c[:limit]:
                    test = dict(schedule_data)
                    form_changes = {}
                    resolutions = []
                    for opt, axis in [(a, parts[0]), (b, parts[1]), (c, parts[2])]:
                        cfg = field_map.get(axis)
                        if not cfg:
                            continue
                        for fk, ok in cfg['fields'].items():
                            val = opt.get(ok)
                            if val is not None:
                                test[fk] = self._parse_time(val) if fk in ('start_time', 'end_time') else val
                                form_changes[fk] = val
                        for dk in cfg.get('display_keys', []):
                            form_changes[dk] = opt.get('display', '')
                        resolutions.append(self._make_resolution(cfg['action'], cfg['desc_fn'](opt), opt))
                    remaining = self._count_real_conflicts(test, existing_schedules, exclude_id)
                    original = len(conflict_dicts)
                    if original - remaining > 0 and (not best or remaining < best['remaining']):
                        best = {'remaining': remaining, 'form_changes': form_changes, 'resolutions': resolutions}
                        if remaining == 0:
                            return best
        return best

    def _try_exam_three_field_combo(self, exam_data, conflict_dicts, existing_exams,
                                    opts_a, opts_b, opts_c, combo_type, exclude_id):
        best = None
        limit = self.MAX_COMBO_PER_AXIS
        parts = combo_type.split('_')
        field_map = self._combo_field_map(is_exam=True)
        for a in opts_a[:limit]:
            for b in opts_b[:limit]:
                for c in opts_c[:limit]:
                    test = dict(exam_data)
                    form_changes = {}
                    resolutions = []
                    for opt, axis in [(a, parts[0]), (b, parts[1]), (c, parts[2])]:
                        cfg = field_map.get(axis)
                        if not cfg:
                            continue
                        for fk, ok in cfg['fields'].items():
                            val = opt.get(ok)
                            if val is not None:
                                if fk in ('start_time', 'end_time'):
                                    test[fk] = self._parse_time(val)
                                elif fk == 'exam_date':
                                    test[fk] = self._parse_date(val)
                                else:
                                    test[fk] = val
                                form_changes[fk] = val
                        for dk in cfg.get('display_keys', []):
                            form_changes[dk] = opt.get('display', '')
                        resolutions.append(self._make_resolution(cfg['action'], cfg['desc_fn'](opt), opt))
                    remaining = self._count_exam_conflicts(test, existing_exams, exclude_id)
                    original = len(conflict_dicts)
                    if original - remaining > 0 and (not best or remaining < best['remaining']):
                        best = {'remaining': remaining, 'form_changes': form_changes, 'resolutions': resolutions}
                        if remaining == 0:
                            return best
        return best

    # ── Combo field mapping ───────────────────────────────────────

    @staticmethod
    def _combo_field_map(is_exam=False):
        """Return a mapping from axis name to field config for combos."""
        m = {
            'time': {
                'fields': {'start_time': 'start_time', 'end_time': 'end_time'},
                'display_keys': [],
                'action': 'change_time',
                'desc_fn': lambda o: f"Change time to {o.get('display', o.get('start_time', '') + ' - ' + o.get('end_time', ''))}"
            },
            'room': {
                'fields': {'room_id': 'room_id'},
                'display_keys': ['_room_display'],
                'action': 'change_room',
                'desc_fn': lambda o: f"Use {o.get('display', 'Room ' + str(o.get('room_id', '')))}"
            },
            'faculty': {
                'fields': {'faculty_id': 'faculty_id'},
                'display_keys': ['_faculty_display'],
                'action': 'change_faculty',
                'desc_fn': lambda o: f"Assign to {o.get('display', 'Faculty #' + str(o.get('faculty_id', '')))}"
            },
        }
        if is_exam:
            m['date'] = {
                'fields': {'exam_date': 'date'},
                'display_keys': [],
                'action': 'change_date',
                'desc_fn': lambda o: f"Change date to {o.get('display', o.get('date', o.get('exam_date', '')))}"
            }
            m['day'] = m['date']  # alias for combo_type parsing
        else:
            m['day'] = {
                'fields': {'day_of_week': 'day'},
                'display_keys': [],
                'action': 'change_day',
                'desc_fn': lambda o: f"Change day to {o.get('display', o.get('day', ''))}"
            }
        return m

    # ── Helpers ────────────────────────────────────────────────────

    def _count_real_conflicts(self, schedule_data, existing_schedules, exclude_id):
        """Run ConflictDetector and return count of CRITICAL/HIGH conflicts."""
        conflicts = self.conflict_detector.detect_class_conflicts(
            schedule_data, existing_schedules, exclude_id
        )
        return sum(
            1 for c in conflicts
            if c.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.HIGH)
        )

    def _count_exam_conflicts(self, exam_data, existing_exams, exclude_id):
        """Run ConflictDetector for exams and return count of CRITICAL/HIGH."""
        conflicts = self.conflict_detector.detect_exam_conflicts(
            exam_data, existing_exams, exclude_id
        )
        return sum(
            1 for c in conflicts
            if c.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.HIGH)
        )

    @staticmethod
    def _make_resolution(action, description, opt):
        return {
            'action': action,
            'description': description,
            'confidence': opt.get('confidence', opt.get('score', 50)),
            'details': opt
        }

    def _build_plan(self, result, conflict_dicts):
        """Convert an internal result dict into the public plan format."""
        total = len(conflict_dicts)
        form_changes = result.get('form_changes', {})
        actionable_change_count = sum(1 for key in form_changes.keys() if not str(key).startswith('_'))

        dedup_map = {}
        for res in result.get('resolutions', []):
            action = res.get('action', 'change')
            description = res.get('description', 'Change')
            dedup_key = f"{action}|{description}"
            if dedup_key not in dedup_map:
                dedup_map[dedup_key] = {
                    'resolution': {
                        'action': action,
                        'description': description,
                        'confidence': res.get('confidence', 50),
                        'details': res.get('details', {})
                    },
                    'affected_conflicts': 1
                }
            else:
                dedup_map[dedup_key]['affected_conflicts'] += 1

        resolvable = list(dedup_map.values())

        unresolvable = []
        if result['remaining'] > 0:
            # We can't pinpoint which specific conflicts remain without
            # re-running detection, so give a generic message
            unresolvable.append({
                'conflict': {'type': 'remaining', 'message': f"{result['remaining']} conflict(s) still need manual resolution"},
                'reason': 'Could not be resolved automatically with available alternatives'
            })

        return {
            'resolvable': resolvable,
            'unresolvable': unresolvable,
            'form_changes': form_changes,
            'stats': {
                'total_conflicts': total,
                'auto_resolvable': actionable_change_count,
                'needs_manual': result['remaining']
            }
        }

    def _empty_plan(self):
        return {
            'resolvable': [],
            'unresolvable': [],
            'form_changes': {},
            'stats': {'total_conflicts': 0, 'auto_resolvable': 0, 'needs_manual': 0}
        }

    @staticmethod
    def _parse_time(t):
        """Parse a time string 'HH:MM' into a datetime.time object."""
        if isinstance(t, time):
            return t
        return datetime.strptime(t, '%H:%M').time()

    @staticmethod
    def _parse_date(d):
        """Parse a date string 'YYYY-MM-DD' into a datetime.date object."""
        if isinstance(d, date):
            return d
        return datetime.strptime(d, '%Y-%m-%d').date()

    @staticmethod
    def _normalise_conflict(c):
        """Ensure conflict is a plain dict."""
        if isinstance(c, dict):
            return c
        if hasattr(c, 'to_dict'):
            return c.to_dict()
        return {'type': str(c), 'message': str(c)}

    @staticmethod
    def _dicts_to_conflict_objs(conflict_dicts):
        """Convert conflict dicts back to Conflict objects for RecommendationEngine."""
        objs = []
        type_map = {v.value: v for v in ConflictType}
        severity_map = {v.value: v for v in ConflictSeverity}

        for cd in conflict_dicts:
            ctype = type_map.get(cd.get('type', ''), ConflictType.SECTION)
            csev = severity_map.get(cd.get('severity', ''), ConflictSeverity.HIGH)
            objs.append(Conflict(
                type=ctype,
                severity=csev,
                message=cd.get('message', ''),
                details=cd.get('details', {}),
                conflicting_schedule_id=cd.get('conflicting_schedule_id')
            ))
        return objs

    @staticmethod
    def _get_conflict_types(conflict_dicts):
        """Get set of conflict type strings from list of conflict dicts."""
        return set(c.get('type', '') for c in conflict_dicts)

    @staticmethod
    def _try_better(current_best, candidate):
        """Return whichever result resolves more conflicts."""
        if candidate is None:
            return current_best
        if current_best is None:
            return candidate
        if candidate['remaining'] < current_best['remaining']:
            return candidate
        return current_best

    @staticmethod
    def _extract_options(recommendations, rec_type):
        """Extract option lists from Recommendation objects by type."""
        for rec in recommendations:
            if rec.type == rec_type and rec.options:
                return rec.options
        return []


class ResolutionApplier:
    """
    Applies a confirmed resolution plan to the database.
    Used when resolving conflicts for an EXISTING schedule (edit mode).
    Runs in a single transaction — all succeed or all roll back.
    """

    @staticmethod
    def apply_plan(resolution_plan: Dict, schedule_id: int,
                   user_id: int = None) -> Dict:
        """
        Apply form_changes from a resolution plan to an existing schedule.

        Args:
            resolution_plan: Plan dict from ConflictResolver.generate_resolution_plan()
            schedule_id: ID of the schedule to update
            user_id: Current user ID for activity logging

        Returns:
            {'success': bool, 'applied': int, 'errors': [...]}
        """
        from app.extensions import db
        from app.models.schedule import Schedule

        form_changes = resolution_plan.get('form_changes', {})
        if not form_changes or not schedule_id:
            return {'success': False, 'applied': 0, 'errors': ['No changes to apply']}

        try:
            schedule = Schedule.query.get(schedule_id)
            if not schedule:
                return {'success': False, 'applied': 0, 'errors': [f'Schedule {schedule_id} not found']}

            changes_made = 0

            if 'start_time' in form_changes:
                schedule.start_time = ConflictResolver._parse_time(form_changes['start_time'])
                changes_made += 1
            if 'end_time' in form_changes:
                schedule.end_time = ConflictResolver._parse_time(form_changes['end_time'])
                changes_made += 1
            if 'day_of_week' in form_changes:
                schedule.day_of_week = form_changes['day_of_week']
                changes_made += 1
            if 'room_id' in form_changes:
                schedule.room_id = form_changes['room_id']
                changes_made += 1
            if 'faculty_id' in form_changes:
                schedule.faculty_id = form_changes['faculty_id']
                changes_made += 1

            if changes_made == 0:
                return {'success': False, 'applied': 0, 'errors': ['No applicable field changes']}

            schedule.updated_at = datetime.utcnow()
            schedule.version = (schedule.version or 1) + 1

            # Activity log
            if user_id:
                from app.models.activity_log import UserActivityLog
                applied_count = resolution_plan.get('stats', {}).get('auto_resolvable', changes_made)
                log = UserActivityLog(
                    user_id=user_id,
                    action='auto_resolve_conflicts',
                    entity_type='schedule',
                    entity_id=schedule_id,
                    details=f'Auto-resolved {applied_count} conflict(s) for schedule #{schedule_id}',
                    ip_address=''
                )
                db.session.add(log)

            db.session.commit()
            return {'success': True, 'applied': changes_made, 'errors': []}

        except Exception as e:
            db.session.rollback()
            return {'success': False, 'applied': 0, 'errors': [str(e)]}


# Global instance
conflict_resolver = ConflictResolver()
