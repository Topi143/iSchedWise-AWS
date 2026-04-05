# B2 — Inline What-If Feedback (Smart Status Line)

> **Category:** Part B — Add DSS Power Behind Simple Surfaces  
> **Priority:** 4  
> **Effort:** Medium  
> **DSS Impact:** ★★★★★ HIGH — The defining DSS feature, woven into the form flow  
> **Simplicity Impact:** ★★★★★ HIGH — No extra panels, the form itself becomes intelligent  

---

## Problem Statement

Currently, the schedule form workflow is:
1. User fills fields one by one
2. After all fields are filled, auto-conflict check fires (800ms debounce)
3. User reads AI panel for conflicts/recommendations
4. User decides whether to submit or adjust

The user has **no incremental feedback as they fill each field**. They don't know until the very end whether their choices are leading to a good or bad schedule. There's no "what would happen if I pick Monday?" preview.

---

## Current Progress Bar

### File: [app/templates/schedule/_class_form_content.html](../../app/templates/schedule/_class_form_content.html) (lines 175-183)

```html
<!-- ═══ Step Progress Indicator ═══ -->
<div class="mb-5">
    <div class="flex items-center justify-between mb-2">
        <span class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Progress</span>
        <span id="classFormProgress" class="text-[10px] font-bold text-blue-600">0 / 6</span>
    </div>
    <div class="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
        <div id="classFormProgressBar" class="bg-gradient-to-r from-blue-500 to-indigo-500 h-1.5 rounded-full transition-all duration-500 ease-out" style="width: 0%"></div>
    </div>
</div>
```

**Current behavior:** Shows "0/6" → "1/6" → ... → "6/6" as fields are filled. Static blue gradient. No contextual feedback.

---

## Proposed Solution

### Transform Progress Bar into Smart Status Line

Replace the static "0/6 → 6/6" counter with a **contextual intelligence line** that gives real-time feedback at each step:

```
Step 0: "Select a section to begin"                            (gray)
Step 1: "BSIT 1A selected — 12 subjects in curriculum"        (blue)
Step 2: "Data Structures — 3 units, Lecture"                   (blue)
Step 3: "Prof. Santos — 18/21 units (86% capacity)"            (AMBER ⚠)
Step 4: "Monday — Prof. Santos teaches 3 other classes"        (AMBER ⚠)
Step 5: "Room 301 — Lecture Room, available at this time"      (blue)
Step 6: "10:00 AM — ✓ No conflicts, 82% SQI impact"           (GREEN ✓)
     or "10:00 AM — ⚠ Room conflict with BSCS 2A"            (RED ✕)
```

### Visual Design

```html
<!-- Smart Status Line (replaces plain progress bar) -->
<div class="mb-4">
    <!-- Progress bar (top) -->
    <div class="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden mb-2">
        <div id="classFormProgressBar" 
             class="h-1.5 rounded-full transition-all duration-500 ease-out" 
             style="width: 0%"
             data-color="blue">
        </div>
    </div>
    
    <!-- Context line (bottom) -->
    <div id="classFormStatusLine" 
         class="flex items-center gap-2 text-xs transition-all duration-300">
        <span id="statusIcon" class="flex-shrink-0">
            <!-- Dynamic icon: spinner / check / warning / error -->
        </span>
        <span id="statusText" class="text-gray-500">
            Select a section to begin
        </span>
        <span id="statusBadge" class="ml-auto flex-shrink-0 hidden">
            <!-- Optional badge: "18/21 units" or "3 conflicts" -->
        </span>
    </div>
</div>
```

---

## Status Messages by Field

### When Each Field Changes

| Field Changed | Status Text | Color | Badge | Data Source |
|--------------|-------------|-------|-------|-------------|
| **Section selected** | "BSIT 1A — 12 subjects in curriculum" | Blue | — | Section → Curriculum → count subjects |
| **Curriculum selected** | "BSIT Curriculum — 6 subjects this semester" | Blue | — | Curriculum → filter subjects |
| **Subject selected** | "Data Structures — 3 units, Lecture type" | Blue | "3 units" | Subject model |
| **Schedule Type† changed** | "Lab type — requires Lab room" | Blue | — | Static mapping |
| **Faculty selected** | Message varies by load status (see below) | Variable | "18/21" | `faculty.get_load_status()` |
| **Day selected** | Message varies by faculty's day load (see below) | Variable | "N classes" | Count faculty schedules on that day |
| **Room selected** | "Room 301 — Lecture Room, Bldg A" | Blue | — | Room model |
| **Start Time selected** | Full conflict check + summary (see below) | Variable | — | ConflictDetector + what-if |

