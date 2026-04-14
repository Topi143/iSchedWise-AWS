# iSchedWise V4: Scheduling Algorithms and Process Flows

This document explains the actual algorithms and process flows used in iSchedWise V4 for class scheduling, exam scheduling, conflict handling, recommendations, exports, and automated backups.

## 1) Scope and Source Files

Main implementation files covered:

- `app/services/auto_scheduler.py`
- `app/services/smart_scheduler.py`
- `app/services/conflict_detector.py`
- `app/services/conflict_resolver.py`
- `app/services/recommendation_engine.py`
- `app/ai_scheduler.py`
- `app/routes/schedule.py`
- `app/routes/exam_schedule.py`
- `app/services/auto_backup_scheduler.py`
- `app/services/database_backup_service.py`

## 2) Core Conflict Detection Algorithm

### 2.1 Time overlap rule

Used consistently in class and exam conflict checks:

- Overlap condition: `start1 < end2 AND end1 > start2`

Implemented in:

- `ConflictDetector.times_overlap` (`app/services/conflict_detector.py`)
- `AutoScheduler._times_overlap` (`app/services/auto_scheduler.py`)
- Route-level SQL overlap filters in add/edit endpoints (`app/routes/schedule.py`, `app/routes/exam_schedule.py`)

### 2.2 Conflict categories and severity

Implemented enum types:

- Types: `duplicate`, `section`, `faculty`, `room`, `time_invalid`, `date_past`, `workload`, `proctor_unavailable`
- Severity: `critical`, `high`, `medium`, `low`

Conflict detection functions:

- `detect_class_conflicts(...)`
- `detect_exam_conflicts(...)`
- `preview_slot_conflicts(...)`

File:

- `app/services/conflict_detector.py`

## 3) Manual Class Scheduling Process (Create/Edit)

Endpoint path:

- `POST /schedule/add`
- `POST /schedule/edit`

Route file:

- `app/routes/schedule.py`

Algorithm and validation sequence:

1. Parse and validate required fields.
2. Parse start/end time and verify `start < end`.
3. Check configured schedule window (`schedule_start_time` to `schedule_end_time`).
4. Query section conflicts (same section, same day, overlapping time).
5. Query faculty conflicts (same faculty, same day, overlapping time).
6. Query room conflicts (same room, same day, overlapping time).
7. Faculty availability check (warning-only when `not_in_schedule`).
8. Reactivate soft-deleted row if same slot exists, else insert new row.
9. Auto-create `FacultySubjectAssignment` if missing.
10. Log activity and broadcast real-time updates.

Concurrency behavior:

- Uses pessimistic locks (`with_for_update`) in create flow for slot/faculty/room conflict checks.
- Uses optimistic version check and edit lock handling in update flow.

## 4) Manual Exam Scheduling Process (Create/Edit)

Endpoint path:

- `POST /exam-schedule/add`
- `POST /exam-schedule/edit`

Route file:

- `app/routes/exam_schedule.py`

Algorithm and validation sequence:

1. Parse and validate required fields.
2. Validate exam date is not in the past.
3. Validate exam date within configured `exam_period_start` to `exam_period_end`.
4. Validate `start < end` and configured exam time window.
5. Warn if lunch overlap.
6. Warn if duration exceeds `exam_duration_limit`.
7. Query section conflict (same section, same date, overlapping time).
8. Query faculty conflict (same date/time overlap).
9. Query room conflict (same date/time overlap).
10. Proctor availability check:
   - `unavailable` -> blocking error
   - `not_in_schedule` -> warning
11. Reactivate soft-deleted record if same unique slot exists, else insert.
12. Log and broadcast.

Concurrency behavior:

- Uses pessimistic locking (`with_for_update`) during create conflict checks.
- Uses optimistic version checks and row lock in edit flow.

## 5) Batch Class Auto-Scheduling Algorithms

Main service:

- `AutoScheduler` in `app/services/auto_scheduler.py`

Main route:

- `POST /schedule/batch-generate` in `app/routes/schedule.py`

### 5.1 Slot derivation per subject

Function:

- `_determine_slots_needed(subject)`

Behavior:

- Splits each subject into lecture/lab schedule slots depending on `lec_units` and `lab_units`.
- Uses duration logic per slot type (lecture/lab and mixed cases).

