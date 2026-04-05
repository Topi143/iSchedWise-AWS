# Entity Relationship Diagram (ERD)
## iSchedWise V4 — School Scheduling System

> **Source of truth:** `ischedwise_db.sql`
>
> **Legend:** PK = Primary Key · FK = Foreign Key
>
> **See also:** [THESIS_ARCHITECTURE.md](THESIS_ARCHITECTURE.md) for client-server and container architecture views.

---

## Simplified ERD *(for thesis main body)*

> Shows entities, key attributes, and relationships only. Omits operational columns (`created_at`, `updated_at`, `ip_address`, etc.).

```mermaid
erDiagram

    USERS {
        int id PK
        varchar username
        varchar email
        varchar role
        tinyint is_active
        tinyint is_archived
        tinyint two_factor_enabled
    }
    LOGIN_HISTORY {
        int id PK
        int user_id FK
        datetime login_at
        datetime logout_at
    }
    USER_ACTIVITY_LOGS {
        int id PK
        int user_id FK
        varchar action
        varchar entity_type
    }
    TRUSTED_DEVICES {
        int id PK
        int user_id FK
        varchar label
        datetime expires_at
    }
    USER_PROGRAMS {
        int id PK
        int user_id FK
        int program_id FK
    }

    DEPARTMENTS {
        int id PK
        varchar department_name
        varchar department_code
    }
    PROGRAMS {
        int id PK
        varchar program_code
        varchar program_name
        int department_id FK
        tinyint is_archived
    }

    CURRICULA {
        int id PK
        varchar curriculum_code
        varchar curriculum_name
        int program_id FK
        tinyint is_archived
    }
    YEAR_LEVELS {
        int id PK
        int curriculum_id FK
        int year_number
        varchar year_name
    }
    SEMESTERS {
        int id PK
        int year_level_id FK
        varchar semester_name
    }
    SUBJECTS {
        int id PK
        int semester_id FK
        varchar subject_code
        varchar course_description
        decimal total_units
    }
    SECTIONS {
        int id PK
        int program_id FK
        varchar section_name
        int year_level
    }

    FACULTY {
        int id PK
        varchar last_name
        varchar first_name
        int department_id FK
        tinyint is_archived
    }
    FACULTY_AVAILABILITY {
        int id PK
        int faculty_id FK
        varchar day_of_week
        time start_time
        time end_time
    }
    FACULTY_SUBJECT_ASSIGNMENTS {
        int id PK
        int faculty_id FK
        int subject_id FK
        varchar academic_year
        varchar semester
    }

    BUILDINGS {
        int id PK
        varchar building_name
        tinyint is_archived
    }
    ROOMS {
        int id PK
        int building_id FK
        varchar room_number
        varchar room_type
    }

    ACADEMIC_SETTINGS {
        int id PK
        varchar academic_year
        varchar semester
        tinyint is_active
    }
    SCHEDULES {
        int id PK
        int section_id FK
        int subject_id FK
        int faculty_id FK
        int room_id FK
        varchar day_of_week
        time start_time
        time end_time
    }
    EXAM_SCHEDULES {
        int id PK
        int section_id FK
        int subject_id FK
        int faculty_id FK
        int room_id FK
        date exam_date
        varchar exam_period
    }
    SCHEDULE_SNAPSHOTS {
        int id PK
        varchar snapshot_name
        varchar snapshot_scope
        int section_id FK
        int created_by FK
        datetime created_at
    }

    ARCHIVES {
        int id PK
        int section_id FK
        int subject_id FK
        int faculty_id FK
        int room_id FK
        varchar academic_year
        varchar schedule_type
        int archived_by FK
    }

    INSTITUTION_SETTINGS {
        int id PK
        varchar institution_name
        varchar institution_head
    }
    SYSTEM_CONFIG {
        int id PK
        varchar config_key
        text config_value
        varchar category
    }

    USERS ||--o{ LOGIN_HISTORY : "has sessions"
    USERS ||--o{ USER_ACTIVITY_LOGS : "has logs"
    USERS ||--o{ TRUSTED_DEVICES : "has trusted devices"
    USERS ||--o{ USER_PROGRAMS : "assigned programs"
    DEPARTMENTS ||--o{ PROGRAMS : "has programs"
    DEPARTMENTS ||--o{ FACULTY : "employs"
    USERS |o--o{ PROGRAMS : "archives"
    PROGRAMS ||--o{ USER_PROGRAMS : "maps access"
    USERS |o--o{ BUILDINGS : "archives"
    PROGRAMS ||--o{ CURRICULA : "has curricula"
    PROGRAMS ||--o{ SECTIONS : "has sections"
    CURRICULA ||--o{ YEAR_LEVELS : "contains"
    YEAR_LEVELS ||--o{ SEMESTERS : "has semesters"
    SEMESTERS ||--o{ SUBJECTS : "contains subjects"
    USERS |o--o{ CURRICULA : "creates / archives"
    FACULTY ||--o{ FACULTY_AVAILABILITY : "has availability"
    FACULTY ||--o{ FACULTY_SUBJECT_ASSIGNMENTS : "has assignments"
    SUBJECTS ||--o{ FACULTY_SUBJECT_ASSIGNMENTS : "assigned to"
    USERS |o--o{ FACULTY : "archives"
    USERS |o--o{ FACULTY_AVAILABILITY : "creates"
    USERS |o--o{ FACULTY_SUBJECT_ASSIGNMENTS : "archives"
    BUILDINGS ||--o{ ROOMS : "contains rooms"
    SECTIONS ||--o{ SCHEDULES : "scheduled in"
    SUBJECTS ||--o{ SCHEDULES : "part of"
    FACULTY |o--o{ SCHEDULES : "teaches"
    ROOMS |o--o{ SCHEDULES : "held in"
    USERS |o--o{ SCHEDULES : "locks"
    SECTIONS ||--o{ EXAM_SCHEDULES : "has exams"
    SUBJECTS ||--o{ EXAM_SCHEDULES : "part of"
    FACULTY |o--o{ EXAM_SCHEDULES : "proctors"
    ROOMS |o--o{ EXAM_SCHEDULES : "held in"
    USERS |o--o{ EXAM_SCHEDULES : "locks"
    SECTIONS |o--o{ SCHEDULE_SNAPSHOTS : "snapshot scope"
    USERS |o--o{ SCHEDULE_SNAPSHOTS : "created by"
    SECTIONS |o--o{ ARCHIVES : "archived from"
    SUBJECTS |o--o{ ARCHIVES : "archived from"
    FACULTY |o--o{ ARCHIVES : "archived from"
    ROOMS |o--o{ ARCHIVES : "archived from"
    USERS ||--o{ ARCHIVES : "archived by"
    USERS |o--o{ INSTITUTION_SETTINGS : "updates"
    USERS |o--o{ SYSTEM_CONFIG : "updates"
```

