"""
Quick test to check if activity logs are being created
"""
from app import create_app
from app.extensions import db
from app.models.activity_log import UserActivityLog
from app.models.user import User

app = create_app()

with app.app_context():
    # Check if there are any activity logs
    log_count = UserActivityLog.query.count()
    print(f"\n📊 Total Activity Logs: {log_count}")
    
    if log_count > 0:
        # Show first 5 logs
        print("\n📝 Recent Activity Logs:")
        recent_logs = UserActivityLog.query.order_by(UserActivityLog.created_at.desc()).limit(5).all()
        for log in recent_logs:
            user = User.query.get(log.user_id)
            print(f"  - {log.action} on {log.entity_type} by {user.full_name if user else 'Unknown'} at {log.created_at}")
    else:
        print("\n⚠️  No activity logs found!")
        print("\n💡 Try performing some actions in the app:")
        print("   - Login/logout")
        print("   - Create/edit/delete schedules")
        print("   - Create/edit departments, buildings, etc.")
        print("\nThese actions will create activity logs.")
    
    # Check users
    users = User.query.all()
    print(f"\n👥 Available Users: {len(users)}")
    for user in users:
        print(f"  - {user.username} ({user.role})")