### 5.2 Greedy batch placer (Quick mode)

Functions:

- `_greedy_place_batch(...)`
- `_find_best_slot_batch(...)`

High-level algorithm:

1. Collect unscheduled slots.
2. Sort subjects by `total_units` descending (heavier first).
3. For each slot, enumerate candidate day/time/room combinations.
4. Apply hard constraints:
   - section overlap
   - room overlap
5. Score candidates and choose highest score.
6. Add chosen placement to tentative list so next rows see new constraints.

Scoring factors used in code:

- Time preference (`TIME_PREFERENCE` map)
- Day preference (`DAY_PREFERENCE` map)
- Day balancing (penalty for overloaded days)
- Gap/break scoring (penalties for too-short gaps, bonuses for ideal gaps)
- Lunch overlap penalty
- Sibling section alignment bonus (for lecture-only alignment)
- Room-type bonus (PE gym preference, lab room bonus, lecture room bonus)
- Preferred building bonus

Special heuristics:

- LEC+LAB pairing: tries same-day and back-to-back lab after lecture first.
- Sibling lecture synchronization: tries matching lecture day/time with sibling sections in same program and year level.

### 5.3 Smart backtracking solver (Smart mode)

Service:

- `SmartScheduler` in `app/services/smart_scheduler.py`

Main functions:

- `generate_smart_preview(...)`
- `_build_candidates(...)`
- `_backtrack(...)`
- `_forward_check_fails(...)`

Algorithm:

1. Build all valid candidates per subject-slot.
2. Sort by Most Constrained Variable (fewest candidates first).
3. Recursive backtracking with forward checking.
4. Prune branch when a candidate makes any future slot impossible.
5. Return complete or partial solution.
6. Fallback to greedy mode if no solution or limits reached.

Safety limits:

- Timeout limit (default 30s; clamped via settings)
- Per-subject backtrack limit
- Global backtrack limit

### 5.4 Auto mode selection logic

Route decision in `batch_generate_schedule()` (`app/routes/schedule.py`):

1. Run quick greedy first.
2. If no unplaceable slots, keep quick result.
3. If unplaceable exists, run smart solver.
4. Choose smart only if it improves result:
   - fewer unplaceables, or
   - same unplaceables but more scheduled rows.

## 6) Batch Class Confirm Algorithm

Function:

- `confirm_schedule(section_id, proposed_items, user_id)`

File:

- `app/services/auto_scheduler.py`

Process:

1. Load active-term schedules.
2. Iterate each proposed row.
3. Resolve faculty deterministically:
   - valid numeric id first
   - unique normalized-name fallback
4. Validate against existing + tentative rows:
   - section overlap
   - faculty overlap
   - room overlap
5. Update existing target row (if schedule_id provided) or insert/reactivate.
6. Add tentative mock row for intra-batch checks.
7. Auto-create missing `FacultySubjectAssignment`.
8. Commit once if any created/updated rows exist.

## 7) Batch Conflict Check Algorithms (Class and Exam)

Class endpoint:

- `POST /schedule/batch-check-conflicts`

Exam endpoint:

- `POST /exam-schedule/batch-check-conflicts`

Route files:

- `app/routes/schedule.py`
- `app/routes/exam_schedule.py`

Per-row evaluation logic:

1. Parse incoming row values.
2. DB conflict check through `ConflictDetector`.
3. Intra-batch overlap check against other input rows.
4. Time-window checks (schedule/exam configured bounds).
5. Extra checks:
   - class: faculty availability warning
   - exam: duration-limit warning
6. Row status assignment:
   - `conflict` (critical/high)
   - `warning` (medium/low)
   - `ok`

## 8) Batch Exam Scheduling Algorithms

Main service methods in `app/services/auto_scheduler.py`:

- `generate_exam_batch_preview(...)`
- `_greedy_place_exam_batch(...)`
- `_find_best_exam_slot(...)`
- `confirm_exam_schedule(...)`

### 8.1 Exam preview generation

Process:

1. Validate active settings and exam period dates.
2. Fetch section subjects and split into lecture/lab exam slots.
3. Remove already-examined pairs `(subject_id, schedule_type)`.
4. Build candidate exam dates (Mon-Sat only) inside exam period.
5. Build time slots using configured exam start/end and duration limit.
6. Greedy placement over date/time/room.

