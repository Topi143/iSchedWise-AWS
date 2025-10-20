"""
Direct Test of AI Helper - Verify Gemini API Integration
Run this to test if AI helper is working independently of Flask routes
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

print("=" * 60)
print("Testing AI Helper Direct Integration")
print("=" * 60)

# Test 1: Check API Key
print("\nTest 1: Checking API Key...")
api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    print(f"[OK] API Key found: {api_key[:10]}...{api_key[-5:]}")
    print(f"   Length: {len(api_key)} characters")
else:
    print("[FAIL] API Key NOT found in environment!")
    print("   Make sure GEMINI_API_KEY is set in .env file")
    sys.exit(1)

# Test 2: Import AI Helper
print("\nTest 2: Importing AI Helper...")
try:
    from app.ai_helper import ScheduleAIHelper
    print("[OK] AI Helper module imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import AI Helper: {e}")
    sys.exit(1)

# Test 3: Initialize AI Helper
print("\nTest 3: Initializing AI Helper...")
try:
    ai_helper = ScheduleAIHelper(api_key)
    print("[OK] AI Helper initialized successfully")
except Exception as e:
    print(f"[FAIL] Failed to initialize AI Helper: {e}")
    sys.exit(1)

# Test 4: Test Conflict Analysis
print("\nTest 4: Testing Conflict Analysis...")
print("   Creating sample section conflict scenario...")

requested_schedule = {
    'section_name': 'BSCS 3A',
    'subject_code': 'CS301',
    'course_description': 'Data Structures and Algorithms',
    'day_of_week': 'Monday',
    'start_time': '09:00',
    'end_time': '10:00',
    'room_number': 'Room 101',
    'faculty_name': 'Prof. Smith',
    'schedule_type': 'lecture'
}

available_resources = {
    'time_slots': ['10:00-11:00', '11:00-12:00', '13:00-14:00', '14:00-15:00', '15:00-16:00']
}

existing_schedules = [
    {
        'day_of_week': 'Monday',
        'start_time': '09:00',
        'end_time': '10:00',
        'subject_code': 'CS302',
        'course_description': 'Database Systems',
        'room_number': 'Room 102',
        'faculty_name': 'Prof. Jones',
        'schedule_type': 'lecture'
    }
]

try:
    print("\n   Calling AI to analyze conflict...")
    result = ai_helper.analyze_conflict_and_suggest(
        conflict_type='section',
        requested_schedule=requested_schedule,
        available_resources=available_resources,
        existing_schedules=existing_schedules
    )
    
    if result.get('success'):
        print("\n[OK] AI Analysis Successful!")
        print(f"\nResults:")
        print(f"   Conflict Type: {result['conflict_type']}")
        print(f"\n   AI Analysis:")
        print(f"   {'-' * 56}")
        
        # Print analysis (truncated if too long)
        analysis = result['analysis']
        if len(analysis) > 500:
            print(f"   {analysis[:500]}...")
            print(f"   ... (truncated, total {len(analysis)} characters)")
        else:
            print(f"   {analysis}")
        
        print(f"\n   Suggestions Count: {len(result.get('suggestions', []))}")
        if result.get('suggestions'):
            print(f"\n   Suggestions:")
            for i, suggestion in enumerate(result['suggestions'], 1):
                print(f"      {i}. {suggestion}")
        
        print(f"\n{'=' * 60}")
        print("SUCCESS: All Tests Passed! AI Helper is working correctly.")
        print("=" * 60)
    else:
        print(f"\n[FAIL] AI Analysis Failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print(f"\n   This could mean:")
        print(f"   - Invalid API key")
        print(f"   - API quota exceeded")
        print(f"   - Network connectivity issue")
        print(f"   - Gemini API service issue")
        
except Exception as e:
    print(f"\n[FAIL] Exception during AI analysis: {e}")
    print(f"\n   Full error: {str(e)}")
    import traceback
    print(f"\n   Traceback:")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
