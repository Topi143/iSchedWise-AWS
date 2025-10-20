"""
Data Migration Script: Convert existing subjects to Subject Template system

This script:
1. Creates SubjectTemplate records from unique subject codes
2. Links existing Subject instances to their templates
3. Converts faculty assignments to template-based assignments
4. Removes duplicates and consolidates assignments

IMPORTANT: Backup your database before running this script!

Usage:
    python migrate_to_templates.py
"""

import sys
import os
from datetime import datetime
from collections import defaultdict

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Subject, SubjectTemplate, FacultySubjectAssignment, Department


def create_subject_templates():
    """
    Create SubjectTemplate records from existing unique subject codes
    """
    print("\n" + "="*80)
    print("STEP 1: Creating Subject Templates from existing subjects")
    print("="*80)
    
    # Group existing subjects by subject_code
    subjects_by_code = defaultdict(list)
    all_subjects = Subject.query.all()
    
    print(f"Found {len(all_subjects)} existing subject instances")
    
    for subject in all_subjects:
        # Use the current subject_code (or effective if already migrated)
        code = subject.subject_code if subject.subject_code else subject.effective_subject_code
        subjects_by_code[code].append(subject)
    
    print(f"Found {len(subjects_by_code)} unique subject codes")
    
    # Create templates for each unique subject code
    templates_created = 0
    templates_existing = 0
    
    for subject_code, subject_list in subjects_by_code.items():
        # Use the first occurrence as the template source
        source = subject_list[0]
        
        # Check if template already exists
        template = SubjectTemplate.query.filter_by(subject_code=subject_code).first()
        
        if not template:
            # Determine department (from curriculum if available)
            department_id = None
            if source.semester and source.semester.year_level and source.semester.year_level.curriculum:
                department_id = source.semester.year_level.curriculum.department_id
            
            # Get values from source
            lec_units = float(source.lec_units) if source.lec_units is not None else 0.0
            lab_units = float(source.lab_units) if source.lab_units is not None else 0.0
            
            template = SubjectTemplate(
                subject_code=subject_code,
                course_description=source.course_description or f"Course: {subject_code}",
                lec_units=lec_units,
                lab_units=lab_units,
                department_id=department_id,
                is_active=True
            )
            db.session.add(template)
            db.session.flush()  # Get the ID
            templates_created += 1
            
            print(f"  ✓ Created template: {template.subject_code} ({len(subject_list)} instances)")
        else:
            templates_existing += 1
            print(f"  ✓ Template exists: {template.subject_code}")
        
        # Link all subjects with this code to the template
        for subject in subject_list:
            if subject.subject_template_id != template.id:
                subject.subject_template_id = template.id
                # Clear individual fields to use template values (optional - comment out to preserve overrides)
                # subject.subject_code = None
                # subject.course_description = None
                # subject.lec_units = None
                # subject.lab_units = None
    
    db.session.commit()
    
    print(f"\n✓ Created {templates_created} new templates")
    print(f"✓ Found {templates_existing} existing templates")
    print(f"✓ Linked {len(all_subjects)} subject instances to templates")
    
    return templates_created, templates_existing


