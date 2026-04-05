# B5 — Auto-Conflict Check for Exam Form (Parity Fix)

> **Category:** Part B — Add DSS Power Behind Simple Surfaces  
> **Priority:** 4 (tied with B2)  
> **Effort:** Low  
> **DSS Impact:** Medium  
> **Simplicity Impact:** ★★★★★ HIGH — Removes a manual step the user shouldn't have to do  

---

## Problem Statement

The **class schedule form** auto-triggers conflict detection on every field change (debounced 800ms). The **exam schedule form** requires the user to manually click a "Check with AI" button to trigger conflict detection. This inconsistency means:

1. Users creating exam schedules may forget to check for conflicts
2. Users who are used to the class form's auto-check are confused by the exam form's manual requirement
3. Conflicts are discovered late (at button click) rather than early (as fields are filled)

---

## Current Behavior Comparison

| Feature | Class Form | Exam Form |
|---------|-----------|-----------|
| Auto-trigger on field change | ✅ Yes (800ms debounce) | ❌ No |
| DOMContentLoaded auto-init | ✅ `initAutoConflictDetection()` | ❌ None |
| Event listeners on fields | ✅ 8 fields monitored | ❌ None |
| Manual trigger button | ❌ Not needed | ✅ "Check with AI" button |
| Debounce mechanism | ✅ 800ms | ❌ N/A |
| Submit button blocking | ✅ Blocked until conflicts resolved | ⚠️ Only after manual check |

---

## Current Code

### Class Form Auto-Check: [app/static/js/schedule/auto_conflict_check.js](../../app/static/js/schedule/auto_conflict_check.js)

```javascript
// Lines 1-20: Initialization
const AUTO_CHECK_DEBOUNCE_MS = 800;
let autoCheckTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    initAutoConflictDetection();
});

function initAutoConflictDetection() {
    setupAutoCheckForModal('add');
    setupAutoCheckForModal('edit');
}

function setupAutoCheckForModal(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const fields = [
        `curriculum_id${suffix}`, `subject_id${suffix}`, 
        `faculty_id${suffix}`, `room_id${suffix}`,
        `day_of_week${suffix}`, `schedule_type${suffix}`,
        `start_time${suffix}`, `end_time${suffix}`
    ];
    
    fields.forEach(fieldId => {
        const el = document.getElementById(fieldId);
        if (el) {
            el.addEventListener('change', () => {
                clearTimeout(autoCheckTimer);
                autoCheckTimer = setTimeout(() => {
                    performAutoConflictCheck(mode);
                }, AUTO_CHECK_DEBOUNCE_MS);
            });
        }
    });
}
```

### Exam Form Manual Check: [app/static/js/schedule/exam_ai.js](../../app/static/js/schedule/exam_ai.js)

```javascript
// Lines 9-98: Manual trigger function
function checkExamScheduleWithAI(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    // Gets: section_id_exam, subject_id_exam, faculty_id_exam, room_id_exam,
    //        exam_date, start_time_exam, end_time_exam
    // Validates ALL 7 fields required
    // POSTs to /exam-schedule/ai-check-conflicts
    // Renders results in AI panel
}
```

**Key difference:** `exam_ai.js` has NO `addEventListener`, NO `DOMContentLoaded` hook, NO debounce. The function is only called when the user explicitly clicks the "Check with AI" button.

---

## Proposed Solution

### Add Auto-Trigger to Exam Form Fields

Mirror the class form's `auto_conflict_check.js` pattern in `exam_ai.js`:

