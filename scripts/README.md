# Scripts Directory

This folder contains utility scripts for database management and maintenance.

## 📁 Structure

```
scripts/
├── archive/           # Old/deprecated scripts (kept for reference)
├── init_db.py         # Initialize database with sample data
├── reimport_database.ps1  # Reset and reimport database
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

## ⚠️ Migration Scripts (One-time use)

These scripts were used for specific migrations and are kept in `archive/`:

- `add_room_type_column.sql` - Added room_type to rooms table
- `add_concurrency_columns.sql` - Added optimistic locking columns
- `add_sample_schedule_2025_2026_2nd.sql` - Sample schedule data

## 📋 Notes

- Always backup your database before running any scripts
- Scripts assume you're in the project root directory
- Virtual environment should be activated for Python scripts
