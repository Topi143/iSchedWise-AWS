# Schedule Module - Archived Items Filter Implementation

**Date**: October 27, 2025  
**Issue**: Schedules were displaying archived departments, sections, faculty, and rooms  
**Status**: ✅ Fixed

---

## 🎯 Problem Statement

The schedule management module was displaying:
- ❌ Sections from archived departments
- ❌ Schedules with archived faculty members
- ❌ Schedules with rooms from archived buildings
- ❌ Archived departments in filters

This caused confusion and potential data integrity issues when viewing and managing schedules.

---

## 🔧 Solution Implemented

### 1. **Department Filter** (Lines 647-660)
**What Changed:**
- Added `is_archived=False` filter to department queries
- Both admin and dean department lists now exclude archived departments

**Before:**
```python
# Admin - see all departments
departments = Department.query.filter_by(is_active=True)

# Dean - only assigned departments  
departments = Department.query.filter(
    Department.is_active == True,
    Department.id.in_(user_department_ids)
)
```

**After:**
```python
# Admin - see all active, non-archived departments
departments = Department.query.filter_by(
    is_active=True,
    is_archived=False
)

# Dean - only assigned active, non-archived departments
departments = Department.query.filter(
    Department.is_active == True,
    Department.is_archived == False,
    Department.id.in_(user_department_ids)
)
```

---

### 2. **Section List Filter** (Lines 670-684)
**What Changed:**
- Added join to `Department` table
- Filter sections only from non-archived departments

**Before:**
```python
sections_query = Section.query.filter_by(is_active=True)
```

**After:**
```python
sections_query = Section.query.filter_by(is_active=True)\
    .join(Department).filter(
        Department.is_active == True,
        Department.is_archived == False
    )
```

**Impact:**
- Sections from archived departments no longer appear in class/exam schedule lists
- Department dropdown filters only show active departments

---

### 3. **Class Schedule Display** (Lines 707-742)
**What Changed:**
- Added left outer joins to `Faculty`, `Room`, and `Building` tables
- Filter out schedules with archived faculty
- Filter out schedules with rooms from archived buildings

**Before:**
```python
schedules_query = Schedule.query.filter_by(
    section_id=selected_section_id,
    is_active=True
)
```

**After:**
```python
schedules_query = Schedule.query.filter_by(
    section_id=selected_section_id,
    is_active=True
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
 )
```

**Impact:**
- Schedules with archived faculty don't appear in section schedule view
- Schedules using rooms from archived buildings are hidden
- NULL faculty/rooms are still allowed (optional fields)

---

### 4. **Faculty Tab Filter** (Lines 772-849)
**What Changed:**
- Added `is_archived=False` to all faculty queries
- Faculty list only shows active, non-archived faculty
- Updated comments to clarify filtering logic

**Before:**
```python
faculties_query = Faculty.query.filter(
    Faculty.is_active == True,
    Faculty.id.in_(faculty_ids_with_schedules)
)
```

**After:**
```python
faculties_query = Faculty.query.filter(
    Faculty.is_active == True,
    Faculty.is_archived == False,
    Faculty.id.in_(faculty_ids_with_schedules)
)
```

**Impact:**
- Faculty tab no longer lists archived faculty members
- Only shows faculty with schedules in accessible departments

---

### 5. **Faculty Schedule View** (Lines 868-898)
**What Changed:**
- Added joins to filter schedules by room building status and department status
- Excludes schedules with archived rooms/buildings
- Excludes schedules from archived departments

**Before:**
```python
faculty_schedules_query = Schedule.query.filter_by(
    faculty_id=selected_faculty_id,
    is_active=True
)
```

**After:**
```python
faculty_schedules_query = Schedule.query.filter_by(
    faculty_id=selected_faculty_id,
    is_active=True
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
 )
```

**Impact:**
- Faculty schedule view only shows schedules with active rooms and non-archived departments
- Protects against orphaned schedule data

---

### 6. **Room Tab Filter** (Lines 918-1008)
**What Changed:**
- Added outerjoin to `Building` table in all room queries
- Filter rooms only from non-archived buildings
- Applied to all room query branches (admin, dean, filtered, unfiltered)

