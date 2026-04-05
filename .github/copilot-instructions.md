# GitHub Copilot Instructions for iSchedWise V4

> **Note**: For general software engineering principles (DRY, SOLID, KISS, YAGNI, Clean Code, Design Patterns), see [ENGINEERING_BEST_PRACTICES.md](./ENGINEERING_BEST_PRACTICES.md)

> **Instruction Precedence (Full .agent adoption)**
> 1. **This file is authoritative** for iSchedWise domain rules (Flask, SQL schema workflow, archive pattern, UI constraints, security).
> 2. **ENGINEERING_BEST_PRACTICES.md** provides general engineering quality guidance.
> 3. **.github/.agent/** workflows, rules, and specialist personas are orchestration layers and must not override iSchedWise domain rules.
>
> If guidance conflicts, follow this order: `copilot-instructions.md` -> `ENGINEERING_BEST_PRACTICES.md` -> `.github/.agent/*`.

---

## 🎯 Core Directives

**You are an expert senior software engineer** specializing in Flask, Python, JavaScript, and SQL.

### Response Guidelines
- ✅ Analyze before coding - understand the problem deeply first
- ✅ Provide complete, production-ready code with error handling
- ✅ Identify root causes, not just symptoms
- ✅ Consider architectural implications of changes
- ✅ ALWAYS ensure responsive UI (mobile, tablet, desktop)
- ✅ CRITICAL: Verify changes don't break existing functionality
- ❌ No incomplete code snippets
- ❌ Never assume context - verify file paths and existing code
- ❌ Never modify code without understanding full impact

### Active Skill And Workflow Routing

Use this routing map for `.github/.agent` assets kept active in this repository:

| Need | Agent | Primary skills/workflow |
|------|-------|-------------------------|
| Flask route/model/service work | `backend-specialist` | `python-patterns`, `api-patterns`, `database-design` |
| SQL schema and query design | `database-architect` | `database-design` |
| Jinja/Tailwind responsiveness | `frontend-specialist` | `tailwind-patterns`, `frontend-design` |
| Root-cause debugging | `debugger` | `systematic-debugging`, `.github/.agent/workflows/debug.md` |
| Test and regression validation | `test-engineer` | `testing-patterns`, `.github/.agent/workflows/test.md` |
| Security boundary checks | `security-auditor` | `vulnerability-scanner` |
| Complex multi-domain tasks | `project-planner` + specialists | `.github/.agent/workflows/plan.md` then `.github/.agent/workflows/orchestrate.md` |

Prefer these workflows for this project: `plan.md`, `debug.md`, `test.md`, `enhance.md`, `orchestrate.md`, `deploy.md`, `brainstorm.md`.

---

## 🔍 MANDATORY: Context Gathering Workflow

**Before generating ANY code:**

1. **Read target file completely** - Understand structure, imports, functions
2. **Read connected files:**
   - Routes → Model → Template → JavaScript → ischedwise_db.sql
3. **Search for dependencies** - Use grep_search to find all usages
4. **Verify database schema** - Check ischedwise_db.sql for table structure

### Quick Checklist
- [ ] Read ENTIRE target file
- [ ] Read ALL related model/route/template files
- [ ] Check ischedwise_db.sql for table structure
- [ ] Search for where this code is used
- [ ] Verify foreign key relationships

---

## 🔴 Database Management (CRITICAL)

**This project uses direct SQL files, NOT Flask-Migrate!**

### Source of Truth
| File | Purpose |
|------|---------|
| `ischedwise_db.sql` | **PRIMARY** — Full database dump (schema + data). ALL database changes go here |
| `app/models/*.py` | Python models mirroring ischedwise_db.sql |

### Change Workflow (ALWAYS follow this order)

```
1. Update ischedwise_db.sql  → 2. Update Python models
```

### 🚫 Never Do This
- ❌ `flask db migrate` / `flask db upgrade`
- ❌ Create Alembic migrations
- ❌ Change schema without updating ischedwise_db.sql

### Standard Archive Pattern

All archivable tables use these columns:

```sql
-- ischedwise_db.sql
`is_active` TINYINT(1) NOT NULL DEFAULT 1,
`is_archived` TINYINT(1) NOT NULL DEFAULT 0,
`archived_by` INT(11) DEFAULT NULL,
`archived_at` DATETIME NULL DEFAULT NULL,
`archive_reason` VARCHAR(255) NULL DEFAULT NULL,
KEY `idx_is_archived` (`is_archived`),
CONSTRAINT `{table}_ibfk_archived_by` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
```

```python
# Python model
is_active = db.Column(db.Boolean, nullable=False, default=True)
is_archived = db.Column(db.Boolean, nullable=False, default=False)
archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
archived_at = db.Column(db.DateTime, nullable=True)
archive_reason = db.Column(db.String(255), nullable=True)

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
```

**Rules:**
- ❌ DO NOT create separate archive tables
- ✅ Use flags on main table (`is_archived`, `is_active`)
- ✅ Filter queries by `is_archived=False` for active items

---

## 🏗️ Project Overview

**iSchedWise V4** - Flask-based school scheduling system

### User Roles
- **Admin**: Full system access, user management
- **Dean**: Department-specific schedule management

### Key Features
- Class & Exam Scheduling with conflict detection
- Faculty workload management
- Room/building management
- Archive system for historical data
- Excel & PDF exports
- AI-powered suggestions (optional, Google Gemini)

### Tech Stack
| Layer | Technology |
|-------|------------|
| Backend | Flask 3.1.2, SQLAlchemy ORM, Flask-Login |
| Database | MySQL + PyMySQL |
| Frontend | Jinja2, Tailwind CSS, Vanilla JS |
| Exports | openpyxl (Excel), reportlab (PDF) |

---

## 📁 Project Structure

```
📁 iSchedWise V4/
├── 🔴 ischedwise_db.sql     # SOURCE OF TRUTH (full database dump)
├── run.py                   # Entry point
├── app/
│   ├── __init__.py          # App factory
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Blueprint handlers
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 templates
│   ├── static/              # CSS, JS, images
│   └── utils/               # Helpers
├── config/config.py         # Configuration
├── tests/                   # ALL test files here
├── docs/                    # Documentation
└── scripts/                 # Utility scripts
```

### Key Files
- **run.py** - Application entry point
- **app/decorators.py** - `@role_required` decorator
- **app/ai_scheduler.py** - AI integration (optional)
- **app/utils/activity_logger.py** - Audit logging

---

## 🔧 Coding Standards

### Flask Patterns
1. **Application Factory**: Use `create_app()` pattern
2. **Blueprints**: Organize routes by feature
3. **Models**: One model per file, match ischedwise_db.sql exactly
4. **Route Decorators**: Always include `@login_required`
5. **Service Layer**: Complex business logic in `app/services/`

### Database Conventions
- Table names: lowercase with underscores (`exam_schedules`)
- Foreign keys: Always specify `ondelete` behavior
- Timestamps: Include `created_at`, optional `updated_at`
- Indexes: Add for all foreign keys and frequently queried columns

### Security
- `@login_required` on all protected routes
- `@role_required('Admin')` for role-based access
- CSRF protection on all forms
- Hash passwords with Werkzeug

---

## 🎨 UI/UX Requirements

### 🔴 Responsive Design (MANDATORY)

**Every page MUST be fully responsive!**

```html
<!-- Responsive breakpoints -->
sm: 640px   /* Landscape phones */
md: 768px   /* Tablets */
lg: 1024px  /* Desktops */
xl: 1280px  /* Large desktops */
```

### Common Patterns
```html
<!-- Responsive grid -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

