# Update & Deployment Guide - iSchedWise V4

Complete workflow for updating your GitHub repository and deploying changes to AWS EC2 instances.

## 📋 Table of Contents
1. [Local Development Workflow](#local-development-workflow)
2. [Update GitHub Repository](#update-github-repository)
3. [Deploy to AWS EC2](#deploy-to-aws-ec2)
4. [Database Schema Updates](#database-schema-updates)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting](#troubleshooting)

---

## Local Development Workflow

### Step 1: Make Changes Locally
```powershell
# Navigate to project directory
cd "C:\Users\Topi\Downloads\Thesis\aws\iSchedWise V4 - AWS"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Make your code changes
# Test changes locally
python run.py

# Open browser: http://localhost:5000
# Verify all features work correctly
```

### Step 2: Test Changes Thoroughly
```powershell
# Test database operations (if you made DB changes)
# Drop and recreate database in phpMyAdmin
# Import database.sql
# Import sample_data.sql

# Test all affected features
# Check for errors in console and browser

# Run tests (if you have any)
pytest tests/

# Deactivate virtual environment when done
deactivate
```

---

## Update GitHub Repository

### Step 1: Check Git Status
```powershell
# Check what files have changed
git status

# View specific changes
git diff

# View changes in a specific file
git diff app/routes/schedule.py
```

### Step 2: Stage Changes
```powershell
# Stage all changes
git add .

# OR stage specific files
git add app/routes/schedule.py
git add app/models/schedule.py
git add database.sql

# Check staged changes
git status
```

### Step 3: Commit Changes
```powershell
# Commit with descriptive message
git commit -m "feat: Add archive support for schedules"

# OR for bug fixes
git commit -m "fix: Resolve mobile layout issues in archive view"

# OR for database changes
git commit -m "chore: Update database schema for activity logging"

# OR for documentation
git commit -m "docs: Add deployment update guide"
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `chore:` - Maintenance (dependencies, config)
- `docs:` - Documentation changes
- `refactor:` - Code restructuring
- `style:` - Formatting changes
- `test:` - Adding tests

### Step 4: Push to GitHub
```powershell
# Push to main branch
git push origin main

# If this is your first push or you encounter issues
git push -u origin main

# Enter GitHub credentials if prompted
# Username: Topi143
# Password: Use Personal Access Token (not your GitHub password)
```

### Step 5: Verify on GitHub
1. Go to: https://github.com/Topi143/iSchedWise-AWS
2. Check that your commits appear
3. Verify files were updated correctly
4. Check commit message and timestamp

---

## Deploy to AWS EC2

### Method 1: Git Pull (Recommended for Code Changes)

#### Step 1: Connect to EC2
```powershell
# Navigate to SSH key directory
cd C:\Users\Topi\.ssh

# Connect via SSH
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Replace YOUR_ELASTIC_IP with your actual IP (e.g., 54.123.45.67)
```

#### Step 2: Pull Latest Changes
```bash
# Navigate to project directory
cd /var/www/ischedwise

# Check current status
git status
git log --oneline -5

# Pull latest changes from GitHub
git pull origin main

# You should see:
# Updating abc123..def456
# Fast-forward
#  app/routes/schedule.py | 25 ++++++++++++++++++++
#  1 file changed, 25 insertions(+)
```

#### Step 3: Update Dependencies (if requirements.txt changed)
```bash
# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Deactivate
deactivate
```

#### Step 4: Restart Application
```bash
# Restart Gunicorn service
sudo systemctl restart ischedwise

# Check status
sudo systemctl status ischedwise

# Should show: Active: active (running)

# Check for errors
sudo journalctl -u ischedwise -n 50 --no-pager
```

#### Step 5: Verify Deployment
```bash
# Test application is running
curl -I http://localhost

# Should return: HTTP/1.1 200 OK or 302 Found
```

Open browser: `https://yourdomain.com` (or `http://YOUR_ELASTIC_IP`)
- Log in and test affected features
- Check browser console for errors (F12)
- Verify changes are live

---

### Method 2: Full File Upload (For Major Changes or Initial Setup)

#### When to Use This Method:
- First-time deployment
- Many files changed
- Git history issues
- .env file updates needed
- Complete project restructure

#### Step 1: Prepare Files Locally
```powershell
# Navigate to project directory
cd "C:\Users\Topi\Downloads\Thesis\aws\iSchedWise V4 - AWS"

# Create archive excluding unnecessary files
tar -czf ischedwise-update.tar.gz `
  --exclude=venv `
  --exclude=__pycache__ `
  --exclude=*.pyc `
  --exclude=.git `
  --exclude=.env `
  --exclude=*.log `
  .

# Verify archive created
ls -l ischedwise-update.tar.gz
```

#### Step 2: Upload to EC2
```powershell
# Upload archive to EC2
scp -i "C:\Users\Topi\.ssh\ischedwise-keypair.pem" `
  ischedwise-update.tar.gz `
  ubuntu@YOUR_ELASTIC_IP:~

# Should see progress bar and completion
```

#### Step 3: Extract and Deploy on EC2
```bash
# SSH into EC2
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Backup current installation
sudo cp -r /var/www/ischedwise /var/www/ischedwise-backup-$(date +%Y%m%d)

# Stop application
sudo systemctl stop ischedwise

# Extract new files (preserves .env and venv)
cd /var/www/ischedwise
sudo tar -xzf ~/ischedwise-update.tar.gz --exclude=.env --exclude=venv

# Fix permissions
sudo chown -R ubuntu:ubuntu /var/www/ischedwise

# Update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Start application
sudo systemctl start ischedwise

# Check status
sudo systemctl status ischedwise

# Clean up
rm ~/ischedwise-update.tar.gz
```

---

## Database Schema Updates

### Important: Database changes require special handling!

### Step 1: Update Database Files Locally
```powershell
# ALWAYS update in this order:
# 1. database.sql - Source of truth
# 2. sample_data.sql - Test data
# 3. Python models - Mirror SQL schema

# Test locally:
# 1. Open phpMyAdmin (http://localhost/phpmyadmin)
# 2. Drop database ischedwise_db
# 3. Create new database ischedwise_db
# 4. Import database.sql
# 5. Import sample_data.sql
# 6. Run application: python run.py
# 7. Verify all features work
```

### Step 2: Commit Database Changes to GitHub
```powershell
git add database.sql sample_data.sql
git add app/models/*.py
git commit -m "chore: Update database schema - add activity logging"
git push origin main
```

### Step 3: Backup Production Database
```bash
# SSH into EC2
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Create backup directory
mkdir -p ~/backups

# Backup production database
mysqldump -h YOUR_RDS_ENDPOINT \
  -u admin \
  -p \
  ischedwise_db > ~/backups/ischedwise_db_backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip ~/backups/ischedwise_db_backup_*.sql

# Verify backup
ls -lh ~/backups/

# SAVE THIS BACKUP LOCATION - you may need it for rollback!
```

### Step 4: Apply Database Changes to Production

**Option A: For Simple Column Additions (No Data Loss)**
```bash
# Connect to RDS
mysql -h YOUR_RDS_ENDPOINT -u admin -p

# Enter password when prompted

# Switch to database
USE ischedwise_db;

# Apply changes manually (example)
ALTER TABLE schedules ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE schedules ADD KEY idx_is_archived (is_archived);

# Verify changes
SHOW COLUMNS FROM schedules;

# Exit
exit;
```

**Option B: For Major Schema Changes (Use Fresh Import)**
```bash
# ⚠️ WARNING: This will DELETE all production data!
# Only use if you have a backup or it's acceptable to lose data

# Pull latest code with updated database.sql
cd /var/www/ischedwise
git pull origin main

# Connect to RDS
mysql -h YOUR_RDS_ENDPOINT -u admin -p

# Drop and recreate database
DROP DATABASE ischedwise_db;
CREATE DATABASE ischedwise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Exit MySQL
exit;

# Import new schema
mysql -h YOUR_RDS_ENDPOINT -u admin -p ischedwise_db < database.sql

# Import sample data (optional - for testing)
mysql -h YOUR_RDS_ENDPOINT -u admin -p ischedwise_db < sample_data.sql

# If you have production data backup, restore it:
# gunzip ~/backups/ischedwise_db_backup_YYYYMMDD_HHMMSS.sql.gz
# mysql -h YOUR_RDS_ENDPOINT -u admin -p ischedwise_db < ~/backups/ischedwise_db_backup_YYYYMMDD_HHMMSS.sql
```

### Step 5: Update Python Models and Restart
```bash
# Pull latest models
cd /var/www/ischedwise
git pull origin main

# Restart application
sudo systemctl restart ischedwise

# Check for errors
sudo journalctl -u ischedwise -n 50 --no-pager

# Test database connection
source venv/bin/activate
python3 -c "from app import create_app; app = create_app(); print('Database connection successful!')"
deactivate
```

---

## Rollback Procedures

### Rollback Code Changes

#### Method 1: Revert to Previous Commit
```bash
# SSH into EC2
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Navigate to project
cd /var/www/ischedwise

# View recent commits
git log --oneline -10

# Revert to specific commit (copy commit hash)
git reset --hard abc123def

# Restart application
sudo systemctl restart ischedwise
```

#### Method 2: Restore from Backup
```bash
# SSH into EC2
cd /var/www

# Remove current version
sudo rm -rf ischedwise

# Restore backup
sudo cp -r ischedwise-backup-20241023 ischedwise
sudo chown -R ubuntu:ubuntu ischedwise

# Restart application
sudo systemctl restart ischedwise
```

### Rollback Database Changes

```bash
# SSH into EC2
cd ~/backups

# List backups
ls -lh

# Decompress backup
gunzip ischedwise_db_backup_20241023_143022.sql.gz

# Connect to RDS
mysql -h YOUR_RDS_ENDPOINT -u admin -p

# Drop current database
DROP DATABASE ischedwise_db;
CREATE DATABASE ischedwise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;

# Restore backup
mysql -h YOUR_RDS_ENDPOINT -u admin -p ischedwise_db < ~/backups/ischedwise_db_backup_20241023_143022.sql

# Verify restoration
mysql -h YOUR_RDS_ENDPOINT -u admin -p
USE ischedwise_db;
SHOW TABLES;
SELECT COUNT(*) FROM users;
exit;

# Restart application
sudo systemctl restart ischedwise
```

---

## Troubleshooting

### Issue: Git Pull Fails with "Dubious Ownership"
```bash
# Error: fatal: detected dubious ownership in repository at '/var/www/ischedwise'

# Solution 1: Add safe directory (Recommended)
git config --global --add safe.directory /var/www/ischedwise

# Then try again
git pull origin main

# Solution 2: Fix ownership permanently
sudo chown -R ubuntu:ubuntu /var/www/ischedwise

# Then try again
git pull origin main

# Verify ownership is correct
ls -la /var/www/ischedwise
# Should show: drwxr-xr-x ubuntu ubuntu
```

### Issue: Git Pull Fails with "Conflict"
```bash
# View conflicting files
git status

# Option 1: Keep remote version (discard local changes)
git reset --hard origin/main

# Option 2: Stash local changes, pull, then reapply
git stash
git pull origin main
git stash pop
```

### Issue: Application Won't Start After Update
```bash
# Check service status
sudo systemctl status ischedwise

# View recent logs
sudo journalctl -u ischedwise -n 100 --no-pager

# Common causes:
# 1. Syntax error in Python code
# 2. Missing dependencies
# 3. Database connection issues
# 4. Permission problems

# Test application manually
cd /var/www/ischedwise
source venv/bin/activate
python3 run.py

# Fix syntax errors or install missing packages
pip install missing-package
deactivate

# Restart service
sudo systemctl restart ischedwise
```

### Issue: Database Connection Failed
```bash
# Test RDS connection
mysql -h YOUR_RDS_ENDPOINT -u admin -p

# If fails:
# 1. Check RDS instance is running (AWS Console)
# 2. Verify security group allows EC2 (port 3306)
# 3. Check .env file has correct credentials
cat /var/www/ischedwise/.env | grep DATABASE_URL

# Test from application
cd /var/www/ischedwise
source venv/bin/activate
python3 -c "from app import create_app, db; app = create_app(); app.app_context().push(); print(db.engine.url)"
deactivate
```

### Issue: Changes Not Visible on Website
```bash
# Clear browser cache (Ctrl+Shift+R or Ctrl+F5)

# Check if Nginx is serving old cached files
sudo systemctl restart nginx

# Verify application restarted
sudo systemctl status ischedwise

# Check if correct version is deployed
cd /var/www/ischedwise
git log -1

# Force restart everything
sudo systemctl restart ischedwise
sudo systemctl restart nginx

# Clear browser cache and test
```

### Issue: Permission Denied Errors
```bash
# Fix file ownership
sudo chown -R ubuntu:ubuntu /var/www/ischedwise

# Fix .env permissions
chmod 600 /var/www/ischedwise/.env

# Fix socket permissions
sudo chown ubuntu:www-data /var/www/ischedwise/ischedwise.sock
sudo chmod 660 /var/www/ischedwise/ischedwise.sock

# Restart services
sudo systemctl restart ischedwise
sudo systemctl restart nginx
```

---

## Quick Reference Commands

### Daily Development Workflow
```powershell
# Local: Make changes and test
cd "C:\Users\Topi\Downloads\Thesis\aws\iSchedWise V4 - AWS"
.\venv\Scripts\Activate.ps1
python run.py

# Local: Commit and push
git add .
git commit -m "feat: Add new feature"
git push origin main

# EC2: Deploy
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP
cd /var/www/ischedwise
git pull origin main
sudo systemctl restart ischedwise
exit
```

### Emergency Rollback
```bash
# SSH into EC2
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Rollback code
cd /var/www/ischedwise
git log --oneline -5
git reset --hard PREVIOUS_COMMIT_HASH
sudo systemctl restart ischedwise

# Rollback database
cd ~/backups
gunzip BACKUP_FILE.sql.gz
mysql -h RDS_ENDPOINT -u admin -p ischedwise_db < BACKUP_FILE.sql
```

### Check Logs
```bash
# Application logs
sudo journalctl -u ischedwise -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Last 50 application errors
sudo journalctl -u ischedwise -n 50 --no-pager | grep -i error
```

---

## Best Practices

### ✅ DO:
- **Test locally** before pushing to GitHub
- **Commit frequently** with descriptive messages
- **Backup database** before schema changes
- **Use git branches** for major features
- **Test on production** after deployment
- **Monitor logs** after updates
- **Keep backups** for 7-30 days

### ❌ DON'T:
- Don't push untested code to production
- Don't skip database backups
- Don't commit sensitive data (.env files)
- Don't deploy during peak usage hours
- Don't apply database changes without testing
- Don't forget to restart services after updates
- Don't delete backups immediately

---

## Deployment Checklist

### Before Deployment:
- [ ] All changes tested locally
- [ ] Database schema updated (if needed)
- [ ] Committed to GitHub with descriptive message
- [ ] Reviewed changes on GitHub
- [ ] Verified no sensitive data in commits
- [ ] Created database backup (if DB changes)
- [ ] Notified users of maintenance (if needed)

### During Deployment:
- [ ] Connected to EC2 via SSH
- [ ] Pulled latest changes from GitHub
- [ ] Updated dependencies (if needed)
- [ ] Applied database changes (if needed)
- [ ] Restarted application service
- [ ] Checked service status (no errors)

### After Deployment:
- [ ] Tested application in browser
- [ ] Verified changes are live
- [ ] Checked application logs for errors
- [ ] Tested affected features
- [ ] Monitored for 5-10 minutes
- [ ] Rolled back if issues found
- [ ] Documented any issues or notes

---

## Automated Deployment (Optional Advanced Setup)

### Set Up GitHub Actions for Auto-Deploy

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to EC2
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /var/www/ischedwise
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart ischedwise
```

Add secrets to GitHub repository:
1. Go to: https://github.com/Topi143/iSchedWise-AWS/settings/secrets/actions
2. Add `EC2_HOST` - Your Elastic IP
3. Add `EC2_SSH_KEY` - Content of ischedwise-keypair.pem

**Note:** This auto-deploys on every push to main! Use with caution.

---

## Support Resources

- **Project Documentation**: `docs/` folder
- **AWS Console**: https://console.aws.amazon.com/
- **GitHub Repository**: https://github.com/Topi143/iSchedWise-AWS
- **Flask Docs**: https://flask.palletsprojects.com/
- **AWS EC2 Docs**: https://docs.aws.amazon.com/ec2/

---

**Last Updated:** October 23, 2025

For questions or issues, review project documentation or create a GitHub issue.
