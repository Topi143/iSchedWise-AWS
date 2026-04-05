import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def run_sql_file(filename):
    app = create_app()
    with app.app_context():
        print(f"Executing {filename}...")
        with open(filename, 'r') as f:
            sql_content = f.read()
            
        # Split by semicolon to execute statement by statement
        # This is a simple splitter and might fail on complex SQL with semicolons in strings
        # But for our simple insert script it should be fine.
        statements = sql_content.split(';')
        
        try:
            for statement in statements:
                if statement.strip():
                    db.session.execute(text(statement))
            db.session.commit()
            print("Successfully executed SQL script.")
        except Exception as e:
            db.session.rollback()
            print(f"Error executing SQL script: {e}")

if __name__ == "__main__":
    script_path = os.path.join(os.path.dirname(__file__), 'add_sample_schedule_2025_2026_2nd.sql')
    run_sql_file(script_path)
