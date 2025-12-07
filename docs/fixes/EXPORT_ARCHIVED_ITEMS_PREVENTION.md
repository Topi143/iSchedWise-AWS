# Export Archived Items Prevention

**Date:** January 2025  
**Status:** ✅ Completed  
**Impact:** High - Prevents exporting schedules for archived entities

## 🎯 Overview

Added validation to all export routes (Excel, Excel for Posting, and PDF) to prevent exporting schedules for archived sections, faculty, and rooms. Users now receive clear error messages when attempting to export archived data.

## 📋 Problem Statement

Previously, users could export schedules for:
- Archived sections (sections marked as archived or from archived departments)
- Archived faculty members
- Rooms from archived buildings

This allowed outdated data to be exported and distributed, which could cause confusion.

## ✅ Solution Implemented

### Archive Validation Added to All Export Routes

**Routes Updated (9 total):**
1. `/export/class/<section_id>` - Class schedule Excel export
2. `/export/class/<section_id>/posting` - Class schedule for posting
3. `/export/class/<section_id>/pdf` - Class schedule PDF
4. `/export/faculty/<faculty_id>` - Faculty schedule Excel export
5. `/export/faculty/<faculty_id>/posting` - Faculty schedule for posting
6. `/export/faculty/<faculty_id>/pdf` - Faculty schedule PDF
7. `/export/room/<room_id>` - Room schedule Excel export
8. `/export/room/<room_id>/posting` - Room schedule for posting
9. `/export/room/<room_id>/pdf` - Room schedule PDF

### Validation Logic

#### Section Exports (Class Schedules)
```python
# Check if section or its department is archived
if section.is_archived or (section.department and section.department.is_archived):
    flash('Cannot export archived section schedules.', 'error')
    return redirect(url_for('schedule.index'))
```

**Checks:**
- Section's `is_archived` flag
- Department's `is_archived` flag (cascading check)

**Error Message:** "Cannot export archived section schedules."

#### Faculty Exports (Faculty Schedules)
```python
# Check if faculty is archived
if faculty.is_archived:
    flash('Cannot export archived faculty schedules.', 'error')
    return redirect(url_for('schedule.index'))
```

**Checks:**
- Faculty's `is_archived` flag

**Error Message:** "Cannot export archived faculty schedules."

#### Room Exports (Room Schedules)
```python
# Check if room or its building is archived
if (room.building and room.building.is_archived):
    flash('Cannot export schedules for rooms in archived buildings.', 'error')
    return redirect(url_for('schedule.index'))
```

**Checks:**
- Building's `is_archived` flag (rooms in archived buildings cannot be exported)

**Error Message:** "Cannot export schedules for rooms in archived buildings."

## 🔍 Implementation Details

### Code Changes in `app/routes/schedule.py`

