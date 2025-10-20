# Lecture/Lab-Based Time Slot Generation

**Feature:** AI scheduler generates alternative time slots based on schedule type (lecture or lab) using academic unit standards.

**Date Implemented:** January 19, 2025

---

## 📚 Academic Standards

### Lecture Units
- **Formula:** 1 lecture unit = 1 hour of instruction
- **Example:** 3 lec units = 3 hours of class time
- **Typical Range:** 1.0 - 5.0 lecture units

### Lab Units
- **Formula:** 1 lab unit = 3 lab hours (academic standard)
- **Example:** 1 lab unit = 3 hours of laboratory work
- **Rationale:** Lab work requires more contact hours due to hands-on activities, setup, and cleanup time
- **Typical Range:** 1.0 - 2.0 lab units

### Combined (Both)
- **Formula:** total_units (lec_units + lab_units) for combined lecture+lab sessions
- **Example:** 3 lec units + 1 lab unit = 4 total units = 4 hours
- **Use Case:** Single time block for integrated lecture and lab instruction
- **Note:** This is different from separate lecture and lab sessions

---

## 🎯 Implementation Overview

### 1. AI Scheduler Logic (`app/ai_scheduler.py`)

**Modified Function:** `_find_alternative_times()`

```python
def _find_alternative_times(self, schedule_data: Dict, existing_schedules: List, 
                           day: str) -> List[Dict]:
    """Find alternative time slots on the same day based on schedule type (lecture/lab/both)"""
    
    # Get subject and schedule type
    subject_id = schedule_data.get('subject_id')
    subject = Subject.query.get(subject_id) if subject_id else None
    schedule_type = schedule_data.get('schedule_type', 'lecture')
    
    # Calculate required duration based on schedule type
    if subject:
        if schedule_type == 'lab':
            # Lab: 1 lab_unit = 3 hours
            required_hours = float(subject.lab_units) * 3.0 if subject.lab_units else 3.0
        elif schedule_type == 'both':
            # Combined: total_units (lec + lab together)
            required_hours = float(subject.total_units) if subject.total_units else 3.0
        else:
            # Lecture: 1 lec_unit = 1 hour
            required_hours = float(subject.lec_units) if subject.lec_units else 1.5
        required_minutes = int(required_hours * 60)
    else:
        required_minutes = 90  # Default fallback
```

**Key Changes:**
- Detects `schedule_type` from schedule data
- Uses `lec_units` for lecture schedules
- Uses `lab_units * 3` for lab schedules
- Maintains 30-minute increment slots within 8 AM - 5 PM window

---

### 2. Automatic Recheck System (`app/static/js/schedule/auto_conflict_check.js`)

**Modified Function:** `setupAutoCheckForModal()`

```javascript
function setupAutoCheckForModal(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Fields that trigger conflict check (schedule_type added)
    const fields = [
        'subject_id' + suffix,
        'faculty_id' + suffix,
        'room_id' + suffix,
        'day_of_week' + suffix,
        'schedule_type' + suffix,  // ← NEW: Triggers recheck on type change
        'start_time' + suffix,
        'end_time' + suffix
    ];
    
    // Attach change listeners
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('change', () => {
                scheduleAutoConflictCheck(mode);
            });
        }
    });
}
```

**Modified Function:** `performAutoConflictCheck()`

```javascript
function performAutoConflictCheck(mode) {
    // ... existing code ...
    
    // Include schedule_type in request data
    const requestData = {
        section_id: parseInt(sectionId),
        subject_id: subjectId ? parseInt(subjectId) : null,
        faculty_id: facultyId ? parseInt(facultyId) : null,
        room_id: roomId ? parseInt(roomId) : null,
        day_of_week: dayOfWeek,
        schedule_type: scheduleType,  // ← NEW: Sent to backend
        start_time: startTime,
        end_time: endTime,
        schedule_id: scheduleId ? parseInt(scheduleId) : null
    };
    
    // Send to /schedule/ai-check-conflicts
}
```

