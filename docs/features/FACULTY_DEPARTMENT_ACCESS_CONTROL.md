# Faculty Subject Assignment - Department Access Control

## Overview
Implemented department-based access control for faculty subject assignments. Users (specifically Deans) can now only assign subjects from curricula within their assigned departments.

## Changes Made

### 1. Modified `app/routes/faculty.py` - `index()` Route (Lines ~86-105)
**Purpose:** Filter curricula by user's department access

**Changes:**
- Added department filtering to curricula query
- Deans can only see curricula from their assigned departments
- Admins continue to see all curricula (unrestricted access)

```python
# Apply department filter for non-admin users (Deans)
user_department_ids = current_user.get_department_ids()
if user_department_ids is not None:  # None means admin (access to all)
    curricula_query = curricula_query.filter(Curriculum.department_id.in_(user_department_ids))
```

### 2. Modified `app/routes/faculty.py` - `assign_subjects()` Route (Lines ~360-440)
**Purpose:** Validate department access when assigning multiple subjects

**Changes:**
- Added department validation before assigning each subject
- Tracks unauthorized subjects separately from already-assigned subjects
- Provides clear error messages explaining why subjects were rejected

**Validation Logic:**
```python
# Get curriculum's department through relationship chain
# Subject -> Semester -> YearLevel -> Curriculum -> Department
curriculum = subject.semester.year_level.curriculum if subject.semester and subject.semester.year_level else None

# Validate user has access to this subject's department
if user_department_ids is not None:  # None means admin (access to all)
    if not curriculum or curriculum.department_id not in user_department_ids:
        unauthorized_subjects.append(subject.subject_code)
        skipped_count += 1
        continue
```

**Enhanced Error Messages:**
- Success message includes both already-assigned and unauthorized subjects
- Dedicated error message when all subjects are unauthorized: "Cannot assign subjects from other departments"
- Lists up to 3 unauthorized subjects by code, with "and X more" for additional ones

### 3. Modified `app/routes/faculty.py` - `assign_subject()` Route (Lines ~480-510)
**Purpose:** Validate department access when assigning a single subject

**Changes:**
- Added same department validation as batch assignment
- Provides specific error message before checking if already assigned
- Early return prevents further processing of unauthorized subjects

**Error Message:**
```
"You do not have permission to assign subjects from other departments. 
Subject 'XXX' is not in your department."
```

## Access Control Flow

### For Admins (Full Access)
1. `current_user.get_department_ids()` returns `None`
2. All curricula are visible in the assignment modal
3. All subjects can be assigned to any faculty
4. No validation restrictions applied

### For Deans (Department-Restricted Access)
1. `current_user.get_department_ids()` returns list of assigned department IDs (e.g., `[1, 4]`)
2. Only curricula from those departments appear in the assignment modal
3. Backend validation ensures submitted subjects belong to dean's departments
4. Unauthorized subjects are rejected with clear error messages

## Security Layers

### Layer 1: Frontend Filtering (UI)
- Curricula query filtered by department in `index()` route
- Deans only see subjects from their departments in the modal
- Prevents accidental submission of unauthorized subjects

### Layer 2: Backend Validation (API)
- Both `assign_subjects()` and `assign_subject()` validate department access
- Prevents direct API calls from bypassing UI restrictions
- Provides detailed error messages for troubleshooting

## Testing

### Test File: `tests/test_faculty_department_restriction.py`
Verifies:
- ✅ Admins have unrestricted access (get_department_ids returns None)
- ✅ Deans have restricted access (get_department_ids returns specific IDs)
- ✅ Curricula filtering works correctly
- ✅ Subject access follows curriculum department relationship
- ✅ Validation logic correctly identifies accessible vs restricted subjects

### Test Results
```
✅ Admin User: admin@norzagaray.edu (Role: admin)
✅ Dean User: dean@norzagaray.edu (Role: dean)

📋 Dean's Department IDs: [1, 4]
📋 Admin's Department IDs: None (None = All departments)

✅ Department-based access control is working correctly!
```

## User Experience

### Dean Attempting to Assign Subjects

**Before Submission:**
- Opens "Assign Subjects" modal for a faculty member
- Only sees curricula from their assigned departments
- Subject list automatically filtered by accessible departments

**During Submission:**
- Selects subjects and clicks "Assign Selected Subjects"
- Backend validates each subject's department

**After Submission - Success:**
```
Successfully assigned 3 subjects to John Doe for 2024-2025 - 1st Semester!
```

**After Submission - Partial Success:**
```
Successfully assigned 2 subjects to John Doe for 2024-2025 - 1st Semester! 
(1 already assigned: CS101; 2 not in your department: ENG201, MATH301)
```

**After Submission - All Unauthorized:**
```
Cannot assign subjects from other departments. 
You can only assign subjects from your department.
```

## Database Relationships

### Department Access Chain
```
User (Dean)
  └─> user_departments (junction table)
      └─> Department
          └─> Curriculum
              └─> YearLevel
                  └─> Semester
                      └─> Subject
```

### Key Models
- **User**: Has `get_department_ids()` method returning None (admin) or list of department IDs (dean)
- **Curriculum**: Has `department_id` foreign key linking to Department
- **Subject**: Accessed through relationship chain to determine department

## Implementation Notes

### Why This Approach?
1. **Defense in Depth**: Frontend filtering + backend validation
2. **User-Friendly**: Clear error messages explain restrictions
3. **Maintainable**: Reuses existing `get_department_ids()` method
4. **Scalable**: Works with multiple department assignments per user

### Relationship Chain Traversal
```python
curriculum = subject.semester.year_level.curriculum
```
This safely traverses the relationship chain with null checks, ensuring no errors even if relationships are incomplete.

### Admin Detection
```python
if user_department_ids is not None:
    # User is a Dean - apply restrictions
else:
    # user_department_ids is None - Admin has full access
```

## Future Enhancements

### Potential Improvements
1. Add department filter dropdown in faculty assignment modal UI
2. Show department name next to each curriculum in the modal
3. Add activity log entries when unauthorized assignment attempts are made
4. Implement real-time validation feedback in the modal before submission

### Additional Considerations
- Consider restricting faculty viewing to same department
- Add department-based filtering for faculty workload reports
- Implement similar restrictions for schedule management

## Files Modified
1. `app/routes/faculty.py` (3 functions updated)
   - `index()` - Added curricula filtering
   - `assign_subjects()` - Added batch validation
   - `assign_subject()` - Added single validation

## Files Created
1. `tests/test_faculty_department_restriction.py` - Comprehensive test coverage

## Verification Steps
1. ✅ Test passes and shows correct department filtering
2. ✅ Admins see all curricula and can assign any subject
3. ✅ Deans only see curricula from their departments
4. ✅ Backend validation rejects unauthorized subjects
5. ✅ Error messages are clear and actionable

---

**Implementation Date:** October 24, 2025  
**Status:** ✅ Complete and Tested  
**Breaking Changes:** None - Admins retain full access
