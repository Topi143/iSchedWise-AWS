# Schedule Badge Count Fix

**Date**: October 27, 2025  
**Issue**: Schedule count badges showing incorrect numbers (including schedules with archived faculty/rooms)  
**Status**: ✅ Fixed

---

## 🎯 Problem Statement

The schedule count badges (e.g., "12 Schedules" on section cards) were counting **all** active schedules, including:
- ❌ Schedules with archived faculty members
- ❌ Schedules with rooms from archived buildings
- ❌ Schedules from sections that should be filtered out

**Example:**
```
BSCS-1A
Bachelor of Science in Computer Science
12 Schedules  ← Should only show 8 (4 have archived faculty)
```

This caused confusion because:
1. Badge showed "12 schedules"
2. User opens section
3. Only 8 schedules actually display (4 filtered out due to archived faculty)
4. Numbers don't match! 😕

---

## 🔧 Solution Implemented

Updated all schedule count calculations to use the **same filtering logic** as the schedule display queries.

### Changes Made:

1. **Section Schedule Counts** (Lines 702-754)
2. **Faculty Schedule Counts** (Lines 893-943)  
3. **Room Schedule Counts** (Lines 1098-1138)
4. **Exam Schedule Counts** (Lines 1182-1233)

---

## 📝 Implementation Details

### 1. Section Schedule Count (Class Tab)

**Before:**
```python
count = Schedule.query.filter_by(
    section_id=section.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).count()
```

**After:**
```python
count = Schedule.query.filter_by(
    section_id=section.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).outerjoin(Faculty, Schedule.faculty_id == Faculty.id)\
 .outerjoin(Room, Schedule.room_id == Room.id)\
 .outerjoin(Building, Room.building_id == Building.id)\
 .filter(
     or_(
         Schedule.faculty_id == None,
         and_(Faculty.is_active == True, Faculty.is_archived == False)
     ),
     or_(
         Schedule.room_id == None,
         and_(
             Room.is_available == True,
             or_(
                 Building.id == None,
                 and_(Building.is_active == True, Building.is_archived == False)
             )
         )
     )
 ).count()
```

**Impact:**
- Badge only counts schedules with active faculty and rooms from active buildings
- Badge count now matches displayed schedule count

---

### 2. Faculty Schedule Count (Faculty Tab)

**Before:**
```python
count = Schedule.query.filter_by(
    faculty_id=faculty.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).count()
```

**After:**
```python
count = Schedule.query.filter_by(
    faculty_id=faculty.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).outerjoin(Room, Schedule.room_id == Room.id)\
 .outerjoin(Building, Room.building_id == Building.id)\
 .join(Section, Schedule.section_id == Section.id)\
 .join(Department, Section.department_id == Department.id)\
 .filter(
     or_(
         Schedule.room_id == None,
         and_(
             Room.is_available == True,
             or_(
                 Building.id == None,
                 and_(Building.is_active == True, Building.is_archived == False)
             )
         )
     ),
     Department.is_active == True,
     Department.is_archived == False
 ).count()
```

**Impact:**
- Faculty badge only counts schedules with active rooms and from active departments
- Excludes schedules from archived departments

---

### 3. Room Schedule Count (Room Tab)

**Before:**
```python
count = Schedule.query.filter_by(
    room_id=room.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).count()
```

**After:**
```python
count = Schedule.query.filter_by(
    room_id=room.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).outerjoin(Faculty, Schedule.faculty_id == Faculty.id)\
 .join(Section, Schedule.section_id == Section.id)\
 .join(Department, Section.department_id == Department.id)\
 .filter(
     or_(
         Schedule.faculty_id == None,
         and_(Faculty.is_active == True, Faculty.is_archived == False)
     ),
     Department.is_active == True,
     Department.is_archived == False
 ).count()
```

**Impact:**
- Room badge only counts schedules with active faculty and from active departments
- Excludes schedules with archived faculty

---

### 4. Exam Schedule Count (Exam Tab)