**Key Changes:**
- `schedule_type` added to field listener list
- Changing between "Lecture" and "Lab" now triggers automatic recheck
- `schedule_type` included in API request to backend

---

### 3. Backend Route (`app/routes/schedule.py`)

**Modified Route:** `/schedule/ai-check-conflicts`

```python
@schedule_bp.route('/ai-check-conflicts', methods=['POST'])
@login_required
@csrf.exempt
def ai_check_conflicts():
    """AI-powered conflict detection with schedule type support"""
    
    data = request.get_json()
    
    # Parse schedule data (schedule_type added)
    section_id = data.get('section_id')
    subject_id = data.get('subject_id')
    faculty_id = data.get('faculty_id')
    room_id = data.get('room_id')
    day_of_week = data.get('day_of_week')
    schedule_type = data.get('schedule_type', 'lecture')  # ← NEW: Default to lecture
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    
    # Prepare schedule data for AI
    schedule_data = {
        'section_id': section_id,
        'subject_id': subject_id,
        'faculty_id': faculty_id,
        'room_id': room_id,
        'day_of_week': day_of_week,
        'schedule_type': schedule_type,  # ← NEW: Passed to AI scheduler
        'start_time': start_time,
        'end_time': end_time
    }
    
    # Get AI analysis
    analysis = ai_scheduler.analyze_schedule_conflicts(schedule_data, existing_schedules)
```

**Key Changes:**
- Extracts `schedule_type` from request JSON
- Defaults to `'lecture'` if not provided
- Passes `schedule_type` to AI scheduler for duration calculation

---

## 📊 Example Scenarios

### Scenario 1: Lecture Schedule (3 lec units)

**Subject:** "Database Systems" - 3.0 lec units, 0.0 lab units

**Schedule Type:** Lecture

**AI Recommendation:**
```
Alternative Times:
  • 08:00 AM - 11:00 AM (3.0 hrs)  ← 3 lec units = 3 hours
  • 01:00 PM - 04:00 PM (3.0 hrs)
  • 09:00 AM - 12:00 PM (3.0 hrs)
```

**Calculation:**
- Required hours = 3.0 lec units × 1 hour = **3 hours**
- Required minutes = 3 × 60 = **180 minutes**
- Slots: 08:00-11:00, 08:30-11:30, 09:00-12:00, etc.

---

### Scenario 2: Lab Schedule (1 lab unit)

**Subject:** "Programming Lab" - 0.0 lec units, 1.0 lab unit

**Schedule Type:** Lab

**AI Recommendation:**
```
Alternative Times:
  • 08:00 AM - 11:00 AM (3.0 hrs)  ← 1 lab unit = 3 hours
  • 01:00 PM - 04:00 PM (3.0 hrs)
  • 09:00 AM - 12:00 PM (3.0 hrs)
```

**Calculation:**
- Required hours = 1.0 lab unit × 3 hours = **3 hours**
- Required minutes = 3 × 60 = **180 minutes**
- Slots: 08:00-11:00, 08:30-11:30, 09:00-12:00, etc.

---

### Scenario 3: Combined Subject (3 lec + 1 lab)

**Subject:** "Data Structures" - 3.0 lec units, 1.0 lab unit

#### If Schedule Type = **Lecture:**
```
Alternative Times:
  • 08:00 AM - 11:00 AM (3.0 hrs)  ← Uses lec_units
  • 01:00 PM - 04:00 PM (3.0 hrs)
```
- Calculation: 3.0 lec units × 1 = **3 hours**

#### If Schedule Type = **Lab:**
```
Alternative Times:
  • 08:00 AM - 11:00 AM (3.0 hrs)  ← Uses lab_units × 3
  • 01:00 PM - 04:00 PM (3.0 hrs)
```
- Calculation: 1.0 lab unit × 3 = **3 hours**

