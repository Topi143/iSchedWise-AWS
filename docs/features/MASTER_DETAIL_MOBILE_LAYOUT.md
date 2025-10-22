# Master-Detail Mobile Layout Implementation

## Overview
Implemented a master-detail layout pattern for the Schedule tab sub-tabs (Class, Faculty, Rooms, and Exam) in the Archive page to provide optimal mobile viewing experience.

## What is Master-Detail Layout?
A master-detail layout is a common mobile UI pattern where:
- **Desktop/Tablet**: Shows both master (list) and detail panels side-by-side
- **Mobile**: Shows only one panel at a time (master OR detail)
- Users can navigate between list view and detail view with smooth transitions

## Implementation Summary

### 1. CSS Classes Added
```css
/* Master-Detail Layout */
.master-panel {
    /* Left panel with list of items */
}

.detail-panel {
    /* Right panel with archive cards */
}

.mobile-back-button {
    /* Back button to return to master view */
}

/* Mobile-specific visibility controls */
@media (max-width: 768px) {
    .mobile-hidden {
        display: none !important;
    }
    
    .mobile-master-view {
        display: flex !important;
    }
    
    .mobile-detail-view {
        display: flex !important;
    }
}
```

### 2. HTML Structure Changes

#### Before (Traditional Layout)
```html
<div class="w-80 flex-shrink-0">
    <!-- List panel -->
</div>
<div class="flex-1">
    <!-- Detail panel -->
</div>
```

#### After (Master-Detail Layout)
```html
<div class="master-panel w-80 flex-shrink-0">
    <!-- List panel -->
</div>
<div class="detail-panel flex-1">
    <!-- Mobile back button -->
    <button onclick="showMasterView('tabname')" class="mobile-back-button">
        Back to List
    </button>
    
    <!-- Detail content -->
</div>
```

### 3. JavaScript Functions Added

#### `showMasterView(tabName)`
Shows the master panel (list) and hides the detail panel on mobile.
```javascript
function showMasterView(tabName) {
    const masterPanel = document.querySelector(`#${tabName}-archives-section .master-panel`);
    const detailPanel = document.querySelector(`#${tabName}-archives-section .detail-panel`);
    
    if (masterPanel && detailPanel) {
        masterPanel.classList.remove('mobile-hidden');
        masterPanel.classList.add('mobile-master-view');
        detailPanel.classList.remove('mobile-detail-view');
        detailPanel.classList.add('mobile-hidden');
    }
}
```

#### `showDetailView(tabName)`
Shows the detail panel and hides the master panel on mobile.
```javascript
function showDetailView(tabName) {
    const masterPanel = document.querySelector(`#${tabName}-archives-section .master-panel`);
    const detailPanel = document.querySelector(`#${tabName}-archives-section .detail-panel`);
    
    if (masterPanel && detailPanel) {
        masterPanel.classList.remove('mobile-master-view');
        masterPanel.classList.add('mobile-hidden');
        detailPanel.classList.remove('mobile-hidden');
        detailPanel.classList.add('mobile-detail-view');
    }
}
```

#### `handleMobileSelection(tabName)`
Automatically switches to detail view when an item is selected, but only on mobile devices.
```javascript
function handleMobileSelection(tabName) {
    // Only switch views on mobile screens (≤768px)
    if (window.innerWidth <= 768) {
        showDetailView(tabName);
    }
}
```

### 4. Updated Selection Functions

All four selection functions were updated to call `handleMobileSelection()`:

#### Class Tab
```javascript
function selectClassSection(sectionName) {
    // ... existing code ...
    handleMobileSelection('class');
}
```

#### Faculty Tab
```javascript
function selectFaculty(facultyName) {
    // ... existing code ...
    handleMobileSelection('faculty');
}
```

#### Rooms Tab
```javascript
function selectRoom(roomNumber) {
    // ... existing code ...
    handleMobileSelection('rooms');
}
```

#### Exam Tab
```javascript
function selectExamSection(sectionName) {
    // ... existing code ...
    handleMobileSelection('exam');
}
```

## User Experience Flow

### Desktop/Tablet View (> 768px)
1. User sees both panels side-by-side
2. Clicking an item in the master panel updates the detail panel
3. No view switching occurs

### Mobile View (≤ 768px)
1. **Initial State**: Only master panel (list) is visible
2. **User Action**: Clicks on a list item (section, faculty, room, or exam section)
3. **Transition**: Detail panel slides in, master panel is hidden
4. **Detail View**: User sees archived schedules
5. **Back Action**: User clicks "Back to [List Type] List" button
6. **Return**: Master panel slides back in, detail panel is hidden

## Tabs Implemented

✅ **Class Tab** - Select section → View class archives
✅ **Faculty Tab** - Select faculty → View faculty archives
✅ **Rooms Tab** - Select room → View room archives
✅ **Exam Tab** - Select section → View exam archives

## Benefits

### Mobile Users
- ✅ Full-width list view for easier item selection
- ✅ Full-width detail view for better readability of archive cards
- ✅ Clear navigation with visible back button
- ✅ Eliminates horizontal scrolling
- ✅ Optimizes limited screen space

### Desktop/Tablet Users
- ✅ No impact - maintains side-by-side layout
- ✅ Seamless experience across breakpoints

## Responsive Breakpoints

| Screen Size | Behavior |
|-------------|----------|
| > 768px | Side-by-side layout (both panels visible) |
| ≤ 768px | Master-detail layout (one panel at a time) |

## Testing Checklist

- [x] Class tab switches views on mobile
- [x] Faculty tab switches views on mobile
- [x] Rooms tab switches views on mobile
- [x] Exam tab switches views on mobile
- [x] Back buttons return to master view
- [x] Desktop layout unaffected (side-by-side remains)
- [x] Tablet layout works correctly
- [x] No JavaScript errors in console
- [x] Smooth transitions between views

## Files Modified

- **app/templates/archive.html**
  - Added master-detail CSS classes (lines 371-438)
  - Updated Class tab HTML structure
  - Updated Faculty tab HTML structure
  - Updated Rooms tab HTML structure
  - Updated Exam tab HTML structure
  - Added JavaScript view switching functions
  - Updated selection functions to trigger mobile view switching

## Related Documentation

- See `.github/copilot-instructions.md` for coding guidelines
- See `MASTER_DETAIL_PATTERN.md` in docs/features/ for design pattern details

## Future Enhancements

- Add swipe gestures for mobile navigation (left swipe = back, right swipe = detail)
- Add animation transitions for smoother view switching
- Consider implementing same pattern for other archive tabs (Curricula, Departments, etc.)