**Before:**
```python
count = ExamSchedule.query.filter_by(
    section_id=section.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).count()
```

**After:**
```python
count = ExamSchedule.query.filter_by(
    section_id=section.id,
    is_active=True,
    academic_year=current_settings.academic_year,
    semester=current_settings.semester
).outerjoin(Faculty, ExamSchedule.faculty_id == Faculty.id)\
 .outerjoin(Room, ExamSchedule.room_id == Room.id)\
 .outerjoin(Building, Room.building_id == Building.id)\
 .filter(
     or_(
         ExamSchedule.faculty_id == None,
         and_(Faculty.is_active == True, Faculty.is_archived == False)
     ),
     or_(
         ExamSchedule.room_id == None,
         and_(
             Room.is_available == True,
             or_(
                 Building.id == None,
                 and_(Building.is_active == True, Building.is_archived == False)
             )
         )
     )
 ).count()
```

**Impact:**
- Exam badge only counts exam schedules with active faculty and rooms from active buildings
- Badge count matches displayed exam schedule count

---

## ✅ Before vs After

### Class Schedule Tab

**Before:**
```
BSCS-1A
Bachelor of Science in Computer Science
12 Schedules  ← Includes 4 schedules with archived faculty

[Click to open]
→ Shows only 8 schedules (4 filtered out)
```

**After:**
```
BSCS-1A
Bachelor of Science in Computer Science
8 Schedules  ← Accurate count excluding archived faculty

[Click to open]
→ Shows exactly 8 schedules ✅
```

---

### Faculty Tab

**Before:**
```
John Doe
Computer Science Department
15 Schedules  ← Includes 3 schedules from archived department

[Click to open]
→ Shows only 12 schedules (3 filtered out)
```

**After:**
```
John Doe
Computer Science Department
12 Schedules  ← Accurate count excluding archived department schedules

[Click to open]
→ Shows exactly 12 schedules ✅
```

---

### Room Tab

**Before:**
```
Room 101
Building A
20 Schedules  ← Includes 5 schedules with archived faculty

[Click to open]
→ Shows only 15 schedules (5 filtered out)
```

**After:**
```
Room 101
Building A
15 Schedules  ← Accurate count excluding archived faculty

[Click to open]
→ Shows exactly 15 schedules ✅
```

---

## 🎯 Key Benefits

### 1. **Accurate Badge Counts**
✅ Badge numbers now match displayed schedule counts  
✅ No more confusion about missing schedules  
✅ Consistent filtering across badges and displays  

### 2. **User Experience**
✅ Users can trust the badge numbers  
✅ No surprise discrepancies when opening sections  
✅ Clear indication of actual active schedule count  

### 3. **Data Integrity**
✅ Badge respects archive status throughout relationships  
✅ Consistent with schedule display filtering  
✅ Maintains referential integrity  

---

## 🧪 Testing Scenarios

### Test 1: Section with Archived Faculty
1. Create section with 10 schedules
2. Archive faculty member with 3 schedules
3. **Expected Result:**
   - Badge shows "7 Schedules" (not 10)
   - Opening section shows exactly 7 schedules
   - ✅ Badge matches display

### Test 2: Faculty in Archived Department
1. Faculty has 15 schedules across 2 departments
2. Archive one department (5 schedules)
3. **Expected Result:**
   - Badge shows "10 Schedules" (not 15)
   - Opening faculty shows exactly 10 schedules
   - ✅ Badge matches display

### Test 3: Room with Mixed Schedules
1. Room has 20 schedules
2. 5 schedules have archived faculty
3. 3 schedules are from archived department
4. **Expected Result:**
   - Badge shows "12 Schedules" (not 20)
   - Opening room shows exactly 12 schedules
   - ✅ Badge matches display

### Test 4: Exam Schedules
1. Section has 8 exam schedules
2. 2 exams use rooms from archived building
3. **Expected Result:**
   - Badge shows "6 Exam Schedules" (not 8)
   - Opening section shows exactly 6 exam schedules
   - ✅ Badge matches display

