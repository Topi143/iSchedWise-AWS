"""
Test to verify subject template display properties
"""
from app import create_app
from app.models import Subject, SubjectTemplate, Semester

app = create_app()

with app.app_context():
    print(f"\n{'='*60}")
    print(f"SUBJECT DISPLAY TEST")
    print(f"{'='*60}\n")
    
    # Get first 5 subjects
    subjects = Subject.query.limit(10).all()
    
    if not subjects:
        print("⚠️  No subjects found! Add subjects first.")
    else:
        print(f"Found {len(subjects)} subjects:\n")
        
        for i, subject in enumerate(subjects, 1):
            print(f"{i}. Subject ID: {subject.id}")
            print(f"   Template ID: {subject.subject_template_id}")
            print(f"   Is Using Template: {subject.is_using_template}")
            
            # Show raw database values
            print(f"\n   📊 Raw DB Values:")
            print(f"   - subject_code: {subject.subject_code}")
            print(f"   - course_description: {subject.course_description}")
            print(f"   - lec_units: {subject.lec_units}")
            print(f"   - lab_units: {subject.lab_units}")
            
            # Show effective properties
            print(f"\n   ✅ Effective Properties (What should display):")
            print(f"   - effective_subject_code: {subject.effective_subject_code}")
            print(f"   - effective_course_description: {subject.effective_course_description}")
            print(f"   - effective_lec_units: {subject.effective_lec_units}")
            print(f"   - effective_lab_units: {subject.effective_lab_units}")
            print(f"   - total_units: {subject.total_units}")
            print(f"   - prerequisite: {subject.prerequisite or 'None'}")
            
            if subject.is_using_template and subject.template:
                print(f"\n   📋 Template: {subject.template.subject_code}")
                print(f"   - {subject.template.course_description}")
                print(f"   - {subject.template.lec_units} Lec + {subject.template.lab_units} Lab")
            
            print(f"\n{'-'*60}\n")
    
    print(f"{'='*60}")
    print(f"✅ Test complete!")
    print(f"{'='*60}\n")
