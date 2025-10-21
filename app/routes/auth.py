"""
Authentication routes (login, logout, password reset)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app.extensions import db, mail
from app.models import User
from app.models.activity_log import UserActivityLog
from app.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    # Always redirect authenticated users to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.username.data)
        ).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username/email or password', 'error')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact the administrator.', 'error')
            return redirect(url_for('auth.login'))
        
        # Log in the user
        login_user(user, remember=form.remember.data)
        
        # Update last login time
        user.last_login = db.func.current_timestamp()
        
        # Log the login action
        UserActivityLog.log_action(
            user_id=user.id,
            action='login',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.full_name,
            details=f'User logged in from {request.remote_addr}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.dashboard'))
    
    response = make_response(render_template('login.html', form=form))
    # Prevent caching of login page
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    # Log the logout action before logging out
    UserActivityLog.log_action(
        user_id=current_user.id,
        action='logout',
        entity_type='user',
        entity_id=current_user.id,
        entity_name=current_user.full_name,
        details=f'User logged out from {request.remote_addr}',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.commit()
    
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password - send reset email"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Generate reset token
            token = user.generate_reset_token()
            
            # Send reset email
            try:
                send_password_reset_email(user, token)
                flash('Password reset instructions have been sent to your email.', 'success')
            except Exception as e:
                flash('An error occurred while sending the email. Please try again later.', 'error')
                print(f"Email error: {str(e)}")
        else:
            # Don't reveal if email exists or not (security best practice)
            flash('Password reset instructions have been sent to your email.', 'success')
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Verify token
    user = User.verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired reset link. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Set new password
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Your password has been reset successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form, token=token)


def send_password_reset_email(user, token):
    """
    Send password reset email to user
    
    Args:
        user: User object
        token: Reset token
    """
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    msg = Message(
        subject='iSchedWise - Password Reset Request',
        recipients=[user.email],
        sender='noreply@ischedwise.com'
    )
    
    # HTML email body
    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #1f2937;
                background-color: #f3f4f6;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                padding: 40px 30px;
                text-align: center;
                color: white;
            }}
            .header h1 {{
                font-size: 32px;
                font-weight: bold;
                margin-bottom: 8px;
                letter-spacing: -0.5px;
            }}
            .header p {{
                font-size: 14px;
                opacity: 0.95;
                font-weight: 500;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .greeting {{
                font-size: 18px;
                font-weight: 600;
                color: #111827;
                margin-bottom: 20px;
            }}
            .message {{
                font-size: 16px;
                color: #4b5563;
                margin-bottom: 30px;
                line-height: 1.7;
            }}
            .button-container {{
                text-align: center;
                margin: 40px 0;
                padding: 30px;
                background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                border-radius: 12px;
                border: 2px solid #93c5fd;
            }}
            .button {{
                display: inline-block;
                padding: 18px 50px;
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                color: white !important;
                text-decoration: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4);
                transition: all 0.3s ease;
                letter-spacing: 0.5px;
            }}
            .button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 12px 24px rgba(37, 99, 235, 0.5);
            }}
            .link-box {{
                background-color: #f9fafb;
                border: 2px dashed #d1d5db;
                border-radius: 8px;
                padding: 15px;
                margin: 25px 0;
                text-align: center;
            }}
            .link-box p {{
                font-size: 13px;
                color: #6b7280;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            .link-box a {{
                color: #2563eb;
                word-break: break-all;
                font-size: 13px;
                text-decoration: underline;
            }}
            .warning {{
                background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                border-left: 5px solid #f59e0b;
                border-radius: 8px;
                padding: 20px;
                margin: 30px 0;
                box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
            }}
            .warning-title {{
                font-size: 16px;
                font-weight: bold;
                color: #92400e;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
            }}
            .warning-icon {{
                font-size: 24px;
                margin-right: 8px;
            }}
            .warning ul {{
                margin: 8px 0 0 0;
                padding-left: 25px;
                color: #78350f;
            }}
            .warning li {{
                margin: 8px 0;
                font-size: 14px;
                font-weight: 500;
            }}
            .help-text {{
                background-color: #f0f9ff;
                border-left: 3px solid #0284c7;
                padding: 15px;
                border-radius: 6px;
                margin: 25px 0;
                font-size: 14px;
                color: #0c4a6e;
            }}
            .signature {{
                margin-top: 35px;
                padding-top: 25px;
                border-top: 2px solid #e5e7eb;
                font-size: 15px;
                color: #4b5563;
            }}
            .signature strong {{
                color: #2563eb;
                font-size: 16px;
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 25px 30px;
                text-align: center;
                border-top: 1px solid #e5e7eb;
            }}
            .footer p {{
                color: #6b7280;
                font-size: 12px;
                margin: 5px 0;
            }}
            .divider {{
                height: 1px;
                background: linear-gradient(90deg, transparent, #d1d5db, transparent);
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>🔐 iSchedWise</h1>
                <p>Intelligent Scheduling System</p>
            </div>
            
            <!-- Content -->
            <div class="content">
                <p class="greeting">Hi {user.full_name},</p>
                
                <p class="message">
                    You requested to reset your password. Click the button below to create a new password for your account:
                </p>
                
                <!-- Button -->
                <div class="button-container">
                    <a href="{reset_url}" class="button">🔒 Reset My Password</a>
                </div>
                
                <!-- Alternative Link -->
                <div class="link-box">
                    <p>Or copy and paste this link into your browser:</p>
                    <a href="{reset_url}">{reset_url}</a>
                </div>
                
                <!-- Warning Box -->
                <div class="warning">
                    <div class="warning-title">
                        <span class="warning-icon">⚠️</span>
                        <span>Important Security Information</span>
                    </div>
                    <ul>
                        <li>This link will expire in <strong>1 hour</strong></li>
                        <li>If you didn't request this, simply ignore this email</li>
                        <li>Never share this link with anyone</li>
                    </ul>
                </div>
                
                <!-- Help Text -->
                <div class="help-text">
                    <strong>💡 Need Help?</strong><br>
                    Contact your system administrator if you didn't request this password reset or have any concerns.
                </div>
                
                <!-- Signature -->
                <div class="signature">
                    Best regards,<br>
                    <strong>The iSchedWise Team</strong>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <p><strong>&copy; 2025 Norzagaray College</strong></p>
                <div class="divider"></div>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text fallback
    msg.body = f"""
    RESET YOUR PASSWORD
    
    Hi {user.full_name},
    
    You requested to reset your password. Click or copy this link to create a new password:
    
    {reset_url}
    
    ⚠️ Important:
    - This link expires in 1 hour
    - Didn't request this? Ignore this email
    
    Need help? Contact your system administrator.
    
    Best regards,
    iSchedWise Team
    
    ---
    © 2025 Norzagaray College. All rights reserved.
    This is an automated email. Please do not reply.
    """
    
    mail.send(msg)