<!-- Responsive text -->
<h1 class="text-2xl md:text-3xl lg:text-4xl">

<!-- Hide/show by screen -->
<div class="block md:hidden">Mobile only</div>
<div class="hidden md:block">Tablet & Desktop</div>
```

### 🔴 Custom UI Components (No Native Dialogs!)

- ❌ `alert()` → Use toast notifications
- ❌ `confirm()` → Use custom confirmation modals
- ❌ `prompt()` → Use custom input modals

### 🔴 Fixed-Viewport Application Layout (MANDATORY)

**All pages MUST use this fixed-viewport layout pattern!**

```
┌──────────┬──────────────────────────────────┐
│          │  📌 PAGE HEADER                  │  ← Never scrolls
│  🏆      ├──────────────────────────────────┤
│ SIDEBAR  │                                  │
│          │     📜 CONTENT AREA              │  ← Only this scrolls
│ (Fixed)  │     (Each page scrolls here)     │
│          │                                  │
└──────────┴──────────────────────────────────┘
```

**How it works:**
- App always fits `100vw × 100vh`
- No body/page scrolling
- Sidebar is fixed (never scrolls with page)
- Each page uses its own scrollable content area

**Why Fixed Sidebar?**
- ✅ Users constantly switch pages (Schedules ↔ Faculty ↔ Rooms)
- ✅ Navigation must be instantly accessible
- ✅ Builds muscle memory
- ✅ Feels like a real "system", not a website
- 👉 This is how SIS, ERP, hospital schedulers do it

**Benefits:**
- ✅ Consistent UX across all pages
- ✅ Predictable navigation
- ✅ No random white spaces
- ✅ Easier layout maintenance

#### Sidebar Structure (in base.html)
```html
<!-- Fixed Sidebar - NEVER scrolls with page -->
<aside id="sidebar" class="fixed top-0 left-0 z-50 h-screen">
    <!-- Logo section (flex-shrink-0) -->
    <!-- Nav section (flex-1 overflow-y-auto) - only nav items scroll -->
    <!-- User section (flex-shrink-0) -->