### Faculty Selection — Contextual Messages

```javascript
function getFacultyStatusMessage(faculty_id, subject_name) {
    // API call to get faculty load status
    const loadInfo = await fetchFacultyLoad(faculty_id);
    
    if (loadInfo.utilization_pct > 100) {
        return {
            text: `${loadInfo.name} — OVERLOADED (${loadInfo.current}/${loadInfo.max} units)`,
            color: 'red',
            icon: '⚠',
            badge: `${loadInfo.current}/${loadInfo.max}`
        };
    } else if (loadInfo.utilization_pct > 80) {
        return {
            text: `${loadInfo.name} — Near capacity (${loadInfo.current}/${loadInfo.max} units)`,
            color: 'amber',
            icon: '⚠',
            badge: `${loadInfo.current}/${loadInfo.max}`
        };
    } else {
        return {
            text: `${loadInfo.name} — ${loadInfo.current}/${loadInfo.max} units (${loadInfo.utilization_pct}%)`,
            color: 'blue',
            icon: '✓',
            badge: `${loadInfo.current}/${loadInfo.max}`
        };
    }
}
```

### Day Selection — Contextual Messages

```javascript
function getDayStatusMessage(day_of_week, faculty_id) {
    // Count faculty's schedules on this day
    const daySchedules = await fetchFacultyDaySchedules(faculty_id, day_of_week);
    const count = daySchedules.length;
    const hours = daySchedules.reduce((sum, s) => sum + s.duration_hours, 0);
    
    if (hours > 6) {
        return {
            text: `${day_of_week} — ${faculty_name} already teaches ${hours}h (exceeds 6h max)`,
            color: 'red',
            icon: '✕'
        };
    } else if (hours > 4) {
        return {
            text: `${day_of_week} — ${faculty_name} has ${count} classes (${hours}h, approaching limit)`,
            color: 'amber',
            icon: '⚠'
        };
    } else if (count === 0) {
        return {
            text: `${day_of_week} — ${faculty_name} has no classes yet (fresh day)`,
            color: 'emerald',
            icon: '✓'
        };
    } else {
        return {
            text: `${day_of_week} — ${faculty_name} has ${count} class(es) (${hours}h)`,
            color: 'blue',
            icon: 'ℹ'
        };
    }
}
```

### Time Selection — Final Summary

When start time is selected (completing all fields), the full conflict check fires automatically (existing behavior). The status line shows the **summary result**:

```javascript
function getTimeStatusMessage(conflictResult) {
    if (conflictResult.has_conflicts) {
        const criticalCount = conflictResult.conflicts.filter(c => c.severity === 'critical').length;
        return {
            text: `${criticalCount} conflict(s) detected — check AI panel for details`,
            color: 'red',
            icon: '✕'
        };
    } else {
        return {
            text: `✓ No conflicts — schedule is clear to submit`,
            color: 'emerald',
            icon: '✓'
        };
    }
}
```

---

## New API Endpoint (Lightweight)

### `GET /schedule/field-context`

A lightweight endpoint that returns contextual data for a single field change — much cheaper than the full conflict check.

```python
@schedule_bp.route('/field-context', methods=['GET'])
@login_required
def get_field_context():
    """Return contextual information for a single field change.
    
    Query params:
        field: 'faculty' | 'day' | 'section' | 'subject'
        faculty_id: int (for faculty/day context)
        day_of_week: str (for day context)
        section_id: int (for section context)
        academic_year: str
        semester: str
    """
    field = request.args.get('field')
    
    if field == 'faculty':
        faculty_id = request.args.get('faculty_id', type=int)
        faculty = Faculty.query.get(faculty_id)
        if not faculty:
            return jsonify({'error': 'Faculty not found'}), 404
        
        load_info = faculty.get_load_status()
        return jsonify({
            'name': faculty.full_name,
            'current_units': load_info[0],
            'max_units': load_info[1],
            'utilization_pct': load_info[2],
            'status': load_info[3]  # 'normal', 'warning', 'exceeded'
        })
    
    elif field == 'day':
        faculty_id = request.args.get('faculty_id', type=int)
        day = request.args.get('day_of_week')
        
        # Count schedules on this day for this faculty
        schedules = Schedule.query.filter_by(
            faculty_id=faculty_id,
            day_of_week=day,
            is_archived=False
        ).all()
        
        total_hours = sum(
            (s.end_time.hour + s.end_time.minute/60) - (s.start_time.hour + s.start_time.minute/60)
            for s in schedules
        )
        
        return jsonify({
            'schedule_count': len(schedules),
            'total_hours': round(total_hours, 1),
            'max_daily_hours': 6
        })
    
    elif field == 'section':
        section_id = request.args.get('section_id', type=int)
        # Return subject count in curriculum
        from app.models.curriculum import CurriculumSubject
        subject_count = CurriculumSubject.query.filter_by(
            section_id=section_id
        ).count()
        
        return jsonify({
            'subject_count': subject_count
        })
    
    return jsonify({'error': 'Unknown field'}), 400
```

