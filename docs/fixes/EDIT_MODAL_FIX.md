# Edit Modal Fix - Class and Exam Schedules

**Issue:** The edit modal was not showing when clicking the edit button on class schedules and exam schedules (both table and calendar views).

**Date Fixed:** October 19, 2025

## Root Cause

The issue was caused by improper JSON escaping in the `onclick` attribute. When passing complex JavaScript objects with quotes and special characters through Jinja2's `tojson` filter, the resulting JSON was not properly escaped for use within HTML attributes.

**Original Code:**
```html
onclick="editSchedule({{ schedule.id }}, {{ schedule.to_dict()|tojson }})"
```

**Problem:** 
- Double quotes in the JSON conflicted with the double quotes wrapping the `onclick` attribute
- Special characters in subject descriptions, faculty names, etc., caused JavaScript parsing errors
- The `tojson` filter without `|safe` was double-escaping some characters

## Solution

Changed all edit button `onclick` handlers to:
1. Use single quotes for the HTML attribute value
2. Add the `|safe` filter to properly handle the JSON output

**Fixed Code:**
```html
onclick='editSchedule({{ schedule.id }}, {{ schedule.to_dict()|tojson|safe }})'
```

## Files Modified

**File:** `app/templates/schedule.html`

**Locations Fixed (4 total):**

1. **Line ~551** - Class schedule table view edit button
   ```html
   <button onclick='editSchedule({{ schedule.id }}, {{ schedule.to_dict()|tojson|safe }})' class="text-blue-600 hover:text-blue-900 p-2 rounded-lg hover:bg-blue-50 transition-colors" title="Edit">
   ```

2. **Line ~632** - Class schedule calendar view card
   ```html
   <div class="calendar-schedule-card ... " onclick='editSchedule({{ schedule.id }}, {{ schedule.to_dict()|tojson|safe }})' ...>
   ```

3. **Line ~1509** - Exam schedule table view edit button
   ```html
   <button onclick='editExamSchedule({{ exam.id }}, {{ exam.to_dict()|tojson|safe }})' class="text-blue-600 hover:text-blue-900 p-2 rounded-lg hover:bg-blue-50 transition-colors" title="Edit">
   ```

4. **Line ~1590** - Exam schedule calendar view card
   ```html
   <div class="calendar-schedule-card ... " onclick='editExamSchedule({{ exam.id }}, {{ exam.to_dict()|tojson|safe }})' ...>
   ```

## Testing

After applying the fix:
1. Navigate to Schedule Management page
2. Select a section from the Class Schedules tab
3. Click the edit button (pencil icon) on any schedule
4. ✅ Edit modal should open with pre-filled data
5. Switch to Exam Schedules tab
6. Select a section
7. Click the edit button on any exam schedule
8. ✅ Edit exam modal should open with pre-filled data
9. Test both table view and calendar view for each tab

## Technical Details

### Why `|safe` is needed

The `|safe` filter marks the output as safe HTML/JavaScript, preventing Jinja2 from double-escaping already-escaped JSON. Without it:
- `"` becomes `&quot;` in some cases
- `'` becomes `&#39;` in some cases
- This breaks JavaScript object parsing

### Why single quotes work better

Using single quotes for the attribute value (`onclick='...'`) allows the JSON to use double quotes internally without conflict:
```html
<!-- Good: Single quotes wrap, double quotes inside -->
onclick='editSchedule(1, {"name": "Math 101", "faculty": "Dr. Smith"})'

<!-- Bad: Double quotes conflict -->
onclick="editSchedule(1, {"name": "Math 101", "faculty": "Dr. Smith"})"
```

## Related Models

The fix relies on proper `to_dict()` methods in:
- **`app/models/schedule.py`** - `Schedule.to_dict()` - Converts schedule to JSON-safe dictionary
- **`app/models/exam_schedule.py`** - `ExamSchedule.to_dict()` - Converts exam schedule to JSON-safe dictionary

Both methods properly format dates and times as strings for JSON serialization.

## Verification

Run the application and check:
- ✅ No JavaScript console errors when clicking edit buttons
- ✅ Edit modal appears with correct data pre-filled
- ✅ Subject dropdown loads correctly based on section
- ✅ All fields are populated from the schedule data
- ✅ Modal can be closed and reopened without issues

## Prevention

**Best Practices for passing data to JavaScript:**

1. **Use single quotes for onclick attributes** when passing JSON
2. **Always use `|tojson|safe`** when passing Python objects to JavaScript
3. **Test with special characters** in names and descriptions
4. **Check browser console** for JavaScript errors during testing

**Alternative approaches:**
- Use data attributes: `data-schedule='{{ schedule.to_dict()|tojson }}'`
- Event delegation: Add click handlers via JavaScript instead of inline onclick
- API calls: Load data via AJAX when modal opens

## Status

✅ **FIXED** - Edit modals now work correctly on both Class Schedules and Exam Schedules tabs (table and calendar views)
