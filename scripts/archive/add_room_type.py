"""
Script to add room_type column to rooms table
"""
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Parse database URL or use defaults
db_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:@localhost/ischedwise_db')
# Extract credentials from URL
import re
match = re.match(r'mysql\+pymysql://([^:]*):([^@]*)@([^/]*)/(.+)', db_url)
if match:
    db_user, db_pass, db_host, db_name = match.groups()
else:
    db_user, db_pass, db_host, db_name = 'root', '', 'localhost', 'ischedwise_db'

try:
    conn = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_pass,
        database=db_name
    )
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("SHOW COLUMNS FROM rooms LIKE 'room_type'")
    if cursor.fetchone():
        print("Column 'room_type' already exists!")
    else:
        # Add the column
        cursor.execute("""
            ALTER TABLE rooms 
            ADD COLUMN room_type VARCHAR(50) NOT NULL DEFAULT 'Lecture' 
            AFTER room_number
        """)
        conn.commit()
        print("Column 'room_type' added successfully!")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
