"""
Test script to verify activity logging displays correctly
"""
from app import create_app, db
from app.models.activity_log import UserActivityLog
from app.models.user import User
import json

app = create_app()

with app.app_context():
    # Test 1: Check existing logs with [object Object] issue
    print("=" * 60)
    print("TEST 1: Checking existing activity logs")
    print("=" * 60)
    
    logs = UserActivityLog.query.order_by(UserActivityLog.created_at.desc()).limit(10).all()
    
    for log in logs:
        print(f"\nLog ID: {log.id}")
        print(f"Action: {log.action}")
        print(f"Entity: {log.entity_type} - {log.entity_name}")
        print(f"Details (raw): {repr(log.details)}")
        
        # Test to_dict conversion
        log_dict = log.to_dict()
        print(f"Details (to_dict): {log_dict['details']}")
        print(f"Details type: {type(log_dict['details'])}")
        
        # Check if details would show as [object Object]
        if isinstance(log_dict['details'], dict):
            print("⚠️  WARNING: Details is still a dict, will show as [object Object]")
        else:
            print("✓ Details is a string, will display correctly")
    
    # Test 2: Create a new log entry with details
    print("\n" + "=" * 60)
    print("TEST 2: Creating new activity log with details")
    print("=" * 60)
    
    admin = User.query.filter_by(username='admin').first()
    if admin:
        # Test with dictionary details
        test_details = {
            'department': 'Computer Science',
            'year_level': '1st Year',
            'section_count': 5
        }
        
        # Create log (this will format the dict to string)
        from app.utils.activity_logger import log_create
        
        # Temporarily set current_user context
        from flask_login import login_user
        with app.test_request_context():
            login_user(admin)
            
            # This should format details properly
            log = log_create('test_entity', 999, 'TEST-001', test_details)
            db.session.commit()
            
            print(f"\nCreated log ID: {log.id}")
            print(f"Details (raw): {repr(log.details)}")
            
            log_dict = log.to_dict()
            print(f"Details (to_dict): {log_dict['details']}")
            print(f"Details type: {type(log_dict['details'])}")
            
            if isinstance(log_dict['details'], dict):
                print("❌ FAILED: Details is still a dict")
            else:
                print("✓ PASSED: Details is a string")
            
            # Clean up test log
            db.session.delete(log)
            db.session.commit()
            print("\nTest log cleaned up")
    
    # Test 3: Check logs with JSON string details
    print("\n" + "=" * 60)
    print("TEST 3: Logs with JSON string details (from old system)")
    print("=" * 60)
    
    json_logs = UserActivityLog.query.filter(UserActivityLog.details.like('{%')).limit(5).all()
    
    for log in json_logs:
        print(f"\nLog ID: {log.id}")
        print(f"Details (raw): {repr(log.details)}")
        
        log_dict = log.to_dict()
        print(f"Details (to_dict): {log_dict['details']}")
        print(f"Details type: {type(log_dict['details'])}")
        
        if isinstance(log_dict['details'], dict):
            print("⚠️  Details is dict (will show as [object Object])")
        else:
            print("✓ Details is string (will display)")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("If all new logs show 'Details is a string', the fix is working!")
    print("Old logs with JSON format should also be converted to readable strings.")