### 8.2 Sibling exam slot synchronization

In `_greedy_place_exam_batch(...)`:

1. Identify sibling sections (same program and year level).
2. Build sibling slot map `(subject_id, schedule_type) -> (date, start, end)`.
3. Place anchored slots first by reusing sibling date/time, searching room only.
4. If anchored slot fails, fallback to normal greedy search.

### 8.3 Exam slot scoring

In `_find_best_exam_slot(...)`:

- Earlier exam dates preferred
- Morning slots preferred (time preference map)
- Day preference applied
- Lunch-overlap penalty
- Preferred building bonus

### 8.4 Exam batch confirm

In `confirm_exam_schedule(...)`:

1. Validate required fields and parse date/time.
2. Duplicate prevention by `(subject_id, section_id, schedule_type)`.
3. Check section/faculty/room conflicts using existing + tentative list.
4. Update target exam row or insert/reactivate slot.
5. Auto-create missing `FacultySubjectAssignment`.
6. Return created/updated/skipped with row-level errors.

## 9) Recommendation Engine Algorithm

File:

- `app/services/recommendation_engine.py`

Main APIs:

- `generate_class_recommendations(...)`
- `generate_exam_recommendations(...)`

Suggestion axes:

- Class: time, day, room, faculty
- Exam: time, date, room, faculty

Scoring and ranking behavior:

- Uses conflict-free filtering first.
- Applies score model per axis (time/day preference, room fit, workload impact).
- Generates confidence value by normalization (`_normalize_score`).
- Produces top-N sorted options per axis (for example top 5).

Workload-aware rules include:

- Weekly and daily load thresholds
- Penalties for overload
- Bonuses for balanced day distribution

Availability-aware rules include:

- Skips options where faculty/proctor is unavailable or not in configured schedule.

## 10) Conflict Resolution Algorithm

File:

- `app/services/conflict_resolver.py`

Main APIs:

- `generate_resolution_plan(...)` for class schedules
- `generate_exam_resolution_plan(...)` for exams

Search strategy cascade:

1. Single-field changes (time/day/room/faculty or time/date/room/faculty)
2. Two-field combinations
3. Three-field combinations
4. Iterative fallback (apply best partial fix, re-detect, retry)

Selection policy:

- Simulate each candidate change on copied form data.
- Re-run conflict counting (`critical` + `high` only).
- Keep candidate with minimum remaining conflicts.
- Stop early when remaining conflicts becomes zero.

Bounded exploration controls:

- Max options per axis
- Max combinations per axis
- Max iterative rounds

Plan application:

- `ResolutionApplier.apply_plan(...)` updates target schedule in one transaction.

## 11) AI-Assisted Conflict Explanation Process

Files:

- `app/ai_scheduler.py`
- `app/routes/schedule.py`
- `app/routes/exam_schedule.py`

Runtime flow:

1. Detect conflicts via `ConflictDetector`.
2. Generate algorithmic alternatives via `RecommendationEngine`.
3. If `use_ai=true` and Gemini configured:
   - generate concise natural-language explanation.
4. Else:
   - use offline rule-based explanation fallback.

Important design note:

- AI is used for explanation only.
- Core validation and recommendation are deterministic Python logic.

## 12) Exam Export Time-Grid Normalization Algorithm

File:

- `app/routes/exam_schedule.py`

Functions:

- `_select_exam_export_base_slots(...)`
- `_write_exam_export_time_rows(...)`

Algorithm:

1. Build unique exam time slots and sort by end/start.
2. Select canonical non-overlapping base slots.
3. Render canonical rows once.
4. Insert lunch row when crossing lunch boundary.
5. For each exam, map to overlapping canonical rows.
6. Merge vertically for off-grid or multi-row overlaps.
7. Fill subject/proctor text and preserve formatting/borders.

Result:

- Compact timetable export with stable row structure and support for custom exam windows.

## 13) Automatic Backup and Retention Algorithms

Files:

- `app/services/auto_backup_scheduler.py`
- `app/services/database_backup_service.py`

### 13.1 Daily lock and stale-lock handling

Key logic:

- Date-scoped lock file naming: `.auto_backup_lock_YYYYMMDD.lock`
- Atomic lock acquisition with `O_CREAT | O_EXCL`
- Stale lock detection by modified time threshold
- Stale lock cleanup for prior days