**Note:** Same duration in this case, but different source fields!

---

### Scenario 4: Combined Schedule (3 lec + 1 lab = Both)

**Subject:** "Data Structures" - 3.0 lec units, 1.0 lab unit

**Schedule Type:** Both (Combined Lecture + Lab)

**AI Recommendation:**
```
Alternative Times:
  • 08:00 AM - 12:00 PM (4.0 hrs)  ← Uses total_units (3 + 1 = 4)
  • 01:00 PM - 05:00 PM (4.0 hrs)
  • 09:00 AM - 01:00 PM (4.0 hrs)
```

**Calculation:**
- Required hours = total_units = 3.0 lec + 1.0 lab = **4 hours**
- Required minutes = 4 × 60 = **240 minutes**
- Slots: 08:00-12:00, 08:30-12:30, 09:00-13:00, etc.

**Use Case:** Integrated session where lecture theory is immediately followed by lab practice in the same time block.

---

### Scenario 5: Short Lecture (1.5 lec units)

**Subject:** "Ethics" - 1.5 lec units, 0.0 lab units

**Schedule Type:** Lecture

**AI Recommendation:**
```
Alternative Times:
  • 08:00 AM - 09:30 AM (1.5 hrs)  ← 1.5 lec units = 1.5 hours
  • 10:00 AM - 11:30 AM (1.5 hrs)
  • 01:00 PM - 02:30 PM (1.5 hrs)
```

**Calculation:**
- Required hours = 1.5 lec units × 1 = **1.5 hours**
- Required minutes = 1.5 × 60 = **90 minutes**
- Slots: 08:00-09:30, 08:30-10:00, 09:00-10:30, etc.

---

### Scenario 6: Long Lab (2 lab units)

**Subject:** "Advanced Programming Lab" - 0.0 lec units, 2.0 lab units

**Schedule Type:** Lab

**AI Recommendation:**
```
Alternative Times:
  • 08:00 AM - 02:00 PM (6.0 hrs)  ← 2 lab units = 6 hours
  • 09:00 AM - 03:00 PM (6.0 hrs)
  • 10:00 AM - 04:00 PM (6.0 hrs)
```

**Calculation:**
- Required hours = 2.0 lab units × 3 = **6 hours**
- Required minutes = 6 × 60 = **360 minutes**
- Slots must fit within 8 AM - 5 PM window (9 hours)

---

## 🔄 User Workflow

### Creating a Lecture Schedule

1. **Open Add Schedule Modal**
   - Click "Add Schedule" button

2. **Fill in Schedule Details**
   - **Subject:** Select subject (e.g., "Database Systems - 3.0 lec, 0.0 lab")
   - **Schedule Type:** Select "Lecture"
   - **Faculty:** Select faculty member
   - **Day:** Select day of week
   - **Room:** Select room

3. **AI Automatic Check Triggers**
   - System detects `schedule_type = 'lecture'`
   - Calculates duration: `3.0 lec_units × 1 = 3 hours`
   - Checks conflicts with 3-hour time blocks
   - Shows recommendations in right panel

4. **Review AI Recommendations**
   ```
   ✅ No conflicts detected!
   
   Alternative Times:
     • 08:00 AM - 11:00 AM (3.0 hrs) ✓ Available
     • 01:00 PM - 04:00 PM (3.0 hrs) ✓ Available
   ```

5. **Click Recommended Time Slot**
   - Start time and end time auto-fill
   - Conflict check runs again automatically

6. **Submit Schedule**
   - Button enabled after conflicts resolved
   - Schedule saved with correct duration

---

### Creating a Lab Schedule

1. **Open Add Schedule Modal**
   - Click "Add Schedule" button

2. **Fill in Schedule Details**
   - **Subject:** Select subject (e.g., "Programming Lab - 0.0 lec, 1.0 lab")
   - **Schedule Type:** Select "Lab" ← **KEY DIFFERENCE**
   - **Faculty:** Select faculty member
   - **Day:** Select day of week
   - **Room:** Select lab room