---

## Full Physical ERD *(for thesis appendix)*

> Complete schema with all columns and data types, mirroring `ischedwise_db.sql` exactly.
> Split into 8 diagrams by logical group. Stub entries (id only) represent cross-group foreign key references.

---

### Diagram 1 — User & Authentication

```mermaid
erDiagram

    USERS {
        int id PK
        varchar username
        varchar email
        varchar password_hash
        varchar role
        varchar full_name
        tinyint is_active
        tinyint is_archived
        int archived_by FK
        datetime archived_at
        varchar archive_reason
        tinyint email_verified
        datetime email_verified_at
        tinyint needs_password_change
        tinyint two_factor_enabled
        varchar two_factor_secret
        datetime two_factor_enabled_at
        int text_size
        tinyint dark_mode
        datetime created_at
        datetime updated_at
        datetime last_login
        datetime force_logout_at
    }

    LOGIN_HISTORY {
        int id PK
        int user_id FK
        datetime login_at
        datetime logout_at
        varchar ip_address
        text user_agent
        varchar session_id
        tinyint is_active
    }

    USER_ACTIVITY_LOGS {
        int id PK
        int user_id FK
        varchar action
        varchar entity_type
        int entity_id
        varchar entity_name
        text details
        varchar ip_address
        varchar user_agent
        datetime created_at
    }

    TRUSTED_DEVICES {
        int id PK
        int user_id FK
        varchar token_hash
        varchar label
        varchar ip_address
        varchar user_agent
        datetime expires_at
        datetime last_used_at
        datetime created_at
    }

    USERS ||--o{ LOGIN_HISTORY : "has sessions"
    USERS ||--o{ USER_ACTIVITY_LOGS : "has logs"
    USERS ||--o{ TRUSTED_DEVICES : "has trusted devices"
```

---

### Diagram 2 — Organization

```mermaid
erDiagram

    USERS {
        int id PK
    }

    DEPARTMENTS {
        int id PK
        varchar department_name
        varchar department_code
        varchar secretary_name
        tinyint is_active
        datetime created_at
        datetime updated_at
    }

    PROGRAMS {
        int id PK
        varchar program_code
        varchar program_name
        int department_id FK
        varchar program_logo
        int year_levels
        varchar shared_program_code
        int shared_until_year
        tinyint is_active
        tinyint is_archived
        int archived_by FK
        datetime archived_at
        varchar archive_reason
        datetime created_at
        datetime updated_at
    }

    USER_PROGRAMS {
        int id PK
        int user_id FK
        int program_id FK
        datetime created_at
    }

    DEPARTMENTS ||--o{ PROGRAMS : "has programs"
    USERS |o--o{ PROGRAMS : "archives"
    USERS ||--o{ USER_PROGRAMS : "assigned programs"
    PROGRAMS ||--o{ USER_PROGRAMS : "maps user access"
```