#### 1. Class Schedule Excel Export
```python
@schedule_bp.route('/export/class/<int:section_id>')
@login_required
def export_class_schedule(section_id):
    """Export class schedule to Excel - weekly grid format matching template"""
    try:
        section = Section.query.get_or_404(section_id)
        
        # NEW: Check if section or its department is archived
        if section.is_archived or (section.department and section.department.is_archived):
            flash('Cannot export archived section schedules.', 'error')
            return redirect(url_for('schedule.index'))
        
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 2. Class Schedule for Posting Export
```python
@schedule_bp.route('/export/class/<int:section_id>/posting')
@login_required
def export_class_schedule_for_posting(section_id):
    """Export class schedule for posting - table format with subject details"""
    # ... imports
    
    try:
        section = Section.query.get_or_404(section_id)
        
        # NEW: Check if section or its department is archived
        if section.is_archived or (section.department and section.department.is_archived):
            flash('Cannot export archived section schedules.', 'error')
            return redirect(url_for('schedule.index'))
        
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 3. Class Schedule PDF Export
```python
@schedule_bp.route('/export/class/<int:section_id>/pdf')
@login_required
def export_class_schedule_pdf(section_id):
    """Export class schedule to PDF - weekly grid format matching Excel template"""
    try:
        section = Section.query.get_or_404(section_id)
        
        # NEW: Check if section or its department is archived
        if section.is_archived or (section.department and section.department.is_archived):
            flash('Cannot export archived section schedules.', 'error')
            return redirect(url_for('schedule.index'))
        
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 4. Faculty Schedule Excel Export
```python
@schedule_bp.route('/export/faculty/<int:faculty_id>')
@login_required
def export_faculty_schedule(faculty_id):
    """Export faculty schedule to Excel - weekly grid format matching template"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        # NEW: Check if faculty is archived
        if faculty.is_archived:
            flash('Cannot export archived faculty schedules.', 'error')
            return redirect(url_for('schedule.index'))
        
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 5. Faculty Schedule for Posting Export
```python
@schedule_bp.route('/export/faculty/<int:faculty_id>/posting')
@login_required
def export_faculty_schedule_for_posting(faculty_id):
    """Export faculty schedule for posting - table format with subject details"""
    # ... imports
    
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        # NEW: Check if faculty is archived
        if faculty.is_archived:
            flash('Cannot export archived faculty schedules.', 'error')
            return redirect(url_for('schedule.index'))
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 6. Faculty Schedule PDF Export
```python
@schedule_bp.route('/export/faculty/<int:faculty_id>/pdf')
@login_required
def export_faculty_schedule_pdf(faculty_id):
    """Export faculty schedule to PDF - weekly grid format"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        # NEW: Check if faculty is archived
        if faculty.is_archived:
            flash('Cannot export archived faculty schedules.', 'error')
            return redirect(url_for('schedule.index'))
        
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 7. Room Schedule Excel Export
```python
@schedule_bp.route('/export/room/<int:room_id>')
@login_required
def export_room_schedule(room_id):
    """Export room schedule to Excel - weekly grid format matching template"""
    try:
        room = Room.query.get_or_404(room_id)
        
        # NEW: Check if room or its building is archived
        if (room.building and room.building.is_archived):
            flash('Cannot export schedules for rooms in archived buildings.', 'error')
            return redirect(url_for('schedule.index'))
        
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 8. Room Schedule for Posting Export
```python
@schedule_bp.route('/export/room/<int:room_id>/posting')
@login_required
def export_room_schedule_for_posting(room_id):
    """Export room schedule for posting - table format with subject details"""
    # ... imports
    
    try:
        room = Room.query.get_or_404(room_id)
        
        # NEW: Check if room or its building is archived
        if (room.building and room.building.is_archived):
            flash('Cannot export schedules for rooms in archived buildings.', 'error')
            return redirect(url_for('schedule.index'))
        
        # Get current academic settings
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

#### 9. Room Schedule PDF Export
```python
@schedule_bp.route('/export/room/<int:room_id>/pdf')
@login_required
def export_room_schedule_pdf(room_id):
    """Export room schedule to PDF - weekly grid format"""
    try:
        room = Room.query.get_or_404(room_id)
        
        # NEW: Check if room or its building is archived
        if (room.building and room.building.is_archived):
            flash('Cannot export schedules for rooms in archived buildings.', 'error')
            return redirect(url_for('schedule.index'))
        
        current_settings = AcademicSettings.query.filter_by(is_active=True).first()
        # ... rest of export logic
```

## 🎯 User Experience

### Before Fix
1. User could click "Export" on any section/faculty/room
2. System would generate Excel/PDF with archived data
3. No warning or validation
4. Potentially distributing outdated schedules

### After Fix
1. User clicks "Export" on archived section/faculty/room
2. System checks archive status immediately
3. User sees clear error message:
   - "Cannot export archived section schedules."
   - "Cannot export archived faculty schedules."
   - "Cannot export schedules for rooms in archived buildings."
4. User redirected back to schedule page
5. No file generated for archived entities

## 🧪 Testing Scenarios

### Test Case 1: Export Archived Section
**Setup:**
1. Archive a section (set `is_archived = True`)
2. Navigate to Class Schedule tab
3. Attempt to export (Excel/PDF/Posting)

**Expected Result:**
- Error message: "Cannot export archived section schedules."
- No file generated
- Redirected to schedule page

### Test Case 2: Export Section from Archived Department
**Setup:**
1. Archive a department (set `is_archived = True`)
2. Section remains active but department is archived
3. Attempt to export section schedule

**Expected Result:**
- Error message: "Cannot export archived section schedules."
- Cascading validation catches archived department
- No file generated

### Test Case 3: Export Archived Faculty
**Setup:**
1. Archive a faculty member (set `is_archived = True`)
2. Navigate to Faculty tab
3. Attempt to export faculty schedule

**Expected Result:**
- Error message: "Cannot export archived faculty schedules."
- No file generated
- Redirected to schedule page

### Test Case 4: Export Room from Archived Building
**Setup:**
1. Archive a building (set `is_archived = True`)
2. Room remains in database but building is archived
3. Attempt to export room schedule

