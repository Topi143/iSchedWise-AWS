# Master-Detail Mobile Layout Pattern

## Overview
The Schedule Management page implements a responsive master-detail layout pattern to optimize the user experience on mobile devices. This pattern shows a list view (master) and detail view separately on small screens, while displaying them side-by-side on larger screens.

## Implementation Date
October 22, 2025

## Problem Solved
The original schedule interface had left and right panels displayed side-by-side, which was difficult to use on mobile devices due to:
- Limited screen space causing cramped layouts
- Small touch targets making selection difficult
- Difficulty reading schedule details on small screens
- Horizontal scrolling required to see full content

## Solution
Implemented a responsive master-detail pattern that:
- **Desktop (≥768px)**: Shows master (list) and detail (schedules) side-by-side
- **Mobile (<768px)**: Shows only master OR detail, with back button navigation
- **Tablet (769-1024px)**: Slightly reduced left panel width for optimization

## Affected Pages
- `app/templates/schedule.html` - Main schedule page
- `app/templates/schedule/_class_tab.html` - Class schedules tab
- `app/templates/schedule/_faculty_tab.html` - Faculty schedules tab
- `app/templates/schedule/_room_tab.html` - Room schedules tab
- `app/templates/schedule/_exam_tab.html` - Exam schedules tab
- `app/templates/schedule/_styles.html` - Responsive styles
- `app/static/js/schedule/main.js` - Master-detail navigation functions
- `app/static/js/schedule/schedule_full.js` - Integration with existing selection logic

## Technical Details

### HTML Structure Changes

#### Master Panel IDs
Each tab now has an identifiable master panel:
- Class: `id="class-master"`
- Faculty: `id="faculty-master"`
- Room: `id="room-master"`
- Exam: `id="exam-master"`

#### Detail Panel IDs
Each tab now has an identifiable detail panel:
- Class: `id="class-detail"`
- Faculty: `id="faculty-detail"`
- Room: `id="room-detail"`
- Exam: `id="exam-detail"`

#### Responsive Classes
- Master panels: `w-80 md:flex-shrink-0 flex-shrink-0 md:w-80 w-full`
- Detail panels: `flex-1 md:flex w-full`
- Hidden initially if no selection: `{% if not selected_item %}hidden{% endif %}`

#### Back Buttons
Each detail view includes a mobile-only back button:
```html
<button onclick="showXxxMaster()" class="md:hidden inline-flex items-center text-blue-600 hover:text-blue-800 mb-3 font-semibold">
    <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
    </svg>
    Back to [List Name]
</button>
```

### CSS Media Queries

#### Mobile (<768px)
```css
@media (max-width: 768px) {
    /* Hide master when detail is shown */
    #class-master.hide-on-mobile,
    #faculty-master.hide-on-mobile,
    #room-master.hide-on-mobile,
    #exam-master.hide-on-mobile {
        display: none !important;
    }
    
    /* Detail panels take full width */
    #class-detail,
    #faculty-detail,
    #room-detail,
    #exam-detail {
        width: 100%;
        max-width: 100%;
    }
    
    /* Smaller tab buttons */
    .tab-button {
        font-size: 0.75rem;
        padding: 0.5rem 0.75rem;
    }
    
    /* Optimized table and calendar views */
    .table-container {
        font-size: 0.75rem;
    }
    
    .calendar-grid > div {
        min-width: 600px;
    }
}
```

#### Tablet (769-1024px)
```css
@media (min-width: 769px) and (max-width: 1024px) {
    /* Reduced left panel width */
    #class-master,
    #faculty-master,
    #room-master,
    #exam-master {
        width: 240px;
    }
}
```

### JavaScript Functions

#### Navigation Functions (main.js)
Eight new functions control master-detail navigation:

**Show Master Functions:**
- `showClassMaster()` - Show section list for class schedules
- `showFacultyMaster()` - Show faculty list
- `showRoomMaster()` - Show room list
- `showExamMaster()` - Show section list for exam schedules

**Show Detail Functions:**
- `showClassDetail()` - Show class schedule details (auto-called on selection)
- `showFacultyDetail()` - Show faculty schedule details
- `showRoomDetail()` - Show room schedule details
- `showExamDetail()` - Show exam schedule details

#### Integration with Selection Logic (schedule_full.js)
Modified existing selection functions to call detail view functions:

```javascript
function selectSection(id, name) {
    // ... existing code ...
    
    // Show detail view on mobile
    if (typeof showClassDetail === 'function') {
        showClassDetail();
    }
    
    // ... rest of function ...
}
```

Similar updates applied to:
- `selectFaculty()`
- `selectRoom()`
- `selectExamSection()`

## User Flow

### Desktop/Tablet (≥768px)
1. User sees list and detail panels side-by-side
2. Clicking an item updates the detail panel in place
3. No navigation between views needed

### Mobile (<768px)
1. User lands on page → sees master (list) view only
2. User selects an item → detail view slides in, master hidden
3. User clicks "Back" button → master view returns, detail hidden
4. Cycle repeats as needed

## Benefits
✅ **Improved Mobile UX**: Full-screen views prevent cramped layouts  
✅ **Consistent Pattern**: Same behavior across all 4 tabs  
✅ **No Breaking Changes**: Desktop experience unchanged  
✅ **Better Touch Targets**: Full-width list items easier to tap  
✅ **Readable Content**: Detail view uses full screen width  
✅ **Intuitive Navigation**: Back button clearly returns to list  
✅ **Performance**: No additional API calls, pure UI changes

## Testing Checklist
- [x] Class schedules master-detail navigation
- [x] Faculty schedules master-detail navigation
- [x] Room schedules master-detail navigation
- [x] Exam schedules master-detail navigation
- [x] Desktop layout unchanged (≥768px)
- [x] Tablet layout optimized (769-1024px)
- [x] Mobile layout functional (<768px)
- [x] Back buttons work correctly
- [x] List item selection highlights properly
- [x] Detail view loads correctly on selection
- [x] No JavaScript errors in console

## Browser Compatibility
- ✅ Chrome/Edge (Chromium-based)
- ✅ Firefox
- ✅ Safari (iOS)
- ✅ Mobile browsers (Chrome Mobile, Safari Mobile)

## Future Enhancements
- [ ] Add swipe gestures for mobile navigation
- [ ] Implement transition animations between views
- [ ] Add breadcrumb navigation on mobile
- [ ] Consider slide-in animation for detail view
- [ ] Add keyboard shortcuts for desktop navigation

## Related Documentation
- `docs/features/MASTER_DETAIL_MOBILE_LAYOUT.md` - Original mobile layout concept
- `docs/SCHEDULE_REFACTORING_COMPLETE.md` - Schedule refactoring overview
- `docs/CALENDAR_VIEW_ALL_TABS.md` - Calendar view implementation

## Notes
- The pattern follows Tailwind's responsive design philosophy
- Uses `md:` breakpoint (768px) as the transition point
- Maintains existing functionality without breaking changes
- JavaScript functions are defensive (check if function exists before calling)
- CSS uses `!important` for hide-on-mobile to ensure it overrides other styles
