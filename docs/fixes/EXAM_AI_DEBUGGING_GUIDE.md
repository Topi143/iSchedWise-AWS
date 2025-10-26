# Exam AI Network Error - Debugging Guide

**Date:** 2024-02-10  
**Issue:** "❌ Network error - Please check your connection" appears when using exam AI  
**Status:** Enhanced logging added for investigation

---

## 🔍 Investigation Steps

### What We've Done So Far

1. **Fixed JavaScript Element ID Mismatches** (Previous fix)
   - Changed suffix pattern from `'_exam_add'/'_exam_edit'` to `'_add'/'_edit'`
   - This fixed the manual "Check with AI" button

2. **User Reported New Issue**
   - Network error still appears "when i havent change the faculty and the room into a search"
   - This suggests the issue appeared AFTER converting faculty/room to searchable dropdowns

3. **Added Enhanced Debug Logging**
   - Element existence checking (which fields are found/missing)
   - Detailed error messages with HTTP status codes
   - Server-side error details in console

---

## 🎯 Current Form Structure

### Exam Schedule Form Fields (Add Modal)

| Field | Element ID | Type | Notes |
|-------|-----------|------|-------|
| Section | `section_id_exam_add` | Hidden input | Set when modal opens |
| Curriculum | `curriculum_id_exam_add` | Select dropdown | |
| Subject | `subject_id_exam_add` | Select dropdown | Filtered by curriculum |
| Faculty (Search) | `faculty_search_exam_add` | Text input | **NEW: Searchable** |
| Faculty (Value) | `faculty_id_exam_add` | Hidden input | Actual value used by API |
| Room (Search) | `room_search_exam_add` | Text input | **NEW: Searchable** |
| Room (Value) | `room_id_exam_add` | Hidden input | Actual value used by API |
| Exam Date | `exam_date_add` | Date input | |
| Start Time | `start_time_exam_add` | Select dropdown | |
| End Time | `end_time_exam_add` | Select dropdown | |

### JavaScript Expectations

**Auto-Conflict Check (`auto_conflict_check_exam.js`):**
```javascript
const suffix = '_add' or '_edit'
// Looks for these IDs:
'section_id_exam' + suffix  → section_id_exam_add ✅
'subject_id_exam' + suffix  → subject_id_exam_add ✅
'faculty_id_exam' + suffix  → faculty_id_exam_add ✅
'room_id_exam' + suffix     → room_id_exam_add ✅
'exam_date' + suffix        → exam_date_add ✅
'start_time_exam' + suffix  → start_time_exam_add ✅
'end_time_exam' + suffix    → end_time_exam_add ✅
```

**Manual AI Check (`exam_ai.js`):**
```javascript
const suffix = '_add' or '_edit'
// Same pattern as auto-check
```

---

## 🐛 Potential Issues

### Issue 1: Hidden Fields Not Populated
The searchable faculty/room fields use hidden inputs that must be populated when a selection is made:
- `faculty_id_exam_add` - Set by `selectFacultyModalExam()`
- `room_id_exam_add` - Set by `selectRoomModalExam()`

**Problem:** If these hidden fields are not populated when auto-check triggers, the API gets `null` or `undefined` values.

**Test:** Check browser console for log messages showing:
```
[AUTO-CHECK-EXAM] Element check: { facultyId: 'FOUND', roomId: 'FOUND' }
[AUTO-CHECK-EXAM] Form data: { facultyId: null, roomId: null }
```

If elements are FOUND but values are `null`, the search selection functions aren't working.

### Issue 2: Event Listeners Not Attached
The auto-conflict check attaches listeners to the hidden `faculty_id_exam_add` field, but if that field is dynamically created or not present at initialization time, the listener won't work.

**Test:** Check console for:
```
[AUTO-CHECK-EXAM] Listeners attached for add exam modal
```

### Issue 3: Network Request Fails
The fetch request to `/exam-schedule/ai-check-conflicts` might be failing due to:
- Server error (500)
- Invalid data format
- Missing required fields
- CORS issues (unlikely on same domain)

**Test:** Check console for:
```
[AUTO-CHECK-EXAM] Response status: 500 Internal Server Error
```

### Issue 4: Search Functions Not Defined
The HTML references JavaScript functions that might not be loaded:
- `filterFacultyModalExam()`
- `showFacultyDropdownModalExam()`
- `selectFacultyModalExam()`
- `filterRoomsModalExam()`
- `showRoomDropdownModalExam()`
- `selectRoomModalExam()`

**Test:** Check console for errors like:
```
Uncaught ReferenceError: selectFacultyModalExam is not defined
```

---

## 🧪 How to Debug (For User)

### Step 1: Open Browser Developer Console
1. Open exam schedule page
2. Press **F12** to open DevTools
3. Click **Console** tab

### Step 2: Open Exam Schedule Modal
1. Click "Add Exam Schedule" button for any section
2. Watch console output

### Step 3: Look for Element Check Messages
You should see:
```
[AUTO-CHECK-EXAM] Initializing automatic conflict detection for exams...
[AUTO-CHECK-EXAM] Listeners attached for add exam modal
```

