# Password Reset Email Setup Guide

## Overview
The forgot password feature has been implemented with email functionality using Flask-Mail. Users can request a password reset link that will be sent to their registered email address.

## Features Implemented

### 1. **Forgot Password Flow**
   - User clicks "Forgot password?" on login page
   - Enters their email address
   - Receives reset link via email (expires in 1 hour)
   - Clicks link to set new password
   - Redirected to login with success message

### 2. **Security Features**
   - Secure token generation using `itsdangerous`
   - Token expires after 1 hour
   - Email not revealed if user doesn't exist (security best practice)
   - Password strength indicator
   - Password confirmation validation

### 3. **Email Template**
   - Professional HTML email with branding
   - Plain text fallback
   - Clear reset button and link
   - Security warnings

## Email Configuration

### Gmail Setup (Recommended for Development)

1. **Enable 2-Factor Authentication** on your Gmail account
   - Go to: https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Create App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select app: Mail
   - Select device: Other (Custom name) - enter "iSchedWise"
   - Click Generate
   - Copy the 16-character password

3. **Update .env File**
   ```bash
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-16-char-app-password
   MAIL_DEFAULT_SENDER=your-email@gmail.com
   ```

### Alternative SMTP Providers

#### Microsoft Outlook/Office 365
```bash
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@outlook.com
MAIL_PASSWORD=your-password
```

#### SendGrid (Production Recommended)
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
```

#### Mailgun
```bash
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-mailgun-username
MAIL_PASSWORD=your-mailgun-password
```

## Testing the Feature

### 1. Configure Email Settings
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your email credentials
```

### 2. Test Password Reset Flow
```bash
# Start the application
python run.py

# Open browser: http://localhost:5000/login
# Click "Forgot password?"
# Enter: dean@ischedwise.com (or admin@ischedwise.com)
# Check your configured email for reset link
# Click the link and set new password
```

### 3. Verify Email Sent
Check the terminal output for email debugging info:
```
Email sent to: user@example.com
Reset token: eyJ0eXAiOiJKV1QiLCJhbGc...
Reset URL: http://localhost:5000/reset-password/eyJ0eXA...
```

## Files Modified/Created

### Modified Files:
1. **requirements.txt** - Added Flask-Mail==0.10.0
2. **config/config.py** - Added email configuration
3. **app/extensions.py** - Added mail extension
4. **app/__init__.py** - Initialize mail with app
5. **app/models/user.py** - Added token generation/verification methods
6. **app/forms.py** - Added ForgotPasswordForm and ResetPasswordForm
7. **app/routes/auth.py** - Added forgot/reset password routes and email sending
8. **.env.example** - Added email configuration template

### New Templates:
1. **app/templates/forgot_password.html** - Forgot password form page
2. **app/templates/reset_password.html** - Reset password form page

## URL Routes

- `GET/POST /forgot-password` - Request password reset
- `GET/POST /reset-password/<token>` - Reset password with token

## Troubleshooting

### Email Not Sending
1. **Check SMTP credentials** - Verify username/password in .env
2. **Check firewall** - Ensure port 587 is not blocked
3. **Gmail App Password** - Use app password, not regular password
4. **Check terminal** - Look for error messages

### "Invalid or expired reset link"
1. **Token expired** - Links expire after 1 hour, request new one
2. **Secret key changed** - SECRET_KEY in .env must remain constant
3. **Database reset** - User must still exist in database

### Email Goes to Spam
1. Use a verified domain for MAIL_DEFAULT_SENDER
2. Configure SPF/DKIM records (production only)
3. Use professional email service (SendGrid, Mailgun)

## Production Considerations

### Security
- ✅ Use strong SECRET_KEY
- ✅ Use environment variables for credentials
- ✅ Enable HTTPS
- ✅ Consider shorter token expiry (30 minutes)
- ✅ Rate limit password reset requests

### Email Delivery
- ✅ Use transactional email service (SendGrid, Mailgun, AWS SES)
- ✅ Configure SPF, DKIM, DMARC records
- ✅ Monitor email delivery rates
- ✅ Set up bounce/complaint handling

### Monitoring
- ✅ Log password reset attempts
- ✅ Track email delivery success/failure
- ✅ Alert on high failure rates
- ✅ Monitor for abuse

## Email Service Recommendations

### Development
- **Gmail** - Free, easy to set up
- **Outlook** - Free, good for testing

### Production
- **SendGrid** - 100 emails/day free, reliable
- **Mailgun** - 5000 emails/month free for 3 months
- **AWS SES** - $0.10 per 1000 emails, highly scalable
- **Postmark** - $15/month for 10,000 emails, excellent deliverability

## Default Test Accounts

Test the password reset with these accounts:

- **Admin**: admin@ischedwise.com / admin123
- **Dean**: dean@ischedwise.com / dean123

**Note**: Make sure these email addresses in the database match actual email addresses you have access to for testing.

## Support

For issues or questions:
1. Check terminal logs for detailed error messages
2. Verify .env configuration
3. Test SMTP connection using Python:
   ```python
   from flask_mail import Mail, Message
   from app import create_app
   
   app = create_app()
   with app.app_context():
       mail = Mail(app)
       msg = Message('Test', recipients=['test@example.com'])
       msg.body = 'Test email'
       mail.send(msg)
   ```

---

**Last Updated**: 2025-10-19
**Feature**: Password Reset with Email
**Status**: ✅ Implemented and Ready for Testing