</aside>

<!-- Main Content - offset by sidebar width -->
<div class="lg:ml-60 xl:ml-64">
    <!-- Page content goes here -->
</div>
```

#### Page Content Structure
```html
<!-- Fixed-Viewport Application Layout -->
<div class="bg-gray-50 h-screen overflow-hidden flex flex-col p-2 sm:p-3">
    <div class="w-full flex flex-col h-full overflow-hidden">
        
        <!-- Page Header - FIXED (flex-shrink-0) -->
        <div class="mb-2 sm:mb-3 flex-shrink-0">
            <div class="bg-white border border-gray-100 rounded-xl shadow-sm p-3 sm:p-4">
                <!-- Header content: icon, title, subtitle, action buttons -->
            </div>
        </div>
        
        <!-- Scrollable Content Area (flex-1 overflow-y-auto) -->
        <div class="flex-1 overflow-y-auto custom-scrollbar">
            <!-- All page content goes here - this area scrolls -->
        </div>
        
    </div>
</div>
```

#### Key CSS Classes
| Class | Purpose |
|-------|---------|
| `h-screen` | Full viewport height |
| `overflow-hidden` | Prevent page-level scrolling |
| `flex-shrink-0` | Fixed header (doesn't shrink) |
| `flex-1` | Content fills remaining space |
| `overflow-y-auto` | Internal scrolling for content |

#### Standard Page Header Pattern
```html
<div class="bg-white border border-gray-100 rounded-xl shadow-sm p-3 sm:p-4">
    <div class="flex items-center gap-2 sm:gap-3">
        <div class="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
            <svg class="w-5 h-5 sm:w-6 sm:h-6 text-blue-600"><!-- Icon --></svg>
        </div>
        <div class="flex-1 min-w-0">
            <h1 class="text-lg sm:text-xl font-semibold text-gray-900">Page Title</h1>
            <p class="text-xs sm:text-sm text-gray-600">Page description</p>
        </div>
        <!-- Optional: Action buttons on the right -->
    </div>
</div>
```

#### Custom Scrollbar (Required)
```css
.custom-scrollbar::-webkit-scrollbar,
.overflow-y-auto::-webkit-scrollbar {
    width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track,
.overflow-y-auto::-webkit-scrollbar-track {
    background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb,
.overflow-y-auto::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.4);
    border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover,
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.6);
}
```

#### Mobile Responsiveness
On smaller screens (< 1024px), allow natural page scrolling:
```css
@media (max-width: 1024px) {
    .page-container {
        height: auto !important;
        min-height: auto !important;
        overflow: visible !important;
    }
}
```

#### ❌ DON'T Do This
```html
<!-- WRONG: Regular scrolling page -->
<div class="min-h-screen p-4">
    <div class="max-w-7xl mx-auto">
        <!-- Content that causes page scroll -->
    </div>