3. **AI Automatic Check Triggers**
   - System detects `schedule_type = 'lab'`
   - Calculates duration: `1.0 lab_units × 3 = 3 hours` ← **Uses 3x multiplier**
   - Checks conflicts with 3-hour time blocks
   - Shows recommendations in right panel

4. **Review AI Recommendations**
   ```
   ✅ No conflicts detected!
   
   Alternative Times:
     • 08:00 AM - 11:00 AM (3.0 hrs) ✓ Available (Lab)
     • 01:00 PM - 04:00 PM (3.0 hrs) ✓ Available (Lab)
   ```

5. **Click Recommended Time Slot**
   - Start time and end time auto-fill with 3-hour duration
   - Conflict check runs again automatically

6. **Submit Schedule**
   - Button enabled after conflicts resolved
   - Lab schedule saved with correct 3-hour duration

---

### Switching Between Lecture and Lab

**Scenario:** User changes schedule type after entering subject

1. **Initial State:**
   - Subject: "Data Structures" (3 lec, 1 lab)
   - Schedule Type: "Lecture"
   - AI shows 3-hour slots based on lec_units

2. **User Changes to Lab:**
   - Dropdown changes from "Lecture" → "Lab"
   - `change` event fires on `schedule_type_add` field
   - **Automatic recheck triggered** (800ms debounce)

3. **AI Recalculation:**
   - Detects new `schedule_type = 'lab'`
   - Recalculates duration: `1.0 lab_units × 3 = 3 hours`
   - Updates recommendations in right panel

4. **User Sees Updated Recommendations:**
   ```
   Alternative Times:
     • 08:00 AM - 11:00 AM (3.0 hrs)  ← Now based on lab_units
     • 01:00 PM - 04:00 PM (3.0 hrs)
   ```

**No manual "Check with AI" button needed!**

---

## 🧪 Testing Scenarios

### Test 1: Lecture Schedule (3 lec units)
**Subject:** Database Systems (3.0 lec, 0.0 lab)
**Schedule Type:** Lecture
**Expected Duration:** 3 hours
**Expected Slots:** 08:00-11:00, 09:00-12:00, 01:00-04:00

### Test 2: Lab Schedule (1 lab unit)
**Subject:** Programming Lab (0.0 lec, 1.0 lab)
**Schedule Type:** Lab
**Expected Duration:** 3 hours (1 lab unit × 3)
**Expected Slots:** 08:00-11:00, 09:00-12:00, 01:00-04:00

### Test 3: Combined Subject - Lecture Mode
**Subject:** Data Structures (3.0 lec, 1.0 lab)
**Schedule Type:** Lecture
**Expected Duration:** 3 hours (uses lec_units)
**Expected Slots:** 08:00-11:00, 09:00-12:00, 01:00-04:00

### Test 4: Combined Subject - Lab Mode
**Subject:** Data Structures (3.0 lec, 1.0 lab)
**Schedule Type:** Lab
**Expected Duration:** 3 hours (1 lab unit × 3)
**Expected Slots:** 08:00-11:00, 09:00-12:00, 01:00-04:00

### Test 5: Combined Subject - Both Mode
**Subject:** Data Structures (3.0 lec, 1.0 lab)
**Schedule Type:** Both
**Expected Duration:** 4 hours (3 + 1 = 4 total units)
**Expected Slots:** 08:00-12:00, 09:00-01:00, 01:00-05:00

### Test 6: Short Lecture (1.5 lec units)
**Subject:** Ethics (1.5 lec, 0.0 lab)
**Schedule Type:** Lecture
**Expected Duration:** 1.5 hours
**Expected Slots:** 08:00-09:30, 10:00-11:30, 01:00-02:30

