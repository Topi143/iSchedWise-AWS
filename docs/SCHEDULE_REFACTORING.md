# Schedule Page Refactoring

## Problem
The schedule page had grown to **3,384 lines** in a single template file (`schedule.html`) and **1000+ lines** of Python code in one route file, making it extremely difficult to:
- Find and fix bugs
- Add new features
- Understand the code flow
- Maintain consistency
- Collaborate with others

## Solution
Break the monolithic schedule page into **modular, reusable components** organized by feature.

---

## New Structure

### Template Components (`app/templates/schedule/`)
```
schedule/
├── _class_tab.html          # Class schedules tab content
├── _faculty_tab.html        # Faculty schedules tab content  
├── _room_tab.html           # Room schedules tab content
├── _exam_tab.html           # Exam schedules tab content
├── _modals.html             # All modals (add/edit for class & exam)
├── _calendar_components.html # Calendar view shared components
└── _styles.html             # Shared CSS styles
```

### JavaScript Modules (`app/static/js/schedule/`)
```
schedule/
├── tabs.js        # Tab switching logic
├── modals.js      # Modal open/close logic
├── filters.js     # Department/building filters
├── calendar.js    # Calendar view switching
├── ai.js          # AI conflict detection
├── forms.js       # Form handling (subject selection, time calc)
└── main.js        # Main initialization and coordination
```

### Route Modules (`app/routes/schedule/`)
```
schedule/
├── __init__.py           # Blueprint registration
├── class_routes.py       # Class schedule CRUD
├── faculty_routes.py     # Faculty schedule views
├── room_routes.py        # Room schedule views
├── exam_routes.py        # Exam schedule CRUD
├── export_routes.py      # Excel export endpoints
└── api_routes.py         # AJAX API endpoints
```

---

## Benefits

### 1. **Easier to Find Code**
- Need to edit class schedule modal? → `_modals.html`
- Fix faculty filter bug? → `filters.js`
- Update export logic? → `export_routes.py`

### 2. **Smaller, Focused Files**
- Each file handles ONE concern
- ~200-400 lines per file (instead of 3,384)
- Clear naming tells you what's inside

### 3. **Reusable Components**
- Calendar view used in all tabs → single component
- Modals shared across tabs → `_modals.html`
- Filter logic reused → `filters.js`

### 4. **Better Collaboration**
- Multiple developers can work on different tabs without conflicts
- Easier code reviews (small, focused changes)
- Clear ownership of features

### 5. **Improved Performance**
- Load only needed JavaScript modules
- Browser caches individual JS files
- Easier to optimize specific components

---

## Migration Guide

### How to Add New Features

#### Adding a New Tab
1. Create `_new_tab.html` in `app/templates/schedule/`
2. Add route in appropriate `schedule/*_routes.py`
3. Include in main template: `{% include 'schedule/_new_tab.html' %}`
4. Register tab in `tabs.js`

#### Adding a Modal
1. Add modal HTML to `_modals.html`
2. Add open/close functions to `modals.js`
3. Wire up buttons in tab template

#### Adding AI Feature
1. Add API endpoint in `api_routes.py`
2. Add client-side logic in `ai.js`
3. Update modal to call new function

---

## File Responsibilities

### Template Files

**`_class_tab.html`**
- Section list (left panel)
- Class schedules table/calendar (right panel)
- Add schedule button
- Export button
- Department filter

**`_faculty_tab.html`**
- Faculty list (left panel)
- Faculty schedules table/calendar (right panel)
- Export button
- Department filter

**`_room_tab.html`**
- Room list (left panel)
- Room schedules table/calendar (right panel)
- Export button
- Building filter

**`_exam_tab.html`**
- Section list for exams (left panel)
- Exam schedules table/calendar (right panel)
- Add exam schedule button
- Export button
- Department filter

**`_modals.html`**
- Add class schedule modal
- Edit class schedule modal
- Add exam schedule modal
- Edit exam schedule modal

**`_calendar_components.html`**
- Calendar grid structure
- Time slots
- Schedule cards
- View toggle buttons

**`_styles.html`**
- Toast notifications
- List item styles (section, faculty, room)
- Table styles
- Calendar styles
- Modal styles
- Badge styles

### JavaScript Files

**`tabs.js`**
```javascript
// Tab switching logic
function switchTab(tabName)
// Restore active tab from localStorage
```

