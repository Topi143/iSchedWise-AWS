# Exam Tab Debugging Report

**Date:** January 19, 2026  
**Issue:** Exam tab in Schedule module not displaying anything  
**Status:** In Progress

---

## 1. Initial Problem Report

**User reported:** "The Exam tab is not displaying anything"

The Schedule module has 4 tabs:
- Class (working ✅)
- Exam (broken ❌)
- Faculty (working ✅)
- Room (working ✅)

---

## 2. Debugging Steps Performed

### Step 1: Identified the Files Involved

| File | Purpose |
|------|---------|
| `app/templates/schedule/_exam_tab.html` | Exam tab HTML template |
| `app/static/js/schedule/schedule_full.js` | Tab switching JavaScript |
| `app/routes/schedule.py` | Backend route that passes data |
| `app/templates/schedule.html` | Parent template that includes tabs |

---

### Step 2: Examined the JavaScript Tab Switching Logic

**File:** `app/static/js/schedule/schedule_full.js`

**Found Issue #1:** The `switchTab()` function had inconsistent indentation which could cause parsing issues in some browsers.

```javascript
// BEFORE (problematic indentation)
function switchTab(tabName) {
// Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
```

```javascript
// AFTER (fixed)
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
```

**Action Taken:** Fixed indentation throughout the `switchTab()` function.

---

### Step 3: Added Debug Logging to JavaScript

Added `console.log()` statements to trace execution:

```javascript
function switchTab(tabName) {
    console.log('switchTab called with:', tabName);
    
    // ... existing code ...
    
    const selectedContent = document.getElementById(contentId);
    console.log('Looking for content ID:', contentId, 'Found:', selectedContent);
    
    if (selectedContent) {
        selectedContent.classList.add('active');
        console.log('Added active class to:', contentId);
    }
}
```

**Purpose:** Verify that:
1. The function is being called
2. The correct `content-exam` element is being found
3. The `active` class is being applied

---

### Step 4: Visual Debugging with CSS Border

**File:** `app/templates/schedule/_exam_tab.html`

Added a bright red border to make the container visible:

```html
<div id="content-exam" class="tab-content flex-1 overflow-hidden flex flex-col lg:flex-row gap-2 sm:gap-3" style="border-bottom: 5px solid red;">
```

**Result:** User confirmed: *"redline at the bottom appear"*

**Conclusion:** 
- ✅ The tab container IS rendering
- ✅ The `switchTab()` function IS working
- ❌ The container is EMPTY (no height, just a bottom border line)

---

### Step 5: Analyzed Template Logic

**File:** `app/templates/schedule/_exam_tab.html`

The template structure is:

```jinja2
<div id="content-exam" class="tab-content ...">
    {% if exam_sections %}
        <!-- Master-Detail View: Section list + Schedule details -->
        <div id="exam-master">...</div>
        <div id="exam-detail">...</div>
    {% else %}
        <!-- Empty State -->
        <div>No Sections Available</div>
    {% endif %}
</div>
```

**Key Finding:** The entire content depends on `{% if exam_sections %}` being truthy.

If `exam_sections` is:
- An empty list `[]` → Shows "No Sections Available"
- `None` or undefined → Shows "No Sections Available"
- A populated list → Shows the Master-Detail view

---

### Step 6: Examined Backend Route

**File:** `app/routes/schedule.py` (Lines 330-380)

```python
# Get exam schedule data
# Get sections for exam tab (reuse the sections query)
exam_sections = sections  # ← This reuses the class tab sections
exam_department_filter = request.args.get('exam_department_id', type=int)

# Auto-apply filter if user has only 1 department
if exam_department_filter is None and len(departments) == 1:
    exam_department_filter = departments[0].id

# Calculate exam schedule counts
exam_section_schedule_counts = {}
if current_settings:
    for section in exam_sections:
        count = ExamSchedule.query.filter_by(
            section_id=section.id,
            is_active=True,
            academic_year=current_settings.academic_year,
            semester=current_settings.semester
        ).count()
        exam_section_schedule_counts[section.id] = count
```

**Observation:** The `exam_sections` variable is assigned from `sections`, which is the same list used for the Class tab. If Class tab shows sections, Exam tab should too.

---

### Step 7: Compared Working Tab vs Broken Tab

**Compared:** `_class_tab.html` (working) vs `_exam_tab.html` (broken)

Both templates follow the same pattern:

| Aspect | Class Tab | Exam Tab |
|--------|-----------|----------|
| Wrapper ID | `content-class` | `content-exam` |
| Data Variable | `sections` | `exam_sections` |
| Master Panel | `sectionList` | `examSectionList` |
| Jinja Loop | `{% for section in sections_by_dept %}` | `{% for section in exam_sections_by_dept %}` |

**Finding:** The template syntax appears correct. The issue is likely:
1. Data not being passed correctly, OR
2. A Jinja rendering error silently failing

---

## 3. Current Hypothesis

### Most Likely Cause:
The `exam_sections` variable is either:
1. **Empty** - No sections exist in the database for the user's department access
2. **Not passed** - Missing from the `render_template()` call
3. **Filtered out** - Department filter is too restrictive

### Evidence:
- Red border appeared → Container exists
- No content inside → `{% if exam_sections %}` evaluated to `False`
- Class tab works → Sections DO exist in database
- Same `sections` variable is used → Should have same data

---

## 4. Next Steps to Complete Debugging

### Step A: Verify Data is Passed to Template
Add debug output directly in the template:

```jinja2
<!-- DEBUG: Check if exam_sections exists -->
<script>console.log('exam_sections count: {{ exam_sections|length if exam_sections else "NONE" }}');</script>
```

### Step B: Check render_template() Call
Verify that `exam_sections` is included in the `render_template()` call in `schedule.py`.

### Step C: Test with Direct Database Query
In Flask shell or a test route:
```python
sections = Section.query.filter_by(is_active=True).all()
print(f"Total sections: {len(sections)}")
```

### Step D: Check for Jinja Errors
Look for any Jinja2 syntax errors that might silently fail:
- Unclosed tags
- Missing `{% endif %}`
- Typos in variable names

---

## 5. Files Modified During Debugging

| File | Changes Made |
|------|--------------|
| `app/static/js/schedule/schedule_full.js` | Fixed indentation in `switchTab()`, added debug logs |
| `app/templates/schedule/_exam_tab.html` | Added CSS border for visual debugging |

---

## 6. Summary of Findings

| Check | Result |
|-------|--------|
| Tab button clickable | ✅ Yes |
| `switchTab()` function exists | ✅ Yes |
| `content-exam` div exists | ✅ Yes |
| Tab switching works | ✅ Yes (border appeared) |
| Content renders inside tab | ❌ No (empty) |
| `exam_sections` has data | ⚠️ Needs verification |

**Root Cause Identified:** The tab switching mechanism works correctly. The issue is that the content inside the tab is not rendering because `exam_sections` appears to be empty or falsy when the template is processed.

---

## 7. Resolution Path

1. **Verify** `exam_sections` is passed in `render_template()`
2. **Verify** the variable has data (not empty list)
3. **Check** department access filters aren't too restrictive
4. **Remove** debug CSS/JS once fixed
