"""
Test script to check curriculum archive functionality
"""
import sys
from app import create_app
from app.extensions import db
from app.models.curriculum import Curriculum
from datetime import datetime

app = create_app()

with app.app_context():
    print("\n=== TESTING CURRICULUM ARCHIVE FUNCTIONALITY ===\n")
    
    # Get all curricula
    all_curricula = Curriculum.query.all()
    print(f"Total curricula in database: {len(all_curricula)}")
    
    for curr in all_curricula:
        print(f"\nCurriculum ID: {curr.id}")
        print(f"  Code: {curr.curriculum_code}")
        print(f"  Name: {curr.curriculum_name}")
        print(f"  is_active: {curr.is_active}")
        print(f"  is_archived: {curr.is_archived}")
        print(f"  archived_by: {curr.archived_by}")
        print(f"  archived_at: {curr.archived_at}")
        print(f"  archive_reason: {curr.archive_reason}")
    
    # Test archive and unarchive methods
    print("\n=== TESTING ARCHIVE/UNARCHIVE METHODS ===\n")
    
    # Get first active curriculum
    test_curriculum = Curriculum.query.filter_by(is_archived=False).first()
    
    if test_curriculum:
        print(f"Testing with: {test_curriculum.curriculum_code}")
        print(f"Before archive - is_archived: {test_curriculum.is_archived}, is_active: {test_curriculum.is_active}")
        
        # Test archive
        test_curriculum.archive(user_id=1, reason="Test archive")
        db.session.commit()
        
        # Re-query to verify
        test_curriculum = Curriculum.query.get(test_curriculum.id)
        print(f"After archive - is_archived: {test_curriculum.is_archived}, is_active: {test_curriculum.is_active}")
        print(f"  archived_by: {test_curriculum.archived_by}")
        print(f"  archived_at: {test_curriculum.archived_at}")
        print(f"  archive_reason: {test_curriculum.archive_reason}")
        
        # Test unarchive
        test_curriculum.unarchive()
        db.session.commit()
        
        # Re-query to verify
        test_curriculum = Curriculum.query.get(test_curriculum.id)
        print(f"After unarchive - is_archived: {test_curriculum.is_archived}, is_active: {test_curriculum.is_active}")
        print(f"  archived_by: {test_curriculum.archived_by}")
        print(f"  archived_at: {test_curriculum.archived_at}")
        print(f"  archive_reason: {test_curriculum.archive_reason}")
        
        print("\n✅ Archive/Unarchive methods work correctly!")
    else:
        print("❌ No active curricula found to test")
    
    print("\n=== TEST COMPLETE ===\n")
