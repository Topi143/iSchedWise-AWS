"""
Test unarchiving REAL archived curriculum (ID 1 - BSHM-2024)
"""
from app import create_app
from app.extensions import db
from app.models.curriculum import Curriculum

app = create_app()

with app.app_context():
    print("\n=== TESTING REAL ARCHIVED CURRICULUM ===\n")
    
    # Get curriculum ID 1 (BSHM-2024 which is archived)
    curriculum = Curriculum.query.get(1)
    
    if not curriculum:
        print("❌ Curriculum ID 1 not found!")
    else:
        print(f"Curriculum: {curriculum.curriculum_code}")
        print(f"  is_archived: {curriculum.is_archived} (type: {type(curriculum.is_archived).__name__})")
        print(f"  is_active: {curriculum.is_active} (type: {type(curriculum.is_active).__name__})")
        print(f"  archived_by: {curriculum.archived_by}")
        print(f"  archived_at: {curriculum.archived_at}")
        
        # Check the boolean check
        print(f"\nBoolean check 'if not curriculum.is_archived': {not curriculum.is_archived}")
        print(f"Boolean check 'if curriculum.is_archived': {curriculum.is_archived}")
        
        if not curriculum.is_archived:
            print("\n❌ ERROR: System thinks curriculum is NOT archived!")
            print("This is why the API returns 400 error")
        else:
            print("\n✅ System correctly identifies curriculum as archived")
            print("Attempting to unarchive...")
            
            curriculum.unarchive()
            db.session.commit()
            
            # Verify
            curriculum = Curriculum.query.get(1)
            print(f"\nAfter unarchive:")
            print(f"  is_archived: {curriculum.is_archived}")
            print(f"  is_active: {curriculum.is_active}")
            print(f"  archived_by: {curriculum.archived_by}")
            print(f"  archived_at: {curriculum.archived_at}")
            
            if not curriculum.is_archived and curriculum.is_active:
                print("\n✅✅✅ UNARCHIVE SUCCESSFUL!")
            else:
                print("\n❌ Unarchive failed - flags not set correctly")
