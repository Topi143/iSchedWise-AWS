# ============================================================================
# iSchedWise V4 - Database Re-import with Subject Templates
# ============================================================================
# This script drops and recreates the database with the new template system
# 
# Prerequisites:
# - XAMPP/MySQL must be running
# - database.sql and sample_data.sql must exist in parent directory
# 
# Usage:
#   .\reimport_with_templates.ps1
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "iSchedWise V4 - Database Re-import" -ForegroundColor Cyan
Write-Host "With Subject Template System" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Configuration
$MYSQL_USER = "root"
$MYSQL_PASSWORD = ""  # Default XAMPP has no password
$DB_NAME = "ischedwise_db"
$DB_SCHEMA = "..\database.sql"
$SAMPLE_DATA = "..\sample_data.sql"

# Check if MySQL is available
Write-Host "[1/6] Checking MySQL installation..." -ForegroundColor Yellow
try {
    $mysqlVersion = & mysql --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "MySQL not found"
    }
    Write-Host "      [OK] MySQL found: $mysqlVersion" -ForegroundColor Green
} catch {
    Write-Host "      [X] ERROR: MySQL not found in PATH" -ForegroundColor Red
    Write-Host "      Please ensure XAMPP MySQL is running and mysql.exe is in your PATH" -ForegroundColor Red
    Write-Host "      Typical location: C:\xampp\mysql\bin\" -ForegroundColor Yellow
    exit 1
}

# Check if SQL files exist
Write-Host "`n[2/6] Checking SQL files..." -ForegroundColor Yellow
if (-not (Test-Path $DB_SCHEMA)) {
    Write-Host "      [X] ERROR: database.sql not found at: $DB_SCHEMA" -ForegroundColor Red
    exit 1
}
Write-Host "      [OK] Found database.sql" -ForegroundColor Green

if (-not (Test-Path $SAMPLE_DATA)) {
    Write-Host "      [X] ERROR: sample_data.sql not found at: $SAMPLE_DATA" -ForegroundColor Red
    exit 1
}
Write-Host "      [OK] Found sample_data.sql" -ForegroundColor Green

# Drop existing database
Write-Host "`n[3/6] Dropping existing database..." -ForegroundColor Yellow
$dropCommand = @"
DROP DATABASE IF EXISTS ``$DB_NAME``;
"@

$dropCommand | & mysql -u $MYSQL_USER --password=$MYSQL_PASSWORD 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "      [OK] Database dropped successfully" -ForegroundColor Green
} else {
    Write-Host "      [!] Database did not exist or could not be dropped" -ForegroundColor Yellow
}

# Import database schema
Write-Host "`n[4/6] Importing database schema..." -ForegroundColor Yellow
Write-Host "      This creates all tables, indexes, and constraints..." -ForegroundColor Gray

Get-Content $DB_SCHEMA | & mysql -u $MYSQL_USER --password=$MYSQL_PASSWORD 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "      [OK] Database schema imported successfully" -ForegroundColor Green
} else {
    Write-Host "      [X] ERROR: Failed to import database schema" -ForegroundColor Red
    exit 1
}

# Import sample data with templates
Write-Host "`n[5/6] Importing sample data with templates..." -ForegroundColor Yellow
Write-Host "      This includes:" -ForegroundColor Gray
Write-Host "        - 63 subject templates" -ForegroundColor Gray
Write-Host "        - ~130 subject instances" -ForegroundColor Gray
Write-Host "        - Template and instance-level faculty assignments" -ForegroundColor Gray
Write-Host "        - Sample departments, buildings, rooms, and faculty" -ForegroundColor Gray

Get-Content $SAMPLE_DATA | & mysql -u $MYSQL_USER --password=$MYSQL_PASSWORD $DB_NAME 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "      [OK] Sample data imported successfully" -ForegroundColor Green
} else {
    Write-Host "      [X] ERROR: Failed to import sample data" -ForegroundColor Red
    exit 1
}

# Verify import
Write-Host "`n[6/6] Verifying import..." -ForegroundColor Yellow

$verifyQuery = @"
SELECT 
    (SELECT COUNT(*) FROM subject_templates) as templates,
    (SELECT COUNT(*) FROM subjects) as subjects,
    (SELECT COUNT(*) FROM faculty_subject_assignments WHERE assignment_type = 'template') as template_assignments,
    (SELECT COUNT(*) FROM faculty_subject_assignments WHERE assignment_type = 'instance') as instance_assignments,
    (SELECT COUNT(*) FROM faculty) as faculty,
    (SELECT COUNT(*) FROM departments) as departments,
    (SELECT COUNT(*) FROM curricula) as curricula;
"@

$result = $verifyQuery | & mysql -u $MYSQL_USER --password=$MYSQL_PASSWORD $DB_NAME -s 2>&1

if ($LASTEXITCODE -eq 0) {
    $counts = $result -split "`t"
    Write-Host "      [OK] Database verification successful:" -ForegroundColor Green
    Write-Host "        - Subject Templates: $($counts[0])" -ForegroundColor Cyan
    Write-Host "        - Subject Instances: $($counts[1])" -ForegroundColor Cyan
    Write-Host "        - Template-level Assignments: $($counts[2])" -ForegroundColor Cyan
    Write-Host "        - Instance-level Assignments: $($counts[3])" -ForegroundColor Cyan
    Write-Host "        - Faculty Members: $($counts[4])" -ForegroundColor Cyan
    Write-Host "        - Departments: $($counts[5])" -ForegroundColor Cyan
    Write-Host "        - Curricula: $($counts[6])" -ForegroundColor Cyan
} else {
    Write-Host "      [!] Could not verify import (but import likely succeeded)" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "[OK] Database re-import completed successfully!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run the Flask application: python run.py" -ForegroundColor White
Write-Host "  2. Login with:" -ForegroundColor White
Write-Host "     Admin - admin@norzagaray.edu / admin123" -ForegroundColor Cyan
Write-Host "     Dean  - dean@norzagaray.edu / dean123" -ForegroundColor Cyan
Write-Host "  3. Navigate to Curriculum or Faculty to see templates in action!`n" -ForegroundColor White

Write-Host "Template System Features:" -ForegroundColor Yellow
Write-Host "  - Template-level assignments: Faculty assigned to templates teach ALL instances" -ForegroundColor White
Write-Host "  - Instance-level assignments: Override specific curriculum instances" -ForegroundColor White
Write-Host "  - Subject overrides: Customize subject details per curriculum" -ForegroundColor White
Write-Host "  - Reduced duplication: Define once, use many times`n" -ForegroundColor White