</div>
```

#### ✅ Reference Pages
- `faculty.html` - Master-detail panel layout
- `building.html` - Master-detail panel layout  
- `schedule.html` - Tab-based layout with calendar
- `dashboard.html` - Card grid layout with scrollable content

---

## 🛡️ Preventing Breaking Changes

**Before modifying any code:**

1. **Grep search** for all usages of function/class/route
2. **Check consumers** - templates, JavaScript, other routes
3. **Verify backward compatibility** - don't change function signatures without updating callers
4. **Test related features** after changes

### Warning Signs - STOP if you're about to:
- Remove/rename a function called elsewhere
- Change function parameters without updating call sites
- Modify database schema without updating all queries
- Change API response structure without checking consumers

---

## 🎯 Quick Reference

### When User Asks To...
| Task | Actions |
|------|---------|
| Add feature | ischedwise_db.sql → models → routes → templates |
| Fix bug | Read logs → Grep usages → Fix → Test related features |
| Archive something | Use standard archive pattern (flags, not separate tables) |
| Change database | ischedwise_db.sql → Python models |
| Modify function | Grep ALL call sites → Update consumers → Test |

### Standard Route Pattern
```python
@blueprint.route('/resource')
@login_required
def list_resource():
    items = Model.query.filter_by(is_archived=False).all()
    return render_template('resource.html', items=items)

@blueprint.route('/resource/add', methods=['GET', 'POST'])
@login_required
def add_resource():
    if request.method == 'POST':
        try:
            item = Model(**request.form)
            db.session.add(item)
            db.session.commit()
            flash('Added successfully!', 'success')
            return redirect(url_for('resource.list_resource'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('resource_form.html')
```

### Department Access Control (Deans)
```python
user_department_ids = current_user.get_department_ids()
if user_department_ids is not None:
    query = query.filter(Model.department_id.in_(user_department_ids))
```

### Query Optimization
```python
# ❌ N+1 problem
schedules = Schedule.query.all()
for s in schedules:
    print(s.faculty.name)  # N additional queries!

# ✅ Eager loading
schedules = Schedule.query.options(db.joinedload(Schedule.faculty)).all()
```

---

## 🧪 Testing Workflow

### Database Reset
```bash
# 1. Drop database in MySQL Workbench
# 2. Create database: ischedwise_db
# 3. Import ischedwise_db.sql
# 4. Run: python run.py
```

### Default Users
- **Super Admin**: test@ischedwise.local / superadmin123 (`super_admin` role, seeded via ischedwise_db.sql)
- **Admin**: admin@ischedwise.com / admin123
- **Dean**: dean@ischedwise.com / dean123

### Default Database
- **Database name**: `ischedwise_db`
- **Connection**: `mysql+pymysql://root:@localhost/ischedwise_db` (see `config/config.py`)
- **Primary dump file**: `ischedwise_db.sql` — this is the full database dump used for deployment/restore.

### Before Committing
- [ ] Application starts without errors
- [ ] All existing features still work
- [ ] New feature works as expected
- [ ] Mobile layout looks correct
- [ ] No browser console errors

---

## ⚡ Commands

```bash
# Start app
python run.py

# Virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

---

## 🆘 Common Issues

| Issue | Solution |
|-------|----------|
| Database connection error | Check MySQL is running, verify config.py, ensure `ischedwise_db` database exists |
| Module not found | Activate venv, `pip install -r requirements.txt` |
| Foreign key constraint | Check table creation order in ischedwise_db.sql |
| CSRF error | Add `{{ form.hidden_tag() }}` to form |
| N+1 queries | Use `db.joinedload()` for eager loading |

---

## 🎯 Final Reminders

1. **Database order**: ischedwise_db.sql → Python models
2. **Archive pattern**: Flags on main table, not separate tables
3. **Testing**: Reimport database after schema changes
4. **Security**: Always `@login_required`, validate input
5. **Performance**: Watch N+1 queries, add indexes
6. **UI**: Must be responsive on all devices
7. **Breaking changes**: Grep usages before modifying functions

**When in doubt, check existing code patterns!** 🚀
