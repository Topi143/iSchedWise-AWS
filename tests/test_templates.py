"""
Quick test script to verify subject templates functionality
"""
from app import create_app
from app.models import SubjectTemplate, Curriculum, YearLevel, Semester

app = create_app()

with app.app_context():
    # Check subject templates
    templates = SubjectTemplate.query.filter_by(is_active=True).all()
    print(f"\n{'='*60}")
    print(f"SUBJECT TEMPLATES TEST")
    print(f"{'='*60}")
    print(f"\nFound {len(templates)} active subject templates:")
    
    if templates:
        for i, t in enumerate(templates[:10], 1):  # Show first 10
            print(f"  {i}. {t.subject_code}: {t.course_description}")
            print(f"     Units: {t.lec_units} Lec + {t.lab_units} Lab = {t.total_units} Total")
    else:
        print("  ⚠️  No templates found! Run sample_data.sql to populate.")
    
    # Check curricula
    curricula = Curriculum.query.filter_by(is_active=True).all()
    print(f"\n{'='*60}")
    print(f"CURRICULA TEST")
    print(f"{'='*60}")
    print(f"\nFound {len(curricula)} active curricula:")
    
    if curricula:
        for c in curricula:
            print(f"  - {c.curriculum_code}: {c.curriculum_name}")
            year_levels = YearLevel.query.filter_by(curriculum_id=c.id).count()
            print(f"    Year Levels: {year_levels}")
    else:
        print("  ⚠️  No curricula found! Run sample_data.sql to populate.")
    
    print(f"\n{'='*60}")
    print(f"✅ Database connection successful!")
    print(f"{'='*60}\n")