### 13.2 Midnight scheduler and startup catch-up

Key logic:

- APScheduler daily cron at 12:00 AM (Asia/Manila).
- Flask debug-process guard to avoid duplicate scheduler instances.
- Startup catch-up within configured post-midnight window when backup was missed.
- Double-check guard to avoid duplicate same-day backup after lock acquisition.

### 13.3 Backup creation and retention

In `DatabaseBackupService`:

- Creates full SQL dump using `mysqldump` with safety options.
- Validates and lists backup files.
- Deletes known dummy artifacts.
- Enforces retention count by deleting oldest backups beyond limit.
- Stores last successful auto-backup timestamp.

## 14) End-to-End Process Maps

### 14.1 Class scheduling end-to-end

1. User picks manual add/edit or batch generate.
2. System validates required inputs and schedule-time boundaries.
3. Conflict checks execute:
   - section
   - faculty
   - room
4. Optional AI/basic analysis returns alternatives and explanation.
5. Optional conflict resolver creates auto-fix plan.
6. Save operation writes schedule rows and related assignments.
7. Activity logs and live broadcast events are emitted.

### 14.2 Exam scheduling end-to-end

1. User picks manual add/edit or batch generate.
2. System validates exam date window, exam hours, and duration warnings.
3. Conflict checks execute:
   - section
   - proctor/faculty
   - room
   - proctor availability
4. Optional AI/basic analysis and resolver plan are available.
5. Save operation writes exam rows (insert/update/reactivate).
6. Activity logs and live broadcast events are emitted.

## 15) Quick Reference: Which Algorithm Runs Where

Class batch generation mode selection:

- Route: `batch_generate_schedule()` in `app/routes/schedule.py`
- Modes:
  - `quick` -> greedy (`AutoScheduler.generate_batch_preview`)
  - `smart` -> backtracking (`SmartScheduler.generate_smart_preview`)
  - `auto` -> quick first, smart fallback when beneficial

Exam batch generation:

- Route: `/exam-schedule/batch-generate`
- Service: `AutoScheduler.generate_exam_batch_preview`

Conflict analysis endpoints:

- Class: `/schedule/ai-check-conflicts`
- Exam: `/exam-schedule/ai-check-conflicts`

Conflict resolution endpoints:

- Class: `/schedule/resolve-conflicts`
- Exam: `/exam-schedule/resolve-conflicts`

---

If this document is used for thesis writeup, you can cite sections 3-8 as the scheduling core, section 9-11 as decision-support logic, and sections 12-13 as operational support algorithms.

## 16) Page-by-Page Algorithm Discussion (Presentation-Ready)

This section is written for system presentation/defense. For each major page, it explains what algorithm/process runs and a short way to present it.

### 16.1 Dashboard Page (`/dashboard`)

Main logic:

1. Scope normalization:
   - Admin sees all programs.
   - Dean is restricted to assigned programs.
   - Optional program filter is access-validated.
2. Aggregated KPI computation:
   - curricula, sections, subjects, faculty, schedules, exam schedules.
3. Smart class counting for "today":
   - Uses `_count_classes_smart(...)`.
   - Merges lec+lab into one class only when adjacent and same faculty.
4. Workload and risk indicators:
   - Computes faculty utilization and classifies as normal/warning/exceeded.
5. Action intelligence:
   - Builds context-aware quick actions from completion, overload, and upcoming exams.
6. Trend generation:
   - Compares current vs previous period and computes weekly activity summary.

How to present:

- "The dashboard is not just displaying counts. It applies scope filtering, smart class merging, workload analytics, and trend logic so decisions are based on current and program-specific evidence."

### 16.2 Class Schedule Page (`/schedule/class`)

Main logic:

1. Program-aware section retrieval.
2. Per-section schedule counts for active term.
3. Selected section timetable retrieval ordered by weekday and start time.
4. Uses the class scheduling validation pipeline when adding/editing:
   - required field validation,
   - term/time-window validation,
   - section/faculty/room overlap conflict checks,
   - optional faculty availability warning,
   - insert/reactivate with activity logging.

How to present:

- "This page combines visibility and safety: users see section load instantly, and every create/edit passes multi-layer conflict validation before saving."

### 16.3 Faculty Schedule Page (`/schedule/faculty`)

