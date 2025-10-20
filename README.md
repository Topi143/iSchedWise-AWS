# iSchedWise V4 - School Scheduling System

A professional Flask-based web application for managing school schedules, rooms, and faculty. Designed for Administrators and Deans with **AI-powered decision support**.

## ✨ Features

- 🔐 **Secure Login System** - Professional split-screen login page with Tailwind CSS
- 👥 **User Roles** - Admin and Dean user types
- 📅 **Schedule Management** - Create and manage class and exam schedules
- 🤖 **AI Decision Support** - Google Gemini AI for intelligent conflict detection and resolution
  - Automatic conflict detection (section, faculty, room)
  - Smart recommendations for alternative time slots, days, rooms, and faculty
  - Natural language explanations for scheduling decisions
  - Workload balancing and optimization suggestions
- 🏢 **Room & Building Management** - Track rooms and building resources
- 👨‍🏫 **Faculty Management** - Manage faculty assignments and schedules
- 📚 **Curriculum Management** - With Subject Template System (reduces duplication by 50-70%)
- 📦 **Archive System** - Store historical schedules filtered by academic year, semester, and exam period
- 📱 **Responsive Design** - Works seamlessly on desktop, tablet, and mobile devices
- 🎨 **Modern UI** - Clean, professional interface with Tailwind CSS
- 🔒 **Security** - CSRF protection, password hashing, and session management

## 🚀 Tech Stack

- **Backend**: Flask 3.1.2 with application factory pattern
- **Database**: MySQL (XAMPP) with SQLAlchemy ORM
- **AI Integration**: Google Gemini API for intelligent scheduling assistance
- **Authentication**: Flask-Login with role-based access
- **Forms**: Flask-WTF with CSRF protection
- **Frontend**: Tailwind CSS with responsive design
- **Database Management**: Direct SQL imports (database.sql as source of truth)

## 📦 Quick Start

### Prerequisites
- Python 3.8+
- MySQL (XAMPP recommended)
- Virtual environment (already created in `venv/`)
- Google Gemini API key (optional, for AI features)

### 1. Activate Virtual Environment

**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

### 2. Setup Database (Choose One Method)

#### Method A: Automated (Recommended) ⚡
```powershell
.\scripts\apply_subject_templates.ps1
```

