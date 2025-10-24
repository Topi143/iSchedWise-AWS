"""
Test script to verify detailed activity logging across all routes.
Checks that all edit operations now track before→after changes.

Run with: python tests/test_detailed_activity_logging.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.activity_log import UserActivityLog
from app.models.user import User

def test_activity_log_details():
    """Test that activity logs have detailed change tracking"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("DETAILED ACTIVITY LOGGING TEST")
        print("=" * 80)
        
        # Get recent activity logs (last 50)
        logs = UserActivityLog.query.order_by(UserActivityLog.created_at.desc()).limit(50).all()
        
        print(f"\n✓ Found {len(logs)} recent activity logs\n")
        
        # Group logs by action type
        action_types = {}
        for log in logs:
            action = log.action
            if action not in action_types:
                action_types[action] = []
            action_types[action].append(log)
        
        # Display summary
        print("Activity Log Summary:")
        print("-" * 80)
        for action, action_logs in sorted(action_types.items()):
            print(f"  {action:20} {len(action_logs):3} logs")
        
        print("\n" + "=" * 80)
        print("EDIT ACTIONS (Should have change details):")
        print("=" * 80)
        
        edit_logs = [log for log in logs if 'edit' in log.action.lower()]
        
        if not edit_logs:
            print("\n⚠️  No edit actions found in recent logs")
            print("   Create some edit actions to test detailed logging")
            return
        
        logs_with_details = 0
        logs_without_details = 0
        
        for log in edit_logs:
            log_dict = log.to_dict()
            user = User.query.get(log.user_id)
            username = user.username if user else "Unknown"
            
            has_details = bool(log_dict.get('details'))
            
            if has_details:
                logs_with_details += 1
                status = "✓"
            else:
                logs_without_details += 1
                status = "✗"
            
            print(f"\n{status} {log.action}")
            print(f"  User: {username}")
            print(f"  Target: {log.entity_type} #{log.entity_id} ({log.entity_name})")
            print(f"  Time: {log.created_at}")
            
            if has_details:
                print(f"  Details: {log_dict['details']}")
            else:
                print(f"  Details: (none)")
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        print(f"  Total edit logs: {len(edit_logs)}")
        print(f"  ✓ With details: {logs_with_details} ({logs_with_details/len(edit_logs)*100:.1f}%)")
        print(f"  ✗ Without details: {logs_without_details} ({logs_without_details/len(edit_logs)*100:.1f}%)")
        
        if logs_without_details > 0:
            print("\n⚠️  Some edit actions are missing details!")
            print("   These operations should track before→after changes:")
            no_details = [log for log in edit_logs if not log.to_dict().get('details')]
            for log in no_details:
                print(f"     - {log.action} on {log.entity_type} (ID: {log.entity_id})")
        else:
            print("\n✓ All edit actions have detailed change tracking!")
        
        print("\n" + "=" * 80)
        print("EXAMPLE DETAILS (from recent logs):")
        print("=" * 80)
        
        detailed_logs = [log for log in logs if log.to_dict().get('details')][:10]
        
        for log in detailed_logs:
            log_dict = log.to_dict()
            user = User.query.get(log.user_id)
            username = user.username if user else "Unknown"
            
            print(f"\n{log.action} - {log.entity_type}")
            print(f"  User: {username}")
            print(f"  Target: {log.entity_name}")
            print(f"  Details: {log_dict['details']}")
        
        print("\n" + "=" * 80)

if __name__ == '__main__':
    test_activity_log_details()