Main logic:

1. Department filter is mapped correctly from program access.
2. Includes faculty with explicit department membership plus those dynamically teaching in scoped programs.
3. Calculates per-faculty load status badge (`normal`, `warning`, `exceeded`) for fast decision support.
4. Selected faculty timetable is ordered by day/time for clarity.

How to present:

- "Faculty view is workload-aware. It does not only list schedules; it computes load-risk badges so overloading can be prevented before it becomes a conflict."

### 16.4 Room Schedule Page (`/schedule/room`)

Main logic:

1. Loads active buildings and available rooms.
2. Computes room schedule counts for the active term.
3. Shows selected room timetable in day/time order.
4. Room conflict logic is enforced by class/exam add/edit routes using overlap predicates.

How to present:

- "Room planning is capacity-protected. The page gives occupancy visibility, while conflict detection guarantees no double-booking in the same slot."

### 16.5 Exam Schedule Page (`/schedule/exam` + exam APIs)

Main logic:

1. Program/section scope filtering mirrors class scheduling.
2. Exam rows are filtered by active term and ordered by date/time.
3. Add/edit exam algorithm validates:
   - exam period bounds,
   - exam time window,
   - duration and lunch break warnings,
   - section/faculty/room overlap,
   - proctor availability (`unavailable` blocks save; `not_in_schedule` warns).
4. Uses deterministic conflict analysis, recommendation, and resolution endpoints:
   - `/exam-schedule/ai-check-conflicts`
   - `/exam-schedule/resolve-conflicts`

How to present:

- "Exam scheduling extends class checks with calendar-aware constraints and proctor availability, so operational exam-day risks are reduced before finalizing."

### 16.6 Unified Create/Edit Form (`/schedule/create`)

Main logic:

1. Single form context for class and exam tabs.
2. Centralized loading of active settings, accessible sections, faculty, and rooms.
3. Time-window settings are injected into the UI, so front-end and back-end use consistent constraints.

How to present:

- "The unified form reduces user errors and training cost because both class and exam scheduling share one validated workflow and one constraints source."

### 16.7 Faculty Management Page (`/faculty`)

Main logic:

1. Loads active faculty and computes term-specific workload using batched schedule/assignment queries.
2. Workload metrics include assigned subjects, total units, class count, weekly teaching hours, and utilization percentage.
3. Curricula list is filtered by active semester and user access scope.
4. Availability subsystem supports weekly availability windows and proctor-slot checks.

How to present:

- "Faculty management is analytics-driven. The system computes real workload and availability, not just profile data, enabling fair and feasible assignments."

### 16.8 Building and Room Management Page (`/buildings`)

Main logic:

1. Master-detail building view with associated rooms.
2. Duplicate protection for building and room records.
3. Archive cascade behavior:
   - when a building is archived, schedules/exam schedules using its rooms are identified and removed,
   - operations are logged for auditability.

How to present:

- "Infrastructure changes are safely propagated. If a building is archived, dependent schedules are handled consistently, preventing orphaned room allocations."

### 16.9 Curriculum Page (`/curriculum`)

Main logic:

1. Access-aware curriculum listing (admin all, dean scoped programs).
2. Auto-select optimization for single-program dean users.
3. Curriculum creation algorithm auto-generates year levels and default semesters based on active settings.
4. Edit logic keeps structure synchronized with target year-level configuration.

How to present:

- "Curriculum setup is semi-automated: once code and program are defined, the year-level/semester skeleton is generated using current institutional settings."

### 16.10 Reports Overview (`/reports`)

Main logic:

1. Central statistics engine `calculate_statistics(...)` computes scoped KPIs.
2. Include-set optimization allows partial recomputation for AJAX refresh (`counts`, `faculty`, `rooms`, `weekly`, `completion`).
3. Dean/admin scope normalization ensures only authorized program data is aggregated.
4. Rule-based insights banner summarizes top risk signals.

How to present:

- "Reports are generated by a reusable statistics engine with scope normalization, so every chart/card remains consistent and access-compliant across the system."

### 16.11 Reports: Faculty (`/reports/faculty`)

Main logic:

1. Reuses statistics engine with focused include-set (`counts`, `faculty`).
2. Calculates utilization classes and overload distribution.
3. Surfaces unassigned and restricted-availability faculty indicators.

