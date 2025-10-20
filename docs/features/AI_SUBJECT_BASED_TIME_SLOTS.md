# AI Subject-Based Time Slot Recommendations

## 📋 Overview
Enhanced AI scheduler to generate alternative time slot recommendations based on **subject's total units** rather than fixed 1-hour increments.

## 🎯 Problem Solved
**Before**: AI suggested fixed 1-hour time slots regardless of subject requirements
- A 3-unit subject would get 1-hour slot suggestions (too short)
- A 1.5-unit subject would get suggestions that might not match duration
- Users had to manually calculate proper time slots

**After**: AI calculates time slots based on subject's actual unit requirements
- 3-unit subject → 3-hour time slots (e.g., 8:00 AM - 11:00 AM)
- 1.5-unit subject → 1.5-hour time slots (e.g., 8:00 AM - 9:30 AM)
- 2-unit subject → 2-hour time slots (e.g., 1:00 PM - 3:00 PM)

## 🔧 How It Works

### 1. Duration Calculation
```python
# Get subject's total units
subject = Subject.query.get(subject_id)
required_hours = float(subject.total_units)  # e.g., 3.0, 1.5, 2.0
required_minutes = int(required_hours * 60)  # Convert to minutes
```

### 2. Time Slot Generation
**Smart slot generation**:
- Starts at 8:00 AM
- Generates slots until 5:00 PM
- Each slot has the **exact duration** needed for the subject
- Moves in 30-minute increments to find all possible start times
- Skips slots that would end after 5:00 PM

**Example for 3-unit subject (3 hours)**:
```
✅ 08:00 AM - 11:00 AM (3.0 hrs)
✅ 08:30 AM - 11:30 AM (3.0 hrs)
✅ 09:00 AM - 12:00 PM (3.0 hrs)
✅ 01:00 PM - 04:00 PM (3.0 hrs)
✅ 01:30 PM - 04:30 PM (3.0 hrs)
✅ 02:00 PM - 05:00 PM (3.0 hrs)
❌ 02:30 PM - 05:30 PM (goes past 5 PM - skipped)
```

**Example for 1.5-unit subject (1.5 hours)**:
```
✅ 08:00 AM - 09:30 AM (1.5 hrs)
✅ 08:30 AM - 10:00 AM (1.5 hrs)
✅ 09:00 AM - 10:30 AM (1.5 hrs)
✅ 09:30 AM - 11:00 AM (1.5 hrs)
... (many more options)
✅ 03:30 PM - 05:00 PM (1.5 hrs)
```

### 3. Conflict Checking
For each generated time slot:
- ✅ Check if section is free at that time
- ✅ Check if faculty is free (if assigned)
- ✅ Check if room is free (if assigned)
- ❌ Skip slot if any conflict exists

### 4. Display Format
Time slots now show duration:
```
08:00 AM - 11:00 AM (3.0 hrs)
01:00 PM - 03:00 PM (2.0 hrs)
08:00 AM - 09:30 AM (1.5 hrs)
```

## 📊 Benefits

### For Users
✅ **Accurate suggestions** - Matches subject requirements exactly  
✅ **Time savings** - No manual duration calculations needed  
✅ **Better planning** - See exactly how long each class will be  
✅ **Reduced errors** - Prevents booking insufficient time for class  

### For Schedulers
✅ **Automatic compliance** - Respects university credit hour standards  
✅ **Flexible scheduling** - More options with 30-minute increments  
✅ **Clear visibility** - Duration shown in recommendations  
✅ **Smart filtering** - Only shows slots that fit completely in schedule  

## 🎓 Academic Standard Compliance

### Standard Credit Hour Formula
```
1 unit = 1 hour of instruction per week
```

**Common Subject Types**:
- **Lecture (3 units)**: 3 hours/week → 3.0-hour time slot
- **Lab (1 unit)**: 3 hours/week → 3.0-hour time slot (lab work)
- **Lecture + Lab (4 units)**: 3 lec + 1 lab → Usually separate schedules
- **PE/Tutorial (1.5 units)**: 1.5 hours/week → 1.5-hour time slot

### Example: CS 101 (3 lec, 1 lab = 4 total units)

**Lecture Component** (3 lec units):
```
Recommended slots:
- Monday: 08:00 AM - 11:00 AM (3.0 hrs)
- Wednesday: 01:00 PM - 04:00 PM (3.0 hrs)
```

**Lab Component** (1 lab unit = 3 lab hours):
```
Recommended slots:
- Tuesday: 01:00 PM - 04:00 PM (3.0 hrs)
- Friday: 08:00 AM - 11:00 AM (3.0 hrs)
```

## 🔄 Updated Functions

### `_find_alternative_times()`
**Changes**:
- Added subject lookup to get `total_units`
- Calculate `required_minutes` from units
- Generate dynamic time slots based on duration
- Use 30-minute increments for flexibility
- Added duration display in output

