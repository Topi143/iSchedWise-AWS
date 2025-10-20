# iSchedWise V4 - Setup Guide for New PC

This guide will help you set up the iSchedWise application on a new PC from scratch.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Software Installation](#software-installation)
3. [Database Setup](#database-setup)
4. [Python Environment Setup](#python-environment-setup)
5. [Application Configuration](#application-configuration)
6. [Running the Application](#running-the-application)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have administrator access on your PC.

---

## Software Installation

### 1. Install Python 3.13 (or 3.8+)

1. Download Python from [python.org](https://www.python.org/downloads/)
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation by opening Command Prompt or PowerShell:
   ```powershell
   python --version
   ```
   Should display: `Python 3.13.x` or similar

### 2. Install MySQL Database

You have two options:

#### Option A: XAMPP (Easier for beginners)
1. Download XAMPP from [apachefriends.org](https://www.apachefriends.org/)
2. Install XAMPP (default settings are fine)
3. Open XAMPP Control Panel
4. Start Apache and MySQL services
5. Default credentials:
   - Host: `localhost`
   - Port: `3306`
   - Username: `root`
   - Password: *(empty)*

#### Option B: MySQL Workbench (Standalone MySQL)
1. Download MySQL Community Server from [mysql.com](https://dev.mysql.com/downloads/mysql/)
2. Download MySQL Workbench from [mysql.com](https://dev.mysql.com/downloads/workbench/)
3. Install both applications
4. During MySQL Server installation, set a root password (remember this!)
5. Default credentials:
   - Host: `localhost`
   - Port: `3306`
   - Username: `root`
   - Password: *(the one you set)*

### 3. Install Git (Optional but recommended)

1. Download Git from [git-scm.com](https://git-scm.com/downloads)
2. Install with default settings

---

## Database Setup

### Step 1: Create the Database

#### Using XAMPP phpMyAdmin:
1. Open browser and go to: `http://localhost/phpmyadmin`
2. Click "New" in the left sidebar
3. Database name: `ischedwise_db`
4. Collation: `utf8mb4_general_ci`
5. Click "Create"

#### Using MySQL Workbench:
1. Open MySQL Workbench
2. Connect to your MySQL server
3. Click "Create a new schema" icon (database icon with plus sign)
4. Schema name: `ischedwise_db`
5. Charset: `utf8mb4`
6. Click "Apply"

### Step 2: Import the Database Schema

#### Using phpMyAdmin:
1. Select the `ischedwise_db` database
2. Click "Import" tab
3. Click "Choose File" and select `database.sql` from the project folder
4. Click "Go" at the bottom
5. **(Optional)** Repeat steps 2-4 with `sample_data.sql` to add test data

#### Using MySQL Workbench:
1. Open MySQL Workbench
2. Connect to your server
3. Go to: `Server` → `Data Import`
4. Select "Import from Self-Contained File"
5. Browse and select `database.sql`
6. Default Target Schema: `ischedwise_db`
7. Click "Start Import"
8. **(Optional)** Repeat steps 3-7 with `sample_data.sql` for test data

#### Using Command Line:
```powershell
# Navigate to project directory
cd "C:\path\to\iSchedWise V4"

# Import database schema
mysql -u root -p ischedwise_db < database.sql

# (Optional) Import sample data for testing
mysql -u root -p ischedwise_db < sample_data.sql
```

**Note:** The `database.sql` creates only the table structure. The `sample_data.sql` is optional and adds sample departments, rooms, faculty, subjects, and schedules for testing purposes.

---

## Python Environment Setup

### Step 1: Copy Project Files

1. Copy the entire `iSchedWise V4` folder to your desired location
   - Example: `C:\Users\YourName\Documents\iSchedWise V4`

### Step 2: Open Project in VS Code (Recommended)

1. Install [Visual Studio Code](https://code.visualstudio.com/)
2. Install Python extension in VS Code
3. Open the project folder: `File` → `Open Folder` → Select `iSchedWise V4`

### Step 3: Create Virtual Environment

Open Terminal in VS Code (or PowerShell in project directory):

```powershell
# Navigate to project directory
cd "C:\path\to\iSchedWise V4"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

**Note**: If you get an execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Your prompt should now show `(venv)` at the beginning.

### Step 4: Install Required Packages

With virtual environment activated:

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

This will install all required packages:
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- PyMySQL
- cryptography
- etc.

---

## Application Configuration

### Step 1: Configure Database Connection

Open `config\config.py` and verify/update the database connection:

```python
# For XAMPP (default):
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/ischedwise_db'

# For MySQL Workbench with password:
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:your_password@localhost:3306/ischedwise_db'
```

Replace `your_password` with your actual MySQL root password.

### Step 2: Initialize Database (First Time Only)

If the database is empty or you need to reset it:

```powershell
# Make sure virtual environment is activated
python init_db.py
```

This will create all necessary tables and initial data.

### Step 3: Configure Secret Key (Optional for Production)

In `config\config.py`, you can change the SECRET_KEY for better security:

```python
SECRET_KEY = 'your-new-secret-key-here'
```

Generate a secure key using:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Running the Application

### Step 1: Start MySQL Service

- **XAMPP**: Open XAMPP Control Panel and start MySQL
- **MySQL Workbench**: MySQL service should auto-start, or start from Services

### Step 2: Start Flask Application

```powershell
# Make sure virtual environment is activated
# Make sure you're in the project directory

python run.py
```

You should see output like:
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### Step 3: Access the Application

1. Open your web browser
2. Navigate to: `http://localhost:5000` or `http://127.0.0.1:5000`
3. You should see the login page

### Default Login Credentials

Check your `database.sql` file for default admin credentials, or create a new user through the database.

---

## Troubleshooting

### Issue: "No module named 'flask'"
**Solution**: Make sure virtual environment is activated:
```powershell
.\venv\Scripts\Activate.ps1
```

### Issue: "Can't connect to MySQL server"
**Solution**: 
- Check if MySQL service is running (XAMPP Control Panel or Services)
- Verify database credentials in `config\config.py`
- Check if port 3306 is not blocked by firewall

### Issue: "Access denied for user 'root'@'localhost'"
**Solution**: 
- Check password in `config\config.py`
- For XAMPP: password is usually empty
- For MySQL Workbench: use the password you set during installation

### Issue: "Table doesn't exist"
**Solution**: 
- Import `database.sql` again
- Or run `python init_db.py`

### Issue: "Port 5000 already in use"
**Solution**: 
- Close other applications using port 5000
- Or change port in `run.py`:
  ```python
  app.run(debug=True, port=5001)
  ```

### Issue: PowerShell execution policy error
**Solution**: 
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Missing packages after installation
**Solution**: 
```powershell
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] MySQL (XAMPP or MySQL Workbench) installed
- [ ] MySQL service running
- [ ] Database `ischedwise_db` created
- [ ] `database.sql` imported
- [ ] Virtual environment created
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database connection configured in `config\config.py`
- [ ] Application running (`python run.py`)
- [ ] Browser opened to `http://localhost:5000`

---

## Additional Notes

### Stopping the Application
- Press `CTRL + C` in the terminal where the app is running

### Deactivating Virtual Environment
```powershell
deactivate
```

### Updating Dependencies
```powershell
pip install --upgrade -r requirements.txt
```

### Creating a Backup
1. Backup database:
   - phpMyAdmin: Select database → Export → Go
   - MySQL Workbench: Server → Data Export
2. Backup project files: Copy entire project folder

---

## Need Help?

If you encounter issues not covered here:
1. Check the error message carefully
2. Verify all prerequisites are installed
3. Make sure MySQL service is running
4. Ensure virtual environment is activated
5. Check Python and package versions

---

**Last Updated**: October 2025  
**Application Version**: iSchedWise V4
