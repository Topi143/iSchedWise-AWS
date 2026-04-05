"""
Quick test script to verify password reset setup
Run this to check if all components are properly configured
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_password_reset_setup_check():
    print("=" * 60)
    print("PASSWORD RESET FEATURE - SETUP VERIFICATION")
    print("=" * 60)
    print()
    
    # Test 1: Check if Flask-Mail is installed
    print("✓ Test 1: Checking Flask-Mail installation...")
    try:
        import flask_mail
        print("  ✅ Flask-Mail is installed")
    except ImportError:
        print("  ❌ Flask-Mail is NOT installed")
        print("  → Run: pip install Flask-Mail==0.10.0")
        return False
    
    # Test 2: Check if itsdangerous is available
    print("\n✓ Test 2: Checking itsdangerous (for tokens)...")
    try:
        from itsdangerous import URLSafeTimedSerializer
        print("  ✅ itsdangerous is available")
    except ImportError:
        print("  ❌ itsdangerous is NOT installed")
        return False
    
    # Test 3: Check if extensions are properly configured
    print("\n✓ Test 3: Checking extensions...")
    try:
        from app.extensions import mail
        print("  ✅ Mail extension is imported")
    except ImportError as e:
        print(f"  ❌ Error importing mail extension: {e}")
        return False
    
    # Test 4: Check if User model has token methods
    print("\n✓ Test 4: Checking User model methods...")
    try:
        from app.models import User
        user = User()
        assert hasattr(user, 'generate_reset_token'), "generate_reset_token method missing"
        assert hasattr(User, 'verify_reset_token'), "verify_reset_token method missing"
        print("  ✅ User model has token methods")
    except AssertionError as e:
        print(f"  ❌ {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Test 5: Check if forms are available
    print("\n✓ Test 5: Checking password reset forms...")
    try:
        from app.forms import ForgotPasswordForm, ResetPasswordForm
        print("  ✅ ForgotPasswordForm exists")
        print("  ✅ ResetPasswordForm exists")
    except ImportError as e:
        print(f"  ❌ Error importing forms: {e}")
        return False
    
    # Test 6: Check if routes are registered
    print("\n✓ Test 6: Checking routes...")
    try:
        from app import create_app
        app = create_app()
        
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        
        if '/forgot-password' in routes:
            print("  ✅ /forgot-password route exists")
        else:
            print("  ❌ /forgot-password route NOT found")
            return False
            
        # Check for reset password route with token parameter
        reset_route_found = any('/reset-password/' in route for route in routes)
        if reset_route_found:
            print("  ✅ /reset-password/<token> route exists")
        else:
            print("  ❌ /reset-password/<token> route NOT found")
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking routes: {e}")
        return False
    
    # Test 7: Check if templates exist
    print("\n✓ Test 7: Checking templates...")
    import os
    from pathlib import Path
    
    base_dir = Path(__file__).parent.parent
    templates_dir = base_dir / 'app' / 'templates'
    
    forgot_template = templates_dir / 'forgot_password.html'
    reset_template = templates_dir / 'reset_password.html'
    
    if forgot_template.exists():
        print("  ✅ forgot_password.html exists")
    else:
        print("  ❌ forgot_password.html NOT found")
        return False
        
    if reset_template.exists():
        print("  ✅ reset_password.html exists")
    else:
        print("  ❌ reset_password.html NOT found")
        return False
    
    # Test 8: Check environment variables
    print("\n✓ Test 8: Checking email configuration...")
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MAIL_PASSWORD')
    
    if mail_username:
        print(f"  ✅ MAIL_USERNAME is set: {mail_username}")
    else:
        print("  ⚠️  MAIL_USERNAME is NOT set in .env")
        print("     → You need to configure this before sending emails")
    
    if mail_password:
        print(f"  ✅ MAIL_PASSWORD is set: {'*' * len(mail_password)}")
    else:
        print("  ⚠️  MAIL_PASSWORD is NOT set in .env")
        print("     → You need to configure this before sending emails")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if not mail_username or not mail_password:
        print("\n✅ Password reset feature is INSTALLED")
        print("⚠️  Email configuration REQUIRED before testing")
        print("\nTo configure email:")
        print("1. Copy .env.example to .env")
        print("2. Set MAIL_USERNAME to your Gmail address")
        print("3. Set MAIL_PASSWORD to your Gmail App Password")
        print("4. Get App Password: https://myaccount.google.com/apppasswords")
        print("\nSee docs/features/PASSWORD_RESET_QUICKSTART.md for details")
    else:
        print("\n✅✅✅ PASSWORD RESET FEATURE IS READY TO TEST! ✅✅✅")
        print("\nNext steps:")
        print("1. Start the app: python run.py")
        print("2. Go to: http://localhost:5000/login")
        print("3. Click 'Forgot password?'")
        print("4. Enter your email and test!")
    
    print("\n" + "=" * 60)
    return True


def test_password_reset_setup():
    assert run_password_reset_setup_check() is True


if __name__ == '__main__':
    try:
        run_password_reset_setup_check()
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
