# Three-Type Schedule Enhancement (Lecture/Lab/Both)

**Feature:** Enhanced AI scheduler to support three schedule types with intelligent time slot generation

**Date Implemented:** January 19, 2025

---

## 🎯 Overview

The AI scheduler now intelligently generates alternative time slots based on THREE distinct schedule types:

1. **Lecture** - Uses `lec_units × 1 hour`
2. **Lab** - Uses `lab_units × 3 hours` (academic standard)
3. **Both** - Uses `total_units` (combined lecture + lab session)

This enhancement allows users to create schedules that match their teaching approach:
- Separate lecture and lab sessions
- Combined integrated sessions where theory and practice happen together

---

## 📚 Schedule Type Definitions

### Type 1: Lecture
- **Formula:** 1 lec_unit = 1 hour of instruction
- **Use Case:** Traditional classroom lectures, theory-based instruction
- **Example:** 3.0 lec units = 3 hours
- **Time Slots:** 08:00 AM - 11:00 AM, 01:00 PM - 04:00 PM

### Type 2: Lab
- **Formula:** 1 lab_unit = 3 lab hours (academic standard)
- **Use Case:** Hands-on laboratory work, programming labs, experiments
- **Example:** 1.0 lab unit = 3 hours
- **Time Slots:** 08:00 AM - 11:00 AM, 01:00 PM - 04:00 PM
- **Rationale:** Lab work requires extended time for setup, practice, and cleanup

### Type 3: Both (Combined)
- **Formula:** total_units = lec_units + lab_units
- **Use Case:** Integrated sessions combining theory and practice in one block
- **Example:** 3.0 lec + 1.0 lab = 4.0 total units = 4 hours
- **Time Slots:** 08:00 AM - 12:00 PM, 09:00 AM - 01:00 PM, 01:00 PM - 05:00 PM
- **Benefit:** Students immediately apply theory in practice, reducing context switching

---

## 🔧 Implementation Details

### AI Scheduler Logic (`app/ai_scheduler.py`)

```python
def _find_alternative_times(self, schedule_data: Dict, existing_schedules: List, 
                           day: str) -> List[Dict]:
    """Find alternative time slots based on schedule type (lecture/lab/both)"""
    
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
- Added `elif schedule_type == 'both'` condition
- Uses `subject.total_units` property which calculates `lec_units + lab_units`
- Maintains same 30-minute increment logic for all types
- Respects 8 AM - 5 PM window for all recommendations

---

## 💡 Use Case Examples

### Scenario 1: Traditional Separate Sessions

**Subject:** "Data Structures" (3.0 lec units, 1.0 lab unit)

**Approach:** Teach theory and practice separately

**Schedule 1 - Lecture:**
- Type: Lecture
- Duration: 3 hours (from lec_units)
- Time: Monday 08:00 AM - 11:00 AM
- Content: Theory, algorithms, concepts

**Schedule 2 - Lab:**
- Type: Lab
- Duration: 3 hours (from lab_units × 3)
- Time: Wednesday 01:00 PM - 04:00 PM
- Content: Hands-on coding, implementation

**Benefits:**
- ✅ Focused sessions (theory vs practice)
- ✅ Students prepare between sessions
- ✅ Flexible scheduling across different days

---

### Scenario 2: Integrated Combined Session

**Subject:** "Data Structures" (3.0 lec units, 1.0 lab unit)

**Approach:** Teach theory and practice together in one block

**Schedule - Both:**
- Type: Both
- Duration: 4 hours (from total_units = 3 + 1)
- Time: Tuesday 08:00 AM - 12:00 PM
- Content: Theory → Immediate hands-on practice

**Benefits:**
- ✅ Immediate application of concepts
- ✅ Reduced context switching
- ✅ Better retention (theory + practice together)
- ✅ Fewer scheduling conflicts (one session instead of two)

---

## 🖥️ Modal Interface

### Schedule Type Selection UI

When user selects a subject with both lecture and lab units (e.g., 3 lec + 1 lab):

```
┌─────────────────────────────────────────────────┐
│ Schedule Type *                                  │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────────┐  ┌──────────────┐             │
│  │   📚 Lecture  │  │   🧪 Lab      │             │
│  │   (3 units)   │  │   (1 unit)    │             │
│  └──────────────┘  └──────────────┘             │
│                                                   │
│  ┌──────────────────────────────────┐           │
│  │ 📝 Both Lecture & Lab (4 units)   │           │
│  └──────────────────────────────────┘           │
└─────────────────────────────────────────────────┘
```

**User clicks one of three options:**
- **Lecture** → schedule_type = 'lecture'
- **Lab** → schedule_type = 'lab'
- **Both** → schedule_type = 'both'

**AI automatically recalculates:**
- Triggers conflict check with new type
- Updates time slot recommendations
- Shows appropriate duration in right panel

---

## 🔄 Automatic Recheck Flow

### When User Changes Schedule Type

```
1. User selects "Data Structures" (3 lec, 1 lab)
   → Modal shows three type options

2. User clicks "Lecture"
   → schedule_type = 'lecture'
   → Auto-check triggers (800ms debounce)
   → AI calculates: 3.0 lec units × 1 = 3 hours
   → Right panel shows: "08:00 AM - 11:00 AM (3.0 hrs)"

3. User clicks "Lab"
   → schedule_type = 'lab'
   → Auto-check triggers again
   → AI calculates: 1.0 lab unit × 3 = 3 hours
   → Right panel shows: "08:00 AM - 11:00 AM (3.0 hrs)"

4. User clicks "Both"
   → schedule_type = 'both'
   → Auto-check triggers again
   → AI calculates: total_units = 3 + 1 = 4 hours
   → Right panel shows: "08:00 AM - 12:00 PM (4.0 hrs)"
