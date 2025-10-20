# ============================================================================
# Quick Database Re-Import Script
# ============================================================================
# This script drops and recreates the database with all the fixes applied
# ============================================================================

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  iSchedWise V4 - Database Re-Import Script" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if MySQL is running
Write-Host "Checking if MySQL is running..." -ForegroundColor Yellow
$mysqlPath = "C:\xampp\mysql\bin\mysql.exe"

if (-not (Test-Path $mysqlPath)) {
    Write-Host "❌ ERROR: MySQL not found at $mysqlPath" -ForegroundColor Red
    Write-Host "   Please make sure XAMPP is installed and MySQL path is correct." -ForegroundColor Red
    exit 1
}x

# Confirm before proceeding
Write-Host ""
Write-Host "⚠️  WARNING: This will DELETE and RECREATE the 'ischedwise_db' database!" -ForegroundColor Yellow
Write-Host "   All existing data will be LOST and replaced with sample data." -ForegroundColor Yellow
Write-Host ""
$confirmation = Read-Host "Are you sure you want to continue? (yes/no)"

if ($confirmation -ne "yes") {
    Write-Host "❌ Operation cancelled." -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Step 1: Dropping existing database..." -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan

try {
    & $mysqlPath -u root -e "DROP DATABASE IF EXISTS ischedwise_db;"
    Write-Host "✅ Database dropped successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Error dropping database: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Step 2: Creating new database..." -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan

try {
    & $mysqlPath -u root -e "CREATE DATABASE ischedwise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    Write-Host "✅ Database created successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Error creating database: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Step 3: Importing database schema (database.sql)..." -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan

try {
    Get-Content "database.sql" | & $mysqlPath -u root ischedwise_db
    Write-Host "✅ Schema imported successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Error importing schema: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Step 4: Importing sample data (sample_data.sql)..." -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan

try {
    Get-Content "sample_data.sql" | & $mysqlPath -u root ischedwise_db
    Write-Host "✅ Sample data imported successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Error importing sample data: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "  ✅ DATABASE RE-IMPORT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Restart your Flask application if it's running" -ForegroundColor White
Write-Host "  2. Login with: username=admin, password=admin123" -ForegroundColor White
Write-Host "  3. Test curriculum deletion - it should work without errors!" -ForegroundColor White
Write-Host ""
Write-Host "Sample Data Included:" -ForegroundColor Cyan
Write-Host "  • 4 Departments (BSCS, BEED, BSED, BSHM)" -ForegroundColor White
Write-Host "  • 4 Curricula with Year Levels and Semesters" -ForegroundColor White
Write-Host "  • Multiple Subjects per curriculum" -ForegroundColor White
Write-Host "  • Faculty members with subject assignments" -ForegroundColor White
Write-Host "  • Sample schedules" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
