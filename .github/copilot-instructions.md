# GitHub Copilot Instructions for iSchedWise V4

## 📋 Response Style Guidelines

**Keep responses concise and actionable:**
- ✅ Provide code directly with minimal explanation
- ✅ List files created/modified with file paths
- ✅ Focus on solving the specific problem
- ✅ Show before/after diffs for clarity when needed
- ✅ Include verification steps for critical changes
- ❌ No verbose explanations or unnecessary commentary
- ❌ No lengthy introductions or summaries
- ❌ Don't assume context - always verify file paths and existing code

## 🎯 Quick Reference

### When User Asks To...
- **Add a feature** → Check database.sql → Update models → Update routes → Update templates
- **Fix a bug** → Read error logs → Check related code → Test fix → Verify no side effects
- **Archive something** → Use standard archive pattern (see below) → Don't create separate tables
- **Change database** → Update database.sql FIRST → Then sample_data.sql → Then Python models
- **Add a route** → Use blueprints → Add @login_required → Check user permissions
- **Modify UI** → Check base.html → Use Tailwind classes → Keep mobile-responsive
- **Clean workspace** → Delete old templates (*_old.html, *.backup) → Move obsolete test files → Archive outdated docs
- **Test changes** → Drop DB → Import database.sql → Import sample_data.sql → Run app

## 🔴 CRITICAL: Database Management Approach

**This project uses direct SQL files, NOT Flask-Migrate migrations!**

### Database Schema Source of Truth
- ✅ **`database.sql`** - Contains ALL table definitions, indexes, constraints
- ✅ **`sample_data.sql`** - Contains test data matching the schema
- ❌ **Flask-Migrate** - NOT used for schema changes
- ❌ **Alembic migrations** - NOT used for schema changes

### 🔴 MANDATORY: Database Consistency Rules

**When making ANY database changes, ALWAYS maintain consistency across ALL three layers:**

#### Layer 1: Database Schema (`database.sql`)
- **ALWAYS update FIRST** - This is the source of truth
- Include ALL details: data types, defaults, constraints, indexes, foreign keys
- Use consistent naming conventions (see below)
- Add comments explaining purpose of new columns/tables

#### Layer 2: Sample Data (`sample_data.sql`)
- **ALWAYS update SECOND** - Must match schema exactly
- Remove references to deleted tables (DELETE, ALTER AUTO_INCREMENT)
- Add sample rows for new tables
- Ensure foreign key values are valid

#### Layer 3: Python Models (`app/models/*.py`)
- **ALWAYS update THIRD** - Must mirror database.sql exactly
- Match column names, data types, and constraints
- Include relationships (backref, cascade)
- Add helper methods if needed

### 🎯 Consistency Checklist for Database Changes

Before committing database changes, verify:

- [ ] **Column names match** across SQL and Python models
- [ ] **Data types match** (TINYINT(1) → Boolean, VARCHAR → String, etc.)
- [ ] **Default values match** (DEFAULT 0 → default=0)
- [ ] **NULL/NOT NULL matches** (NOT NULL → nullable=False)
- [ ] **Foreign keys match** (FOREIGN KEY → db.ForeignKey)
- [ ] **ON DELETE behavior matches** (CASCADE → ondelete='CASCADE')
- [ ] **Indexes exist** for foreign keys and frequently queried columns
- [ ] **Sample data includes** examples of new tables/columns
- [ ] **No orphaned references** to deleted tables in sample_data.sql
- [ ] **Comments explain** the purpose of changes

### 📋 Standard Archive Pattern

**All archive features MUST follow this consistent pattern:**

```sql
-- In database.sql - Add these columns to archivable tables:
`is_active` TINYINT(1) NOT NULL DEFAULT 1,
`is_archived` TINYINT(1) NOT NULL DEFAULT 0,
`archived_by` INT(11) DEFAULT NULL,
`archived_at` DATETIME NULL DEFAULT NULL,
`archive_reason` VARCHAR(255) NULL DEFAULT NULL,
KEY `idx_is_archived` (`is_archived`),
KEY `archived_by` (`archived_by`),
CONSTRAINT `{table}_ibfk_archived_by` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
```

```python
# In Python models - Add these columns and methods:
is_active = db.Column(db.Boolean, nullable=False, default=True)
is_archived = db.Column(db.Boolean, nullable=False, default=False)
archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
archived_at = db.Column(db.DateTime, nullable=True)
archive_reason = db.Column(db.String(255), nullable=True)

def archive(self, user_id=None, reason=None):
    """Mark as archived instead of deleting."""
    self.is_archived = True
    self.is_active = False
    self.archived_by = user_id
    self.archive_reason = reason
    from datetime import datetime
    self.archived_at = datetime.utcnow()

def unarchive(self):
    """Restore from archive."""
    self.is_archived = False
    self.is_active = True
    self.archived_by = None
    self.archive_reason = None
    self.archived_at = None
```

