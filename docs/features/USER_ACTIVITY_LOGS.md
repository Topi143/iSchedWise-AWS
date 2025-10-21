# User Activity Logs Feature

## Overview
The User Activity Logs feature provides administrators with comprehensive tracking and auditing capabilities for all user actions within the iSchedWise system.

## Access
- **Admin Only**: This feature is only accessible to users with the `admin` role
- **Location**: Reports page → User Activity tab

## Features

### Activity Dashboard
- **Total Actions**: Total count of all recorded actions
- **Last 24 Hours**: Recent activity count
- **Unique Actions**: Number of different action types
- **Most Active User**: User with the highest number of actions

### Activity Filters
Filter activity logs by:
- **User**: Filter by specific user
- **Action Type**: Filter by action (created, edited, deleted, archived, etc.)
- **Entity Type**: Filter by entity (schedule, faculty, building, curriculum, etc.)

### Activity Log Table
Displays:
- **Time**: When the action occurred
- **User**: Who performed the action (with role)
- **Action**: Type of action with color-coded badges:
  - 🟢 Green: Created/Added
  - 🔵 Blue: Edited/Updated
  - 🔴 Red: Deleted/Removed
  - 🟠 Orange: Archived
  - 🟣 Purple: Unarchived/Restored
  - ⚪ Gray: Other actions
- **Entity**: Type and name of affected entity
- **Details**: Additional information about the action

### Pagination
- 50 logs per page
- Previous/Next navigation
- Shows current range and total count

## Database Schema

### Table: `user_activity_logs`
```sql
CREATE TABLE `user_activity_logs` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `action` VARCHAR(100) NOT NULL,
  `entity_type` VARCHAR(50) NOT NULL,
  `entity_id` INT(11) DEFAULT NULL,
  `entity_name` VARCHAR(255) DEFAULT NULL,
  `details` TEXT DEFAULT NULL,
  `ip_address` VARCHAR(45) DEFAULT NULL,
  `user_agent` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `idx_action` (`action`),
  KEY `idx_entity_type` (`entity_type`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `user_activity_logs_ibfk_1` FOREIGN KEY (`user_id`) 
    REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Usage

### Logging Actions in Code

#### Method 1: Using Helper Functions (Recommended)
```python
from app.utils.activity_logger import log_create, log_edit, log_delete, log_archive

# Log entity creation
log_create(
    entity_type='schedule',
    entity_id=schedule.id,
    entity_name=f"{schedule.subject.subject_code} - {schedule.section.section_name}",
    details='Created new class schedule'
)

# Log entity editing
log_edit(
    entity_type='faculty',
    entity_id=faculty.id,
    entity_name=faculty.full_name,
    details='Updated faculty department'
)

# Log entity deletion
log_delete(
    entity_type='building',
    entity_id=building.id,
    entity_name=building.building_name,
    details='Removed building from system'
)

# Commit the transaction
db.session.commit()
```

#### Method 2: Using Model Directly
```python
from app.models.activity_log import UserActivityLog
from flask_login import current_user
from flask import request

# Log an action
UserActivityLog.log_action(
    user_id=current_user.id,
    action='created',
    entity_type='schedule',
    entity_id=schedule.id,
    entity_name=f"{schedule.subject.subject_code} - {schedule.section.section_name}",
    details='Created new class schedule',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)

# Commit the transaction
db.session.commit()
```

### Common Action Types
- `created` - New entity created
- `edited` - Entity modified
- `deleted` - Entity removed
- `archived` - Entity archived
- `unarchived` - Entity restored from archive
- `login` - User logged in
- `logout` - User logged out

### Common Entity Types
- `schedule` - Class schedules
- `exam_schedule` - Exam schedules
- `faculty` - Faculty members
- `building` - Buildings
- `room` - Rooms
- `department` - Departments
- `curriculum` - Curricula
- `subject` - Subjects
- `section` - Sections
- `user` - User accounts

## API Endpoints

### Get Activity Logs
```
GET /reports/api/user-activity
Query Parameters:
- page: Page number (default: 1)
- per_page: Items per page (default: 50)
- user_id: Filter by user ID
- action: Filter by action type
- entity_type: Filter by entity type
```

### Get Activity Statistics
```
GET /reports/api/user-activity/stats
Returns:
- total_actions: Total action count
- recent_actions_24h: Actions in last 24 hours
- actions_by_type: Breakdown by action type
- actions_by_entity: Breakdown by entity type
- most_active_users: Top 10 most active users
```

## Implementation Files

### Database
- `database.sql` - Table schema

### Models
- `app/models/activity_log.py` - UserActivityLog model

### Routes
- `app/routes/reports.py` - API endpoints for activity logs

### Templates
- `app/templates/reports.html` - User Activity tab UI

## Future Enhancements
- Export activity logs to Excel
- Real-time activity monitoring
- Activity log retention policies
- Advanced analytics and charts
- IP geolocation tracking
- Detailed action diffs (show what changed)

## Notes
- Activity logs are automatically cleaned up when users are deleted (CASCADE)
- Logs are indexed for fast searching by user, action, entity type, and date
- IP address and user agent are optional but recommended for security auditing
- The `details` field can store JSON or text for additional context
