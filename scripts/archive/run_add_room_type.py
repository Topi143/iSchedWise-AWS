import os
import sys
import pymysql

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import Config

def run_sql_script():
    """Run the SQL script to add room_type column"""
    print("Adding room_type column to rooms table...")
    
    # Parse database URI
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    # Format: mysql+pymysql://user:password@host/dbname
    if 'mysql+pymysql://' in db_uri:
        parts = db_uri.replace('mysql+pymysql://', '').split('@')
        user_pass = parts[0].split(':')
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        
        host_db = parts[1].split('/')
        host = host_db[0]
        db_name = host_db[1]
        
        try:
            conn = pymysql.connect(
                host=host,
                user=user,
                password=password,
                database=db_name
            )
            cursor = conn.cursor()
            
            # Read SQL file
            with open('scripts/add_room_type_column.sql', 'r') as f:
                sql = f.read()
            
            # Execute SQL
            try:
                cursor.execute(sql)
                conn.commit()
                print("Successfully added room_type column!")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print("Column room_type already exists.")
                else:
                    raise e
            
            conn.close()
            
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)
    else:
        print("Error: Only MySQL is supported for this script.")
        sys.exit(1)

if __name__ == "__main__":
    run_sql_script()