```javascript
// === NEW: Auto-conflict detection for exam form ===
const EXAM_AUTO_CHECK_DEBOUNCE_MS = 800;
let examAutoCheckTimerAdd = null;
let examAutoCheckTimerEdit = null;

document.addEventListener('DOMContentLoaded', () => {
    initExamAutoConflictDetection();
});

function initExamAutoConflictDetection() {
    setupExamAutoCheck('add');
    setupExamAutoCheck('edit');
}

function setupExamAutoCheck(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Exam-specific field IDs
    const fieldIds = [
        `section_id_exam${suffix}`,
        `subject_id_exam${suffix}`,
        `faculty_id_exam${suffix}`,
        `room_id_exam${suffix}`,
        `exam_date${suffix}`,
        `start_time_exam${suffix}`,
        `end_time_exam${suffix}`
    ];
    
    fieldIds.forEach(fieldId => {
        const el = document.getElementById(fieldId);
        if (el) {
            el.addEventListener('change', () => {
                debounceExamCheck(mode);
            });
            
            // Also listen to 'input' for date fields
            if (fieldId.includes('exam_date')) {
                el.addEventListener('input', () => {
                    debounceExamCheck(mode);
                });
            }
        }
    });
}

function debounceExamCheck(mode) {
    if (mode === 'add') {
        clearTimeout(examAutoCheckTimerAdd);
        examAutoCheckTimerAdd = setTimeout(() => {
            performExamAutoCheck(mode);
        }, EXAM_AUTO_CHECK_DEBOUNCE_MS);
    } else {
        clearTimeout(examAutoCheckTimerEdit);
        examAutoCheckTimerEdit = setTimeout(() => {
            performExamAutoCheck(mode);
        }, EXAM_AUTO_CHECK_DEBOUNCE_MS);
    }
}

function performExamAutoCheck(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Check minimum fields are filled (at least section + subject + 1 more)
    const sectionId = document.getElementById(`section_id_exam${suffix}`)?.value;
    const subjectId = document.getElementById(`subject_id_exam${suffix}`)?.value;
    const facultyId = document.getElementById(`faculty_id_exam${suffix}`)?.value;
    const roomId = document.getElementById(`room_id_exam${suffix}`)?.value;
    const examDate = document.getElementById(`exam_date${suffix}`)?.value;
    const startTime = document.getElementById(`start_time_exam${suffix}`)?.value;
    const endTime = document.getElementById(`end_time_exam${suffix}`)?.value;
    
    // Need at least these fields to run a meaningful check
    if (!sectionId || !subjectId) return;
    
    // Need at least one scheduling field
    if (!facultyId && !roomId && !examDate && !startTime) return;
    
    // All fields filled → run full check  
    // Partial fields → run partial check (skip validation for unfilled fields)
    const allFilled = sectionId && subjectId && facultyId && roomId && examDate && startTime && endTime;
    
    if (allFilled) {
        // Reuse existing full check function
        checkExamScheduleWithAI(mode);
    } else {
        // Show partial status (optional lighter check)
        showExamPartialStatus(mode, { sectionId, subjectId, facultyId, roomId, examDate, startTime, endTime });
    }
}

function showExamPartialStatus(mode, fields) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const statusContainer = document.getElementById(`aiAssistantExam${suffix}`);
    
    if (!statusContainer) return;
    
    // Show a soft "checking..." indicator while fields are being filled
    // This replaces the empty state with a helpful message
    const filledCount = Object.values(fields).filter(Boolean).length;
    const totalRequired = 7;
    
    // Update status to show progress
    const statusEl = statusContainer.querySelector('.ai-status') || statusContainer;
    statusEl.innerHTML = `
        <div class="flex items-center gap-2 text-xs text-gray-500 p-3">
            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>${filledCount}/${totalRequired} fields filled — complete all to check conflicts</span>
        </div>
    `;
}
```

---

## Changes to Existing Manual Button

The manual "Check with AI" button should still exist as a fallback, but now it's secondary:

```html
<!-- Before: Primary action -->
<button onclick="checkExamScheduleWithAI('add')" class="btn-primary">Check with AI</button>

<!-- After: Secondary, with note that auto-check is active -->
<button onclick="checkExamScheduleWithAI('add')" class="btn-secondary text-xs">
    Re-check Conflicts
</button>
<p class="text-[10px] text-gray-400 mt-1">Auto-checks on every field change</p>
```

---

## Implementation Steps

### Step 1: Add Auto-Check Functions to `exam_ai.js`
1. Add `EXAM_AUTO_CHECK_DEBOUNCE_MS`, timer variables
2. Add `DOMContentLoaded` → `initExamAutoConflictDetection()`
3. Add `setupExamAutoCheck(mode)` with field listeners
4. Add `debounceExamCheck(mode)` with timer management
5. Add `performExamAutoCheck(mode)` with minimum-field validation

### Step 2: Verify Field IDs
1. Confirm exam form field IDs match (`section_id_exam_add`, `subject_id_exam_add`, etc.)
2. Check both add and edit mode suffixes

### Step 3: Update Manual Button (Optional)
1. Change manual button from primary to secondary styling
2. Add "Auto-checks on field change" note text

### Step 4: Submit Button Blocking (If Not Already)
1. Ensure exam submit button is blocked when conflicts are detected
2. Mirror the class form's `updateConflictState()` behavior

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/static/js/schedule/exam_ai.js` | **Medium edit** | Add auto-check initialization, field listeners, debounce |
| `app/templates/schedule/_exam_form_content.html` | **Small edit** | Optionally update manual check button to secondary style |

---

## Testing Checklist

- [ ] Changing exam section → auto-check fires after 800ms
- [ ] Changing exam subject → auto-check fires after 800ms
- [ ] Changing exam date → auto-check fires after 800ms
- [ ] Changing faculty → auto-check fires after 800ms
- [ ] Changing room → auto-check fires after 800ms
- [ ] Changing start time → auto-check fires after 800ms
- [ ] Changing end time → auto-check fires after 800ms
- [ ] Rapid field changes → only last change triggers check (debounce works)
- [ ] Partial fields (only 3 of 7 filled) → shows progress indicator, not full check
- [ ] All 7 fields filled → runs full conflict check automatically
- [ ] Conflicts render correctly in exam AI panel
- [ ] Recommendations render with "Apply" buttons working
- [ ] Submit button blocked when conflicts exist
- [ ] Manual "Re-check" button still works as fallback
- [ ] Both Add and Edit modes work
- [ ] No duplicate API calls (debounce prevents spam)
- [ ] Performance: check completes within 2 seconds
