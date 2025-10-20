# Schedule Calendar View - Quick Reference

## What Was Added

✅ **Calendar View Toggle** - Switch between Table and Calendar views
✅ **Compact Weekly Calendar Grid** - Visual representation fitting right panel
✅ **Interactive Schedule Cards** - Click to edit schedules
✅ **Color-Coded Days** - Each day has a distinct color
✅ **Time Slot Grid** - 7:00 AM to 7:00 PM hourly view (compact)
✅ **Persistent Preference** - View choice saved in browser
✅ **Optimized Layout** - Smaller font sizes and reduced spacing for better fit

---

## Location

**File**: `app/templates/schedule.html`

**Sections Modified**:
1. Header - Added view toggle buttons
2. Content area - Added calendar view HTML
3. CSS - Added calendar styling
4. JavaScript - Added view switching function

---

## View Toggle Buttons

```html
<!-- Table Button | Calendar Button -->
[📊 Table] [📅 Calendar]
```

**Position**: Top right of schedule panel, next to Export and Add Schedule buttons

---

## Calendar Layout (Compact)

```
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│Time │ Mon │ Tue │ Wed │ Thu │ Fri │ Sat │ Sun │
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│07:00│     │     │     │     │     │     │     │
│08:00│[SCH]│     │     │[SCH]│     │     │     │
│09:00│     │[SCH]│     │     │[SCH]│     │     │
│10:00│     │     │[SCH]│     │     │     │     │
│11:00│[SCH]│     │     │     │     │     │     │
│12:00│     │     │     │     │     │     │     │
│13:00│     │[SCH]│     │[SCH]│     │     │     │
│ ... │ ... │ ... │ ... │ ... │ ... │ ... │ ... │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

**Compact Design Features:**
- Reduced cell padding (1-2px)
- Smaller font sizes (0.65-0.7rem)
- Abbreviated day names (Mon, Tue, etc.)
- Minimal spacing between cells
- 60px minimum cell height (down from 80px)

---

## Schedule Card Example (Compact)

```
┌─────────────────┐
│ CS101           │ ← Subject Code
│ Intro to Pro... │ ← Truncated Description
│ 👤 Prof. Joh... │ ← Truncated Faculty
│ 🏢 301          │ ← Room
│ 08:00 AM        │ ← Start Time Only
└─────────────────┘
```

**Compact Card Features:**
- Font size: 0.65rem (very small)
- Text truncation with ellipsis
- Only start time shown (hover for full details)
- Reduced padding (0.25rem)
- Smaller icons (0.75rem)

**Colors by Type**:
- 🔵 Blue = Lecture
- 🟢 Green = Lab
- 🟣 Purple = Tutorial

---

## Key Features

### 1. Visual Week Overview
See all schedules for the week in a single view

### 2. Time-Based Layout
Schedules positioned by actual time slots

### 3. Click to Edit
Click any schedule card to open edit modal

### 4. Color-Coded Days
- Monday: Blue
- Tuesday: Pink
- Wednesday: Green
- Thursday: Yellow
- Friday: Indigo
- Saturday: Purple
- Sunday: Red

### 5. Hover Effects
Schedule cards expand slightly on hover

### 6. Tooltip on Hover
Full schedule details appear in browser tooltip when hovering over truncated cards

### 7. Persistent View
Last selected view (Table/Calendar) is remembered

---

## How to Use

### Switching Views
1. Open Schedule Management page
2. Select a section from the left panel
3. Click **Calendar** button in the header
4. View schedules in weekly calendar format
5. Click **Table** button to return to table view

### Editing from Calendar
1. Locate schedule card in calendar
2. Click on the schedule card
3. Edit modal opens with schedule details
4. Make changes and save

### Navigation
- **Scroll vertically** to see different time slots
- **Scroll horizontally** if calendar is wider than screen (smaller displays)

---

## Technical Implementation

### View Switching Function
```javascript
function switchScheduleView(viewType) {
    // Toggle visibility of table/calendar views
    // Update button styles
    // Save preference to localStorage
}
```

### Time Slot Matching Logic
```jinja2
{% if sched_start <= start_time and sched_end > start_time %}
    <!-- Display schedule in this time slot -->
{% endif %}
```

### CSS Grid Layout
```css
.calendar-grid {
    min-width: 1200px;
}

.grid-cols-8 {
    /* 1 column for time + 7 columns for days */
}
```

---

## Benefits

### For Users
✅ Better visualization of schedule patterns
✅ Easier conflict detection
✅ More intuitive time-based view
✅ Quick access to edit schedules
✅ Flexible view options (Table or Calendar)

### For Scheduling
✅ Identify free time slots quickly
✅ Spot overlapping schedules visually
✅ Plan better schedule distribution
✅ See workload across the week

---

## Browser Support

✅ Chrome/Edge (Chromium)
✅ Firefox
✅ Safari
✅ Modern browsers with CSS Grid support

---

## Future Ideas

💡 Drag-and-drop schedule editing
💡 Print-optimized calendar layout
💡 Export calendar as PDF/image
💡 Day view (single day focus)
💡 Month view (multiple weeks)
💡 Conflict highlighting
💡 Quick add from empty time slot
💡 Zoom controls for time slots

---

## Files Modified

📄 `app/templates/schedule.html`
- Added calendar view HTML
- Added view toggle buttons
- Added JavaScript function
- Added CSS styling

📄 `docs/features/SCHEDULE_CALENDAR_VIEW.md`
- Detailed documentation

📄 `docs/features/SCHEDULE_CALENDAR_QUICK_REFERENCE.md`
- Quick reference guide (this file)

---

## Troubleshooting

### Calendar not showing?
- Check if section is selected
- Ensure schedules exist for the section
- Click Calendar button in header

### View not switching?
- Clear browser cache
- Check browser console for errors
- Verify JavaScript is enabled

### Schedules in wrong time slots?
- Check schedule start/end times in database
- Verify time format is correct
- Check timezone settings

### View preference not saving?
- Check if localStorage is enabled
- Check browser privacy settings
- Try incognito/private mode

---

## Related Documentation

📖 [Full Feature Documentation](./SCHEDULE_CALENDAR_VIEW.md)
📖 [Schedule Management Guide](../setup/SETUP_GUIDE.md)
📖 [Schedule Tables Reference](../SCHEDULE_TABLES_REFERENCE.md)

---

**Created**: 2025-10-19
**Version**: 1.0
**Status**: ✅ Implemented
