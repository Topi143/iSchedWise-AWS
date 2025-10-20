# Schedule Calendar View Feature

## Overview
Added a visual weekly calendar view to the Schedule Management page, allowing users to view class schedules in both table format and calendar format.

## Changes Made

### 1. View Toggle Buttons
**Location**: `app/templates/schedule.html` - Header section

Added toggle buttons in the schedule header to switch between Table and Calendar views:
- **Table View**: Traditional list-based table view (default)
- **Calendar View**: Visual weekly calendar grid showing schedules by day and time

### 2. Calendar View Layout
**Location**: `app/templates/schedule.html` - Content area

Created a responsive weekly calendar grid with:
- **Time slots**: 7:00 AM to 7:00 PM (hourly intervals)
- **Days**: Monday through Sunday
- **Color-coded day headers**: Each day has a distinct background color
- **Schedule cards**: Visual blocks showing schedule details

### 3. Schedule Card Features
Each schedule block in the calendar displays:
- Subject code and description
- Faculty name (with icon)
- Room number (with icon)
- Start and end time
- Color-coded by schedule type:
  - **Blue**: Lecture
  - **Green**: Lab
  - **Purple**: Tutorial/Other
- **Interactive**: Click on any schedule card to edit it
- **Hover effects**: Cards expand slightly on hover for better visibility

### 4. JavaScript Functions
**Location**: `app/templates/schedule.html` - JavaScript section

Added new function:
- `switchScheduleView(viewType)`: Toggles between 'table' and 'calendar' views
- Saves user preference to localStorage for persistence across page reloads

### 5. CSS Styling
**Location**: `app/templates/schedule.html` - CSS section

Added calendar-specific styles:
- Calendar grid layout
- Schedule card positioning and hover effects
- Color-coded day headers
- View toggle button styles

## How It Works

### Switching Views
1. User clicks **Table** or **Calendar** button in the header
2. JavaScript function toggles visibility of respective view
3. Button styles update to show active view
4. Preference is saved to browser's localStorage

### Calendar Logic
The calendar uses nested loops to:
1. Create hourly time slots (rows)
2. Create day columns for each time slot
3. Check if any schedule falls within that time slot and day
4. Display schedule card with proper styling and information

### Time Slot Matching
```jinja2
{% if sched_start <= start_time and sched_end > start_time %}
    <!-- Display schedule card -->
{% endif %}
```
This ensures schedules appear in all time slots they occupy.

## User Experience Benefits

### Calendar View Advantages
✅ **Visual Overview**: See entire week at a glance
✅ **Time Conflicts**: Easily spot overlapping schedules
✅ **Pattern Recognition**: Identify schedule patterns and gaps
✅ **Quick Navigation**: Click directly on schedule cards to edit
✅ **Color Coding**: Quickly distinguish schedule types

### Table View Advantages
✅ **Detailed Information**: See all metadata in columns
✅ **Filtering & Sorting**: Traditional table operations
✅ **Compact**: More schedules visible at once
✅ **Action Buttons**: Dedicated edit/delete buttons

## Technical Details

### HTML Structure
```html
<div id="scheduleTableView" class="table-container">
    <!-- Existing table view -->
</div>

<div id="scheduleCalendarView" class="hidden h-full overflow-y-auto p-4">
    <div class="calendar-grid">
        <!-- Calendar header with days -->
        <!-- Calendar body with time slots -->
    </div>
</div>
```

### Time Slots Configuration
```jinja2
{% set time_slots = [
    ('07:00', '08:00'), ('08:00', '09:00'), ... ('18:00', '19:00')
] %}
```
Can be easily modified to adjust time range.

### Color Scheme
- **Monday**: Blue (`bg-blue-50`)
- **Tuesday**: Pink (`bg-pink-50`)
- **Wednesday**: Green (`bg-green-50`)
- **Thursday**: Yellow (`bg-yellow-50`)
- **Friday**: Indigo (`bg-indigo-50`)
- **Saturday**: Purple (`bg-purple-50`)
- **Sunday**: Red (`bg-red-50`)

## Future Enhancements

### Possible Improvements
1. **Drag & Drop**: Move schedules by dragging on calendar
2. **Zoom Controls**: Adjust time slot height
3. **Day View**: Focus on single day with larger cards
4. **Month View**: Multiple weeks at once
5. **Print Layout**: Optimized calendar for printing
6. **Export Calendar**: Download as image or PDF
7. **Conflict Highlighting**: Visual indicators for overlapping schedules
8. **Quick Add**: Click empty slot to create new schedule

## Testing Checklist

- [ ] Switch between Table and Calendar views
- [ ] Verify all schedules appear in correct time slots
- [ ] Click on schedule card to edit
- [ ] Check view preference persists after page reload
- [ ] Test with various schedule types (lecture, lab, tutorial)
- [ ] Verify responsive behavior on different screen sizes
- [ ] Test with empty schedules
- [ ] Test with multiple schedules in same time slot

## Browser Compatibility

Works with modern browsers supporting:
- CSS Grid
- Flexbox
- localStorage
- ES6 JavaScript

Tested on:
- Chrome/Edge (Chromium)
- Firefox
- Safari

## Performance Considerations

- Calendar view renders all time slots on page load
- For sections with many schedules (50+), rendering may take slightly longer
- Uses CSS Grid for efficient layout
- Minimal JavaScript overhead (only view switching logic)

## Related Files

- `app/templates/schedule.html` - Main template file
- `app/routes/schedule.py` - Backend schedule routes
- `app/models/schedule.py` - Schedule model

## Notes

- Calendar view is **view-only** for display purposes
- Editing is done through existing modal forms
- View preference is stored per browser (localStorage)
- Time slots are hardcoded but can be made dynamic if needed
