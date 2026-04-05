# B4 — AI Smart Pre-Fill ("AI Suggest" Button)

> **Category:** Part B — Add DSS Power Behind Simple Surfaces  
> **Priority:** 8  
> **Effort:** Medium  
> **DSS Impact:** ★★★★★ HIGH — System makes decisions for the user  
> **Simplicity Impact:** ★★★★★ HIGH — 7 manual fields → 2 manual + 1 button click  

---

## Problem Statement

Creating one schedule currently requires filling **7 fields manually** (curriculum, subject, type, faculty, day, room, start time). The recommendation engine already knows the best faculty, day, room, and time for any given subject — but it only suggests alternatives *after* the user has already made a bad choice and triggered conflicts.

**The system can recommend but doesn't proactively suggest.**

---

## Current Workflow (9-10 Clicks)

```
1. Select section (or arrive from schedule page)
2. Select curriculum         → manual
3. Select subject            → manual
4. Select schedule type      → manual (usually auto from subject)
5. Select faculty            → manual (search through dropdown)
6. Select day                → manual
7. Select room               → manual (search through dropdown)
8. Select start time         → manual (via custom picker)
9. Wait for conflict check   → auto (800ms)
10. Submit                    → click
```

---

## Proposed Workflow (4-5 Clicks)

```
1. Select section (or arrive from schedule page)
2. Select curriculum         → manual
3. Select subject            → manual  
4. Click "✨ AI Suggest"     → AUTO-FILLS: type, faculty, day, room, time
5. Review + adjust if needed → optional
6. Submit                    → click
```

**Reduction: 7 manual decisions → 2 manual + 1 button**

---

## How It Works

### User Perspective

After selecting a curriculum and subject, a button appears in the form:

```
┌─────────────────────────────────────┐
│ 1. Course Details                   │
│    Curriculum: [BSIT Curriculum ▼]  │
│    Subject:    [Data Structures ▼]  │
│    Type:       ○ Lecture  ○ Lab     │
│                                     │
│    ┌─────────────────────────────┐  │
│    │ ✨ AI Suggest Best Slot     │  │
│    │    Fill all fields with     │  │
│    │    optimal assignment       │  │
│    └─────────────────────────────┘  │
│                                     │
│ 2. Faculty & Day                    │
│    Faculty: [auto-filled]           │
│    Day:     [auto-filled]           │
│                                     │
│ 3. Room & Time                      │
│    Room:    [auto-filled]           │
│    Time:    [auto-filled]           │
└─────────────────────────────────────┘
```

### System Flow

```
User clicks "AI Suggest"
    │
    ▼ POST /schedule/ai-suggest-slot
    │
    ├── 1. Determine schedule type from subject (Lec/Lab)
    ├── 2. Find best faculty (FacultySubjectAssignment + workload scoring)
    ├── 3. Find best day (faculty availability + workload balance)
    ├── 4. Find best room (type match + building preference + availability)
    ├── 5. Find best time (time preference + no conflicts + break compliance)
    └── 6. Verify complete assignment is conflict-free
    │
    ▼ Return: { faculty_id, day, room_id, start_time, end_time, schedule_type, confidence }
    │
    ▼ Auto-fill all form fields with smooth animation
    │
    ▼ Trigger conflict check (existing flow, should return 0 conflicts)
```

---

## Backend: New API Endpoint

### `POST /schedule/ai-suggest-slot`