#### Method B: Manual (phpMyAdmin) 📋
1. Start XAMPP/MySQL service
2. Open phpMyAdmin (http://localhost/phpmyadmin)
3. Import `database.sql` (creates database and tables)
4. Import `sample_data.sql` (optional - adds test data)

### 3. Configure AI (Optional but Recommended)

**For AI-powered schedule conflict resolution:**

1. Get free API key: https://makersuite.google.com/app/apikey
2. Create `.env` file in project root:
   ```env
   GEMINI_API_KEY=your-api-key-here
   ```
3. Restart application

**See:** `docs/AI_QUICK_START.md` for detailed setup

### 4. Run Application
```bash
python run.py
```

### 5. Login
- URL: http://localhost:5000
- **Admin**: username=`admin`, password=`admin123`
- **Dean**: username=`dean`, password=`dean123`

⚠️ **Change default passwords in production!**

## 📁 Project Structure

```
iSchedWise V4/
├── 📄 database.sql              # ⚠️ SOURCE OF TRUTH for database schema
├── 📄 sample_data.sql           # Test data matching schema
├── 📄 run.py                    # Application entry point
├── 📄 config.py                 # Configuration settings
├── 📄 requirements.txt          # Python dependencies
├── 📂 app/                      # Main application package
│   ├── __init__.py              # Application factory
│   ├── extensions.py            # Flask extensions
│   ├── forms.py                 # WTForms form classes
│   ├── ai_scheduler.py          # AI decision support system
│   ├── models/                  # SQLAlchemy models
│   ├── routes/                  # Blueprint route handlers
│   ├── static/                  # CSS, JS, images
│   └── templates/               # Jinja2 templates
├── 📂 scripts/                  # Utility scripts
│   ├── apply_subject_templates.ps1  # Database setup automation
│   ├── reimport_database.ps1    # Database reimport script
│   ├── migrate_to_templates.py  # Data migration script
│   └── init_db.py               # Database initialization
├── 📂 migrations/               # SQL migration files
├── 📂 docs/                     # Documentation
│   ├── setup/                   # Setup guides
│   ├── features/                # Feature documentation
│   ├── AI_DECISION_SUPPORT.md   # AI system documentation
│   ├── AI_DECISION_SUPPORT_QUICK_START.md  # AI quick start
│   └── COPILOT_UPDATE_SUMMARY.md
├── 📂 config/                   # Configuration modules
└── 📂 venv/                     # Virtual environment
```

## 📚 Documentation

### Setup Guides
- **[Setup Guide](docs/setup/SETUP_GUIDE.md)** - Detailed setup instructions
- **[Database Workflow](docs/setup/DATABASE_WORKFLOW.md)** - How to make database changes

### Features
- **[Subject Template System](docs/features/README_APPLY_TEMPLATES.md)** - Quick start guide
- **[Implementation Plan](docs/features/IMPROVEMENT_PLAN.md)** - Technical specification
- **[Migration Guide](docs/features/MIGRATION_GUIDE.md)** - Data migration instructions
- **[Quick Reference](docs/features/QUICK_START.md)** - Quick reference guide

### Development
- **[Copilot Instructions](.github/copilot-instructions.md)** - AI coding assistant guidelines
- **[Copilot Updates](docs/COPILOT_UPDATE_SUMMARY.md)** - Recent updates summary

## 🔧 Database Management

### Important: Database-First Workflow
This project uses **direct SQL files**, NOT Flask-Migrate migrations!

**When making database changes:**
1. ✅ Update `database.sql` (source of truth)
2. ✅ Update `sample_data.sql` to match
3. ✅ Update Python models in `app/models/`
4. ✅ Re-import database to apply changes

**Never do this:**
- ❌ `flask db migrate`
- ❌ `flask db upgrade`
- ❌ Creating Alembic migrations

See [Database Workflow Guide](docs/setup/DATABASE_WORKFLOW.md) for details.

## 🎯 Key Features Explained

### AI Decision Support System 🤖
Intelligent scheduling assistant powered by Google Gemini API.

**Features:**
- **Conflict Detection**: Automatically detects section, faculty, and room conflicts
- **Smart Recommendations**: Suggests alternative time slots, days, rooms, and faculty
- **Natural Language Explanations**: AI explains why conflicts occur and recommends solutions
- **Workload Balancing**: Distributes faculty workload evenly
- **Optimal Scheduling**: Suggests best time slots based on academic best practices

**Setup:**
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add to `.env` file: `GEMINI_API_KEY=your-key-here`
3. Restart application
4. Click "🤖 Check with AI" button in schedule modals

See [docs/AI_DECISION_SUPPORT_QUICK_START.md](docs/AI_DECISION_SUPPORT_QUICK_START.md) for detailed guide.

### Subject Template System
Reduces data duplication by 50-70% by using templates for subjects that appear across multiple curricula.

**Benefits:**
- One template → many curriculum instances
- Easy faculty assignment (assign to template = assigned to all)
- Simple updates (change template = all instances updated)

See [docs/features/](docs/features/) for complete documentation.

### Role-Based Access Control
- **Admin**: Full system access
- **Dean**: Department-specific access

### Archive System
Historical data storage with filters for:
- Academic year
- Semester
- Exam period

## 🛠️ Development

### Running in Development Mode
```bash
python run.py
# or
flask run
```

### Making Database Changes
1. Edit `database.sql`
2. Run: `.\scripts\apply_subject_templates.ps1`
3. Test application

### Project Guidelines
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Document complex logic
- Test before committing

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for complete coding standards.

## 📦 Default Login Credentials

### Admin Account
- **Username**: `admin`
- **Email**: `admin@norzagaray.edu`
- **Password**: `admin123`

### Dean Account
- **Username**: `dean`
- **Email**: `dean@norzagaray.edu`
- **Password**: `dean123`

⚠️ **IMPORTANT**: Change these passwords in production!

## 🚨 Troubleshooting

### Database Connection Issues
- Ensure MySQL/XAMPP is running
- Check database credentials in `.env`
- Verify `ischedwise_db` exists

### Import Errors
- Activate virtual environment first
- Ensure all dependencies installed: `pip install -r requirements.txt`

### Migration Issues
- Don't use `flask db migrate` - use direct SQL import instead
- See [Database Workflow Guide](docs/setup/DATABASE_WORKFLOW.md)

## 📄 License

This project is for educational purposes as part of a thesis project.

## 👥 Contributors

Developed as part of an academic thesis project for school scheduling management.

---

**Need Help?** Check the [documentation](docs/) or review the [setup guide](docs/setup/SETUP_GUIDE.md).
├── ARCHIVE_QUICK_REFERENCE.md      # Archive quick reference
├── ARCHIVE_IMPLEMENTATION_SUMMARY.md  # Archive technical summary
├── test_archive_system.py          # Archive system test script
├── app/                            # Application package
│   ├── __init__.py                # App factory
│   ├── extensions.py              # Flask extensions
│   ├── forms.py                   # WTForms forms
│   ├── models/                    # Database models
│   │   ├── archive.py            # Archive model
│   │   ├── schedule.py           # Schedule models
│   │   ├── exam_schedule.py      # Exam schedule models