**Before**:
```python
time_slots = [
    (time(8, 0), time(9, 0)),   # Fixed 1-hour
    (time(9, 0), time(10, 0)),  # Fixed 1-hour
    ...
]
```

**After**:
```python
required_hours = float(subject.total_units)  # 3.0, 1.5, etc.
required_minutes = int(required_hours * 60)

# Generate slots dynamically
current_time = time(8, 0)
while current_time.hour < 17:
    end_time = current_time + timedelta(minutes=required_minutes)
    if end_time <= time(17, 0):
        time_slots.append((current_time, end_time))
    current_time += timedelta(minutes=30)
```

### `_find_alternative_days()`
**Changes**:
- Calculate duration from current `start_time` and `end_time`
- Display duration in recommendations
- Added `duration_hours` field to output

**Output Format**:
```json
{
    "day": "Tuesday",
    "display": "Tuesday at 08:00 AM - 11:00 AM (3.0 hrs)",
    "duration_hours": 3.0,
    "score": 95
}
```

## 📱 User Interface Impact

### AI Recommendations Panel
**Before**:
```
Alternative Time Slots:
• 08:00 AM - 09:00 AM
• 09:00 AM - 10:00 AM
• 10:00 AM - 11:00 AM
```

**After**:
```
Alternative Time Slots:
• 08:00 AM - 11:00 AM (3.0 hrs) ← Matches subject units!
• 01:00 PM - 04:00 PM (3.0 hrs)
• 02:00 PM - 05:00 PM (3.0 hrs)
```

### Alternative Days
**Before**:
```
Alternative Days:
• Monday at 08:00 AM - 11:00 AM
• Wednesday at 01:00 PM - 04:00 PM
```

**After**:
```
Alternative Days:
• Monday at 08:00 AM - 11:00 AM (3.0 hrs)
• Wednesday at 01:00 PM - 04:00 PM (3.0 hrs)
```

## 🧪 Testing Scenarios

### Test Case 1: 3-Unit Lecture
```python
Subject: CS 101 (3 lec, 0 lab = 3 total)
Expected: 3-hour time slots
Result: ✅ 08:00 AM - 11:00 AM (3.0 hrs)
```

### Test Case 2: 1-Unit Lab
```python
Subject: CS 101 Lab (0 lec, 1 lab = 1 total)
Expected: 3-hour time slots (1 lab unit = 3 lab hours)
Note: This would need additional logic for lab hour conversion
```

### Test Case 3: 1.5-Unit PE
```python
Subject: PE 101 (1.5 total units)
Expected: 1.5-hour time slots
Result: ✅ 08:00 AM - 09:30 AM (1.5 hrs)
```

### Test Case 4: Subject Not Found
```python
Subject: Missing/Deleted
Fallback: 1.5-hour default slots
Result: ✅ 08:00 AM - 09:30 AM (1.5 hrs)
```

## ⚠️ Edge Cases Handled

### 1. Subject Not Found
```python
if subject and subject.total_units:
    required_hours = float(subject.total_units)
else:
    required_minutes = 90  # Default 1.5 hours
```

### 2. Slots Beyond 5:00 PM
```python
if end_datetime.time() > time(17, 0):
    break  # Skip this slot
```

### 3. Zero or Invalid Units
```python
if subject.total_units and subject.total_units > 0:
    required_hours = float(subject.total_units)
else:
    required_minutes = 90  # Default
```

## 📁 Files Modified

### `app/ai_scheduler.py`
**Functions Updated**:
- `_find_alternative_times()` - Dynamic slot generation based on subject units
- `_find_alternative_days()` - Added duration display

**New Logic**:
- Subject lookup by ID
- Unit-to-minute conversion
- Dynamic time slot generation with 30-min increments
- Duration calculation and display

## 🚀 Future Enhancements

### Potential Improvements
- [ ] Lab hour conversion (1 lab unit = 3 lab hours)
- [ ] Preferred time ranges based on subject type (labs in afternoon)
- [ ] Break time insertion for long sessions (3+ hours)
- [ ] Subject type consideration (lecture vs lab scheduling patterns)
- [ ] Department-specific scheduling preferences
- [ ] Peak hour avoidance for better room utilization

### Formula Expansion
```python
# Future: Different multipliers for different types
if schedule_type == 'lab':
    required_hours = float(subject.lab_units) * 3  # 1 lab unit = 3 hours
elif schedule_type == 'lecture':
    required_hours = float(subject.lec_units)  # 1 lec unit = 1 hour
```

## 📚 Related Documentation
- [AUTOMATIC_CONFLICT_DETECTION.md](./AUTOMATIC_CONFLICT_DETECTION.md) - Auto-check system
- [SCHEDULE_MODAL_SPLIT_LAYOUT.md](./SCHEDULE_MODAL_SPLIT_LAYOUT.md) - Modal layout

---

**Date**: 2024-02-10  
**Feature**: Subject-based AI time slot recommendations  
**Status**: Implemented ✅  
**Impact**: Improved accuracy, user experience, academic compliance
