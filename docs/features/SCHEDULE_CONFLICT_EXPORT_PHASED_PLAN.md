# Schedule Conflict Handling: Phased Implementation Plan

Date: 2026-04-13
Status: On Hold (planning paused)

## Goal
Implement one consistent conflict policy across class and exam scheduling:
- Hard conflicts block save, confirm, and export.
- Suggestion actions remain enabled so users can resolve conflicts quickly.
- Batch confirms are atomic (all-or-nothing).

## Final Policy Decisions
1. Export scope: All schedule export endpoints are conflict-gated (backend and UI).
2. Conflict scope: Hard conflicts only.
3. Hard conflicts: Section, faculty, and room overlap conflicts.
4. Suggestion policy: Keep time/day/room/faculty (and exam date) suggestions actionable while conflicts exist.
5. Batch policy: Class and exam batch confirm must be atomic.

## In Scope
- Class schedule exports: section, faculty, room (Excel/PDF/for-posting)
- Exam schedule exports: section and batch exports
- Batch class confirm and batch exam confirm behavior
- Suggestion apply flows for class and exam recommendation cards
- Route/service/UI tests for gates and atomic behavior

## Out of Scope (for now)
- Redesign of recommendation scoring algorithm
- New AI prompt behavior or model changes
- Non-schedule report exports unless requested separately

## Phase 1: Shared Contract and Helper Design
Objective: Lock the blocking contract and add reusable hard-conflict checks.

Tasks:
1. Define a single hard-conflict predicate used by export and batch-confirm paths.
2. Add helper methods for conflict checks by scope:
   - class section
   - faculty
   - room
   - exam section
   - exam batch (current academic period)
3. Ensure warning-only conditions remain non-blocking.

Deliverables:
- Shared helper functions for unresolved hard-conflict detection.
- Clear contract comments/docstrings for what is blocking vs advisory.

## Phase 2: Backend Export Gating
Objective: Prevent direct URL export bypass while conflicts exist.

Tasks:
1. Apply hard-conflict guards to all class export routes.
2. Apply hard-conflict guards to all exam export routes, including batch export.
3. Return safe user feedback and redirect behavior when blocked.

Deliverables:
- Backend enforcement for every covered export endpoint.
- No downloadable export when unresolved hard conflicts exist.

## Phase 3: Export UI Lock States
Objective: Keep UI consistent with backend rules.

Tasks:
1. Add per-tab lock flags in route context.
2. Disable export buttons/menus for blocked scopes.
3. Show clear resolve-first helper text in class/faculty/room/exam tabs.

Deliverables:
- Export controls visually disabled when blocked.
- Messaging aligned with backend gate reason.

## Phase 4: Atomic Batch Confirm (Class + Exam)
Objective: Remove partial-save behavior.

Tasks:
1. Update class batch confirm service path to all-or-nothing.
2. Update exam batch confirm service path to all-or-nothing.
3. Ensure created/updated counts stay zero when any hard-conflict row remains.

Deliverables:
- Zero writes on mixed valid+hard-conflict payloads.
- Full commit only when payload is hard-conflict free.

## Phase 5: Suggestion Flow Alignment (Time/Day/Room/Faculty/Date)
Objective: Preserve recommendations as the remediation path.

Tasks:
1. Keep recommendation apply actions enabled in conflict state.
2. Keep only temporary disable during in-flight checks.
3. Ensure each apply action triggers immediate recheck:
   - class: applyTimeSlot, applyDay, applyRoom, applyFaculty
   - exam: applyExamTimeSlot, applyExamDate, applyExamRoom, applyExamFaculty
4. Keep recommendation type contracts stable:
   - class: time_slot, day, room, faculty
   - exam: time_slot, date, room, faculty

Deliverables:
- Users can resolve conflicts using suggestion cards without manual re-entry.
- Save/export unlock only after hard conflicts are cleared.

## Phase 6: Automated Regression Tests
Objective: Prevent regressions and lock the contract.

Tasks:
1. Add route tests for export conflict gating (blocked and allowed paths).
2. Add service/route tests for atomic batch class confirm.
3. Add service/route tests for atomic batch exam confirm.
4. Add recommendation contract tests for expected types/options under conflict scenarios.

Deliverables:
- Repeatable tests proving gate, atomicity, and suggestion contracts.

## Phase 7: Manual Validation and Rollout
Objective: Validate full behavior from UI to backend.

Checklist:
1. Trigger hard conflicts and verify export is blocked (UI and direct URL).
2. Apply suggestions to resolve conflicts and verify unlock behavior.
3. Verify batch confirm does not partially save on mixed payload.
4. Verify batch confirm succeeds on fully conflict-free payload.

Deliverables:
- Manual signoff for class, exam, and both batch builders.

## Success Criteria
1. All schedule exports are blocked whenever unresolved hard conflicts exist in scope.
2. Batch class/exam confirms are all-or-nothing.
3. Suggestion actions remain usable during conflict state and help clear conflicts.
4. Submit/confirm/export only unlock after hard conflicts are resolved.

## Initial File Targets
- app/routes/schedule.py
- app/routes/exam_schedule.py
- app/services/auto_scheduler.py
- app/services/recommendation_engine.py
- app/static/js/schedule/auto_conflict_check.js
- app/static/js/schedule/auto_conflict_check_exam.js
- app/static/js/schedule/schedule_full.js
- app/static/js/schedule/exam_ai.js
- app/templates/schedule/_class_tab.html
- app/templates/schedule/_faculty_tab.html
- app/templates/schedule/_room_tab.html
- app/templates/schedule/_exam_tab.html

## Notes
- This file is planning-only for now.
- Implementation should follow the project database and routing conventions in copilot-instructions.