def migrate_faculty_assignments():
    """
    Convert existing faculty-subject assignments to template-based
    """
    print("\n" + "="*80)
    print("STEP 2: Converting Faculty Assignments to Template-based")
    print("="*80)
    
    assignments = FacultySubjectAssignment.query.all()
    print(f"Found {len(assignments)} existing faculty assignments")
    
    converted = 0
    deleted = 0
    skipped = 0
    
    # Group assignments by faculty and template
    faculty_template_map = defaultdict(list)
    
    for assignment in assignments:
        # Skip if already template-based
        if assignment.assignment_type == 'template':
            skipped += 1
            continue
        
        # Get template ID from subject
        if assignment.subject and assignment.subject.subject_template_id:
            template_id = assignment.subject.subject_template_id
            faculty_id = assignment.faculty_id
            
            faculty_template_map[(faculty_id, template_id)].append(assignment)
    
    print(f"Found {len(faculty_template_map)} unique faculty-template combinations")
    
    # Convert to template assignments
    for (faculty_id, template_id), assignment_list in faculty_template_map.items():
        # Keep the first assignment and convert it to template
        first_assignment = assignment_list[0]
        first_assignment.subject_template_id = template_id
        first_assignment.subject_id = None
        first_assignment.assignment_type = 'template'
        converted += 1
        
        template = SubjectTemplate.query.get(template_id)
        faculty_name = first_assignment.faculty.full_name if first_assignment.faculty else "Unknown"
        print(f"  ✓ {faculty_name} → {template.subject_code if template else 'Unknown'} (consolidated {len(assignment_list)} assignments)")
        
        # Delete duplicate assignments
        for duplicate in assignment_list[1:]:
            db.session.delete(duplicate)
            deleted += 1
    
    db.session.commit()
    
    print(f"\n✓ Converted {converted} assignments to template-based")
    print(f"✓ Deleted {deleted} duplicate assignments")
    print(f"✓ Skipped {skipped} already template-based assignments")
    
    return converted, deleted


def verify_migration():
    """
    Verify the migration was successful
    """
    print("\n" + "="*80)
    print("STEP 3: Verifying Migration")
    print("="*80)
    
    # Count templates
    template_count = SubjectTemplate.query.count()
    print(f"✓ Total Subject Templates: {template_count}")
    
    # Count subjects linked to templates
    subjects_with_template = Subject.query.filter(Subject.subject_template_id.isnot(None)).count()
    subjects_without_template = Subject.query.filter(Subject.subject_template_id.is_(None)).count()
    print(f"✓ Subjects linked to templates: {subjects_with_template}")
    
    if subjects_without_template > 0:
        print(f"⚠ Subjects WITHOUT templates: {subjects_without_template}")
    
    # Count template assignments
    template_assignments = FacultySubjectAssignment.query.filter_by(assignment_type='template').count()
    instance_assignments = FacultySubjectAssignment.query.filter_by(assignment_type='instance').count()
    print(f"✓ Template-based faculty assignments: {template_assignments}")
    print(f"✓ Instance-based faculty assignments: {instance_assignments}")
    
    # Show some example templates
    print("\nExample Subject Templates:")
    templates = SubjectTemplate.query.limit(10).all()
    for template in templates:
        instance_count = template.instance_count
        faculty_count = template.assigned_faculty_count
        print(f"  • {template.subject_code}: {instance_count} instances, {faculty_count} faculty assigned")
    
    return True


def main():
    """Main migration function"""
    print("\n" + "="*80)
    print("iSchedWise V4 - Subject Template System Migration")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Confirm before proceeding
    print("\n⚠ WARNING: This will modify your database!")
    print("⚠ Make sure you have backed up your database before proceeding.")
    response = input("\nDo you want to continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    app = create_app()
    
    with app.app_context():
        try:
            # Step 1: Create templates
            templates_created, templates_existing = create_subject_templates()
            
            # Step 2: Migrate faculty assignments
            converted, deleted = migrate_faculty_assignments()
            
            # Step 3: Verify migration
            verify_migration()
            
            print("\n" + "="*80)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*80)
            print(f"\nSummary:")
            print(f"  • Subject Templates Created: {templates_created}")
            print(f"  • Subject Templates Already Existing: {templates_existing}")
            print(f"  • Faculty Assignments Converted: {converted}")
            print(f"  • Duplicate Assignments Removed: {deleted}")
            print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("\nNext steps:")
            print("  1. Test the application thoroughly")
            print("  2. Check faculty assignment page")
            print("  3. Check curriculum management page")
            print("  4. Verify schedules still work correctly")
            
        except Exception as e:
            print(f"\n❌ ERROR during migration: {str(e)}")
            print("Rolling back changes...")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
