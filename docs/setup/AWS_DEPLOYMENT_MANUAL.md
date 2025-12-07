# AWS Manual Deployment Guide - iSchedWise V4

Complete step-by-step guide to manually deploy iSchedWise V4 Flask application with MySQL database on AWS.

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Database Setup (RDS)](#database-setup-rds)
4. [Web Server Setup (EC2)](#web-server-setup-ec2)
5. [Application Deployment](#application-deployment)
6. [Domain & SSL Configuration](#domain--ssl-configuration)
7. [Post-Deployment](#post-deployment)
8. [Maintenance & Monitoring](#maintenance--monitoring)

---

## Prerequisites

### What You Need
- AWS Account (with billing enabled)
- Credit card for AWS payment
- Your local project files ready
- Domain name (optional, but recommended)
- Basic command line knowledge

### Estimated Costs (Monthly)
- **EC2 t2.micro**: ~$8-10/month (Free tier: 750 hours/month for 12 months)
- **RDS db.t3.micro**: ~$15-20/month (Free tier: 750 hours/month for 12 months)
- **Data Transfer**: ~$1-5/month (depends on traffic)
- **Elastic IP**: Free while attached to running instance
- **Total**: ~$24-35/month (or ~$0-5 with free tier)

---

## AWS Account Setup

### Step 1: Create AWS Account
1. Go to https://aws.amazon.com/
2. Click **"Create an AWS Account"**
3. Enter email address and account name
4. Choose **"Personal"** account type
5. Enter payment information (credit card required)
6. Verify phone number
7. Select **"Basic Support - Free"** plan
8. Complete account activation

### Step 2: Secure Your Root Account
1. Log in to AWS Console: https://console.aws.amazon.com/
2. Click your name (top right) → **"Security credentials"**
3. Enable **MFA (Multi-Factor Authenticator)**:
   - Click **"Assign MFA device"**
   - Choose **"Virtual MFA device"**
   - Use Google Authenticator app on phone
   - Scan QR code and enter two consecutive codes
4. Save root credentials securely (DO NOT use for daily tasks)

### Step 3: Create IAM Admin User
1. Go to **IAM** service: https://console.aws.amazon.com/iam/
2. Click **"Users"** → **"Add users"**
3. User details:
   - Username: `admin-user`
   - Access type: Check both **"Programmatic access"** and **"AWS Management Console access"**
   - Console password: **"Custom password"** → Enter strong password
   - Uncheck **"Require password reset"**
4. Permissions:
   - Click **"Attach existing policies directly"**
   - Select **"AdministratorAccess"**
5. Tags (optional): Add `Role: Admin`
6. Review and **"Create user"**
7. **IMPORTANT**: Save credentials securely:
   - Access Key ID
   - Secret Access Key
   - Console login link

### Step 4: Set Up Billing Alerts
1. Go to **Billing Dashboard**: https://console.aws.amazon.com/billing/
2. Click **"Budgets"** → **"Create budget"**
3. Choose **"Customize (advanced)"**
4. Budget type: **"Cost budget"**
5. Set budget amount: `$50` (adjust as needed)
6. Configure alerts:
   - Alert at 80% ($40)
   - Alert at 100% ($50)
7. Enter your email for notifications
8. Click **"Create budget"**

---

## Database Setup (RDS)

### Step 1: Create Security Group for Database
1. Go to **EC2** service: https://console.aws.amazon.com/ec2/
2. Click **"Security Groups"** (left sidebar under Network & Security)
3. Click **"Create security group"**
4. Configure:
   - **Security group name**: `ischedwise-db-sg`
   - **Description**: `Security group for iSchedWise MySQL database`
   - **VPC**: Select default VPC
5. Inbound rules - Click **"Add rule"**:
   - **Type**: MySQL/Aurora
   - **Protocol**: TCP
   - **Port Range**: 3306
   - **Source**: Custom → `0.0.0.0/0` (We'll restrict this later to EC2 only)
   - **Description**: `Allow MySQL from anywhere (temp)`
6. Outbound rules: Leave default (All traffic)
7. Click **"Create security group"**

### Step 2: Create RDS MySQL Database
1. Go to **RDS** service: https://console.aws.amazon.com/rds/
2. Click **"Create database"**
3. Database creation method: **"Standard create"**
4. Engine options:
   - **Engine type**: MySQL
   - **Version**: MySQL 8.0.35 (latest stable)
5. Templates: **"Free tier"** (or **"Production"** if you need more resources)
6. Settings:
   - **DB instance identifier**: `ischedwise-db`
   - **Master username**: `admin`
   - **Master password**: Create strong password (e.g., `ISchedWise2025!SecureDB`)
   - **Confirm password**: Re-enter password
   - **SAVE THIS PASSWORD SECURELY!**
7. Instance configuration (Free tier):
   - **DB instance class**: db.t3.micro (2 vCPU, 1 GB RAM)
8. Storage:
   - **Storage type**: General Purpose SSD (gp3)
   - **Allocated storage**: 20 GB (minimum)
   - **Enable storage autoscaling**: Check (max 100 GB)
9. Connectivity:
   - **VPC**: Default VPC
   - **Public access**: **Yes** (for initial setup and maintenance)
   - **VPC security group**: Choose existing → `ischedwise-db-sg`
   - **Availability Zone**: No preference
10. Database authentication: **"Password authentication"**
11. Additional configuration - Click **"Additional configuration"**:
    - **Initial database name**: `ischedwise_db`
    - **Backup retention period**: 7 days
    - **Enable encryption**: Check (recommended)
    - **Enable Enhanced monitoring**: Uncheck (to save costs)
    - **Enable auto minor version upgrade**: Check
12. Review all settings
13. Click **"Create database"**
14. **Wait 5-10 minutes** for database to be created (Status: Available)

### Step 3: Note Database Endpoint
1. Once status shows **"Available"**, click on database name `ischedwise-db`
2. Find **"Endpoint & port"** section
3. **Copy the endpoint** (looks like: `ischedwise-db.xxxxx.us-east-1.rds.amazonaws.com`)
4. **Save this endpoint** - you'll need it for application configuration

### Step 4: Connect to Database and Import Schema
1. **Option A: Using MySQL Workbench** (Recommended)
   - Download MySQL Workbench: https://dev.mysql.com/downloads/workbench/
   - Open MySQL Workbench
   - Click **"+"** to create new connection
   - Connection settings:
     - **Connection Name**: AWS iSchedWise DB
     - **Hostname**: Paste RDS endpoint (without :3306)
     - **Port**: 3306
     - **Username**: admin
     - **Password**: Click "Store in Vault" → Enter master password
   - Click **"Test Connection"** (should succeed)
   - Click **"OK"**
   - Double-click connection to open
   - Go to **"File"** → **"Run SQL Script"**
   - Select `database.sql` from your project
   - Click **"Run"**
   - Repeat for `sample_data.sql`

2. **Option B: Using Command Line**
   ```bash
   # Install MySQL client if not installed
   # Windows: Download from https://dev.mysql.com/downloads/mysql/
   
   # Connect to RDS
   mysql -h ischedwise-db.xxxxx.us-east-1.rds.amazonaws.com -u admin -p
   
   # Enter password when prompted
   # You should see: mysql>
   
   # Import database schema
   mysql> source C:/Users/Topi/Downloads/Thesis/iSchedWise V4/database.sql
   
   # Import sample data
   mysql> source C:/Users/Topi/Downloads/Thesis/iSchedWise V4/sample_data.sql
   
   # Verify tables
   mysql> USE ischedwise_db;
   mysql> SHOW TABLES;
   
   # Exit
   mysql> exit;
   ```

---

## Web Server Setup (EC2)

### Step 1: Create Security Group for Web Server
1. Go to **EC2** → **"Security Groups"**
2. Click **"Create security group"**
3. Configure:
   - **Security group name**: `ischedwise-web-sg`
   - **Description**: `Security group for iSchedWise web server`
   - **VPC**: Default VPC
4. Inbound rules - Add these rules:
   
   | Type | Protocol | Port | Source | Description |
   |------|----------|------|--------|-------------|
   | SSH | TCP | 22 | My IP | SSH access from your IP |
   | HTTP | TCP | 80 | 0.0.0.0/0 | HTTP web traffic |
   | HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS web traffic |
   | Custom TCP | TCP | 5000 | 0.0.0.0/0 | Flask dev server (temp) |

5. Outbound rules: Leave default (All traffic)
6. Click **"Create security group"**

### Step 2: Launch EC2 Instance
1. Go to **EC2** → **"Instances"**
2. Click **"Launch instances"**
3. Name and tags:
   - **Name**: `ischedwise-web-server`
4. Application and OS Images (AMI):
   - **Quick Start**: Ubuntu
   - **AMI**: Ubuntu Server 24.04 LTS (Free tier eligible)
   - **Architecture**: 64-bit (x86)
5. Instance type:
   - **Instance type**: t2.micro (1 vCPU, 1 GB RAM) - Free tier eligible
6. Key pair (login):
   - Click **"Create new key pair"**
   - **Key pair name**: `ischedwise-keypair`
   - **Key pair type**: RSA
   - **Private key file format**: .pem (for OpenSSH)
   - Click **"Create key pair"**
   - **Key file will download** - Save it securely! (e.g., `C:\Users\Topi\.ssh\ischedwise-keypair.pem`)
7. Network settings:
   - **VPC**: Default VPC
   - **Auto-assign public IP**: Enable
   - **Firewall (security groups)**: Select existing → `ischedwise-web-sg`
8. Configure storage:
   - **Root volume**: 8 GB gp3 (Free tier allows up to 30 GB)
9. Advanced details: Leave default
10. Summary: Review all settings
11. Click **"Launch instance"**
12. Wait 1-2 minutes for instance to start (Status: Running)

### Step 3: Allocate Elastic IP (Optional but Recommended)
1. Go to **EC2** → **"Elastic IPs"** (left sidebar)
2. Click **"Allocate Elastic IP address"**
3. Settings: Leave default
4. Click **"Allocate"**
5. Select the newly allocated IP
6. Click **"Actions"** → **"Associate Elastic IP address"**
7. Settings:
   - **Instance**: Select `ischedwise-web-server`
   - **Private IP**: Select the instance's private IP
8. Click **"Associate"**
9. **Note the Elastic IP** - This is your server's permanent public IP

### Step 4: Update Database Security Group
Now that we have the EC2 instance, let's restrict database access:

1. Go to **EC2** → **"Security Groups"**
2. Click on `ischedwise-db-sg`
3. Click **"Inbound rules"** → **"Edit inbound rules"**
4. Delete the `0.0.0.0/0` rule
5. Click **"Add rule"**:
   - **Type**: MySQL/Aurora
   - **Source**: Custom → Search and select `ischedwise-web-sg`
   - **Description**: `Allow MySQL from web server`
6. Click **"Add rule"** (for your local access):
   - **Type**: MySQL/Aurora
   - **Source**: My IP
   - **Description**: `MySQL access from my IP`
7. Click **"Save rules"**

### Step 5: Connect to EC2 Instance
1. Go to **EC2** → **"Instances"**
2. Select `ischedwise-web-server`
3. Click **"Connect"** button
4. Go to **"SSH client"** tab
5. Follow instructions or use:

**Windows (PowerShell):**
```powershell
# Navigate to key directory
cd C:\Users\Topi\.ssh

# Set permissions (if needed)
icacls ischedwise-keypair.pem /inheritance:r
icacls ischedwise-keypair.pem /grant:r "$($env:USERNAME):(R)"

# Connect via SSH
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP
# Replace YOUR_ELASTIC_IP with actual IP
```

**Alternative: Use PuTTY (Windows)**
1. Download PuTTY: https://www.putty.org/
2. Convert .pem to .ppk using PuTTYgen:
   - Open PuTTYgen
   - Click **"Load"** → Select `ischedwise-keypair.pem`
   - Click **"Save private key"** → Save as `ischedwise-keypair.ppk`
3. Open PuTTY:
   - **Host Name**: `ubuntu@YOUR_ELASTIC_IP`
   - **Port**: 22
   - **Connection** → **SSH** → **Auth** → **Credentials**: Browse and select `.ppk` file
   - Click **"Open"**

### Step 6: Update System and Install Dependencies
Once connected via SSH:

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Add deadsnakes PPA (required for Python 3.11)
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11 and pip
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install MySQL client
sudo apt install -y mysql-client

# Install Nginx (web server)
sudo apt install -y nginx

# Install additional tools
sudo apt install -y git curl wget nano

# Verify installations
python3.11 --version
mysql --version
nginx -v
```

---

## Application Deployment

### Step 1: Transfer Project Files to EC2
**Option A: Using SCP (from your local machine)**
```powershell
# From Windows PowerShell
cd "C:\Users\Topi\Downloads\Thesis\iSchedWise V4"

# Create tar archive (requires tar on Windows)
tar -czf ischedwise.tar.gz --exclude=venv --exclude=__pycache__ --exclude=*.pyc .

# Upload to EC2
scp -i "C:\Users\Topi\.ssh\ischedwise-keypair.pem" ischedwise.tar.gz ubuntu@YOUR_ELASTIC_IP:~
```

**Option B: Using Git (Recommended)**
```bash
# On EC2 instance (via SSH)
cd ~

# Clone repository (if you have GitHub repo)
git clone https://github.com/yourusername/ischedwise-v4.git
cd ischedwise-v4

# OR create directory and upload files manually
mkdir -p ischedwise-v4
cd ischedwise-v4

# Extract uploaded tar archive (if using SCP)
# tar -xzf ~/ischedwise.tar.gz
```

**Option C: Manual File Upload (Small projects)**
Use WinSCP or FileZilla:
- Download WinSCP: https://winscp.net/
- Connect with:
  - Host: YOUR_ELASTIC_IP
  - Username: ubuntu
  - Private key: ischedwise-keypair.ppk
- Upload project folder

### Step 2: Set Up Project Structure
```bash
# Create project directory
sudo mkdir -p /var/www/ischedwise
sudo chown -R ubuntu:ubuntu /var/www/ischedwise

# Copy files (if using tar)
cp -r ~/ischedwise-v4/* /var/www/ischedwise/

# OR clone directly to production directory
cd /var/www
sudo git clone https://github.com/yourusername/ischedwise-v4.git ischedwise
sudo chown -R ubuntu:ubuntu /var/www/ischedwise

# Navigate to project
cd /var/www/ischedwise
```

### Step 3: Create Environment Configuration

**IMPORTANT:** This step creates the `.env` file that stores your sensitive configuration. You'll need:
- Your RDS database endpoint (from Database Setup Step 3)
- Your RDS master password (from Database Setup Step 2)
- (Optional) Email settings for password reset feature

#### Step 3a: Generate Secret Key First
```bash
# Generate a secure random key
python3 -c "import secrets; print(secrets.token_hex(32))"
```
**Copy the output** (looks like: `a1b2c3d4e5f6...` - 64 characters). You'll paste this as SECRET_KEY below.

#### Step 3b: Prepare Your Database Connection String
Format: `mysql+pymysql://USERNAME:PASSWORD@ENDPOINT/DATABASE_NAME`

Example with your values:
- Username: `admin`
- Password: (your RDS password from Database Setup)
- Endpoint: `ischedwise-db.xxxxx.us-east-1.rds.amazonaws.com` (from RDS console)
- Database: `ischedwise_db`

Final string looks like:
```
mysql+pymysql://admin:ISchedWise2025!SecureDB@ischedwise-db.c9a8b7c6d5e4.us-east-1.rds.amazonaws.com/ischedwise_db
```

#### Step 3c: Create and Edit .env File
```bash
cd /var/www/ischedwise

# Option 1: Copy from example template
cp .env.example .env

# Option 2: Create new file
nano .env
```

When nano opens, **type or paste** this content:
```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=64cc9009f2edacac016997a313c193a6b7ba0767e1fa346a6792bb39046321e0

# Database Configuration
DATABASE_URL=mysql+pymysql://admin:12345678@ischedwise-db.cw3g6si0u96s.us-east-1.rds.amazonaws.com/ischedwise_db

# Email Configuration (Optional - for password reset feature)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# AI Configuration (Optional - for AI schedule suggestions)
GEMINI_API_KEY=your-gemini-api-key-if-using

# Other Configuration
MAX_CONTENT_LENGTH=16777216
```

#### Step 3d: Replace Placeholders with Your Actual Values

**Required replacements:**
1. `PASTE_YOUR_GENERATED_SECRET_KEY_HERE` → Your generated secret key from Step 3a
2. `YOUR_RDS_PASSWORD` → Your RDS master password (e.g., `ISchedWise2025!SecureDB`)
3. `YOUR_RDS_ENDPOINT` → Your RDS endpoint (e.g., `ischedwise-db.c9a8b7c6d5e4.us-east-1.rds.amazonaws.com`)

**Optional replacements (can skip for now):**
- Email settings: Configure later if you want password reset feature
- AI settings: Configure later if you want AI suggestions

**Example of completed .env file:**
```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=production
SECRET_KEY=a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789

# Database Configuration
DATABASE_URL=mysql+pymysql://admin:ISchedWise2025!SecureDB@ischedwise-db.c9a8b7c6d5e4.us-east-1.rds.amazonaws.com/ischedwise_db

# Email Configuration (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=

# AI Configuration (Optional)
GEMINI_API_KEY=

# Other Configuration
MAX_CONTENT_LENGTH=16777216
```

#### Step 3e: Save and Exit Nano
1. Press **`Ctrl + O`** (letter O) to save
2. Press **`Enter`** to confirm filename
3. Press **`Ctrl + X`** to exit nano

#### Step 3f: Verify .env File
```bash
# Check if file was created
ls -la .env

# View file contents (be careful - contains secrets!)
cat .env

# Set proper permissions (readable only by owner)
chmod 600 .env
```

**Security Note:** Never commit `.env` file to Git! It's already in `.gitignore`.

### Step 4: Install Python Dependencies
```bash
cd /var/www/ischedwise

# Create virtual environment using Python 3.11
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install production server (Gunicorn)
pip install gunicorn

# Verify installation
pip list

# IMPORTANT: If you encounter "ModuleNotFoundError: No module named 'pymysql'" later,
# force install using the venv's pip directly:
./venv/bin/pip install pymysql
./venv/bin/pip install -r requirements.txt
```

### Step 5: Update Configuration for Production
Edit `config/config.py`:
```bash
nano config/config.py
```

Ensure ProductionConfig uses environment variables:
```python
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Remove the @property decorator - SECRET_KEY must be a class attribute
    # Override the parent class SECRET_KEY
    def __init__(self):
        super().__init__()
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY must be set in production environment")
        self.SECRET_KEY = secret_key
```

### Step 6: Test Application
```bash
cd /var/www/ischedwise

# CRITICAL: Always use the venv's Python directly to avoid module errors
# Test database connection
./venv/bin/python -c "from app import create_app; app = create_app(); print('App created successfully')"

# If you get "ModuleNotFoundError: No module named 'pymysql'", run:
# ./venv/bin/pip install pymysql
# ./venv/bin/pip install -r requirements.txt
# Then retry the test command above

# Run Flask app (test)
export FLASK_ENV=production
# Use explicit path to ensure venv is used
./venv/bin/python run.py

# Should see:
# * Running on http://0.0.0.0:5000
```

Open browser: `http://YOUR_ELASTIC_IP:5000`
If you see login page, **SUCCESS!** Press `Ctrl+C` to stop.

### Step 7: Set Up Gunicorn (Production WSGI Server)
```bash
cd /var/www/ischedwise

# Test Gunicorn
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 run:app

# Should start without errors
# Ctrl+C to stop
```

Create Gunicorn systemd service:
```bash
sudo nano /etc/systemd/system/ischedwise.service
```

Add this content:
```ini
[Unit]
Description=iSchedWise Gunicorn Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/ischedwise
Environment="PATH=/var/www/ischedwise/venv/bin"
Environment="FLASK_ENV=production"
EnvironmentFile=/var/www/ischedwise/.env
ExecStart=/var/www/ischedwise/venv/bin/gunicorn --workers 3 --bind unix:/var/www/ischedwise/ischedwise.sock --timeout 120 run:app

[Install]
WantedBy=multi-user.target
```

Save and enable service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Start service
sudo systemctl start ischedwise

# Check status
sudo systemctl status ischedwise

# Enable auto-start on boot
sudo systemctl enable ischedwise
```

### Step 8: Configure Nginx as Reverse Proxy
```bash
# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Create new site configuration
sudo nano /etc/nginx/sites-available/ischedwise
```

Add this content:
```nginx
server {
    listen 80;
    server_name YOUR_ELASTIC_IP;  # Replace with your domain or IP

    # Increase client body size for file uploads
    client_max_body_size 16M;

    location / {
        proxy_pass http://unix:/var/www/ischedwise/ischedwise.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /static {
        alias /var/www/ischedwise/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

Enable site and restart Nginx:
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ischedwise /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

### Step 9: Test Production Deployment
Open browser: `http://YOUR_ELASTIC_IP`

You should see iSchedWise login page!

Test login with default credentials:
- Admin: `admin@ischedwise.com` / `admin123`
- Dean: `dean@ischedwise.com` / `dean123`

---

## Domain & SSL Configuration

### Step 1: Point Domain to AWS (Optional)
If you have a domain name (e.g., from Namecheap, GoDaddy):

1. **Option A: Update DNS A Record**
   - Log in to your domain registrar
   - Go to DNS management
   - Add/Edit A record:
     - **Type**: A
     - **Host**: @ (or subdomain like `app`)
     - **Value**: YOUR_ELASTIC_IP
     - **TTL**: 300
   - Wait 5-60 minutes for DNS propagation

2. **Option B: Use Route 53 (AWS DNS)**
   - Go to **Route 53** in AWS Console
   - Click **"Create hosted zone"**
   - Enter domain name: `yourdomain.com`
   - Click **"Create hosted zone"**
   - Copy the 4 nameservers
   - Update nameservers at your domain registrar
   - Create A record pointing to Elastic IP

### Step 2: Install SSL Certificate (HTTPS)
**Using Let's Encrypt (Free SSL):**

#### Step 2a: Update Nginx Configuration with Your Domain First
```bash
# SSH into EC2
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Edit Nginx configuration
sudo nano /etc/nginx/sites-available/ischedwise
```

Change `server_name` from `YOUR_ELASTIC_IP` to your actual domain:
```nginx
server {
    listen 80;
    server_name ischedwise.online www.ischedwise.online;  # Update this line!

    # Increase client body size for file uploads
    client_max_body_size 16M;

    location / {
        proxy_pass http://unix:/var/www/ischedwise/ischedwise.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /static {
        alias /var/www/ischedwise/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

Test and restart Nginx:
```bash
# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Verify it's working
curl -I http://ischedwise.online
```

**IMPORTANT**: Wait 1-2 minutes and verify your domain works via HTTP first:
- Open browser: `http://ischedwise.online`
- You should see iSchedWise login page
- If not working, check DNS propagation: https://dnschecker.org/

#### Step 2b: Install Certbot and Obtain SSL Certificate
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate (only after domain works via HTTP!)
sudo certbot --nginx -d ischedwise.online -d www.ischedwise.online

# Follow prompts:
# - Enter email address (for renewal notifications)
# - Agree to terms of service (Y)
# - Share email with EFF (optional - N is fine)
# - Choose: Redirect HTTP to HTTPS - Select option 2 (recommended)

# Certificate auto-renewal is set up automatically
# Test renewal:
sudo certbot renew --dry-run
```

**What Certbot does automatically:**
- Adds SSL certificate configuration to Nginx
- Creates HTTPS server block (port 443)
- Sets up automatic HTTP to HTTPS redirect
- Configures SSL security headers
- Sets up auto-renewal cron job

#### Step 2c: Verify SSL Installation
```bash
# Check Nginx configuration
sudo nginx -t

# Restart Nginx (if needed)
sudo systemctl restart nginx

# Check certificate status
sudo certbot certificates
```

Visit: `https://ischedwise.online` (Should show SSL padlock! 🔒)

#### Troubleshooting SSL Issues

**If Certbot fails with "Connection refused":**
```bash
# 1. Verify Nginx is running and serving HTTP
sudo systemctl status nginx
curl -I http://ischedwise.online

# 2. Check firewall allows port 80
sudo ufw status

# 3. Verify DNS points to correct IP
dig ischedwise.online
nslookup ischedwise.online

# 4. Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# 5. Try obtaining certificate with verbose output
sudo certbot --nginx -d ischedwise.online -d www.ischedwise.online -v
```

**If Certbot fails with "Domain not pointing to server":**
- DNS records not propagated yet - wait 5-60 minutes
- Check DNS: https://dnschecker.org/
- Verify A records point to your Elastic IP

**If you need to retry:**
```bash
# Delete failed attempt
sudo certbot delete --cert-name ischedwise.online

# Try again with just main domain first
sudo certbot --nginx -d ischedwise.online

# Then add www subdomain later
sudo certbot --nginx -d ischedwise.online -d www.ischedwise.online --expand
```

**Certificate Renewal (automatic):**
```bash
# Certbot installs a cron job to auto-renew certificates
# Certificates are valid for 90 days and auto-renew at 60 days

# Manually check renewal
sudo certbot renew --dry-run

# Force renew (if needed)
sudo certbot renew --force-renewal
```

---

## Post-Deployment

### Step 1: Create Admin User
```bash
# SSH into server
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Navigate to project
cd /var/www/ischedwise
source venv/bin/activate

# Open Python shell
python3

# Create admin user
from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # Change default admin password
    admin = User.query.filter_by(email='admin@ischedwise.com').first()
    if admin:
        admin.password_hash = generate_password_hash('NEW_SECURE_PASSWORD')
        db.session.commit()
        print("Admin password updated!")
    
    # Or create new admin
    new_admin = User(
        name='Your Name',
        email='youremail@school.edu',
        password_hash=generate_password_hash('STRONG_PASSWORD'),
        role='Admin',
        is_active=True
    )
    db.session.add(new_admin)
    db.session.commit()
    print("New admin created!")

exit()
```

### Step 2: Configure Email (Password Reset)
Edit `.env`:
```bash
nano /var/www/ischedwise/.env
```

For Gmail (requires App Password):
1. Enable 2FA on Gmail account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Update `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=16-digit-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

Restart application:
```bash
sudo systemctl restart ischedwise
```

### Step 3: Remove Sample Data (Production)
```bash
# Connect to RDS database
mysql -h ischedwise-db.xxxxx.us-east-1.rds.amazonaws.com -u admin -p

# Delete sample data
USE ischedwise_db;
DELETE FROM schedules WHERE id > 0;
DELETE FROM exam_schedules WHERE id > 0;
DELETE FROM faculty WHERE id > 0;
-- Keep admin users or create new ones
-- DELETE FROM users WHERE id > 2;

exit;
```

### Step 4: Set Up Automated Backups
```bash
# Create backup script
sudo nano /usr/local/bin/backup-ischedwise.sh
```

Add:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/backups"
mkdir -p $BACKUP_DIR

# Backup database
mysqldump -h ischedwise-db.xxxxx.us-east-1.rds.amazonaws.com \
  -u admin -pYOUR_DB_PASSWORD \
  ischedwise_db > $BACKUP_DIR/ischedwise_db_$DATE.sql

# Compress
gzip $BACKUP_DIR/ischedwise_db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make executable:
```bash
sudo chmod +x /usr/local/bin/backup-ischedwise.sh
```

Set up cron job (daily at 2 AM):
```bash
crontab -e

# Add this line:
0 2 * * * /usr/local/bin/backup-ischedwise.sh >> /var/log/ischedwise-backup.log 2>&1
```

---

## Maintenance & Monitoring

### Check Application Logs
```bash
# Application logs
sudo journalctl -u ischedwise -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Restart Services
```bash
# Restart application
sudo systemctl restart ischedwise

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status ischedwise
sudo systemctl status nginx
```

### Update Application Code
```bash
cd /var/www/ischedwise

# Pull latest code (if using Git)
git pull origin main

# Activate venv and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart application
sudo systemctl restart ischedwise
```

### Monitor System Resources
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check running processes
htop

# Install htop if not available
sudo apt install htop
```

### Set Up CloudWatch (AWS Monitoring)
1. Go to **CloudWatch** in AWS Console
2. Click **"Dashboards"** → **"Create dashboard"**
3. Add widgets:
   - EC2 CPU Utilization
   - EC2 Network In/Out
   - RDS CPU Utilization
   - RDS Database Connections
4. Set up alarms:
   - High CPU usage (>80%)
   - Low disk space (<2 GB)
   - High database connections

### Security Best Practices
```bash
# Update system regularly
sudo apt update && sudo apt upgrade -y

# Enable automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Configure firewall (UFW)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Check firewall status
sudo ufw status
```

---

## Troubleshooting

### Application Won't Start
```bash
# Check service status
sudo systemctl status ischedwise

# View recent logs
sudo journalctl -u ischedwise -n 50

# Common issues:
# 1. Database connection - check .env file
# 2. Permission issues - check file ownership
# 3. Port conflicts - check if socket exists
```

### ModuleNotFoundError: No module named 'pymysql'
This error means dependencies were not installed in the virtual environment, or the wrong Python interpreter is being used.

**Solution 1: Force Install into Venv (Fixes 99% of issues)**
Run these commands to force installation into the specific virtual environment:
```bash
cd /var/www/ischedwise
./venv/bin/pip install pymysql
./venv/bin/pip install -r requirements.txt
```

**Solution 2: Verify Installation**
Check if the package is actually installed in the venv:
```bash
./venv/bin/pip list | grep PyMySQL
```
If this returns nothing, the installation failed. Check for error messages.

**Solution 3: Verify the venv Python can import pymysql**
Test if pymysql is accessible to the venv's Python:
```bash
# This should print the version number
./venv/bin/python -c "import pymysql; print(pymysql.__version__)"

# If you get ModuleNotFoundError, pymysql is NOT in your venv
# Force reinstall:
./venv/bin/pip install --force-reinstall pymysql
```

**Solution 4: Use explicit path for running (CRITICAL)**
Always run scripts using the full path to the venv python:
```bash
# Deactivate if venv is activated (to avoid confusion)
deactivate

# Run using the venv's Python directly
cd /var/www/ischedwise
./venv/bin/python run.py
```

**Why this happens:**
- `pip install` might have installed to system Python, not the venv
- Using `python3` instead of the venv's `python` can cause issues
- Virtual environment not activated, or wrong environment activated

### Can't Connect to Database
```bash
# Test from EC2
mysql -h YOUR_RDS_ENDPOINT -u admin -p

# Check security groups:
# - RDS security group allows EC2 security group
# - EC2 can reach RDS (check VPC and subnets)
```

### 502 Bad Gateway (Nginx)
```bash
# Check if Gunicorn is running
sudo systemctl status ischedwise

# Check socket file exists
ls -l /var/www/ischedwise/ischedwise.sock

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### High Memory Usage
```bash
# Reduce Gunicorn workers
sudo nano /etc/systemd/system/ischedwise.service

# Change: --workers 3 to --workers 2

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ischedwise
```

---

## Cost Optimization Tips

1. **Use Free Tier**: First 12 months free for t2.micro EC2 and db.t3.micro RDS
2. **Stop EC2 when not needed**: Stops charges (RDS continues)
3. **Use Reserved Instances**: 30-70% savings if running 24/7
4. **Delete old snapshots**: RDS automated backups count towards storage
5. **Use S3 for static files**: Cheaper than serving from EC2
6. **Set up billing alerts**: Avoid surprise charges
7. **Monitor usage**: Use AWS Cost Explorer

---

## Quick Reference Commands

```bash
# SSH to server
ssh -i "ischedwise-keypair.pem" ubuntu@YOUR_ELASTIC_IP

# Restart application
sudo systemctl restart ischedwise

# View logs
sudo journalctl -u ischedwise -f

# Update code
cd /var/www/ischedwise && git pull && sudo systemctl restart ischedwise

# Database backup
mysqldump -h RDS_ENDPOINT -u admin -p ischedwise_db > backup.sql

# Check system resources
htop
df -h
free -h
```

---

## Next Steps

1. ✅ Test all features thoroughly
2. ✅ Change all default passwords
3. ✅ Set up regular backups
4. ✅ Configure email notifications
5. ✅ Monitor logs and performance
6. ✅ Set up SSL certificate
7. ✅ Configure custom domain
8. ✅ Remove sample data
9. ✅ Create real user accounts
10. ✅ Document custom configurations

---

## Support & Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Flask Deployment**: https://flask.palletsprojects.com/en/latest/deploying/
- **Gunicorn**: https://docs.gunicorn.org/
- **Nginx**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org/docs/

---

**Congratulations! Your iSchedWise V4 application is now live on AWS! 🎉**

For questions or issues, refer to project documentation or AWS support.
