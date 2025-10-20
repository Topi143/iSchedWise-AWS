# ============================================================================
# Reimport Database with Subject Template System
# ============================================================================
# This script automates the process of reimporting the database with the
# new Subject Template System applied.
#
# Prerequisites:
# - XAMPP MySQL/MariaDB running
# - MySQL command line tools available
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "iSchedWise V4 - Database Reimport with Subject Template System" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$dbName = "ischedwise_db"
$dbUser = "root"
$dbPassword = ""  # Default XAMPP root password is empty
$mysqlPath = "C:\xampp\mysql\bin\mysql.exe"
$databaseFile = "database.sql"
$sampleDataFile = "sample_data.sql"

# Check if MySQL is accessible
if (-not (Test-Path $mysqlPath)) {
    Write-Host "❌ ERROR: MySQL not found at $mysqlPath" -ForegroundColor Red
    Write-Host "   Please ensure XAMPP is installed or update the `$mysqlPath variable" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Common paths:" -ForegroundColor Yellow
    Write-Host "   - C:\xampp\mysql\bin\mysql.exe" -ForegroundColor Yellow
    Write-Host "   - C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if database files exist
if (-not (Test-Path $databaseFile)) {
    Write-Host "❌ ERROR: $databaseFile not found" -ForegroundColor Red
    Write-Host "   Please run this script from the project root directory" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ MySQL found: $mysqlPath" -ForegroundColor Green
Write-Host "✅ Database schema file found: $databaseFile" -ForegroundColor Green

if (Test-Path $sampleDataFile) {
    Write-Host "✅ Sample data file found: $sampleDataFile" -ForegroundColor Green
    $importSampleData = $true
} else {
    Write-Host "⚠️  Sample data file not found: $sampleDataFile (will skip)" -ForegroundColor Yellow
    $importSampleData = $false
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "WARNING: This will DROP and RECREATE the database!" -ForegroundColor Yellow
Write-Host "All existing data will be LOST!" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "What will happen:" -ForegroundColor White
Write-Host "1. Drop existing database '$dbName'" -ForegroundColor White
Write-Host "2. Import schema from '$databaseFile' (with Subject Template System)" -ForegroundColor White
if ($importSampleData) {
    Write-Host "3. Import sample data from '$sampleDataFile'" -ForegroundColor White
}
Write-Host ""

$confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host ""
    Write-Host "❌ Operation cancelled by user" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 0
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Starting Database Import..." -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Import database schema (which includes DROP and CREATE)
Write-Host "📦 Step 1: Importing database schema..." -ForegroundColor Cyan
Write-Host "   File: $databaseFile" -ForegroundColor Gray

try {
    if ($dbPassword) {
        $result = cmd /c "`"$mysqlPath`" -u $dbUser -p$dbPassword < `"$databaseFile`" 2>&1"
    } else {
        $result = cmd /c "`"$mysqlPath`" -u $dbUser < `"$databaseFile`" 2>&1"
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database schema imported successfully!" -ForegroundColor Green
        Write-Host "   - Database '$dbName' created" -ForegroundColor Gray
        Write-Host "   - All tables created with Subject Template System" -ForegroundColor Gray
        Write-Host "   - subject_templates table added" -ForegroundColor Gray
        Write-Host "   - subjects table modified (template support)" -ForegroundColor Gray
        Write-Host "   - faculty_subject_assignments modified (template + instance)" -ForegroundColor Gray
    } else {
        Write-Host "❌ Error importing database schema!" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} catch {
    Write-Host "❌ Error importing database schema!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Step 2: Import sample data (if available)
if ($importSampleData) {
    Write-Host "📦 Step 2: Importing sample data..." -ForegroundColor Cyan
    Write-Host "   File: $sampleDataFile" -ForegroundColor Gray
    
    try {
        if ($dbPassword) {
            $result = cmd /c "`"$mysqlPath`" -u $dbUser -p$dbPassword $dbName < `"$sampleDataFile`" 2>&1"
        } else {
            $result = cmd /c "`"$mysqlPath`" -u $dbUser $dbName < `"$sampleDataFile`" 2>&1"
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Sample data imported successfully!" -ForegroundColor Green
            Write-Host "   - Departments added" -ForegroundColor Gray
            Write-Host "   - Buildings and rooms added" -ForegroundColor Gray
            Write-Host "   - Faculty members added" -ForegroundColor Gray
            Write-Host "   - Sections added" -ForegroundColor Gray
            Write-Host "   - Curricula and subjects added" -ForegroundColor Gray
        } else {
            Write-Host "❌ Error importing sample data!" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    } catch {
        Write-Host "❌ Error importing sample data!" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "⏭️  Step 2: Skipping sample data import (file not found)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "✅ Database Import Complete!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database Summary:" -ForegroundColor White
Write-Host "  Database Name: $dbName" -ForegroundColor Gray
Write-Host "  Status: Ready with Subject Template System" -ForegroundColor Gray
Write-Host ""
Write-Host "New Features Available:" -ForegroundColor White
Write-Host "  ✅ subject_templates table - Master subject definitions" -ForegroundColor Green
Write-Host "  ✅ subjects.subject_template_id - Links to templates" -ForegroundColor Green
Write-Host "  ✅ faculty_subject_assignments.assignment_type - Template/Instance support" -ForegroundColor Green
Write-Host "  ✅ Backward compatible - Old subjects still work" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Start the application: python run.py" -ForegroundColor Gray
Write-Host "  2. Login with default credentials:" -ForegroundColor Gray
Write-Host "     - Username: admin" -ForegroundColor Gray
Write-Host "     - Password: admin123" -ForegroundColor Gray
Write-Host "  3. Test the curriculum and faculty pages" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation:" -ForegroundColor White
Write-Host "  - APPLY_SUBJECT_TEMPLATES.md - This migration guide" -ForegroundColor Gray
Write-Host "  - IMPROVEMENT_PLAN.md - Technical specification" -ForegroundColor Gray
Write-Host "  - QUICK_START.md - Quick reference" -ForegroundColor Gray
Write-Host ""
Write-Host "🎉 You're all set! The Subject Template System is now active!" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to exit"