### Step 4: Fill Out Form Fields
1. Select **Curriculum** - watch console
2. Select **Subject** - watch console
3. Search and select **Faculty** - watch console
4. Search and select **Room** - watch console
5. Pick **Exam Date** - watch console
6. Select **Start Time** - watch console
7. Select **End Time** - watch console

### Step 5: Check Element Detection
After filling fields, you should see:
```
[AUTO-CHECK-EXAM] Element check: {
  sectionId: 'FOUND',
  subjectId: 'FOUND',
  facultyId: 'FOUND',  ← Must be FOUND
  roomId: 'FOUND',     ← Must be FOUND
  examDate: 'FOUND',
  startTime: 'FOUND',
  endTime: 'FOUND'
}
```

**❌ If ANY show 'MISSING':** That element ID doesn't exist in HTML

### Step 6: Check Form Data Values
You should see:
```
[AUTO-CHECK-EXAM] Form data: {
  sectionId: "1",
  subjectId: "5",
  facultyId: "3",     ← Must have a value, not null
  roomId: "7",        ← Must have a value, not null
  examDate: "2024-02-15",
  startTime: "08:00",
  endTime: "10:00"
}
```

**❌ If facultyId or roomId are `null`:** The search selection didn't populate the hidden field

### Step 7: Check Network Response
If the request is sent, you should see:
```
[AUTO-CHECK-EXAM] Response status: 200 OK
```

**❌ If you see a different status:**
```
[AUTO-CHECK-EXAM] Response status: 500 Internal Server Error
[AUTO-CHECK-EXAM] Error details: {
  message: "Server error (500): ..."
}
```

This means the backend is rejecting the request.

### Step 8: Check for JavaScript Errors
Look for errors BEFORE the network request:
```
❌ Uncaught ReferenceError: selectFacultyModalExam is not defined
❌ Uncaught TypeError: Cannot read property 'value' of null
```

---

## 📝 What to Report Back

Please provide the following from your browser console:

1. **Element Check Results:**
   ```
   [AUTO-CHECK-EXAM] Element check: { ... }
   ```

2. **Form Data Values:**
   ```
   [AUTO-CHECK-EXAM] Form data: { ... }
   ```

3. **Response Status (if request sent):**
   ```
   [AUTO-CHECK-EXAM] Response status: ...
   ```

4. **Any Error Messages:**
   ```
   [AUTO-CHECK-EXAM] Error: ...
   [AUTO-CHECK-EXAM] Error details: { ... }
   ```

5. **JavaScript Errors (if any):**
   ```
   Uncaught ReferenceError: ...
   Uncaught TypeError: ...
   ```

---

## 🔧 Possible Fixes (After Diagnosis)

### If Hidden Fields Are Not Populated:

**Problem:** `faculty_id_exam_add` and `room_id_exam_add` exist but have no value.

**Solution:** Check the search selection functions:
```javascript
function selectFacultyModalExam(mode, facultyId, facultyName) {
    // Must set the hidden field
    document.getElementById('faculty_id_exam_' + mode).value = facultyId;
    document.getElementById('faculty_search_exam_' + mode).value = facultyName;
    // Hide dropdown
    document.getElementById('faculty_dropdown_exam_' + mode).classList.add('hidden');
    
    // ⚠️ CRITICAL: Trigger auto-check
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode.replace('_', ''));  // 'add' or 'edit'
    }
}
```

### If Search Functions Are Missing:

**Problem:** `selectFacultyModalExam is not defined`

**Solution:** Create the missing JavaScript functions for exam modal search.

### If Auto-Check Doesn't Trigger:

**Problem:** Form fields change but no auto-check runs.

**Solution:** Ensure event listeners are attached to the correct fields, especially the hidden `faculty_id_exam_add` and `room_id_exam_add` fields.

### If Server Returns 500 Error:

**Problem:** Backend crashes when processing request.

**Solution:** Check Flask console for Python exceptions and fix backend issue.

---

## 🎯 Expected Behavior

When working correctly:

1. User opens "Add Exam Schedule" modal
2. User fills in all required fields
3. **Auto-check triggers** every time a field changes (with 800ms debounce)
4. Console shows element check (all FOUND)
5. Console shows form data (all fields have values)
6. Console shows response status (200 OK)
7. UI displays conflict check results or "No conflicts"

---

## ✅ Next Steps

1. **User:** Follow debugging steps above and report console output
2. **Developer:** Analyze console output to identify specific issue
3. **Fix:** Apply appropriate solution based on diagnosis
4. **Test:** Verify fix works for both auto-check and manual AI check
5. **Document:** Update this guide with final solution

---

## 📚 Related Files

- `app/templates/schedule/_modals.html` - Form structure and field IDs
- `app/static/js/schedule/auto_conflict_check_exam.js` - Auto-conflict detection
- `app/static/js/schedule/exam_ai.js` - Manual AI check
- `app/static/js/schedule/schedule_full.js` - Modal open/close and search functions
- `app/routes/exam_schedule.py` - Backend AI endpoint

---

**Status:** 🟡 Waiting for user console output to diagnose exact issue