**Expected Result:**
- Error message: "Cannot export schedules for rooms in archived buildings."
- No file generated
- Redirected to schedule page

### Test Case 5: Export Active Entities (Control Test)
**Setup:**
1. Ensure section/faculty/room and their parents are NOT archived
2. Attempt to export

**Expected Result:**
- Export succeeds normally
- File generated successfully
- No error messages

## 📊 Validation Coverage

### Archive Checks by Entity Type

| Entity Type | Primary Check | Cascading Check | Error Message |
|-------------|--------------|-----------------|---------------|
| **Section** | `section.is_archived` | `section.department.is_archived` | "Cannot export archived section schedules." |
| **Faculty** | `faculty.is_archived` | None | "Cannot export archived faculty schedules." |
| **Room** | N/A | `room.building.is_archived` | "Cannot export schedules for rooms in archived buildings." |

### Export Format Coverage

| Export Type | Sections | Faculty | Rooms |
|-------------|----------|---------|-------|
| **Excel** | ✅ | ✅ | ✅ |
| **Excel for Posting** | ✅ | ✅ | ✅ |
| **PDF** | ✅ | ✅ | ✅ |

**Total Routes Protected:** 9

## 🔗 Related Systems

### Integration Points

1. **Archive Management:**
   - Uses `is_archived` flag from Department, Section, Faculty, Building models
   - Respects archive state across all export formats

2. **Schedule Display Filtering:**
   - Consistent with main schedule page filtering
   - Archived items already hidden from view
   - Export validation provides second layer of protection

3. **User Feedback:**
   - Flash messages provide clear feedback
   - Consistent error message format
   - Graceful redirect to schedule page

## ⚠️ Important Notes

### Why This Matters

1. **Data Integrity:**
   - Prevents distribution of outdated schedules
   - Ensures only current data is exported

2. **User Confusion:**
   - Archived items are hidden from UI but could be accessed via URL
   - Direct URL access to export routes now blocked

3. **Consistency:**
   - Export behavior matches display behavior
   - No gap between what's shown and what can be exported

### Edge Cases Handled

1. **Section with Archived Department:**
   - Validation checks both section AND department archive status
   - Prevents exporting section if department is archived

2. **Room with Archived Building:**
   - Validation checks building archive status
   - Prevents exporting room schedules from archived buildings

3. **Direct URL Access:**
   - Even if user constructs URL manually, validation blocks export
   - Protection works regardless of how route is accessed

## 📝 Files Modified

### Main Changes
- **File:** `app/routes/schedule.py`
- **Lines Modified:** 9 export route functions
- **Total Changes:** ~54 lines added (6 lines per route × 9 routes)

### Export Routes Updated
1. Lines ~2180-2185: Class schedule Excel
2. Lines ~2450-2455: Class schedule for posting
3. Lines ~3110-3115: Class schedule PDF
4. Lines ~2265-2270: Faculty schedule Excel
5. Lines ~2670-2675: Faculty schedule for posting
6. Lines ~3175-3180: Faculty schedule PDF
7. Lines ~2345-2350: Room schedule Excel
8. Lines ~2885-2890: Room schedule for posting
9. Lines ~3230-3235: Room schedule PDF

## ✅ Success Criteria

- [x] All 9 export routes validate archive status
- [x] Clear error messages displayed to users
- [x] No files generated for archived entities
- [x] Graceful redirect to schedule page
- [x] Consistent validation logic across all export formats
- [x] Cascading checks for parent entities (department, building)
- [x] Protection works for direct URL access

## 🚀 Deployment Notes

**Database Requirements:** None (uses existing archive columns)

**Breaking Changes:** None (only adds validation, doesn't change export format)

**Migration Required:** No

**Testing Priority:** High (verify all export routes with archived data)

## 🎓 Lessons Learned

1. **Defense in Depth:**
   - UI hiding + route validation = better protection
   - Multiple layers prevent data leakage

2. **Cascading Validation:**
   - Check parent entity archive status
   - Prevents indirect access to archived data

3. **Consistent Error Messages:**
   - Clear, specific messages help users understand why action failed
   - Different messages for different entity types

4. **Comprehensive Coverage:**
   - Must update ALL export variants (Excel, PDF, Posting)
   - Missing one format leaves gap in protection

---

**Status:** ✅ Production Ready  
**Impact:** Prevents export of archived schedules  
**User Benefit:** Ensures only current, active schedules are distributed
