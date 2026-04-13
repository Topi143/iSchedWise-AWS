# Scripts Directory

This folder contains utility scripts for database management and maintenance.

## 📁 Structure

```
scripts/
├── archive/           # Old/deprecated scripts (kept for reference)
├── init_db.py         # Initialize database with sample data
├── install_startup_task.cmd  # Install/remove Windows startup task
├── reimport_database.ps1  # Reset and reimport database
├── startup_ischedwise_boot.cmd  # Boot runner for cloudflared + XAMPP + iSchedWise
└── README.md          # This file
```

## 🚀 Common Tasks

### Reset Database
```powershell
.\scripts\reimport_database.ps1
```

### Initialize Sample Data
```bash
python scripts/init_db.py
```

### Run Sample Data Script
```bash
python scripts/run_sample_data.py
```

### Windows Startup Automation
1. Install startup task (run as admin):
```cmd
scripts\install_startup_task.cmd
```

2. Test task execution immediately:
```cmd
schtasks /Run /TN "iSchedWiseAutoStart"
```

3. Verify task status and last result:
```cmd
schtasks /Query /TN "iSchedWiseAutoStart" /V /FO LIST
```

4. Remove startup task if needed:
```cmd
scripts\install_startup_task.cmd remove
```

### Startup Runner Notes
- `startup_ischedwise_boot.cmd` runs this sequence:
	1. `cloudflared tunnel run topi_pc`
	2. Start XAMPP MySQL and Apache (service-first with fallback scripts)
	3. Start iSchedWise using `venv\Scripts\python.exe` and `run.py`
- Runner log file: `scripts\logs\startup_boot.log`
- XAMPP path auto-resolution order:
	1. `ISCHEDWISE_XAMPP_DIR` (if set)
	2. Current `XAMPP_DIR` environment value (if set)
	3. Common install paths (`C:\xampp`, `%ProgramFiles%\xampp`, `%ProgramFiles(x86)%\xampp`, `D:\xampp`, `E:\xampp`)
- If MySQL/Apache Windows services are not registered, the runner uses XAMPP launchers (`mysql_start.bat`, `apache_start.bat`). This is expected behavior.
- To force a custom XAMPP location before running:
```cmd
set ISCHEDWISE_XAMPP_DIR=D:\xampp
scripts\startup_ischedwise_boot.cmd
```
- Dry-run mode (no process/service starts):
```cmd
scripts\startup_ischedwise_boot.cmd --dry-run
```

## ⚠️ Migration Scripts (One-time use)

These scripts were used for specific migrations and are kept in `archive/`:

- `add_room_type_column.sql` - Added room_type to rooms table
- `add_concurrency_columns.sql` - Added optimistic locking columns
- `add_sample_schedule_2025_2026_2nd.sql` - Sample schedule data

## 📋 Notes

- Always backup your database before running any scripts
- Scripts assume you're in the project root directory
- Virtual environment should be activated for Python scripts
- Startup task runs at boot as `SYSTEM` with highest privileges