---

### Diagram 3 — Curriculum & Subjects

```mermaid
erDiagram

    PROGRAMS {
        int id PK
    }

    USERS {
        int id PK
    }

    CURRICULA {
        int id PK
        varchar curriculum_code
        varchar curriculum_name
        int program_id FK
        varchar degree_program
        tinyint is_active
        tinyint is_archived
        int archived_by FK
        datetime archived_at
        varchar archive_reason
        int created_by FK
        datetime created_at
        datetime updated_at
    }

    YEAR_LEVELS {
        int id PK
        int curriculum_id FK
        int year_number
        varchar year_name
        datetime created_at
        datetime updated_at
    }

    SEMESTERS {
        int id PK
        int year_level_id FK
        int semester_number
        varchar semester_name
        datetime created_at
        datetime updated_at
    }

    SUBJECTS {
        int id PK
        int semester_id FK
        varchar subject_code
        varchar course_description
        decimal lec_units
        decimal lab_units
        decimal total_units
        varchar prerequisite
        datetime created_at
        datetime updated_at
    }

    SECTIONS {
        int id PK
        int program_id FK
        varchar section_name
        int year_level
        datetime created_at
        datetime updated_at
    }

    PROGRAMS ||--o{ CURRICULA : "has curricula"
    PROGRAMS ||--o{ SECTIONS : "has sections"
    CURRICULA ||--o{ YEAR_LEVELS : "contains year levels"
    YEAR_LEVELS ||--o{ SEMESTERS : "has semesters"
    SEMESTERS ||--o{ SUBJECTS : "contains subjects"
    USERS |o--o{ CURRICULA : "creates / archives"
```

---

### Diagram 4 — Faculty

```mermaid
erDiagram

    DEPARTMENTS {
        int id PK
    }

    SUBJECTS {
        int id PK
    }

    USERS {
        int id PK
    }

    FACULTY {
        int id PK
        varchar last_name
        varchar first_name
        varchar middle_initial
        enum gender
        int department_id FK
        int max_units
        tinyint is_active
        tinyint is_archived
        int archived_by FK
        datetime archived_at
        varchar archive_reason
        datetime created_at
        datetime updated_at
    }

    FACULTY_AVAILABILITY {
        int id PK
        int faculty_id FK
        varchar day_of_week
        time start_time
        time end_time
        varchar academic_year
        varchar semester
        tinyint is_active
        datetime created_at
        datetime updated_at
        int created_by FK
    }

    FACULTY_SUBJECT_ASSIGNMENTS {
        int id PK
        int faculty_id FK
        int subject_id FK
        varchar academic_year
        varchar semester
        tinyint is_active
        tinyint is_archived
        int archived_by FK
        datetime archived_at
        varchar archive_reason
        datetime created_at
        datetime updated_at
    }

    DEPARTMENTS ||--o{ FACULTY : "employs"
    FACULTY ||--o{ FACULTY_AVAILABILITY : "has availability"
    FACULTY ||--o{ FACULTY_SUBJECT_ASSIGNMENTS : "has assignments"
    SUBJECTS ||--o{ FACULTY_SUBJECT_ASSIGNMENTS : "assigned to faculty"
    USERS |o--o{ FACULTY : "archives"
    USERS |o--o{ FACULTY_AVAILABILITY : "creates"
    USERS |o--o{ FACULTY_SUBJECT_ASSIGNMENTS : "archives"
```

---

### Diagram 5 — Facilities

```mermaid
erDiagram

    USERS {
        int id PK
    }

    BUILDINGS {
        int id PK
        varchar building_name
        tinyint is_active
        tinyint is_archived
        int archived_by FK
        datetime archived_at
        varchar archive_reason
        datetime created_at
        datetime updated_at
    }

    ROOMS {
        int id PK
        int building_id FK
        varchar room_number
        varchar room_type
        tinyint is_available
        datetime created_at
        datetime updated_at
    }

    BUILDINGS ||--o{ ROOMS : "contains rooms"
    USERS |o--o{ BUILDINGS : "archives"
```

---

### Diagram 6 — Class & Exam Scheduling