```python
@schedule_bp.route('/ai-suggest-slot', methods=['POST'])
@login_required
@csrf.exempt
def ai_suggest_slot():
    """Suggest the optimal complete schedule assignment for a subject.
    
    Request JSON:
        section_id: int
        subject_id: int
        curriculum_id: int (optional)
        schedule_id: int (optional, for edit mode — exclude self)
        academic_year: str
        semester: str
    
    Response JSON:
        success: bool
        suggestion: {
            schedule_type: 'Lecture' | 'Laboratory'
            faculty_id: int
            faculty_name: str
            day_of_week: str
            room_id: int
            room_name: str
            start_time: str (HH:MM)
            end_time: str (HH:MM)
            confidence: int (0-100)
            reasons: [str]
        }
        fallback_message: str (if no perfect slot found)
    """
    data = request.get_json()
    section_id = data.get('section_id')
    subject_id = data.get('subject_id')
    
    # 1. Get subject info
    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({'success': False, 'error': 'Subject not found'}), 404
    
    # 2. Determine schedule type
    schedule_type = 'Laboratory' if subject.lab_units and subject.lab_units > 0 else 'Lecture'
    units = subject.lab_units if schedule_type == 'Laboratory' else subject.lec_units
    
    # 3. Get settings for time bounds
    settings = AcademicSettings.get_current()
    
    # 4. Get all existing schedules for conflict checking
    all_schedules = Schedule.query.filter_by(
        academic_year=data.get('academic_year', settings.academic_year),
        semester=data.get('semester', settings.semester),
        is_archived=False
    ).all()
    
    # 5. Find best faculty
    best_faculty = _find_best_faculty(subject_id, section_id, schedule_type, all_schedules)
    
    # 6. Find best day
    best_day = _find_best_day(best_faculty.id if best_faculty else None, all_schedules, settings)
    
    # 7. Find best room  
    best_room = _find_best_room(schedule_type, subject, all_schedules, best_day, settings)
    
    # 8. Find best time
    best_time = _find_best_time(
        section_id, best_faculty.id if best_faculty else None, 
        best_room.id if best_room else None, best_day,
        units, all_schedules, settings
    )
    
    if not all([best_faculty, best_day, best_room, best_time]):
        return jsonify({
            'success': False,
            'fallback_message': 'Could not find a conflict-free slot. Try manual assignment.',
            'partial': {
                'faculty_id': best_faculty.id if best_faculty else None,
                'day_of_week': best_day,
                'room_id': best_room.id if best_room else None,
            }
        })
    
    # 9. Calculate overall confidence
    confidence = _calculate_suggestion_confidence(
        best_faculty, best_day, best_room, best_time, all_schedules
    )
    
    return jsonify({
        'success': True,
        'suggestion': {
            'schedule_type': schedule_type,
            'faculty_id': best_faculty.id,
            'faculty_name': best_faculty.full_name,
            'day_of_week': best_day,
            'room_id': best_room.id,
            'room_name': f"{best_room.room_name} ({best_room.building.building_name})",
            'start_time': best_time['start'].strftime('%H:%M'),
            'end_time': best_time['end'].strftime('%H:%M'),
            'confidence': confidence,
            'reasons': best_time.get('reasons', [])
        }
    })
```

### Helper Functions (Leverage Existing Logic)

