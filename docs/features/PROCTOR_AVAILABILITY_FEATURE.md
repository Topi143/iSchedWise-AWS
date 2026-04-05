# Proctor Availability Feature

## Overview

The Proctor Availability feature allows faculty members to set their availability for exam proctoring duties. This helps exam schedulers identify which faculty members are available, preferred, or unavailable for specific time slots when assigning proctors to exams.

## Database Schema

### `faculty_availability` Table

```sql
CREATE TABLE `faculty_availability` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `faculty_id` INT(11) NOT NULL,
  `day_of_week` VARCHAR(20) DEFAULT NULL COMMENT 'Monday, Tuesday, etc. for recurring availability',
  `specific_date` DATE DEFAULT NULL COMMENT 'For specific date availability',
  `start_time` TIME NOT NULL,
  `end_time` TIME NOT NULL,
  `availability_type` ENUM('available', 'unavailable', 'preferred') NOT NULL DEFAULT 'available',
  `reason` VARCHAR(255) DEFAULT NULL COMMENT 'Optional reason for availability status',
  `academic_year` VARCHAR(20) DEFAULT NULL,
  `semester` VARCHAR(50) DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by` INT(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_faculty_id` (`faculty_id`),
  KEY `idx_day_of_week` (`day_of_week`),
  KEY `idx_specific_date` (`specific_date`),
  KEY `idx_availability_type` (`availability_type`),
  CONSTRAINT `faculty_availability_ibfk_1` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE CASCADE,
  CONSTRAINT `faculty_availability_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## API Endpoints

### Faculty Availability Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/faculty/api/<faculty_id>/availability` | Get all availability slots for a faculty |
| POST | `/faculty/api/<faculty_id>/availability` | Add new availability slot |
| PUT | `/faculty/api/<faculty_id>/availability/<id>` | Update existing availability slot |
| DELETE | `/faculty/api/<faculty_id>/availability/<id>` | Delete availability slot |
| POST | `/faculty/api/<faculty_id>/availability/check` | Check availability for specific date/time |
| POST | `/faculty/api/available-proctors` | Get available proctors for an exam slot |

### Request/Response Examples

#### Add Availability Slot
```json
// POST /faculty/api/1/availability
// Request body:
{
  "availability_type": "weekly",  // or "specific"
  "day_of_week": "Monday",        // for weekly
  "specific_date": "2025-01-15",  // for specific
  "start_time": "08:00",
  "end_time": "12:00",
  "status": "preferred",          // available, unavailable, preferred
  "reason": "Morning classes done"
}

// Response:
{
  "success": true,
  "message": "Availability added successfully",
  "availability": {
    "id": 1,
    "faculty_id": 1,
    "day_of_week": "Monday",
    "start_time": "08:00:00",
    "end_time": "12:00:00",
    "availability_type": "preferred",
    "reason": "Morning classes done"
  }
}
```

#### Get Available Proctors
```json
// POST /faculty/api/available-proctors
// Request body:
{
  "exam_date": "2025-01-15",
  "start_time": "09:00",
  "end_time": "12:00",
  "department_id": 1  // optional
}

// Response:
{
  "success": true,
  "proctors": [
    {
      "id": 1,
      "name": "Dr. John Smith",
      "department": "Computer Science",
      "availability_status": "preferred",
      "availability_reason": "Morning classes done"
    },
    {
      "id": 2,
      "name": "Prof. Jane Doe",
      "department": "Computer Science",
      "availability_status": "unavailable",
      "availability_reason": "Department meeting"
    }
  ]
}
```

## Model Methods

### `FacultyAvailability` Class

| Method | Description |
|--------|-------------|
| `to_dict()` | Convert to JSON-serializable dictionary |
| `check_faculty_available(faculty_id, date, start, end)` | Check if faculty is available for slot |
| `get_faculty_weekly_availability(faculty_id)` | Get weekly availability grouped by day |
| `get_available_proctors_for_slot(date, start, end, dept_id)` | Get all faculty with availability status |

### Availability Types

- **available**: Faculty is available for proctoring
- **unavailable**: Faculty cannot proctor during this time
- **preferred**: Faculty prefers this time slot for proctoring

## UI Components

### Faculty Management Page

The faculty detail panel includes an "Availability" section showing:
- Summary counts (preferred, available, unavailable slots)
- "Manage" button to open availability modal

### Availability Modal

Features:
- Toggle between Weekly and Specific Date availability
- Day of week selector (for weekly)
- Date picker (for specific dates)
- Time range selectors
- Status radio buttons (Preferred, Available, Unavailable)
- Optional reason text field
- List of existing availability slots with delete option

### Exam Scheduling Integration

When scheduling exams, the faculty dropdown shows availability badges:
- 🟢 **Preferred** (green badge) - Faculty prefers this slot
- 🔵 **Available** (blue badge) - Faculty is available
- 🔴 **Unavailable** (red badge) - Faculty is not available
- ⚪ **No Info** (gray badge) - No availability data

A warning is displayed when selecting an unavailable proctor.

## JavaScript Functions

Located in `app/static/js/schedule/schedule_full.js`:

| Function | Description |
|----------|-------------|
| `checkProctorAvailability(mode)` | Fetch and display availability when date/time changes |
| `applyProctorAvailabilityBadges(mode, proctors)` | Add badges to faculty dropdown options |
| `createAvailabilityBadge(status, reason)` | Create badge HTML element |
| `resetProctorAvailabilityBadges(mode)` | Remove all availability badges |
| `checkSelectedProctorAvailability(facultyId, mode)` | Show warning for unavailable proctor |
| `setupProctorAvailabilityListeners()` | Initialize event listeners |

## Usage Guide

### Setting Up Availability (Faculty/Admin)

1. Navigate to **Faculty Management**
2. Select a faculty member from the list
3. In the detail panel, find the **Availability** section
4. Click **Manage** to open the availability modal
5. Choose **Weekly** or **Specific Date**
6. For weekly: Select day of week
7. For specific: Select the date
8. Set start and end times
9. Choose status: Preferred, Available, or Unavailable
10. Optionally add a reason
11. Click **Add Availability**

### Viewing Availability When Scheduling Exams

1. Navigate to **Schedule Management** → **Exam Schedules**
2. Click to add or edit an exam schedule
3. Select the exam date and time
4. When selecting a proctor (faculty), colored badges will appear:
   - Green (Preferred): Faculty prefers this time
   - Blue (Available): Faculty is available
   - Red (Unavailable): Faculty is not available
5. If selecting an unavailable faculty, a warning appears below the dropdown

## File Locations

| File | Purpose |
|------|---------|
| `database.sql` | Schema definition for `faculty_availability` table |
| `app/models/faculty.py` | `FacultyAvailability` model class |
| `app/routes/faculty.py` | Availability API routes |
| `app/templates/faculty.html` | Availability UI (modal and detail section) |
| `app/static/js/schedule/schedule_full.js` | Exam scheduling availability integration |
| `app/templates/schedule/_modals.html` | Proctor warning containers |

## Future Enhancements

1. **Bulk Availability Import** - Import availability from spreadsheet
2. **Availability Reports** - Generate reports of faculty availability
3. **Conflict Resolution** - Automatic suggestions for resolving proctor conflicts
4. **Calendar Integration** - Sync with Google Calendar/Outlook
5. **Mobile App** - Faculty can set availability from mobile device
6. **Notifications** - Alert faculty when assigned as proctor during unavailable time