---

## Progress Bar Color Changes

The progress bar gradient changes based on the most recent field's status:

```javascript
function updateProgressBarColor(color) {
    const bar = document.getElementById('classFormProgressBar');
    const colors = {
        'blue':    'bg-gradient-to-r from-blue-500 to-indigo-500',
        'emerald': 'bg-gradient-to-r from-emerald-500 to-green-500',
        'amber':   'bg-gradient-to-r from-amber-500 to-yellow-500',
        'red':     'bg-gradient-to-r from-red-500 to-rose-500'
    };
    
    // Remove all color classes
    Object.values(colors).forEach(cls => {
        cls.split(' ').forEach(c => bar.classList.remove(c));
    });
    
    // Add new color
    colors[color].split(' ').forEach(c => bar.classList.add(c));
}
```

---

## Implementation Steps

### Step 1: Add `/schedule/field-context` API Endpoint
1. Add to `app/routes/schedule.py`
2. Handle `faculty`, `day`, `section` field types
3. Return lightweight JSON responses

### Step 2: Add Smart Status Line HTML
1. Replace existing progress indicator in `_class_form_content.html`
2. Add `statusIcon`, `statusText`, `statusBadge` elements
3. Keep the progress bar — just add the context line below it

### Step 3: Add JavaScript Logic
1. In `auto_conflict_check.js` or new `smart_status.js`
2. Add `change` event listeners that update status line (separate from conflict check)
3. Faculty and Day changes call `/field-context` API
4. Other fields use client-side data already available in the form
5. Debounce: 200ms (faster than conflict check's 800ms — this is lightweight)

### Step 4: Apply to Exam Form
1. Same status line in `_exam_form_content.html`
2. Adapt for exam-specific fields (exam_date instead of day_of_week)

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/routes/schedule.py` | **Small addition** | New `/field-context` GET endpoint |
| `app/templates/schedule/_class_form_content.html` | **Small edit** | Replace progress indicator with smart status line |
| `app/templates/schedule/_exam_form_content.html` | **Small edit** | Same for exam form |
| `app/static/js/schedule/auto_conflict_check.js` | **Medium edit** | Add field-change listeners for status updates |

---

## User Experience Flow

```
User selects: BSIT 1A
Status line:  ℹ "BSIT 1A — 12 subjects in curriculum"     [BLUE]
Progress:     ████░░░░░░ 1/6

User selects: Data Structures
Status line:  ℹ "Data Structures — 3 units, Lecture"        [BLUE]
Progress:     ████████░░ 2/6

User selects: Prof. Santos
Status line:  ⚠ "Prof. Santos — 18/21 units (86%)"        [AMBER]
Progress:     ██████████ 3/6 (amber gradient)

User selects: Monday
Status line:  ⚠ "Monday — Prof. Santos has 3 classes (5h)" [AMBER]
Progress:     ████████████ 4/6 (amber)

User selects: Room 301
Status line:  ℹ "Room 301 — Lecture Room, available"        [BLUE]
Progress:     ██████████████ 5/6 (blue)

User selects: 10:00 AM → auto-conflict check fires
Status line:  ⟳ "Checking for conflicts..."                 [BLUE pulse]
...800ms later...
Status line:  ✓ "No conflicts — ready to submit"            [GREEN]
Progress:     ████████████████ 6/6 (green gradient)
```

---

## Testing Checklist

- [ ] Status line shows correct message for each field type
- [ ] Faculty status shows correct units/capacity from API
- [ ] Day status shows correct schedule count and hours for that faculty
- [ ] Progress bar color changes with status (blue/amber/red/green)
- [ ] Status updates are fast (<200ms for client-side, <500ms for API)
- [ ] Status line doesn't conflict with the full AI conflict check
- [ ] Exam form has equivalent status line behavior
- [ ] Status line works with both Add and Edit modes
- [ ] Mobile: status line text truncates gracefully
- [ ] Dark mode: colors adapt correctly
- [ ] Field context API handles missing/invalid IDs gracefully