```python
def _find_best_faculty(subject_id, section_id, schedule_type, all_schedules):
    """Find the best faculty for this subject using FacultySubjectAssignment + workload."""
    from app.services.recommendation_engine import recommendation_engine
    
    # Get faculty assigned to this subject
    alternatives = recommendation_engine._find_alternative_faculty(
        subject_id=subject_id,
        section_id=section_id,
        schedule_type=schedule_type,
        all_schedules=all_schedules
    )
    
    if alternatives:
        # Return the highest-scored faculty
        return Faculty.query.get(alternatives[0]['faculty_id'])
    
    return None

def _find_best_day(faculty_id, all_schedules, settings):
    """Find the day with least faculty load and best balance."""
    from app.services.recommendation_engine import recommendation_engine
    
    alternatives = recommendation_engine._find_alternative_days(
        faculty_id=faculty_id,
        all_schedules=all_schedules
    )
    
    if alternatives:
        return alternatives[0]['day']
    
    return 'Monday'  # Fallback

def _find_best_room(schedule_type, subject, all_schedules, day, settings):
    """Find the best available room for this type on this day."""
    from app.services.recommendation_engine import recommendation_engine
    
    room_type = 'Laboratory' if schedule_type == 'Laboratory' else 'Lecture Room'
    # PE subjects need Court/Gym
    if subject and 'PE' in (subject.subject_code or '').upper():
        room_type = 'Court/Gym'
    
    alternatives = recommendation_engine._find_alternative_rooms(
        current_room_type=room_type,
        day_of_week=day,
        all_schedules=all_schedules
    )
    
    if alternatives:
        return Room.query.get(alternatives[0]['room_id'])
    
    return None

def _find_best_time(section_id, faculty_id, room_id, day, units, all_schedules, settings):
    """Find the best conflict-free time slot."""
    from app.services.recommendation_engine import recommendation_engine
    
    alternatives = recommendation_engine._find_alternative_times(
        section_id=section_id,
        faculty_id=faculty_id,
        room_id=room_id,
        day_of_week=day,
        duration_units=units,
        all_schedules=all_schedules,
        settings=settings
    )
    
    if alternatives:
        from datetime import time as dt_time
        best = alternatives[0]
        return {
            'start': dt_time.fromisoformat(best['start_time']),
            'end': dt_time.fromisoformat(best['end_time']),
            'reasons': [best.get('reason', '')]
        }
    
    return None
```

---

## Frontend: AI Suggest Button + Auto-Fill

### Button HTML (in form header or after subject selection)

```html
<!-- AI Suggest Button — appears after subject is selected -->
<div id="aiSuggestContainer" class="hidden mb-4">
    <button type="button" id="aiSuggestBtn" onclick="requestAISuggestion()"
            class="w-full py-2.5 px-4 bg-gradient-to-r from-violet-500 to-purple-600 
                   text-white text-xs font-semibold rounded-lg shadow-sm
                   hover:from-violet-600 hover:to-purple-700 
                   transition-all duration-200 flex items-center justify-center gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <!-- Sparkles/magic wand icon -->
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
        </svg>
        <span>AI Suggest Best Slot</span>
    </button>
    <p class="text-[10px] text-gray-400 text-center mt-1">Auto-fill optimal faculty, day, room & time</p>
</div>
```

### JavaScript: Request + Auto-Fill

```javascript
async function requestAISuggestion() {
    const btn = document.getElementById('aiSuggestBtn');
    const suffix = getCurrentFormSuffix(); // '_add' or '_edit'
    
    // Get required fields
    const sectionId = document.getElementById(`section_id${suffix}`)?.value;
    const subjectId = document.getElementById(`subject_id${suffix}`)?.value;
    const curriculumId = document.getElementById(`curriculum_id${suffix}`)?.value;
    
    if (!sectionId || !subjectId) {
        showToast('Please select a section and subject first', 'warning');
        return;
    }
    
    // Loading state
    btn.disabled = true;
    btn.innerHTML = `
        <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/>
            <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        <span>Finding best slot...</span>
    `;
    
    try {
        const response = await fetch('/schedule/ai-suggest-slot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_id: parseInt(sectionId),
                subject_id: parseInt(subjectId),
                curriculum_id: curriculumId ? parseInt(curriculumId) : null,
                academic_year: currentAcademicYear,
                semester: currentSemester
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Auto-fill with animation
            await autoFillFields(data.suggestion, suffix);
            showToast(`AI suggested slot (${data.suggestion.confidence}% confidence)`, 'success');
        } else {
            showToast(data.fallback_message || 'No optimal slot found', 'warning');
            // Partial fill if available
            if (data.partial) {
                await autoFillPartial(data.partial, suffix);
            }
        }
    } catch (error) {
        showToast('Failed to get AI suggestion', 'error');
        console.error('AI suggest error:', error);
    } finally {
        // Restore button
        btn.disabled = false;
        btn.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
            </svg>
            <span>AI Suggest Best Slot</span>
        `;
    }
}