**Archive Pattern Rules:**
- ❌ **DO NOT** create separate archive tables (e.g., `curricula_archives`)
- ✅ **DO** use flags on the main table (`is_archived`, `is_active`)
- ✅ **DO** keep foreign keys intact (curriculum → department remains)
- ✅ **DO** filter queries by `is_archived=False` for active items
- ✅ **DO** track who archived, when, and why

**Exception:** Historical denormalized archives (like `archives` table for schedules) are allowed when:
- Need to preserve data after related records are deleted
- Store point-in-time snapshots with text copies of names/codes
- Support complex time-based filtering (academic year, semester, exam period)

### 🔧 Database Change Workflow

1. **Plan the change:**
   - What tables/columns are affected?
   - What are the foreign key relationships?
   - Do existing queries need updates?
   - Will this break sample data?

2. **Update `database.sql`:**
   ```sql
   -- Add new columns with proper constraints
   ALTER TABLE `table_name` ADD COLUMN `new_field` VARCHAR(50) NULL;
   
   -- Add indexes for foreign keys and frequently queried columns
   ALTER TABLE `table_name` ADD KEY `idx_new_field` (`new_field`);
   
   -- Add foreign key constraints with ON DELETE behavior
   ALTER TABLE `table_name` ADD CONSTRAINT `fk_new_field` 
   FOREIGN KEY (`new_field`) REFERENCES `other_table` (`id`) ON DELETE SET NULL;
   ```

3. **Update `sample_data.sql`:**
   ```sql
   -- Remove references if deleting tables
   DELETE FROM `old_table` WHERE id > 0;
   ALTER TABLE `old_table` AUTO_INCREMENT = 1;
   
   -- Add sample data for new columns
   UPDATE `table_name` SET `new_field` = 'sample_value' WHERE id = 1;
   ```

4. **Update Python models:**
   ```python
   # Add column matching SQL exactly
   new_field = db.Column(db.String(50), nullable=True)
   
   # Add relationship if foreign key
   related_item = db.relationship('OtherTable', backref='items')
   ```

5. **Test the changes:**
   - Drop database in phpMyAdmin
   - Import `database.sql`
   - Import `sample_data.sql`
   - Run application and verify no errors
   - Test affected features

### 🚫 Never Do This:
- ❌ `flask db migrate` - Don't use
- ❌ `flask db upgrade` - Don't use
- ❌ Creating Alembic migration files
- ❌ Modifying database through ORM migrations
- ❌ Changing schema without updating database.sql
- ❌ Creating separate archive tables for new features
- ❌ Inconsistent archive column names across tables
- ❌ Missing indexes on foreign keys
- ❌ Missing ON DELETE behavior on foreign keys
- ❌ Leaving orphaned references in sample_data.sql

---

## 🏗️ Project Overview

iSchedWise V4 is a Flask-based web application for managing school schedules, rooms, and faculty resources. It supports class scheduling, exam scheduling, faculty workload management, and comprehensive reporting.

**User Roles:**
- **Admin**: Full system access, user management, system settings
- **Dean**: Schedule management, faculty assignment, reports (department-specific)

**Key Features:**
- Class & Exam Scheduling with conflict detection and calendar view
- Faculty workload management & assignment
- Room & building management with availability tracking
- Subject templates for standardized curriculum
- Archive system for historical data
- Excel export for reports with charts
- Password reset functionality via email
- AI-powered schedule suggestions (optional)

## Tech Stack & Architecture

### Backend
- **Framework**: Flask 3.1.2 (application factory pattern)
- **Database**: MySQL + SQLAlchemy ORM
- **Authentication**: Flask-Login with role-based access control
- **Forms**: Flask-WTF with CSRF protection
- **AI Integration**: Google Gemini API (optional, for schedule suggestions)

### Frontend
- **CSS Framework**: Tailwind CSS
- **Templates**: Jinja2 with server-side rendering
- **Responsive Design**: Mobile-first approach
- **JavaScript**: Vanilla JS for dynamic interactions

### Key Dependencies
- Flask-SQLAlchemy 3.1.1
- Flask-Login 0.6.3
- PyMySQL 1.1.2
- WTForms 3.2.1
- openpyxl 3.1.5 (Excel exports)
- google-generativeai 0.8.3 (AI features)

## Project Structure

