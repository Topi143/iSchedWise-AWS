# Automatic AI Conflict Detection System

**Status**: ✅ Implemented  
**Date**: October 19, 2025  
**Feature Type**: AI-Powered Schedule Validation  

---

## Overview

The system now automatically detects schedule conflicts in real-time as users fill out the Add/Edit Schedule forms. Users cannot submit schedules with conflicts until they are resolved.

## Key Features

### 1. **Automatic Detection**
- ✅ Conflicts are checked automatically when form fields change
- ✅ Uses debouncing (800ms delay) to prevent excessive API calls
- ✅ Checks triggered on: subject, faculty, room, day, start time, end time changes

### 2. **Submit Prevention**
- ✅ Submit button is disabled when conflicts exist
- ✅ Visual feedback: Button appears gray with "disabled" cursor
- ✅ Tooltip shows "Resolve conflicts before submitting"

### 3. **Visual Feedback**
- **Checking**: Blue background with 🔍 icon
- **Success**: Green background with ✅ icon - "No conflicts detected!"
- **Error/Conflict**: Red background with ⚠️ icon - Shows conflict count
- **Warning**: Yellow background for non-blocking issues

### 4. **Intelligent Behavior**
- ✅ Only checks when minimum required fields are filled (section, day, time)
- ✅ Validates time ranges (end time must be after start time)
- ✅ Shows detailed conflict information (faculty, room, section conflicts)
- ✅ Provides AI-powered recommendations for conflict resolution
- ✅ Handles network errors gracefully (doesn't block submission on errors)

## Technical Implementation

### Files Modified

#### 1. **app/templates/schedule/_modals.html**
- Added IDs to submit buttons: `submitScheduleAdd` and `submitScheduleEdit`
- Added disabled states with visual styling

**Changes:**
```html
<!-- Before -->
<button type="submit" class="...">Add Schedule</button>

<!-- After -->
<button type="submit" id="submitScheduleAdd" 
        class="... disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400">
    Add Schedule
</button>
```

#### 2. **app/static/js/schedule/auto_conflict_check.js** (NEW FILE)
- Automatic conflict detection system
- Debounced field change listeners
- Submit button state management
- Visual status updates

**Key Functions:**
- `initAutoConflictDetection()` - Initializes listeners on page load
- `setupAutoCheckForModal(mode)` - Attaches listeners to form fields
- `scheduleAutoConflictCheck(mode)` - Debounces API calls
- `performAutoConflictCheck(mode)` - Executes the conflict check
- `updateConflictState(mode, hasConflicts)` - Enables/disables submit button
- `showAutoCheckStatus(mode, type, message)` - Updates visual feedback
- `resetAutoCheckState(mode)` - Cleans up when modal closes

#### 3. **app/static/js/schedule/schedule_full.js**
- Updated modal close functions to reset auto-check state

**Changes:**
```javascript
function closeAddScheduleModal() {
    // ... existing code ...
    
    // Reset auto-check state
    if (typeof resetAutoCheckState === 'function') {
        resetAutoCheckState('add');
    }
}
```

#### 4. **app/templates/schedule.html**
- Added new script include for auto_conflict_check.js

**Changes:**
```html
<!-- Automatic Conflict Detection System -->
<script src="{{ url_for('static', filename='js/schedule/auto_conflict_check.js') }}"></script>
```

### Backend Support

The system uses the existing `/schedule/ai-check-conflicts` API endpoint:

**Request:**
```json
{
  "section_id": 1,
  "subject_id": 5,
  "faculty_id": 3,
  "room_id": 2,
  "day_of_week": "Monday",
  "start_time": "08:00",
  "end_time": "09:00",
  "schedule_id": null
}
```

**Response:**
```json
{
  "ai_enabled": true,
  "has_conflicts": true,
  "conflicts": [
    {
      "type": "faculty",
      "message": "Faculty conflict detected",
      "details": {
        "subject": "CS101",
        "day": "Monday",
        "time": "08:00-09:00"
      }
    }
  ],
  "recommendations": [
    {
      "type": "alternative_time",
      "suggestion": "Try 10:00-11:00",
      "priority": 1
    }
  ],
  "ai_explanation": "Conflicts detected. See recommendations below."
}
```

## User Experience Flow

### Adding a New Schedule

1. **User opens Add Schedule modal**
   - Submit button is enabled (no conflicts yet)

2. **User selects day of week** (e.g., Monday)
   - No check yet (waiting for time fields)

3. **User enters start time** (e.g., 08:00)
   - No check yet (waiting for end time)

4. **User enters end time** (e.g., 09:00)
   - ✅ Automatic check triggers after 800ms
   - Status shows: "🔍 Checking for conflicts..."

5. **Check completes:**

   **Scenario A - No Conflicts:**
   - Status shows: "✅ No conflicts detected!"
   - Submit button remains enabled
   - User can submit immediately

   **Scenario B - Conflicts Found:**
   - Status shows: "⚠️ 2 conflicts detected! Resolve conflicts to submit."
   - Submit button becomes DISABLED (gray)
   - Conflict details displayed in red boxes
   - AI recommendations shown below
   - User must change fields to resolve conflicts

6. **User modifies conflicting field** (e.g., changes time to 10:00)
   - Automatic check triggers again
   - Status shows: "🔍 Checking for conflicts..."
   - If resolved: "✅ No conflicts detected!" + button enabled

7. **User submits form**
   - Only possible when no conflicts exist
   - Form submits to backend normally

### Editing Existing Schedule

Same flow as adding, but:
- Excludes the current schedule from conflict detection (using `schedule_id`)
- Pre-fills form with existing data
- Auto-check triggers immediately if time fields are changed

## Configuration

### Debounce Delay
Change in `auto_conflict_check.js`:
```javascript
const AUTO_CHECK_DEBOUNCE_MS = 800; // milliseconds
```

Lower = More responsive, more API calls  
Higher = Fewer API calls, less responsive

Recommended: 500-1000ms

### AI API Requirement
- Requires `GEMINI_API_KEY` in `.env` file
- Falls back gracefully if AI is disabled
- Shows warning: "ℹ️ AI conflict detection not enabled"

## Benefits

### For Users
- ✅ Immediate feedback on schedule conflicts
- ✅ Can't accidentally create conflicting schedules
- ✅ AI-powered suggestions for conflict resolution
- ✅ No need to manually click "Check with AI" button
- ✅ Faster workflow - conflicts caught before submission

### For System
- ✅ Prevents invalid data from reaching database
- ✅ Reduces failed submissions and error handling
- ✅ Better data integrity
- ✅ Leverages existing AI infrastructure

## Testing Checklist

- [ ] Open Add Schedule modal
- [ ] Fill in all fields with valid data
- [ ] Verify "✅ No conflicts detected!" appears
- [ ] Verify submit button is enabled
- [ ] Create conflicting schedule (same time, faculty, room)
- [ ] Open Add Schedule modal again
- [ ] Fill in same conflicting details
- [ ] Verify "⚠️ conflict detected!" appears
- [ ] Verify submit button is DISABLED
- [ ] Change time to non-conflicting slot
- [ ] Verify status changes to "✅ No conflicts detected!"
- [ ] Verify submit button becomes enabled
- [ ] Test Edit modal with same flow
- [ ] Test with AI disabled (no GEMINI_API_KEY)
- [ ] Verify graceful fallback behavior

## Known Limitations

1. **Network Dependency**: Requires API call for each check
2. **AI Dependency**: Works best with Gemini API configured
3. **Debounce Delay**: 800ms delay before check executes
4. **Field Coverage**: Only checks time-based conflicts (not capacity, prerequisites, etc.)

## Future Enhancements

### Possible Improvements
- [ ] Add offline conflict detection (basic validation without AI)
- [ ] Cache recent conflict checks to reduce API calls
- [ ] Add visual indicators next to conflicting fields
- [ ] Highlight conflicting schedules in calendar view
- [ ] Add "Force Submit" option for admins
- [ ] Show conflict severity levels (critical vs. warning)
- [ ] Add auto-fill suggestions when conflicts are resolved

## Debugging

### Enable Console Logging
Check browser console for detailed logs:
```
[AUTO-CHECK] Initializing automatic conflict detection...
[AUTO-CHECK] Listeners attached for add modal
[AUTO-CHECK] day_of_week_add changed, scheduling check...
[AUTO-CHECK] Form data: {...}
[AUTO-CHECK] Sending request: {...}
[AUTO-CHECK] Response: {...}
[AUTO-CHECK] Submit button DISABLED for add modal
```

### Common Issues

**Issue**: Submit button stays disabled even without conflicts
- Check console for API errors
- Verify `/schedule/ai-check-conflicts` endpoint is accessible
- Check network tab for failed requests

**Issue**: No automatic checking happens
- Verify `auto_conflict_check.js` is loaded (check Network tab)
- Check if `initAutoConflictDetection()` was called
- Verify field IDs match (e.g., `day_of_week_add`, `start_time_add`)

**Issue**: Too many API calls
- Increase `AUTO_CHECK_DEBOUNCE_MS` value
- Check if listeners are attached multiple times

---

## Summary

The automatic AI conflict detection system provides a seamless, intelligent user experience by:
1. Automatically detecting conflicts as users type
2. Preventing submission of conflicting schedules
3. Providing clear visual feedback and recommendations
4. Leveraging AI to suggest conflict resolutions

This feature significantly improves data integrity and user experience in the schedule management system.
