"""
Application forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    """Login form for authentication"""
    
    username = StringField('Username or Email', validators=[
        DataRequired(),
        Length(max=254, message='Username/Email must be less than 254 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=30, message='Password must be between 8 and 30 characters')
    ])
    submit = SubmitField('Sign In')


class ForgotPasswordForm(FlaskForm):
    """Forgot password form - request reset link"""
    
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    """Reset password form - set new password"""
    
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, max=30, message='Password must be between 8 and 30 characters')
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')


class TwoFactorVerificationForm(FlaskForm):
    """2FA verification form for email-code login challenge."""

    code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6, message='Verification code must be exactly 6 digits')
    ])
    submit = SubmitField('Verify')


class ResendTwoFactorCodeForm(FlaskForm):
    """Simple CSRF-protected form for OTP resend action."""

    submit = SubmitField('Resend Code')