### Test 7: Long Lab (2 lab units)
**Subject:** Advanced Lab (0.0 lec, 2.0 lab)
**Schedule Type:** Lab
**Expected Duration:** 6 hours (2 lab units × 3)
**Expected Slots:** 08:00-02:00, 09:00-03:00, 10:00-04:00

### Test 8: Type Change Triggers Recheck
**Steps:**
1. Select subject "Data Structures" (3 lec, 1 lab)
2. Set schedule type to "Lecture"
3. Verify AI shows 3-hour slots
4. Change schedule type to "Lab"
5. **Verify automatic recheck triggers** (no manual button click)
6. Verify AI shows 3-hour slots (but calculated from lab_units)
7. Change schedule type to "Both"
8. **Verify automatic recheck triggers again**
9. Verify AI shows 4-hour slots (calculated from total_units)

### Test 9: Subject Not Found Fallback
**Subject ID:** Invalid/null
**Schedule Type:** Lecture
**Expected Duration:** 1.5 hours (90-minute default)
**Expected Slots:** 08:00-09:30, 10:00-11:30, 01:00-02:30

---

## 🔍 Edge Cases

### Edge Case 1: Subject with 0 lab units
**Subject:** "Theory" (3.0 lec, 0.0 lab)
**Schedule Type:** Lab
**Calculation:** `0.0 lab_units × 3 = 0 hours`
**Fallback:** Uses default 3.0 hours
```python
if subject.lab_units:
    required_hours = float(subject.lab_units) * 3.0
else:
    required_hours = 3.0  # Default fallback
```

### Edge Case 2: Subject with 0 lecture units
**Subject:** "Pure Lab" (0.0 lec, 2.0 lab)
**Schedule Type:** Lecture
**Calculation:** `0.0 lec_units × 1 = 0 hours`
**Fallback:** Uses default 1.5 hours
```python
if subject.lec_units:
    required_hours = float(subject.lec_units)
else:
    required_hours = 1.5  # Default fallback
```

### Edge Case 3: Subject not found
**Subject ID:** null
**Schedule Type:** Any
**Fallback:** Uses default 90 minutes (1.5 hours)
```python
if subject:
    # Calculate based on type
else:
    required_minutes = 90  # Default
```

### Edge Case 4: Both type with zero total units
**Subject:** Invalid subject with 0.0 lec and 0.0 lab
**Schedule Type:** Both
**Calculation:** `total_units = 0.0 + 0.0 = 0 hours`
**Fallback:** Uses default 3.0 hours
```python
if schedule_type == 'both':
    required_hours = float(subject.total_units) if subject.total_units else 3.0
```

### Edge Case 5: Very long lab (6+ hours)
**Subject:** "Capstone Project" (0.0 lec, 3.0 lab)
**Schedule Type:** Lab
**Calculation:** `3.0 lab_units × 3 = 9 hours`
**Problem:** Exceeds 8 AM - 5 PM window (9 hours total)
**Result:** No available slots (none fit completely)
```python
if end_datetime.time() > time(17, 0):
    break  # Skip slots that exceed 5 PM
```

---

## 🎨 UI Behavior

### Split-Screen Layout

**Left Panel (Form):**
- Subject dropdown
- Faculty dropdown
- **Schedule Type dropdown** ← User changes this
- Day of week
- Start time / End time
- Room dropdown

**Right Panel (AI Detection):**
- Auto-check status indicator (checking/success/error)
- Conflict list (if any)
- **Recommendations with duration** ← Updates on type change
  ```
  Alternative Times:
    • 08:00 AM - 11:00 AM (3.0 hrs)
    • 01:00 PM - 04:00 PM (3.0 hrs)
  ```

### Button States

**When schedule_type changes:**
1. Button text: "Waiting for conflict check..."
2. Button disabled (gray)
3. After 800ms: API call to `/schedule/ai-check-conflicts`
4. AI calculates duration based on new type
5. Button enabled if no conflicts (blue)