```mermaid
erDiagram

    SECTIONS {
        int id PK
    }

    SUBJECTS {
        int id PK
    }

    FACULTY {
        int id PK
    }

    ROOMS {
        int id PK
    }

    USERS {
        int id PK
    }

    ACADEMIC_SETTINGS {
        int id PK
        varchar academic_year
        varchar semester
        varchar exam_period
        date exam_period_start
        date exam_period_end
        varchar available_semesters
        int schedule_start_hour
        int schedule_end_hour
        int exam_start_hour
        int exam_end_hour
        time exam_lunch_start
        time exam_lunch_end
        int exam_slot_duration
        int exam_duration_limit
        int default_faculty_max_units
        varchar operation_days
        tinyint is_active
        datetime created_at
        datetime updated_at
        time schedule_start_time
        time schedule_end_time
        time exam_start_time
        time exam_end_time
        int smart_max_backtracks_per_subject
        int smart_max_total_backtracks
        int smart_timeout_seconds
    }

    SCHEDULES {
        int id PK
        int section_id FK
        int subject_id FK
        int faculty_id FK
        int room_id FK
        varchar day_of_week
        time start_time
        time end_time
        varchar semester
        varchar academic_year
        varchar schedule_type
        tinyint is_active
        int version
        int locked_by FK
        datetime locked_at
        datetime created_at
        datetime updated_at
    }

    EXAM_SCHEDULES {
        int id PK
        int section_id FK
        int subject_id FK
        int faculty_id FK
        int room_id FK
        date exam_date
        time start_time
        time end_time
        varchar semester
        varchar academic_year
        varchar exam_period
        varchar schedule_type
        tinyint is_active
        int version
        int locked_by FK
        datetime locked_at
        datetime created_at
        datetime updated_at
    }

    SCHEDULE_SNAPSHOTS {
        int id PK
        varchar snapshot_name
        varchar academic_year
        varchar semester
        varchar snapshot_scope
        int section_id FK
        longtext schedule_data
        int schedule_count
        varchar snapshot_type
        int created_by FK
        datetime created_at
        text notes
    }

    SECTIONS ||--o{ SCHEDULES : "scheduled in"
    SUBJECTS ||--o{ SCHEDULES : "part of"
    FACULTY |o--o{ SCHEDULES : "teaches"
    ROOMS |o--o{ SCHEDULES : "held in"
    USERS |o--o{ SCHEDULES : "locks"
    SECTIONS ||--o{ EXAM_SCHEDULES : "has exam schedules"
    SUBJECTS ||--o{ EXAM_SCHEDULES : "part of"
    FACULTY |o--o{ EXAM_SCHEDULES : "proctors"
    ROOMS |o--o{ EXAM_SCHEDULES : "held in"
    USERS |o--o{ EXAM_SCHEDULES : "locks"
    SECTIONS |o--o{ SCHEDULE_SNAPSHOTS : "snapshot scope"
    USERS |o--o{ SCHEDULE_SNAPSHOTS : "created by"
```

---

### Diagram 7 — Archives

```mermaid
erDiagram

    SECTIONS {
        int id PK
    }

    SUBJECTS {
        int id PK
    }

    FACULTY {
        int id PK
    }

    ROOMS {
        int id PK
    }

    USERS {
        int id PK
    }

    ARCHIVES {
        int id PK
        int section_id FK
        int subject_id FK
        int faculty_id FK
        int room_id FK
        varchar section_name
        varchar subject_code
        varchar course_description
        varchar faculty_name
        varchar room_number
        varchar building_name
        varchar program_name
        varchar day_of_week
        date exam_date
        time start_time
        time end_time
        varchar semester
        varchar academic_year
        varchar schedule_type
        varchar exam_period
        int original_schedule_id
        int archived_by FK
        varchar archive_reason
        datetime archived_at
    }

    SECTIONS |o--o{ ARCHIVES : "archived from"
    SUBJECTS |o--o{ ARCHIVES : "archived from"
    FACULTY |o--o{ ARCHIVES : "archived from"
    ROOMS |o--o{ ARCHIVES : "archived from"
    USERS ||--o{ ARCHIVES : "archived by"
```

---

### Diagram 8 — System & Settings

```mermaid
erDiagram

    USERS {
        int id PK
    }

    INSTITUTION_SETTINGS {
        int id PK
        varchar institution_name
        varchar system_name
        varchar institution_logo
        varchar branding_logo
        varchar institution_logo_right
        varchar institution_head
        int updated_by FK
        datetime created_at
        datetime updated_at
        varchar excel_header_line1
        varchar excel_header_line2
        varchar excel_schedule_color
    }

    SYSTEM_CONFIG {
        int id PK
        varchar config_key
        text config_value
        enum config_type
        varchar category
        varchar description
        int updated_by FK
        datetime updated_at
    }

    USERS |o--o{ INSTITUTION_SETTINGS : "updates"
    USERS |o--o{ SYSTEM_CONFIG : "updates"
```