```
📁 iSchedWise V4/
├── 🔴 database.sql          # ⚠️ SOURCE OF TRUTH for database schema
├── 🔴 sample_data.sql       # ⚠️ Test data matching database.sql schema
├── run.py                   # Application entry point (use this, not app.py)
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore patterns
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
├── config/
│   ├── __init__.py
│   └── config.py            # Environment configuration classes
├── app/
│   ├── __init__.py          # Application factory (create_app)
│   ├── extensions.py        # Flask extensions initialization
│   ├── forms.py             # WTForms form classes
│   ├── decorators.py        # Custom decorators (role_required)
│   ├── ai_scheduler.py      # AI schedule suggestion integration
│   ├── models/              # SQLAlchemy models (MUST match database.sql)
│   │   ├── __init__.py
│   │   ├── user.py          # User, role-based access
│   │   ├── schedule.py      # Class schedules
│   │   ├── exam_schedule.py # Exam schedules
│   │   ├── faculty.py       # Faculty management
│   │   ├── building.py      # Buildings and rooms
│   │   ├── department.py    # Departments, sections
│   │   ├── curriculum.py    # Subjects, subject templates
│   │   ├── archive.py       # Historical schedule data
│   │   └── settings.py      # System settings
│   ├── routes/              # Blueprint route handlers
│   │   ├── __init__.py
│   │   ├── auth.py          # Login, logout
│   │   ├── main.py          # Dashboard
│   │   ├── schedule.py      # Schedule CRUD + AI suggestions
│   │   ├── exam_schedule.py # Exam schedule management
│   │   ├── faculty.py       # Faculty management
│   │   ├── building.py      # Building/room management
│   │   ├── department.py    # Department management
│   │   ├── curriculum.py    # Subject management
│   │   ├── archive.py       # Archive management
│   │   ├── reports.py       # Excel reports
│   │   ├── settings.py      # Settings management
│   │   ├── profile.py       # User profile management
│   │   └── user.py          # User management
│   ├── static/              # Static assets (CSS, JS, images)
│   │   ├── images/          # Image files
│   │   ├── js/              # JavaScript files
│   │   └── templates/       # Frontend template references
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html        # Base template with navigation
│       ├── dashboard.html   # Main dashboard
│       ├── schedule.html    # Schedule management
│       ├── faculty.html     # Faculty management
│       ├── building.html    # Building/room management
│       ├── department.html  # Department management
│       ├── curriculum.html  # Curriculum/subject management
│       ├── archive.html     # Archive view
│       ├── reports.html     # Reports page
│       ├── settings.html    # System settings
│       ├── profile.html     # User profile
│       ├── users.html       # User management
│       ├── login.html       # Login page
│       ├── forgot_password.html  # Password reset request
│       ├── reset_password.html   # Password reset form
│       └── schedule/        # Schedule-related templates
├── scripts/                 # Utility scripts
│   ├── init_db.py           # Database initialization helper
│   ├── reimport_database.ps1 # PowerShell script to reset database
│   └── archive/             # Obsolete migration scripts
├── tests/                   # Test files (all test files go here)
│   ├── __init__.py
│   ├── test_ai_direct.py
│   ├── test_faculty_archiving.py
│   ├── test_subject_display.py
│   ├── test_templates.py
│   ├── test_curriculum_archive.py
│   ├── test_password_reset_setup.py
│   └── test_real_unarchive.py
├── docs/                    # Documentation
│   ├── REPORTS_QUICK_REFERENCE.md
│   ├── SIDEBAR_SCROLL_QUICK.md
│   ├── archive/             # Historical implementation notes
│   ├── features/            # Feature documentation
│   ├── fixes/               # Bug fix summaries
│   └── setup/               # Setup guides
└── migrations/              # Legacy (Flask-Migrate not used)
```