How to present:

- "This report isolates workload balance and staffing risk, enabling targeted adjustments rather than manual checking of each faculty record."

### 16.12 Reports: Rooms (`/reports/rooms`)

Main logic:

1. Reuses statistics engine with room-focused include-set (`counts`, `rooms`).
2. Computes merged occupied intervals per day to avoid overlap inflation.
3. Converts occupancy to weekly utilization percent using configured operating window.
4. Computes free-slot windows and building-level utilization rollups.

How to present:

- "Room analytics use interval merging, so utilization is mathematically accurate even when overlapping rows exist in raw schedule data."

### 16.13 Reports: Weekly Distribution (`/reports/weekly`)

Main logic:

1. Computes day-wise class distribution over active operation days.
2. Highlights imbalance signals when one day is disproportionately loaded.

How to present:

- "Weekly distribution transforms schedule rows into load-balance insights, helping spread classes more evenly across teaching days."

### 16.14 Reports: Semester Comparison (`/reports/compare`)

Main logic:

1. Fetches two periods and computes stats for each with archived-inclusive mode.
2. Derives differences and percent change per KPI (`period2 - period1`).
3. Provides trend-ready payload for comparison visualizations.

How to present:

- "Comparison mode supports evidence-based evaluation of improvements by quantifying KPI deltas and percent changes across semesters."

### 16.15 Reports: Activity Logs (`/reports/activity`)

Main logic:

1. Admin-only filtered retrieval with pagination.
2. Multi-criteria filtering (user, action, entity, date range, text, IP).
3. Action/entity aggregations for audit analytics.
4. Structured export pipeline (Excel) for compliance/reporting.

How to present:

- "Activity reporting provides traceability from individual events to aggregated audit metrics, supporting governance and accountability."

### 16.16 Archive Pages (`/archive` and tabs)

Main logic:

1. Archive dashboard and tabbed entities (schedules, curriculum, programs, faculty, buildings).
2. Filter-driven retrieval across academic year, semester, type, section/faculty/room/building/program.
3. Scope enforcement for dean users through accessible program/section filtering.
4. Lifecycle actions:
   - archive single/bulk,
   - unarchive,
   - permanent delete (permission-gated).
5. Export supports grouped and exam-specific variants.

How to present:

- "Archive is a controlled lifecycle layer, not just storage. It applies access rules, supports restore/delete governance, and keeps historical data exportable."

### 16.17 Settings Page (`/settings`)

Main logic:

1. Central term and scheduling configuration state.
2. Validation pipeline for class/exam windows, lunch range, exam duration limits, operation days, and available semesters.
3. Academic-term transition algorithm:
   - archive current class/exam schedules and faculty assignments,
   - activate new settings,
   - attempt restore for matching archived term data,
   - emit user feedback on archive/restore counts.
4. Rule: selecting 2nd semester auto-includes 1st semester in available semesters.

How to present:

- "Settings is the control plane. It validates institutional constraints and orchestrates safe term transitions through archive-and-restore logic."

### 16.18 Users Page (`/users`)

Main logic:

1. Role-aware user visibility and permission boundaries.
2. Validation pipelines for username format, unique identity, name normalization, and password policies.
3. Soft-delete archive lifecycle with restore and super-admin permanent delete.
4. Bulk-action algorithm with safety guards:
   - no self-lockout,
   - prevent deactivation/archive of last active admin,
   - role-based restrictions for super admin accounts.
5. Quick-generate account workflow with uniqueness retry loop for `user###` identities.

How to present:

- "User administration is safety-first: identity validation, role boundaries, and lockout-prevention rules are enforced before any account state change is committed."

### 16.19 Suggested Presentation Flow (5-7 minutes)

Use this sequence for a clear defense narrative:

1. Dashboard: explain scoped KPIs and smart counting.
2. Schedule Class/Exam: explain conflict detection and validation pipeline.
3. Batch Scheduling: explain quick vs smart algorithms and auto fallback.
4. Reports: explain unified statistics engine and room/faculty analytics.
5. Settings + Archive + Users: explain governance, lifecycle control, and safety constraints.

Short closing line:

- "iSchedWise combines deterministic scheduling algorithms, scoped analytics, and governance workflows to produce conflict-aware, auditable, and operationally feasible academic schedules."