**Before:**
```python
rooms_query = Room.query.filter(
    Room.is_available == True,
    Room.id.in_(room_ids_with_schedules)
)
```

**After:**
```python
rooms_query = Room.query.filter(
    Room.is_available == True,
    Room.id.in_(room_ids_with_schedules)
).outerjoin(Building).filter(
    or_(
        Building.id == None,
        and_(Building.is_active == True, Building.is_archived == False)
    )
)
```

**Impact:**
- Room tab only lists rooms from active, non-archived buildings
- Prevents selection of rooms in archived buildings

---

### 7. **Room Schedule View** (Lines 1020-1047)
**What Changed:**
- Added joins to filter schedules by faculty, department status
- Excludes schedules with archived faculty
- Excludes schedules from archived departments

**Before:**
```python
room_schedules_query = Schedule.query.filter_by(
    room_id=selected_room_id,
    is_active=True
)
```

**After:**
```python
room_schedules_query = Schedule.query.filter_by(
    room_id=selected_room_id,
    is_active=True
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
 )
```

**Impact:**
- Room schedule view excludes schedules with archived faculty or from archived departments

---

### 8. **Exam Schedule Filter** (Lines 1080-1126)
**What Changed:**
- Applied same filtering logic to exam schedules
- Filters out exam schedules with archived faculty or rooms
- Updated modal data sources to exclude archived items

**Before:**
```python
exam_schedules_query = ExamSchedule.query.filter_by(
    section_id=selected_exam_section_id,
    is_active=True
)

all_faculties = Faculty.query.filter_by(is_active=True)
all_rooms = Room.query.filter_by(is_available=True)
buildings = Building.query.filter_by(is_active=True)
```

**After:**
```python
exam_schedules_query = ExamSchedule.query.filter_by(
    section_id=selected_exam_section_id,
    is_active=True
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
 )

all_faculties = Faculty.query.filter_by(
    is_active=True,
    is_archived=False
)

all_rooms = Room.query.filter_by(is_available=True)\
    .outerjoin(Building).filter(
        or_(
            Building.id == None,
            and_(Building.is_active == True, Building.is_archived == False)
        )
    )

buildings = Building.query.filter_by(
    is_active=True,
    is_archived=False
)
```

**Impact:**
- Exam schedules respect archive status across all entities
- Modal dropdowns only show active, non-archived options

---

### 9. **Import Statement Update** (Line 26)
**What Changed:**
- Added `Building` to the imports from `app.models.building`

**Before:**
```python
from app.models.building import Room
```

**After:**
```python
from app.models.building import Room, Building
```

**Impact:**
- Enables building-level filtering throughout the module

---

## 🎯 Key Benefits

### 1. **Data Integrity**
✅ Prevents users from viewing or interacting with archived data  
✅ Maintains referential integrity in schedule relationships  
✅ Protects against orphaned schedule entries  

### 2. **User Experience**
✅ Clean, focused UI showing only active, relevant data  
✅ Reduces clutter from historical/archived items  
✅ Prevents confusion about which items are currently in use  

### 3. **Department Access Control**
✅ Deans only see sections from their assigned, active departments  
✅ Admin has system-wide view of active departments only  
✅ Consistent filtering across all schedule views  

### 4. **Cascading Filters**
✅ Archived departments → hide sections  
✅ Archived faculty → hide schedules using them  
✅ Archived buildings → hide rooms → hide schedules  
✅ Hierarchical data integrity maintained  

---

## 📋 Testing Checklist

### Test Scenario 1: Archived Department
- [ ] Archive a department in the Departments module
- [ ] Verify its sections don't appear in Class Schedule tab
- [ ] Verify its sections don't appear in Exam Schedule tab
- [ ] Verify department doesn't appear in filter dropdowns

### Test Scenario 2: Archived Faculty
- [ ] Archive a faculty member with existing schedules
- [ ] Verify faculty doesn't appear in Faculty tab list
- [ ] Verify schedules with that faculty are hidden in section view
- [ ] Verify faculty doesn't appear in exam schedule dropdowns