**Key Files:**
- 🔴 **database.sql** - ALL table definitions, constraints, indexes (UPDATE THIS FIRST)
- 🔴 **sample_data.sql** - Test data that matches database.sql (UPDATE SECOND)
- **app/models/** - Python models that mirror database.sql (UPDATE THIRD)
- **run.py** - Application entry point (use this to start the app)
- **config/config.py** - Environment configurations
- **app/ai_scheduler.py** - AI integration module (optional)
- **app/decorators.py** - Custom decorators (role_required, etc.)

## 📁 Workspace Organization

### Root Directory
- Keep clean - only essential files (run.py, database.sql, sample_data.sql, requirements.txt)
- Test files go in `tests/` directory
- Documentation goes in `docs/` directory
- Scripts go in `scripts/` directory

### Archive Folders
- **docs/archive/** - Historical implementation notes and fix summaries
- **scripts/archive/** - Obsolete migration and setup scripts

### Active Directories
- **app/** - Main application code
- **config/** - Configuration files
- **tests/** - Test files (ALL test files must be in this directory)
- **docs/** - Essential documentation
- **scripts/** - Active utility scripts (init_db.py, reimport_database.ps1)

### File Placement Rules
- ❌ **DO NOT** create test files in root directory
- ✅ **DO** place all test files in `tests/` directory
- ❌ **DO NOT** create obsolete templates (e.g., `*_old.html`, `*.backup`)
- ✅ **DO** delete old templates when creating new versions
- ❌ **DO NOT** keep obsolete test files (e.g., `*_debug.py`, `check_*.py`)
- ✅ **DO** remove test files once functionality is verified and tests are passing
- ❌ **DO NOT** keep migration scripts in root or scripts/
- ✅ **DO** move obsolete scripts to `scripts/archive/`
- ❌ **DO NOT** keep temporary documentation in root directory
- ✅ **DO** move feature docs to `docs/features/` or `docs/archive/`

## Coding Standards & Conventions

### Python Code Style
- Follow PEP 8 style guidelines
- Use docstrings for all models, functions, and classes
- Use type hints where appropriate
- Maximum line length: 120 characters
- Use descriptive variable names

### Flask Patterns
1. **Application Factory**: Always use `create_app()` pattern from `app/__init__.py`
2. **Blueprints**: Organize routes by feature in separate blueprint files
3. **Models**: One model per file in `app/models/`
4. **Route Decorators**: Always include `@login_required` for protected routes
5. **Database Sessions**: Use `db.session` for all database operations

### Database Conventions
- **Table Names**: Use lowercase with underscores (e.g., `schedules`, `exam_schedules`)
- **Foreign Keys**: Always specify `ondelete` behavior (`CASCADE`, `SET NULL`)
- **Timestamps**: Include `created_at` and `updated_at` fields
- **Boolean Fields**: Default to `True` or `False` explicitly
- **Relationships**: Define bidirectional relationships with backref
- **Archive Columns**: Use standard pattern (is_archived, is_active, archived_by, archived_at, archive_reason)
- **Indexes**: Add indexes for all foreign keys and frequently queried columns
- **Constraints**: Name constraints consistently: `{table}_ibfk_{n}` for foreign keys

### 🔴 CRITICAL: Three-Layer Database Consistency

**Every database change MUST update all three layers in order:**

#### Step 1: Update `database.sql` (Source of Truth)
```sql
-- Example: Adding archive support to a table
ALTER TABLE `table_name` 
ADD COLUMN `is_active` TINYINT(1) NOT NULL DEFAULT 1,
ADD COLUMN `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
ADD COLUMN `archived_by` INT(11) DEFAULT NULL,
ADD COLUMN `archived_at` DATETIME NULL DEFAULT NULL,
ADD COLUMN `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
ADD KEY `idx_is_archived` (`is_archived`),
ADD KEY `archived_by` (`archived_by`),
ADD CONSTRAINT `table_name_ibfk_archived_by` 
  FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;
```

#### Step 2: Update `sample_data.sql` (Test Data)
```sql
-- Remove references to deleted tables
DELETE FROM `old_table` WHERE id > 0;
-- Don't reset AUTO_INCREMENT for deleted tables

-- Add sample data for new columns
UPDATE `table_name` SET `is_archived` = 0, `is_active` = 1 WHERE id > 0;

-- Add sample archived records
INSERT INTO `table_name` (..., `is_archived`, `archived_by`, `archived_at`, `archive_reason`) 
VALUES (..., 1, 1, '2024-02-10 14:20:00', 'Sample archived record');
```

#### Step 3: Update Python Models (SQLAlchemy)
```python
# In app/models/table_name.py
class TableName(db.Model):
    __tablename__ = 'table_name'
    
    # Add archive columns matching SQL exactly
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    
    def archive(self, user_id=None, reason=None):
        """Mark as archived instead of deleting."""
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        from datetime import datetime
        self.archived_at = datetime.utcnow()
    
    def unarchive(self):
        """Restore from archive."""
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
```

#### Step 4: Verify Consistency
```bash
# Test the changes
# 1. Drop database in phpMyAdmin
# 2. Import database.sql
# 3. Import sample_data.sql
# 4. Run application: python run.py
# 5. Test affected features
```

### Form Handling
- Use Flask-WTF for all forms with CSRF protection
- Validate forms server-side with WTForms validators
- Flash appropriate messages for success/error states
- Use `form.validate_on_submit()` for POST requests

### Security Best Practices
- Always use `@login_required` decorator for protected routes
- Use `@role_required('Admin')` or `@role_required('Dean')` for role-based access
- Hash passwords with Werkzeug security
- Enable CSRF protection on all forms
- Sanitize user inputs

## Model Relationships

### Key Models
1. **User**: Admin and Dean roles
2. **Department** → Sections (one-to-many)
3. **Section** → Schedules (one-to-many)
4. **Subject** → Schedules (one-to-many)
5. **Faculty** → Schedules (one-to-many)
6. **Building** → Rooms (one-to-many)
7. **Room** → Schedules (one-to-many)
8. **ExamSchedule**: Exam-specific scheduling
9. **Archive**: Historical schedule data filtered by academic year, semester, and exam period

### Common Patterns
- Soft deletes: Use `is_active` boolean field
- Cascading deletes: Configure in foreign key relationships
- Timestamps: Always include `created_at`, optional `updated_at`

## Route Patterns

### Standard CRUD Routes
```python
@blueprint.route('/resource')
@login_required
def list_resource():
    """List all resources"""
    pass

@blueprint.route('/resource/add', methods=['GET', 'POST'])
@login_required
def add_resource():
    """Add new resource"""
    pass

@blueprint.route('/resource/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_resource(id):
    """Edit existing resource"""
    pass

@blueprint.route('/resource/delete/<int:id>', methods=['POST'])
@login_required
def delete_resource(id):
    """Delete resource"""
    pass
```

### Response Patterns
- **Success**: Flash message + redirect
- **Error**: Flash error message + redirect back
- **JSON API**: Return `jsonify()` with appropriate status code

## Template Conventions

### Base Template
- All pages extend `base.html`
- Include navigation sidebar
- Use Tailwind CSS utility classes
- Mobile-responsive design

### Forms
- Use CSRF token: `{{ form.hidden_tag() }}`
- Display flash messages prominently
- Use proper form validation and error display
- Include cancel/back buttons

### Data Tables
- Use responsive tables with Tailwind
- Include search/filter functionality
- Add edit/delete action buttons
- Handle empty states gracefully

## Common Tasks

### Adding a New Feature
1. **Update `database.sql`** - Add table definitions for new feature
2. **Update `sample_data.sql`** - Add test data matching new schema
3. Create model in `app/models/` matching the SQL schema
4. Create forms in `app/forms.py`
5. Create blueprint in `app/routes/`
6. Create templates in `app/templates/`
7. Register blueprint in `app/__init__.py`
8. **Test by re-importing `database.sql` and `sample_data.sql`**

### Database Schema Changes (CRITICAL WORKFLOW)

**Always follow this order:**

#### Step 1: Update database.sql
```sql
-- Example: Adding a new table
CREATE TABLE IF NOT EXISTS `new_table` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `description` TEXT,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Example: Modifying existing table
ALTER TABLE `existing_table` 
ADD COLUMN `new_field` VARCHAR(50) NULL AFTER `id`;

-- Example: Adding foreign key
ALTER TABLE `child_table`
ADD CONSTRAINT `fk_parent` 
FOREIGN KEY (`parent_id`) REFERENCES `parent_table` (`id`) 
ON DELETE CASCADE;
```

#### Step 2: Update sample_data.sql
```sql
-- Add sample data for new table
INSERT INTO `new_table` (`name`, `description`, `is_active`) VALUES
('Sample 1', 'Description 1', 1),
('Sample 2', 'Description 2', 1);

-- Update existing sample data if schema changed
-- Make sure all foreign key references are valid
```

#### Step 3: Update Python Models
```python
# In app/models/new_feature.py
from app.extensions import db

class NewTable(db.Model):
    __tablename__ = 'new_table'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
```

#### Step 4: Test Database Setup
```bash
# 1. Drop and recreate database in phpMyAdmin
# 2. Import database.sql
# 3. Import sample_data.sql
# 4. Verify application works with new schema
```

### DO NOT Use Flask-Migrate for Schema Changes
- ❌ Do NOT use `flask db migrate`
- ❌ Do NOT create Alembic migrations for schema changes
- ❌ Do NOT modify database through migrations/
- ✅ ALWAYS update `database.sql` directly
- ✅ Re-import SQL files for schema changes
- ✅ Keep `sample_data.sql` synchronized

**Reason:** This project uses direct SQL file imports as the primary database setup method. This provides:
- Single source of truth
- Easy database reset
- Clear version control
- No migration conflicts

## Testing & Debugging

### Running the Application
```bash
# Development
python run.py

# Or
flask run
```

### Database Setup
1. Start MySQL (XAMPP or MySQL Workbench)
2. Open phpMyAdmin (http://localhost/phpmyadmin)
3. Create database: `ischedwise_db` (if not exists)
4. Import `database.sql` (creates all tables and default users)
5. Import `sample_data.sql` (optional - adds test data)
6. Application is ready to use

**For Schema Changes:**
1. Drop database `ischedwise_db` in phpMyAdmin
2. Create fresh database `ischedwise_db`
3. Import updated `database.sql`
4. Import updated `sample_data.sql`
5. Test application

### Default Users
- **Admin**: admin@ischedwise.com / admin123
- **Dean**: dean@ischedwise.com / dean123

### Common Issues
- **Database connection**: Check MySQL is running
- **Import errors**: Verify virtual environment is activated
- **CSRF errors**: Ensure `form.hidden_tag()` is in templates
- **AI errors**: Check if API key is configured (optional feature)

## Feature-Specific Notes

### AI Schedule Suggestions (Optional Feature)
- **Integration**: Google Gemini API via `app/ai_scheduler.py`
- **Settings**: AI can be enabled/disabled per user in system settings
- **Functionality**: Provides intelligent schedule suggestions based on context
- **UI**: Inline suggestions in schedule forms (not side panel)
- **Error Handling**: Gracefully degrades if API key not configured
- **Cost**: Uses paid API - respect rate limits

**Implementation Pattern:**
```python
from app.ai_scheduler import get_schedule_suggestion

# In route handler
if current_user.ai_enabled:
    suggestion = get_schedule_suggestion(context_data)
    return jsonify({'suggestion': suggestion})
```

### Schedule Management
- Support both class schedules and exam schedules
- Validate time conflicts before saving
- Filter by academic year, semester, day of week
- Support schedule types: lecture, lab, tutorial
- Real-time conflict detection via AJAX

### Subject Template System
- Templates define standardized curriculum subjects
- Faculty can be pre-assigned to templates
- Auto-populate schedule forms from templates
- Reduce data entry and ensure consistency

### Archive System
- Historical data storage for past schedules
- Filter by academic year, semester, and exam period
- Read-only access to archived data
- Export capabilities for reports

### Faculty Management
- Track faculty assignments and workloads
- Manage faculty schedules and availability
- Handle faculty availability and conflicts
- Support multiple sections per faculty
- Pre-assign faculty to subject templates

### Room Management
- Building and room hierarchy
- Room capacity tracking
- Room availability checking
- Conflict detection for double-booking

## API & AJAX Patterns

When implementing dynamic features:
- Use JSON responses for AJAX requests
- Return appropriate HTTP status codes
- Include error messages in response
- Update UI without page reload when appropriate

## Comments & Documentation

### When to Add Comments
- Complex business logic
- Non-obvious algorithms
- Important assumptions or constraints
- TODO items with context

### Docstring Format
```python
def function_name(param1, param2):
    """
    Brief description of function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    """
    pass
```

## Environment & Configuration

- Use `config/config.py` for configuration classes
- Environment variables for sensitive data
- Different configs for development/production
- Database URI format: `mysql+pymysql://user:password@localhost/ischedwise_db`

## Best Practices Summary

1. ✅ Always validate user input
2. ✅ Use proper error handling with try-except blocks
3. ✅ Flash messages for user feedback
4. ✅ Keep views thin, logic in models/services
5. ✅ Use database transactions for related operations
6. ✅ Log important operations and errors
7. ✅ Test database constraints (unique, foreign keys)
8. ✅ Use meaningful commit messages
9. ✅ Keep templates DRY (Don't Repeat Yourself)
10. ✅ Document complex queries and business logic

## When Suggesting Code

- Prioritize security and data validation
- Follow existing patterns in the codebase
- Use the same coding style as existing files
- Consider database performance (N+1 queries)
- Provide complete, working code snippets
- Include error handling
- Add appropriate comments for complex logic
- Suggest testing approaches when relevant

---

## 🔧 Common Tasks & Solutions

### Adding a New Feature
1. **Plan database changes** - What tables/columns are needed?
2. **Update `database.sql`** - Add table definitions with proper constraints
3. **Update `sample_data.sql`** - Add test data
4. **Create model** in `app/models/` - Match SQL schema exactly
5. **Create forms** in `app/forms.py` - Add validation
6. **Create blueprint** in `app/routes/` - Implement CRUD operations
7. **Create templates** in `app/templates/` - Build UI
8. **Register blueprint** in `app/__init__.py`
9. **Test thoroughly** - Import fresh database and verify functionality

### Fixing a Bug
1. **Reproduce the bug** - Understand exact steps to trigger it
2. **Check error logs** - Look for stack traces and error messages
3. **Identify root cause** - Is it database, logic, or UI issue?
4. **Fix the issue** - Make minimal, targeted changes
5. **Test the fix** - Verify bug is resolved
6. **Check for side effects** - Ensure fix doesn't break other features
7. **Document the fix** - Add comments if logic is complex

### Adding Archive Support to a Table
1. **Update `database.sql`**:
   ```sql
   ALTER TABLE `table_name` 
   ADD COLUMN `is_active` TINYINT(1) NOT NULL DEFAULT 1,
   ADD COLUMN `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
   ADD COLUMN `archived_by` INT(11) DEFAULT NULL,
   ADD COLUMN `archived_at` DATETIME NULL DEFAULT NULL,
   ADD COLUMN `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
   ADD KEY `idx_is_archived` (`is_archived`),
   ADD KEY `archived_by` (`archived_by`),
   ADD CONSTRAINT `table_name_ibfk_archived_by` 
     FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;
   ```

2. **Update `sample_data.sql`**:
   ```sql
   -- Add sample archived record
   INSERT INTO `table_name` (..., `is_archived`, `archived_by`, `archived_at`, `archive_reason`) 
   VALUES (..., 1, 1, NOW(), 'Sample archive reason');
   ```

3. **Update Python model**:
   ```python
   # Add archive columns
   is_active = db.Column(db.Boolean, nullable=False, default=True)
   is_archived = db.Column(db.Boolean, nullable=False, default=False)
   archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
   archived_at = db.Column(db.DateTime, nullable=True)
   archive_reason = db.Column(db.String(255), nullable=True)
   
   def archive(self, user_id=None, reason=None):
       """Mark as archived."""
       self.is_archived = True
       self.is_active = False
       self.archived_by = user_id
       self.archive_reason = reason
       from datetime import datetime
       self.archived_at = datetime.utcnow()
   
   def unarchive(self):
       """Restore from archive."""
       self.is_archived = False
       self.is_active = True
       self.archived_by = None
       self.archive_reason = None
       self.archived_at = None
   ```

4. **Update routes**:
   - Filter active items: `.filter_by(is_archived=False)`
   - Add archive endpoint: Call `item.archive(user_id, reason)`
   - Add unarchive endpoint: Call `item.unarchive()`

5. **Update templates**:
   - Change "Delete" button to "Archive" button
   - Prompt for archive reason
   - Show archived items in archive.html

### Debugging Common Issues

#### Database Connection Error
```python
# Check config.py has correct database URI
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/ischedwise_db'

# Verify MySQL is running in XAMPP
# Check database exists in phpMyAdmin
```

#### Import Error (Module Not Found)
```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install missing package
pip install package-name

# Verify requirements.txt is up to date
pip freeze > requirements.txt
```

#### Foreign Key Constraint Error
```sql
-- Check table creation order in database.sql
-- Parent tables must be created BEFORE child tables
-- Example: users BEFORE departments (departments.archived_by references users.id)

-- Verify foreign key values exist
SELECT * FROM parent_table WHERE id = foreign_key_value;
```

#### CSRF Token Missing
```html
<!-- Ensure form has CSRF token -->
<form method="POST">
    {{ form.hidden_tag() }}
    <!-- form fields -->
</form>
```

#### Template Not Found
```python
# Check template path matches route
return render_template('folder/template.html')

# Verify file exists: app/templates/folder/template.html
# Check template extends base.html correctly
```

---

## 🎨 UI/UX Guidelines

### Tailwind CSS Classes
- **Buttons**: `bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded`
- **Cards**: `bg-white rounded-lg shadow p-6`
- **Inputs**: `border border-gray-300 rounded px-3 py-2 w-full`
- **Alerts**: `bg-green-100 border-l-4 border-green-500 text-green-700 p-4`

### Responsive Design
- Use `hidden md:block` for desktop-only elements
- Use `block md:hidden` for mobile-only elements
- Test on mobile (320px), tablet (768px), desktop (1024px+)

### Accessibility
- Use semantic HTML (`<button>`, `<nav>`, `<main>`)
- Add `aria-label` for icon-only buttons
- Ensure sufficient color contrast (4.5:1 minimum)
- Make all interactive elements keyboard accessible

---

## 🧪 Testing Checklist

### Before Committing
- [ ] Drop and recreate database from `database.sql`
- [ ] Import `sample_data.sql` successfully
- [ ] Application starts without errors
- [ ] All existing features still work
- [ ] New feature works as expected
- [ ] No console errors in browser
- [ ] Mobile layout looks correct
- [ ] All forms have CSRF protection
- [ ] User permissions checked on protected routes
- [ ] Database queries are optimized (no N+1 queries)

### Database Testing
```bash
# Reset database for testing
# 1. Open phpMyAdmin
# 2. Drop database ischedwise_db
# 3. Create new database ischedwise_db
# 4. Import database.sql
# 5. Import sample_data.sql
# 6. Run: python run.py
```

---

## 📝 Code Review Checklist

### Security
- [ ] All routes have `@login_required`
- [ ] Role-based access control where needed
- [ ] User input is validated and sanitized
- [ ] SQL injection prevented (use ORM, not raw SQL)
- [ ] CSRF tokens on all forms
- [ ] Passwords are hashed

### Database
- [ ] `database.sql` updated with schema changes
- [ ] `sample_data.sql` updated to match
- [ ] Python models match database.sql
- [ ] Foreign keys have ON DELETE behavior
- [ ] Indexes on foreign keys and search columns
- [ ] Archive pattern used consistently

### Code Quality
- [ ] Follows PEP 8 style guidelines
- [ ] Functions have docstrings
- [ ] Complex logic has comments
- [ ] No hardcoded values (use config)
- [ ] Error handling with try-except
- [ ] Meaningful variable names
- [ ] DRY principle followed

### Performance
- [ ] No N+1 query problems
- [ ] Appropriate use of lazy loading
- [ ] Database indexes for common queries
- [ ] Pagination for large datasets
- [ ] Static files properly cached

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Database schema finalized
- [ ] Sample data removed (production)
- [ ] Environment variables configured
- [ ] Debug mode disabled
- [ ] Secret key is random and secure
- [ ] Database credentials secured
- [ ] HTTPS enabled
- [ ] Backup strategy in place

### Post-Deployment
- [ ] Database initialized successfully
- [ ] Admin user created
- [ ] All routes accessible
- [ ] Logs being written
- [ ] Error pages working
- [ ] Performance acceptable
- [ ] Monitoring enabled

---

## ⚡ Quick Command Reference

### Development Commands
```bash
# Start application
python run.py

# Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# Activate virtual environment (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Update dependencies
pip freeze > requirements.txt

# Initialize database
python scripts/init_db.py

# Run tests
pytest tests/

# Kill running Python processes (Windows)
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
```

### Database Commands
```bash
# Reset database workflow:
# 1. Open phpMyAdmin (http://localhost/phpmyadmin)
# 2. Drop database: ischedwise_db
# 3. Create database: ischedwise_db
# 4. Import: database.sql
# 5. Import: sample_data.sql
```

### Git Workflow
```bash
# Check status
git status

# Stage changes
git add .

# Commit with meaningful message
git commit -m "feat: Add archive support for faculty assignments"

# Push to remote
git push origin main

# Pull latest changes
git pull origin main

# Create feature branch
git checkout -b feature/new-feature
```

---

## 📚 Project-Specific Patterns

### Department Access Control (for Deans)
```python
# In routes, filter by department access
user_department_ids = current_user.get_department_ids()
if user_department_ids is not None:
    query = query.filter(Model.department_id.in_(user_department_ids))
```

### Flash Messages Pattern
```python
# Success
flash('Operation completed successfully!', 'success')

# Error
flash('An error occurred. Please try again.', 'danger')

# Warning
flash('Please review your input.', 'warning')

# Info
flash('Record saved as draft.', 'info')
```

### Query Optimization
```python
# Bad - N+1 query problem
schedules = Schedule.query.all()
for schedule in schedules:
    print(schedule.section.section_name)  # Queries section table for each schedule

# Good - Use eager loading
schedules = Schedule.query.options(db.joinedload(Schedule.section)).all()
for schedule in schedules:
    print(schedule.section.section_name)  # No additional queries
```

### Pagination Pattern
```python
# In route
page = request.args.get('page', 1, type=int)
per_page = 20
pagination = Model.query.paginate(page=page, per_page=per_page, error_out=False)

# In template
{% for item in pagination.items %}
    <!-- Display item -->
{% endfor %}

<!-- Pagination controls -->
{{ pagination.links }}
```

---

## 🎓 Learning Resources

### Key Documentation
- **Flask**: https://flask.palletsprojects.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Jinja2**: https://jinja.palletsprojects.com/
- **Flask-Login**: https://flask-login.readthedocs.io/

### Project-Specific Docs
- See `docs/` folder for feature-specific documentation
- Check `docs/archive/` for historical implementation notes
- Review `.github/copilot-instructions.md` for coding guidelines

---

## 🆘 Troubleshooting Guide

### Application Won't Start
1. Check if virtual environment is activated
2. Verify all dependencies installed: `pip install -r requirements.txt`
3. Check database connection in `config/config.py`
4. Verify MySQL/XAMPP is running
5. Check for syntax errors in recent changes

### Database Import Fails
1. Check foreign key references (parent tables must exist first)
2. Verify table creation order in `database.sql`
3. Ensure `users` table created before tables that reference it
4. Check for duplicate key constraints
5. Verify character encoding (utf8mb4)

### Import Errors
1. Activate virtual environment
2. Check if package is in `requirements.txt`
3. Verify package name spelling
4. Try reinstalling: `pip install --upgrade package-name`
5. Check for circular imports in models

### Template Rendering Issues
1. Verify template path matches `render_template()` call
2. Check template extends `base.html` correctly
3. Ensure template variables are passed from route
4. Check for unclosed tags in Jinja2 syntax
5. Verify static files path for CSS/JS

### Performance Issues
1. Check for N+1 query problems (use eager loading)
2. Add database indexes for frequently queried columns
3. Implement pagination for large datasets
4. Use query filters to limit result sets
5. Profile slow queries with Flask-DebugToolbar

---

## 💡 Tips & Tricks

### Quick Wins
- Always test with fresh database import after schema changes
- Use `db.session.rollback()` in error handlers to prevent transaction issues
- Add `__repr__()` methods to models for better debugging
- Use f-strings for string formatting in Python 3.6+
- Leverage SQLAlchemy relationships instead of manual joins
- Keep route handlers thin - move logic to model methods
- Use Tailwind's utility classes instead of custom CSS
- Test mobile responsiveness from the start, not at the end

### Code Snippets

#### Model with Archive Support
```python
from app.extensions import db
from datetime import datetime

class MyModel(db.Model):
    __tablename__ = 'my_table'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def archive(self, user_id=None, reason=None):
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        self.archived_at = datetime.utcnow()
    
    def unarchive(self):
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
    
    def __repr__(self):
        return f'<MyModel {self.id}: {self.name}>'
```

#### Blueprint Route Template
```python
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.mymodel import MyModel

my_bp = Blueprint('myfeature', __name__, url_prefix='/myfeature')

@my_bp.route('/')
@login_required
def index():
    """List all items"""
    items = MyModel.query.filter_by(is_archived=False).all()
    return render_template('myfeature/index.html', items=items)

@my_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new item"""
    if request.method == 'POST':
        try:
            item = MyModel(name=request.form.get('name'))
            db.session.add(item)
            db.session.commit()
            flash('Item added successfully!', 'success')
            return redirect(url_for('myfeature.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding item: {str(e)}', 'danger')
    
    return render_template('myfeature/add.html')
```

---

## 🎯 Final Reminders

1. **Database Changes**: Always update database.sql → sample_data.sql → Python models (in that order)
2. **Archive Pattern**: Use flags on main table, not separate archive tables (except for denormalized historical data)
3. **Testing**: Drop and reimport database after schema changes
4. **Security**: Always use @login_required and validate user input
5. **Performance**: Watch for N+1 queries, add indexes, use pagination
6. **Code Style**: Follow PEP 8, add docstrings, keep it DRY
7. **Git Commits**: Write clear, descriptive commit messages
8. **Documentation**: Update docs when adding features
9. **Error Handling**: Use try-except blocks and flash messages
10. **User Experience**: Keep UI responsive and accessible

**Remember**: When in doubt, check existing code for patterns and follow the same approach! 🚀
