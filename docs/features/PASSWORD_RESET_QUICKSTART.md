# 🔐 Password Reset Feature - Quick Start Guide

## ✨ What's New?

A complete "Forgot Password" feature that sends password reset links via email!

## 🎬 User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User on Login Page                                          │
│     ↓ Clicks "Forgot password?"                                 │
├─────────────────────────────────────────────────────────────────┤
│  2. Forgot Password Page                                        │
│     • Enter email address                                       │
│     • Click "Send Reset Link"                                   │
│     ↓                                                            │
├─────────────────────────────────────────────────────────────────┤
│  3. Email Sent                                                  │
│     • Success message shown                                     │
│     • User receives email                                       │
│     ↓ User clicks link in email                                 │
├─────────────────────────────────────────────────────────────────┤
│  4. Reset Password Page                                         │
│     • Enter new password                                        │
│     • Password strength indicator shows                         │
│     • Confirm password                                          │
│     • Click "Reset Password"                                    │
│     ↓                                                            │
├─────────────────────────────────────────────────────────────────┤
│  5. Success!                                                    │
│     • Password updated                                          │
│     • Redirected to login                                       │
│     • Can now login with new password                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Setup (2 Minutes)

### Step 1: Configure Email (Gmail)

1. **Get Gmail App Password**:
   - Visit: https://myaccount.google.com/apppasswords
   - Enable 2-Step Verification if not enabled
   - Create app password for "Mail" → "Other (iSchedWise)"
   - Copy the 16-character password

2. **Update `.env` file**:
   ```bash
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-gmail@gmail.com
   MAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx  # Your app password
   MAIL_DEFAULT_SENDER=your-gmail@gmail.com
   ```

### Step 2: Update Test User Email (Optional)

If you want to test with the default accounts:

```sql
-- In phpMyAdmin or MySQL Workbench
UPDATE users SET email = 'your-real-email@gmail.com' WHERE username = 'admin';
UPDATE users SET email = 'your-real-email@gmail.com' WHERE username = 'dean';
```

### Step 3: Test It!

```bash
# Start the app
python run.py

# Open browser: http://localhost:5000/login
# Click "Forgot password?"
# Enter email and submit
# Check your email inbox
# Click the reset link
# Set new password
# Login with new password ✓
```

## 📧 What the Email Looks Like

```
┌─────────────────────────────────────────────────────┐
│  📧 iSchedWise - Password Reset Request              │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Hello Admin User,                                   │
│                                                      │
│  We received a request to reset your password        │
│  for your iSchedWise account.                        │
│                                                      │
│  ┌──────────────────────────────────────┐           │
│  │      🔗 Reset Password               │           │
│  └──────────────────────────────────────┘           │
│                                                      │
│  ⚠️ This link expires in 1 hour                     │
│                                                      │
│  If you didn't request this, ignore this email.     │
│                                                      │
├─────────────────────────────────────────────────────┤
│  © 2025 Norzagaray College                          │
└─────────────────────────────────────────────────────┘
```

## 🎨 UI Features

### Forgot Password Page:
- ✨ Clean, professional design
- 📧 Email validation
- ⚡ Real-time feedback
- 🔙 Back to login link

### Reset Password Page:
- 🔐 Password strength indicator (Weak/Medium/Strong)
- 👁️ Show/hide password toggle
- ✅ Password match validation
- 📋 Clear password requirements
- 💪 Animated feedback

### Email Template:
- 🎨 Professional HTML design
- 🏢 Branded with college logo
- 📱 Mobile responsive
- 🔒 Security warnings included

## 🔒 Security Features

✅ Secure token generation (cryptographically signed)
✅ Tokens expire after 1 hour
✅ No email disclosure (if email doesn't exist, still shows success message)
✅ Password validation on both client and server
✅ CSRF protection on all forms

## 🧪 Testing Checklist

- [ ] Configure email settings in `.env`
- [ ] Start application: `python run.py`
- [ ] Navigate to login page
- [ ] Click "Forgot password?"
- [ ] Enter a test email
- [ ] Check email inbox (including spam folder)
- [ ] Click reset link in email
- [ ] Enter new password (test strength indicator)
- [ ] Confirm new password (test match validation)
- [ ] Submit form
- [ ] Login with new password
- [ ] Verify old password no longer works

## 🐛 Troubleshooting

### Email Not Received?

1. **Check spam folder** 📬
2. **Verify email settings** in `.env`
3. **Check terminal** for error messages
4. **Test SMTP connection**:
   ```python
   from flask_mail import Mail, Message
   from app import create_app
   
   app = create_app()
   with app.app_context():
       mail = Mail(app)
       msg = Message('Test', recipients=['test@example.com'])
       msg.body = 'Test email'
       try:
           mail.send(msg)
           print("Email sent successfully!")
       except Exception as e:
           print(f"Error: {e}")
   ```

### "Invalid or expired reset link"?

1. **Token expired** - Request a new reset link (1 hour limit)
2. **SECRET_KEY changed** - Make sure SECRET_KEY in .env stays the same
3. **User deleted** - User must still exist in database

### Gmail Not Working?

1. **Enable 2-Step Verification** first
2. **Use App Password**, not your regular Gmail password
3. **Allow less secure apps** (not recommended, use app password instead)
4. **Check if Gmail blocked the login attempt**

## 📁 File Changes Summary

```
Modified:
├── requirements.txt          # Added Flask-Mail
├── config/config.py          # Email configuration
├── app/extensions.py         # Mail extension
├── app/__init__.py           # Initialize mail
├── app/models/user.py        # Token methods
├── app/forms.py              # Password reset forms
├── app/routes/auth.py        # Reset routes + email function
└── .env.example              # Email config template

Created:
├── app/templates/forgot_password.html   # Forgot password form
├── app/templates/reset_password.html    # Reset password form
├── docs/features/PASSWORD_RESET_SETUP.md     # Full documentation
└── docs/features/PASSWORD_RESET_SUMMARY.md   # Implementation summary
```

## 🎯 Production Tips

For production deployment:

1. **Use a transactional email service**:
   - SendGrid (100 emails/day free)
   - Mailgun (5,000 emails/month free trial)
   - AWS SES ($0.10 per 1,000 emails)

2. **Configure DNS records**:
   - SPF record
   - DKIM record
   - DMARC policy

3. **Monitor email delivery**:
   - Track bounce rates
   - Monitor spam complaints
   - Set up delivery notifications

4. **Security considerations**:
   - Rate limit password reset requests
   - Log all reset attempts
   - Consider shorter token expiry (30 minutes)
   - Add captcha on forgot password form

## 📚 Additional Resources

- **Full Setup Guide**: `docs/features/PASSWORD_RESET_SETUP.md`
- **Implementation Details**: `docs/features/PASSWORD_RESET_SUMMARY.md`
- **Flask-Mail Docs**: https://pythonhosted.org/Flask-Mail/

---

## ✅ Status: Ready to Use!

The forgot password feature is fully implemented and ready for testing.  
Configure your email settings and give it a try! 🚀

**Need Help?** Check the detailed documentation in `docs/features/PASSWORD_RESET_SETUP.md`