async function autoFillFields(suggestion, suffix) {
    const fields = [
        { id: `schedule_type${suffix}`, value: suggestion.schedule_type, type: 'radio' },
        { id: `faculty_id${suffix}`, value: suggestion.faculty_id, type: 'select' },
        { id: `day_of_week${suffix}`, value: suggestion.day_of_week, type: 'select' },
        { id: `room_id${suffix}`, value: suggestion.room_id, type: 'select' },
        { id: `start_time${suffix}`, value: suggestion.start_time, type: 'time' },
    ];
    
    // Fill fields sequentially with slight delay for visual feedback
    for (const field of fields) {
        const el = document.getElementById(field.id);
        if (!el) continue;
        
        // Highlight animation
        el.classList.add('ring-2', 'ring-violet-300', 'ring-offset-1');
        
        if (field.type === 'radio') {
            // Handle radio button (schedule type)
            const radio = document.querySelector(`input[name="schedule_type${suffix}"][value="${field.value}"]`);
            if (radio) radio.click();
        } else if (field.type === 'select') {
            el.value = field.value;
            el.dispatchEvent(new Event('change', { bubbles: true }));
        } else if (field.type === 'time') {
            el.value = field.value;
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        // Remove highlight after animation
        await new Promise(r => setTimeout(r, 200));
        setTimeout(() => {
            el.classList.remove('ring-2', 'ring-violet-300', 'ring-offset-1');
        }, 1000);
    }
}
```

### Show Button After Subject Selection

```javascript
// In the subject change handler (existing code):
document.getElementById(`subject_id${suffix}`).addEventListener('change', function() {
    const container = document.getElementById('aiSuggestContainer');
    if (this.value) {
        container.classList.remove('hidden');
    } else {
        container.classList.add('hidden');
    }
});
```

---

## Implementation Steps

### Step 1: Create Backend Endpoint
1. Add `POST /schedule/ai-suggest-slot` to `app/routes/schedule.py`
2. Implement helper functions leveraging existing `recommendation_engine` methods
3. Add confidence calculation

### Step 2: Add Button to Class Form
1. Add AI Suggest button HTML to `_class_form_content.html` after the subject selector
2. Add `aiSuggestContainer` div with hidden class

### Step 3: Add JavaScript Logic
1. Add `requestAISuggestion()` function
2. Add `autoFillFields()` with sequential animation
3. Add subject change listener to show/hide button
4. Ensure auto-fill triggers the existing conflict check flow

### Step 4: Add to Exam Form (Optional)
1. Similar button in `_exam_form_content.html`
2. Endpoint variant for exam scheduling

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/routes/schedule.py` | **Medium addition** | New `/ai-suggest-slot` endpoint + helper functions |
| `app/templates/schedule/_class_form_content.html` | **Small edit** | Add AI Suggest button after subject selector |
| `app/static/js/schedule/auto_conflict_check.js` | **Medium edit** | Add `requestAISuggestion()` + auto-fill logic |
| `app/templates/schedule/_exam_form_content.html` | **Small edit** | Same button for exams (optional) |

---

## Testing Checklist

- [ ] Button hidden until subject is selected
- [ ] Button shows loading state during API call
- [ ] All fields auto-fill correctly (type, faculty, day, room, time)
- [ ] Auto-fill triggers existing conflict check → should return 0 conflicts
- [ ] Visual highlight animation plays on each field as it's filled
- [ ] User can override any auto-filled field manually
- [ ] If no conflict-free slot exists → shows fallback message
- [ ] Partial fill works when some but not all fields can be determined
- [ ] Edit mode works (excludes current schedule from conflict check)
- [ ] Confidence score shown in success toast
- [ ] Button resets after success or failure
- [ ] Mobile: button is full-width and accessible
- [ ] Dark mode: button gradient and highlights work correctly
- [ ] Performance: suggestion returns in <2 seconds
