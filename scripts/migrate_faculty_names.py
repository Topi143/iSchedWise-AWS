"""
One-time migration script: Parse existing faculty `full_name` into `last_name`, `first_name`, `middle_initial`.

Usage:
    1. First, run the ALTER TABLE to add new columns (if not already done via ischedwise_db.sql reimport):
       ALTER TABLE faculty ADD COLUMN last_name VARCHAR(100) NOT NULL DEFAULT '' AFTER id;
       ALTER TABLE faculty ADD COLUMN first_name VARCHAR(100) NOT NULL DEFAULT '' AFTER last_name;
       ALTER TABLE faculty ADD COLUMN middle_initial VARCHAR(5) DEFAULT NULL AFTER first_name;

    2. Then run this script:
       python scripts/migrate_faculty_names.py

    3. After verifying, you can drop the old column:
       ALTER TABLE faculty DROP COLUMN full_name;

Handles these formats:
    - "Lastname, Firstname M."       -> last=Lastname, first=Firstname, mi=M.
    - "Lastname, Firstname"           -> last=Lastname, first=Firstname, mi=None
    - "Lastname, Firstname MI"        -> last=Lastname, first=Firstname, mi=MI
    - "Lastname, First Middle M."     -> last=Lastname, first=First Middle, mi=M.
    - "Firstname Lastname"            -> last=Lastname, first=Firstname, mi=None
    - "Firstname M. Lastname"         -> last=Lastname, first=Firstname, mi=M.
"""

import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db


def parse_faculty_name(full_name):
    """
    Parse a full_name string into (last_name, first_name, middle_initial).
    
    Returns:
        tuple: (last_name, first_name, middle_initial) where middle_initial may be None
    """
    if not full_name or not full_name.strip():
        return ('Unknown', 'Unknown', None)
    
    name = full_name.strip()
    
    # Format 1: "Lastname, Firstname MI" (comma-separated — most common in seed data)
    if ',' in name:
        parts = name.split(',', 1)
        last_name = parts[0].strip()
        rest = parts[1].strip()
        
        if not rest:
            return (last_name, 'Unknown', None)
        
        # Check if the last token looks like a middle initial (1-2 chars, optionally with period)
        tokens = rest.split()
        if len(tokens) >= 2:
            last_token = tokens[-1]
            # Is the last token a middle initial? (e.g., "E.", "B.", "DL", "P.", "Jr")
            if re.match(r'^[A-Z]{1,3}\.?$', last_token, re.IGNORECASE) and len(last_token) <= 4:
                first_name = ' '.join(tokens[:-1])
                middle_initial = last_token
                return (last_name, first_name, middle_initial)
        
        # No middle initial detected
        first_name = rest
        return (last_name, first_name, None)
    
    # Format 2: "Firstname Lastname" or "Firstname M. Lastname" (space-separated)
    tokens = name.split()
    
    if len(tokens) == 1:
        return (tokens[0], 'Unknown', None)
    
    if len(tokens) == 2:
        # "Firstname Lastname"
        return (tokens[1], tokens[0], None)
    
    # 3+ tokens: check if second-to-last looks like middle initial
    # e.g., "Juan M. Cruz" -> last=Cruz, first=Juan, mi=M.
    # e.g., "Juan Miguel P. Dela Merced" -> hard to determine automatically
    
    # Heuristic: if second token has 1-2 chars with optional period, treat as MI
    if len(tokens) == 3 and re.match(r'^[A-Z]{1,2}\.?$', tokens[1], re.IGNORECASE):
        return (tokens[2], tokens[0], tokens[1])
    
    # Default: last word is last name, everything else is first name
    last_name = tokens[-1]
    first_name = ' '.join(tokens[:-1])
    return (last_name, first_name, None)


def migrate():
    """Run the migration."""
    app = create_app()
    
    with app.app_context():
        # Check if old full_name column still exists
        result = db.session.execute(
            db.text("SHOW COLUMNS FROM faculty LIKE 'full_name'")
        ).fetchone()
        
        if not result:
            print("Column 'full_name' does not exist. Migration may have already been completed.")
            print("If you need to migrate, ensure the 'full_name' column exists in the faculty table.")
            return
        
        # Check if new columns exist
        new_cols = db.session.execute(
            db.text("SHOW COLUMNS FROM faculty LIKE 'last_name'")
        ).fetchone()
        
        if not new_cols:
            print("New columns (last_name, first_name, middle_initial) don't exist yet.")
            print("Please run the ALTER TABLE statements first. See script header for instructions.")
            return
        
        # Fetch all faculty
        rows = db.session.execute(
            db.text("SELECT id, full_name, last_name, first_name FROM faculty")
        ).fetchall()
        
        if not rows:
            print("No faculty records found.")
            return
        
        print(f"\nFound {len(rows)} faculty records to process.\n")
        print(f"{'ID':<5} {'Current full_name':<35} {'-> Last':<20} {'First':<20} {'MI':<6} {'Status'}")
        print("-" * 110)
        
        success = 0
        skipped = 0
        errors = []
        
        for row in rows:
            fid = row[0]
            full_name = row[1]
            existing_last = row[2]
            existing_first = row[3]
            
            # Skip if already migrated (last_name and first_name are populated)
            if existing_last and existing_first and existing_last != '' and existing_first != '':
                print(f"{fid:<5} {(full_name or 'N/A'):<35} -> {'(already set)':<20} {'':<20} {'':<6} SKIPPED")
                skipped += 1
                continue
            
            if not full_name:
                print(f"{fid:<5} {'(empty)':<35} -> {'Unknown':<20} {'Unknown':<20} {'N/A':<6} WARNING")
                errors.append(f"ID {fid}: empty full_name")
                continue
            
            last_name, first_name, middle_initial = parse_faculty_name(full_name)
            
            try:
                db.session.execute(
                    db.text("""
                        UPDATE faculty 
                        SET last_name = :last, first_name = :first, middle_initial = :mi 
                        WHERE id = :id
                    """),
                    {'last': last_name, 'first': first_name, 'mi': middle_initial, 'id': fid}
                )
                
                mi_display = middle_initial or 'N/A'
                print(f"{fid:<5} {full_name:<35} -> {last_name:<20} {first_name:<20} {mi_display:<6} OK")
                success += 1
                
            except Exception as e:
                print(f"{fid:<5} {full_name:<35} -> ERROR: {str(e)}")
                errors.append(f"ID {fid} ({full_name}): {str(e)}")
        
        db.session.commit()
        
        print(f"\n{'=' * 110}")
        print(f"Migration complete: {success} updated, {skipped} skipped, {len(errors)} errors")
        
        if errors:
            print("\nErrors/Warnings:")
            for err in errors:
                print(f"  - {err}")
        
        print("\nNext steps:")
        print("  1. Verify the data in MySQL: SELECT id, last_name, first_name, middle_initial FROM faculty;")
        print("  2. Once verified, you can drop the old column:")
        print("     ALTER TABLE faculty DROP COLUMN full_name;")


if __name__ == '__main__':
    migrate()