**`modals.js`**
```javascript
// Modal management
function openAddScheduleModal(sectionId)
function closeAddScheduleModal()
function openEditScheduleModal()
function closeEditScheduleModal()
function openAddExamScheduleModal(sectionId)
function closeAddExamScheduleModal()
function openEditExamScheduleModal()
function closeEditExamScheduleModal()
```

**`filters.js`**
```javascript
// Filter logic
function filterByDepartment(departmentId)
function filterRoomByBuilding(buildingId)
function filterFacultyByDepartment(departmentId)
function filterExamByDepartment(departmentId)
```

**`calendar.js`**
```javascript
// Calendar view switching
function switchScheduleView(viewType)
function switchFacultyView(viewType)
function switchRoomView(viewType)
function switchExamView(viewType)
```

**`ai.js`**
```javascript
// AI conflict detection
function checkScheduleWithAI(mode)
function displayAIConflicts(conflicts, mode)
function displayAIRecommendations(recommendations, mode)
function applyTimeSlot(startTime, endTime, mode)
function applyDay(day, mode)
function applyRoom(roomId, mode)
function applyFaculty(facultyId, mode)
```

**`forms.js`**
```javascript
// Form handling
function handleSubjectChange(mode)
function displaySubjectUnitsInfo(mode, subjectData)
function showScheduleTypeOptions(mode, subjectData)
function selectScheduleType(mode, type)
function updateTimeDurationInfo(mode, type, units)
function calculateEndTime(mode)
function loadSubjectsForSection(sectionId)
function loadSubjectsForEdit(sectionId, scheduleData)
function loadFacultyForSubject(subjectId, mode)
function loadSubjectsForExamSection(sectionId, mode, examData)
```

**`main.js`**
```javascript
// Initialize all modules
// Toast notifications
// Event listeners
// Page load logic
```

### Python Route Files

**`class_routes.py`**
- `/schedule/` - Main index view for class tab
- `/schedule/add` - Add class schedule
- `/schedule/edit` - Edit class schedule
- `/schedule/delete` - Delete class schedule

**`faculty_routes.py`**
- Faculty schedule view data

**`room_routes.py`**
- Room schedule view data

**`exam_routes.py`**
- Exam schedule CRUD operations

**`export_routes.py`**
- `/schedule/export/class/<id>` - Export class schedule to Excel
- `/schedule/export/faculty/<id>` - Export faculty schedule to Excel
- `/schedule/export/room/<id>` - Export room schedule to Excel
- `/schedule/export/exam/<id>` - Export exam schedule to Excel

**`api_routes.py`**
- `/schedule/get-subjects/<id>` - Get subjects for section
- `/schedule/get-faculty/<id>` - Get faculty for subject
- `/schedule/ai-check-conflicts` - AI conflict detection
- `/schedule/ai-suggest-schedule` - AI schedule suggestions

---

## Testing Checklist

After refactoring, verify:

- [ ] All 4 tabs load and switch correctly
- [ ] Class schedule add/edit/delete works
- [ ] Exam schedule add/edit/delete works
- [ ] Department filters work on all tabs
- [ ] Building filter works on room tab
- [ ] Calendar view toggle works on all tabs
- [ ] Modals open and close correctly
- [ ] Subject selection loads correct subjects
- [ ] Faculty selection loads assigned faculty
- [ ] Time auto-calculation works
- [ ] AI conflict detection works (if enabled)
- [ ] Excel export works for all tabs
- [ ] Toast notifications display correctly
- [ ] localStorage preferences persist
- [ ] Mobile responsive layout works
- [ ] No JavaScript console errors

---

## Maintenance Tips

### Adding a New Feature
1. Identify which module it belongs to
2. Add code ONLY to that module
3. Keep files under 500 lines if possible
4. Document complex logic with comments

### Debugging
1. Check browser console for JavaScript errors
2. Use file names in error messages to locate issue quickly
3. Each module is small enough to read in one screen

### Performance Optimization
1. Lazy load calendar view JavaScript only when needed
2. Debounce filter functions
3. Use event delegation for dynamic elements
4. Cache DOM queries in variables

---

## Future Enhancements

Potential improvements:
- [ ] Add drag-and-drop schedule editing in calendar view
- [ ] Batch schedule operations (copy week, duplicate section)
- [ ] Schedule conflict visualization heatmap
- [ ] Print-friendly calendar view
- [ ] Schedule templates (save common patterns)
- [ ] Undo/redo functionality
- [ ] Keyboard shortcuts for common actions

---

Last Updated: October 19, 2025