---

## 📖 Technical Notes

### Why 3x Multiplier for Labs?

**Academic Standard:**
- Theory/lecture classes: 1 unit = 1 hour per week
- Laboratory classes: 1 unit = 3 hours per week

**Rationale:**
- Lab work requires more contact time
- Setup and teardown activities
- Hands-on practice and troubleshooting
- Individual student guidance
- Safety protocols and procedures

**Example:**
- "Computer Programming I" = 3 lec units + 1 lab unit
- Lecture schedule: 3 hours per week (e.g., MWF 8-9 AM)
- Lab schedule: 3 hours per week (e.g., Thursday 1-4 PM)
- Total contact hours: 6 hours per week

### Database Schema

**subjects table:**
```sql
lec_units DECIMAL(3,1)  -- e.g., 3.0, 1.5, 2.0
lab_units DECIMAL(3,1)  -- e.g., 1.0, 0.0, 2.0
```

**schedules table:**
```sql
schedule_type VARCHAR(20) DEFAULT 'lecture'  -- 'lecture' or 'lab'
```

### Time Slot Generation Algorithm

```python
# Start from 8:00 AM
current_time = time(8, 0)

# Generate slots with 30-minute increments
while current_time.hour < 17:
    end_datetime = start_datetime + timedelta(minutes=required_minutes)
    
    # Only include if end time is before or at 5:00 PM
    if end_datetime.time() <= time(17, 0):
        time_slots.append((current_time, end_datetime.time()))
    
    # Move to next 30-minute increment
    current_time += timedelta(minutes=30)
```

**Example with 3-hour duration:**
- 08:00 - 11:00 ✓
- 08:30 - 11:30 ✓
- 09:00 - 12:00 ✓
- ...
- 02:00 - 05:00 ✓ (last valid slot)
- 02:30 - 05:30 ✗ (exceeds 5 PM cutoff)

---

## 🚀 Future Enhancements

### 1. Subject Type Auto-Detection
**Idea:** Automatically set schedule_type based on subject units
```python
if subject.lab_units > 0 and subject.lec_units == 0:
    schedule_type = 'lab'  # Pure lab subject
elif subject.lec_units > 0:
    schedule_type = 'lecture'  # Has lecture component
```

### 2. Block Scheduling for Labs
**Idea:** Recommend longer continuous blocks for labs
```python
if schedule_type == 'lab':
    prefer_afternoon_slots = True  # Less disruption to morning classes
    prefer_continuous_blocks = True  # Avoid split lab sessions
```

### 3. Room Type Validation
**Idea:** Warn if lecture scheduled in lab room or vice versa
```python
if schedule_type == 'lab' and room.room_type != 'Laboratory':
    warnings.append('Lab schedule in non-lab room')
```

### 4. Multi-Day Lab Sessions
**Idea:** Support labs that span multiple days
```python
if required_hours > 6:
    recommend_split_across_days = True
    # Suggest 2 days × 3 hours instead of 1 day × 6 hours
```

---

## 📝 Summary

**What Changed:**
- AI scheduler now respects schedule type (lecture vs lab)
- Lecture schedules use `lec_units × 1 hour`
- Lab schedules use `lab_units × 3 hours` (academic standard)
- Changing schedule type triggers automatic recheck (no manual button)

**Files Modified:**
1. `app/ai_scheduler.py` - Duration calculation logic
2. `app/static/js/schedule/auto_conflict_check.js` - Added schedule_type to listeners
3. `app/routes/schedule.py` - Added schedule_type to API payload

**Academic Compliance:**
- Follows standard credit hour formula
- 1 lecture unit = 1 contact hour
- 1 lab unit = 3 contact hours

**User Experience:**
- Automatic rechecking when type changes
- Clear duration display (e.g., "3.0 hrs")
- Intelligent recommendations based on subject structure

---

**✅ Feature Complete and Ready for Testing!**
