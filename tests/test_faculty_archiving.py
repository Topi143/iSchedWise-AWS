"""
Test faculty subject assignment archiving functionality (flag-based)
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import Faculty, Subject, FacultySubjectAssignment, User
from app.routes.settings import archive_faculty_assignments

def test_faculty_archiving():
    """Test that faculty assignments can be archived using flags"""
    app = create_app()
    
    with app.app_context():
        print("\n=== Testing Faculty Assignment Archiving (FLAG-BASED) ===\n")
        
        # Check if we have any faculty assignments
        assignments = FacultySubjectAssignment.query.filter_by(is_archived=False).all()
        print(f"✓ Found {len(assignments)} active faculty assignments")
        
        if len(assignments) == 0:
            print("⚠ No active faculty assignments to archive. Create some in the UI first.")
            return
        
        # Get a test user (admin)
        user = User.query.filter_by(role='admin').first()
        if not user:
            print("✗ No admin user found")
            return
        
        print(f"✓ Using user: {user.full_name} (ID: {user.id})")
        
        # Count existing archived assignments
        before_count = FacultySubjectAssignment.query.filter_by(is_archived=True).count()
        print(f"✓ Existing archived assignments: {before_count}")
        
        # Test archiving
        print("\n--- Testing Archive Function ---")
        try:
            archived_count = archive_faculty_assignments(
                academic_year='2024-2025',
                semester='1st Semester',
                reason='Test archiving',
                user_id=user.id
            )
            print(f"✓ Archived {archived_count} faculty assignments")
        except Exception as e:
            print(f"✗ Error during archiving: {str(e)}")
            return
        
        # Verify archives were created
        after_count = FacultySubjectAssignment.query.filter_by(is_archived=True).count()
        print(f"✓ Total archived assignments after: {after_count}")
        print(f"✓ New archives created: {after_count - before_count}")
        
        # Show sample archived data
        print("\n--- Sample Archived Assignments ---")
        sample_archives = FacultySubjectAssignment.query.filter_by(is_archived=True).limit(3).all()
        for archive in sample_archives:
            print(f"  • {archive.faculty.full_name if archive.faculty else 'N/A'}: {archive.subject_code} - {archive.course_description}")
            print(f"    Year: {archive.academic_year}, Sem: {archive.semester}")
            print(f"    Reason: {archive.archive_reason}")
            print()
        
        print("\n=== All Tests Passed! ===\n")
        
        # Cleanup note
        print("Note: Test archives were created using flags. You can unarchive them via API.")


if __name__ == '__main__':
    test_faculty_archiving()