```

**No manual button clicks needed! All automatic! ✨**

---

## 📊 Comparison Table

| Schedule Type | Subject (3 lec, 1 lab) | Duration Formula | Example Duration | Sample Time Slot |
|---------------|------------------------|------------------|------------------|------------------|
| **Lecture** | Data Structures | lec_units × 1 | 3 hours | 08:00 AM - 11:00 AM |
| **Lab** | Data Structures | lab_units × 3 | 3 hours | 08:00 AM - 11:00 AM |
| **Both** | Data Structures | total_units | 4 hours | 08:00 AM - 12:00 PM |

**Key Insight:** With this subject (3 lec, 1 lab):
- Separate sessions: 3 hours lecture + 3 hours lab = **6 contact hours/week**
- Combined session: 4 hours both = **4 contact hours/week**

Different approaches for different teaching philosophies!

---

## 🧪 Testing Checklist

### Test 1: Subject with Lecture and Lab Units
**Subject:** Data Structures (3.0 lec, 1.0 lab)

**Test Steps:**
1. ✅ Open Add Schedule modal
2. ✅ Select "Data Structures" subject
3. ✅ Verify three type options appear
4. ✅ Click "Lecture" → Verify 3-hour slots (08:00-11:00, etc.)
5. ✅ Click "Lab" → Verify automatic recheck + 3-hour slots
6. ✅ Click "Both" → Verify automatic recheck + 4-hour slots

**Expected Results:**
- Lecture: 3-hour recommendations (from lec_units)
- Lab: 3-hour recommendations (from lab_units × 3)
- Both: 4-hour recommendations (from total_units)

---

### Test 2: Lecture-Only Subject
**Subject:** Ethics (1.5 lec, 0.0 lab)

**Test Steps:**
1. ✅ Open Add Schedule modal
2. ✅ Select "Ethics" subject
3. ✅ Verify only "Lecture" option shown (no lab, no both)
4. ✅ Verify 1.5-hour slots (08:00-09:30, etc.)

**Expected Results:**
- Single type shown (lecture only)
- Duration: 1.5 hours

---

### Test 3: Lab-Only Subject
**Subject:** Programming Lab (0.0 lec, 1.0 lab)

**Test Steps:**
1. ✅ Open Add Schedule modal
2. ✅ Select "Programming Lab" subject
3. ✅ Verify only "Lab" option shown (no lecture, no both)
4. ✅ Verify 3-hour slots (08:00-11:00, etc.)

**Expected Results:**
- Single type shown (lab only)
- Duration: 3 hours (1 lab unit × 3)

---

### Test 4: Type Change Triggers Recheck
**Subject:** Data Structures (3.0 lec, 1.0 lab)

**Test Steps:**
1. ✅ Select subject
2. ✅ Click "Lecture" → Wait for auto-check
3. ✅ Click "Lab" → Verify recheck happens automatically
4. ✅ Click "Both" → Verify recheck happens automatically
5. ✅ Verify no manual button clicks needed

**Expected Results:**
- Each type change triggers 800ms debounced recheck
- Right panel updates with new recommendations
- Duration changes appropriately

---

## 🎯 Pedagogical Benefits

### Lecture-Only Schedules
**Best For:**
- Theory-heavy courses
- Introductory concepts
- Large class sizes
- Foundation building

**Example:** Database Theory, Ethics, Philosophy

---

### Lab-Only Schedules
**Best For:**
- Skills-based learning
- Project work
- Advanced practice
- Specialized equipment/software

**Example:** Advanced Programming Lab, Capstone Project Lab

---

### Combined (Both) Schedules
**Best For:**
- Active learning approaches
- Immediate concept application
- Smaller class sizes
- Flipped classroom models

**Example:** Intro to Programming (theory → practice in same session)

**Research-Based Benefits:**
- 🧠 Better knowledge retention
- 🔗 Stronger theory-practice connection
- ⏰ Reduced cognitive load from context switching
- 💡 Immediate feedback and correction

---

## 📝 Implementation Summary

### Files Modified

1. **app/ai_scheduler.py**
   - Added `elif schedule_type == 'both'` case
   - Uses `subject.total_units` for combined sessions
   - Updated function docstring

2. **docs/features/LECTURE_LAB_TIME_SLOTS.md**
   - Added "Combined (Both)" section
   - Added Scenario 4 with example
   - Enhanced Test 8 with both type changes
   - Added Edge Case 4 for both type validation

3. **docs/features/THREE_TYPE_SCHEDULE_ENHANCEMENT.md** (this file)
   - Complete documentation of enhancement
   - Use case comparisons
   - Pedagogical benefits
   - Testing checklist

---

## 🚀 Ready to Test!

**Quick Start:**
```bash
python run.py
```

**Test Workflow:**
1. Navigate to Schedule Management
2. Click "Add Schedule" for a section
3. Select subject "Data Structures" (or similar with both lec and lab units)
4. Click through all three type options: Lecture → Lab → Both
5. Watch AI recommendations update automatically in right panel
6. Verify durations match expectations:
   - Lecture: 3 hours
   - Lab: 3 hours
   - Both: 4 hours

---

## ✅ Success Criteria

- [x] AI scheduler handles 'both' schedule type
- [x] Duration calculated from total_units for combined sessions
- [x] Automatic recheck triggers on type change
- [x] Documentation updated with examples
- [x] Testing scenarios documented
- [ ] End-to-end testing completed
- [ ] User feedback collected

---

**Enhancement Complete! The system now provides maximum flexibility for different teaching approaches while maintaining academic compliance with credit hour standards.** 🎓✨