### Test Scenario 3: Archived Building
- [ ] Archive a building with rooms that have schedules
- [ ] Verify rooms from that building don't appear in Room tab
- [ ] Verify schedules using those rooms are hidden
- [ ] Verify building doesn't appear in building filter dropdown

### Test Scenario 4: Multi-Level Archiving
- [ ] Create schedule: Section → Faculty → Room
- [ ] Archive department (section's department)
- [ ] Verify section and all its schedules are hidden
- [ ] Unarchive department, archive faculty
- [ ] Verify schedules with that faculty are hidden
- [ ] Unarchive faculty, archive building
- [ ] Verify schedules with rooms from that building are hidden

### Test Scenario 5: Dean Access Control
- [ ] Login as dean with multiple department access
- [ ] Verify only sections from active, assigned departments show
- [ ] Archive one of dean's departments
- [ ] Verify sections from archived department disappear
- [ ] Verify other department sections still visible

### Test Scenario 6: NULL Handling
- [ ] Create schedule with NULL faculty (optional)
- [ ] Verify schedule still appears (NULL allowed)
- [ ] Create schedule with NULL room (optional)
- [ ] Verify schedule still appears (NULL allowed)
- [ ] Verify filtering doesn't break on NULL foreign keys

---

## 🔄 Related Files

### Modified Files:
- ✅ `app/routes/schedule.py` - Main schedule route with filtering logic

### Database Tables Affected:
- `departments` (is_archived column)
- `faculty` (is_archived column)
- `buildings` (is_archived column)
- `schedules` (filtered by joins)
- `exam_schedules` (filtered by joins)
- `sections` (filtered by department archive status)
- `rooms` (filtered by building archive status)

### No Template Changes Required:
- Templates automatically respect filtered data from backend
- No frontend JavaScript changes needed
- Archive buttons/modals already exist in respective modules

---

## 🚀 Deployment Notes

### Database Requirements:
- ✅ All archive columns already exist (previous implementation)
- ✅ No migrations needed
- ✅ Existing data compatible

### Performance Considerations:
- **Joins Added**: Multiple `outerjoin()` and `join()` calls added
- **Indexes Recommended**: Ensure indexes exist on:
  - `departments.is_archived`
  - `faculty.is_archived`
  - `buildings.is_archived`
  - All foreign key columns

### Rollback Plan:
If issues arise, simply remove the `.outerjoin()` and `.filter()` clauses added in this update. The queries will revert to showing all active items regardless of archive status.

---

## 📚 Technical Notes

### SQLAlchemy Join Types Used:

**`outerjoin()` (LEFT OUTER JOIN)**
- Used when foreign key might be NULL
- Ensures schedules with NULL faculty/rooms still appear
- Example: `Schedule.faculty_id` can be NULL

**`join()` (INNER JOIN)**
- Used when foreign key is required (NOT NULL)
- Only returns rows where relationship exists
- Example: `Schedule.section_id` is always required

### Filter Logic Pattern:

```python
.filter(
    or_(
        foreign_key == None,           # Allow NULL
        and_(
            related_table.is_active == True,
            related_table.is_archived == False
        )
    )
)
```

This pattern ensures:
1. NULL values are allowed (optional relationships)
2. Non-NULL values must be active and non-archived
3. Prevents breaking on missing data

---

## 🎓 Lessons Learned

1. **Cascading Filters**: Archive status must be checked at every relationship level
2. **NULL Handling**: Always use `or_(column == None, ...)` for optional foreign keys
3. **Performance**: Multiple joins require proper indexing strategy
4. **User Experience**: Hidden items are better than disabled/grayed-out items
5. **Data Integrity**: Archive status should propagate through relationships

---

**Implementation Time**: ~2 hours  
**Lines Changed**: ~250 lines across 9 sections  
**Complexity**: Medium (multiple cascading filters with NULL handling)  
**Testing Required**: High (affects core schedule functionality)

---

**Status**: ✅ Implementation Complete  
**Next Steps**: User acceptance testing across all schedule views