---

## 📋 Related Changes

### Previous Implementation:
- **SCHEDULE_ARCHIVED_ITEMS_FILTER.md** - Added filtering to schedule display queries

### This Implementation:
- **SCHEDULE_BADGE_COUNT_FIX.md** - Updated badge counts to match filtered displays

### Consistency:
- Badge count logic now **identical** to display query logic
- Same joins, same filters, same results
- Complete consistency across UI

---

## 🔍 Technical Notes

### Query Pattern Used:

```python
# Pattern for counting schedules with filtered relationships
Schedule.query.filter_by(
    section_id=section.id,
    is_active=True
).outerjoin(Faculty, Schedule.faculty_id == Faculty.id)\
 .outerjoin(Room, Schedule.room_id == Room.id)\
 .outerjoin(Building, Room.building_id == Building.id)\
 .filter(
     or_(
         Schedule.faculty_id == None,  # Allow NULL faculty
         and_(Faculty.is_active == True, Faculty.is_archived == False)
     ),
     or_(
         Schedule.room_id == None,  # Allow NULL room
         and_(
             Room.is_available == True,
             or_(
                 Building.id == None,  # Allow NULL building
                 and_(Building.is_active == True, Building.is_archived == False)
             )
         )
     )
 ).count()
```

### Why `outerjoin()` for Faculty/Room?
- Faculty and room are **optional** (can be NULL)
- `outerjoin()` ensures schedules with NULL faculty/room are still counted
- `or_(foreign_key == None, ...)` pattern allows NULL values through filter

### Why `join()` for Section/Department?
- Section is **required** (never NULL)
- `join()` (INNER JOIN) is more efficient for required relationships
- No need to check for NULL values

---

## 📊 Performance Impact

### Query Complexity:
- **Before**: 1 simple filter query per section/faculty/room
- **After**: 1 filter query with 2-3 joins per section/faculty/room

### Optimization Considerations:
- **Indexes Required**: Ensure indexes on all foreign key columns
- **Join Cost**: Additional joins add minimal overhead with proper indexes
- **Count Caching**: Consider caching counts if performance becomes issue

### Recommended Indexes:
```sql
-- Schedule table
CREATE INDEX idx_schedules_section_id ON schedules(section_id);
CREATE INDEX idx_schedules_faculty_id ON schedules(faculty_id);
CREATE INDEX idx_schedules_room_id ON schedules(room_id);
CREATE INDEX idx_schedules_is_active ON schedules(is_active);

-- Faculty table
CREATE INDEX idx_faculty_is_archived ON faculty(is_archived);
CREATE INDEX idx_faculty_is_active ON faculty(is_active);

-- Room table
CREATE INDEX idx_rooms_building_id ON rooms(building_id);
CREATE INDEX idx_rooms_is_available ON rooms(is_available);

-- Building table
CREATE INDEX idx_buildings_is_archived ON buildings(is_archived);
CREATE INDEX idx_buildings_is_active ON buildings(is_active);

-- Department table
CREATE INDEX idx_departments_is_archived ON departments(is_archived);
CREATE INDEX idx_departments_is_active ON departments(is_active);
```

---

## 🚀 Deployment Notes

### No Database Changes:
- ✅ No schema migrations required
- ✅ No data migrations needed
- ✅ Only backend query logic changed

### Immediate Effect:
- Badge counts update immediately on next page load
- No cache clearing required
- No user action needed

### Rollback:
If issues arise, simply revert the `.count()` queries to simple filter counts (remove joins).

---

**Implementation Time**: ~1 hour  
**Lines Changed**: ~200 lines across 4 count calculation sections  
**Complexity**: Medium (replicated join logic from display queries)  
**Testing Required**: Medium (verify badge counts match displays)

---

**Status**: ✅ Implementation Complete  
**Next Steps**: User verification that badge counts match displayed schedules
