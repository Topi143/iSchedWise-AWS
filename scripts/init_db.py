"""
Database Initialization Script for iSchedWise V4
This script updates user passwords with proper Werkzeug hashes
"""
import pymysql
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize database and set proper password hashes"""
    
    print("=" * 60)
    print("iSchedWise V4 - Database Initialization")
    print("=" * 60)
    
    try:
        # Connect to MySQL database
        print("\n[1/4] Connecting to MySQL database...")
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='',  # Default XAMPP password (empty)
            database='ischedwise_db',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✓ Connected successfully!")
        
        with connection:
            with connection.cursor() as cursor:
                # Check if users table exists
                print("\n[2/4] Checking database tables...")
                cursor.execute("SHOW TABLES LIKE 'users'")
                result = cursor.fetchone()
                
                if not result:
                    print("✗ Users table not found!")
                    print("\nPlease import database.sql first:")
                    print("1. Open phpMyAdmin (http://localhost/phpmyadmin)")
                    print("2. Create database 'ischedwise_db' if it doesn't exist")
                    print("3. Import the database.sql file")
                    return False
                
                print("✓ Users table exists!")
                
                # Generate password hashes
                print("\n[3/4] Generating secure password hashes...")
                admin_password = generate_password_hash('admin123')
                dean_password = generate_password_hash('dean123')
                print("✓ Password hashes generated!")
                
                # Update admin password
                print("\n[4/4] Updating user passwords...")
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE username = 'admin'",
                    (admin_password,)
                )
                admin_updated = cursor.rowcount
                
                # Update dean password
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE username = 'dean'",
                    (dean_password,)
                )
                dean_updated = cursor.rowcount
                
                # Commit changes
                connection.commit()
                
                print(f"✓ Admin password updated: {admin_updated} row(s)")
                print(f"✓ Dean password updated: {dean_updated} row(s)")
                
                # Verify users
                cursor.execute("SELECT id, username, email, role, full_name FROM users")
                users = cursor.fetchall()
                
                print("\n" + "=" * 60)
                print("Database initialization completed successfully!")
                print("=" * 60)
                print(f"\nTotal users in database: {len(users)}")
                print("\nUser accounts:")
                for user in users:
                    print(f"  • {user['username']} ({user['role']}) - {user['email']}")
                
                print("\n" + "=" * 60)
                print("LOGIN CREDENTIALS:")
                print("=" * 60)
                print("\nAdmin Account:")
                print("  Username: admin")
                print("  Password: admin123")
                print("\nDean Account:")
                print("  Username: dean")
                print("  Password: dean123")
                print("\n" + "=" * 60)
                print("\nYou can now log in to the application!")
                print("Start the Flask app: python app.py")
                print("=" * 60)
                
                return True
                
    except pymysql.err.OperationalError as e:
        print(f"\n✗ Database connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure XAMPP MySQL is running")
        print("2. Check if database 'ischedwise_db' exists")
        print("3. Verify MySQL is accessible on localhost:3306")
        print("4. Import database.sql if you haven't already")
        return False
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    init_database()
