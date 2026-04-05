"""Shared professional email templates for security-related messages."""

from datetime import datetime, timezone
from email.utils import parseaddr
from html import escape


def _current_utc_year():
    """Return current UTC year."""
    return datetime.now(timezone.utc).year


def _coerce_minutes(value, default):
    """Return safe positive integer minutes with fallback default."""
    try:
        minutes = int(value)
    except Exception:
        minutes = default
    return max(1, minutes)


def _minute_label(minutes):
    """Return singular/plural minute label."""
    return "minute" if minutes == 1 else "minutes"


def _format_expiry_window(minutes):
    """Format minutes as human-readable hour/minute window."""
    if minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    return f"{minutes} {_minute_label(minutes)}"


def build_branded_mail_sender(*, default_sender, app_brand_name):
    """Return a Flask-Mail sender tuple with system branding and sender email."""
    safe_brand = (str(app_brand_name).strip() if app_brand_name else "iSchedWise")
    sender_email = ""

    if isinstance(default_sender, (tuple, list)) and len(default_sender) >= 2:
        sender_email = (str(default_sender[1]).strip() if default_sender[1] else "")
    else:
        raw_sender = (str(default_sender).strip() if default_sender else "")
        if raw_sender:
            _display_name, parsed_email = parseaddr(raw_sender)
            sender_email = (parsed_email or "").strip()
            if not sender_email and '@' in raw_sender and ' ' not in raw_sender:
                sender_email = raw_sender

    if not sender_email:
        sender_email = "noreply@ischedwise.com"

    return (safe_brand, sender_email)


def _render_security_shell(
    *,
    preheader,
    headline,
    subheadline,
    greeting_name,
    lead_paragraph,
    content_html,
    institution_name,
    app_brand_name,
):
    """Render a table-based email shell compatible with major clients."""
    safe_preheader = escape(preheader)
    safe_headline = escape(headline)
    safe_subheadline = escape(subheadline)
    safe_greeting_name = escape(greeting_name)
    safe_lead_paragraph = escape(lead_paragraph)
    safe_institution_name = escape(institution_name)
    safe_app_brand_name = escape(app_brand_name)

    return f"""
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{safe_headline}</title>
</head>
<body style="margin:0; padding:0; background-color:#f0f4f8; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing:antialiased;">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0; mso-hide:all;">
        {safe_preheader}
    </div>

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f0f4f8; padding:30px 15px;">
        <tr>
            <td align="center">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px; width:100%; background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 2px 16px rgba(0,0,0,0.06);">
                    <tr>
                        <td style="background-color:#1e3a5f; padding:36px 40px 32px; text-align:center;">
                            <h1 style="margin:0; font-size:24px; font-weight:700; color:#ffffff; letter-spacing:-0.2px;">{safe_headline}</h1>
                            <p style="margin:8px 0 0; font-size:13px; color:rgba(255,255,255,0.8);">{safe_subheadline}</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="height:3px; background:linear-gradient(90deg, #1d4ed8, #2563eb, #60a5fa);"></td>
                    </tr>
                    <tr>
                        <td style="padding:32px 40px 28px;">
                            <p style="margin:0 0 18px; font-size:16px; font-weight:600; color:#111827;">Hello {safe_greeting_name},</p>
                            <p style="margin:0 0 20px; font-size:15px; line-height:1.7; color:#4b5563;">{safe_lead_paragraph}</p>
                            {content_html}
                            <p style="margin:24px 0 0; font-size:13px; color:#6b7280; line-height:1.7;">
                                Regards,<br>
                                <strong style="color:#1e3a5f;">{safe_app_brand_name} Team</strong>
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color:#f8fafc; border-top:1px solid #e2e8f0; padding:20px 40px; text-align:center;">
                            <p style="margin:0 0 4px; font-size:13px; font-weight:600; color:#374151;">{safe_institution_name}</p>
                            <p style="margin:0; font-size:12px; color:#9ca3af;">{safe_app_brand_name}</p>
                            <p style="margin:12px 0 0; font-size:11px; color:#9ca3af; line-height:1.6;">
                                &copy; {_current_utc_year()} {safe_institution_name}. This is an automated message; please do not reply.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def build_sign_in_otp_email_payload(*, full_name, institution_name, app_brand_name, code, expires_minutes):
    """Build subject/text/html payload for login OTP messages."""
    safe_name = (str(full_name).strip() if full_name else "User")
    safe_institution = (str(institution_name).strip() if institution_name else "Norzagaray College")
    safe_brand = (str(app_brand_name).strip() if app_brand_name else "iSchedWise")
    safe_code = str(code).strip()
    minutes = _coerce_minutes(expires_minutes, 10)

    content_html = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 20px;">
        <tr>
            <td align="center" style="background-color:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:18px;">
                <p style="margin:0 0 6px; font-size:12px; font-weight:600; color:#1d4ed8; text-transform:uppercase; letter-spacing:0.4px;">Verification Code</p>
                <p style="margin:0; font-size:34px; letter-spacing:6px; font-weight:700; color:#111827;">{escape(safe_code)}</p>
            </td>
        </tr>
    </table>
    <p style="margin:0 0 12px; font-size:14px; line-height:1.7; color:#4b5563;">This code expires in <strong>{minutes} {_minute_label(minutes)}</strong>.</p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td style="background-color:#f8fafc; border-left:3px solid #1e3a5f; border-radius:0 8px 8px 0; padding:14px;">
                <p style="margin:0; font-size:13px; line-height:1.6; color:#374151;">If you did not try to sign in, you can safely ignore this email.</p>
            </td>
        </tr>
    </table>
    """

    text_body = (
        f"Hello {safe_name},\n\n"
        f"Use this verification code to continue signing in to {safe_brand}:\n\n"
        f"{safe_code}\n\n"
        f"This code expires in {minutes} {_minute_label(minutes)}.\n\n"
        "If you did not try to sign in, you can safely ignore this email.\n\n"
        f"{safe_institution} - {safe_brand}"
    )

    html_body = _render_security_shell(
        preheader=f"Your {safe_brand} sign-in code is {safe_code}. It expires in {minutes} {_minute_label(minutes)}.",
        headline="Sign-In Verification Code",
        subheadline=f"{safe_institution} | {safe_brand}",
        greeting_name=safe_name,
        lead_paragraph=f"Use the verification code below to continue signing in to {safe_brand}.",
        content_html=content_html,
        institution_name=safe_institution,
        app_brand_name=safe_brand,
    )

    return {
        "subject": f"Your sign-in verification code - {safe_institution}",
        "text_body": text_body,
        "html_body": html_body,
    }


def build_profile_otp_email_payload(*, full_name, institution_name, app_brand_name, purpose, code, expires_minutes):
    """Build subject/text/html payload for profile security OTP messages."""
    safe_name = (str(full_name).strip() if full_name else "User")
    safe_institution = (str(institution_name).strip() if institution_name else "Norzagaray College")
    safe_brand = (str(app_brand_name).strip() if app_brand_name else "iSchedWise")
    safe_purpose = (str(purpose).strip() if purpose else "complete this security action")
    safe_code = str(code).strip()
    minutes = _coerce_minutes(expires_minutes, 10)

    content_html = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 20px;">
        <tr>
            <td align="center" style="background-color:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:18px;">
                <p style="margin:0 0 6px; font-size:12px; font-weight:600; color:#1d4ed8; text-transform:uppercase; letter-spacing:0.4px;">Verification Code</p>
                <p style="margin:0; font-size:34px; letter-spacing:6px; font-weight:700; color:#111827;">{escape(safe_code)}</p>
            </td>
        </tr>
    </table>
    <p style="margin:0 0 12px; font-size:14px; line-height:1.7; color:#4b5563;">This code expires in <strong>{minutes} {_minute_label(minutes)}</strong>.</p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td style="background-color:#f8fafc; border-left:3px solid #1e3a5f; border-radius:0 8px 8px 0; padding:14px;">
                <p style="margin:0; font-size:13px; line-height:1.6; color:#374151;">If you did not request this action, you can safely ignore this email.</p>
            </td>
        </tr>
    </table>
    """

    text_body = (
        f"Hello {safe_name},\n\n"
        f"Use this verification code to {safe_purpose}:\n\n"
        f"{safe_code}\n\n"
        f"This code expires in {minutes} {_minute_label(minutes)}.\n\n"
        "If you did not request this action, you can safely ignore this email.\n\n"
        f"{safe_institution} - {safe_brand}"
    )

    html_body = _render_security_shell(
        preheader=f"Your verification code for {safe_brand} is {safe_code}. It expires in {minutes} {_minute_label(minutes)}.",
        headline="Security Verification Code",
        subheadline=f"{safe_institution} | {safe_brand}",
        greeting_name=safe_name,
        lead_paragraph=f"Use the verification code below to {safe_purpose}.",
        content_html=content_html,
        institution_name=safe_institution,
        app_brand_name=safe_brand,
    )

    return {
        "subject": f"Your verification code - {safe_institution}",
        "text_body": text_body,
        "html_body": html_body,
    }


def build_password_reset_email_payload(*, full_name, email, institution_name, app_brand_name, reset_url, expires_minutes=60):
    """Build subject/text/html payload for password reset messages."""
    safe_name = (str(full_name).strip() if full_name else "User")
    safe_email = (str(email).strip() if email else "")
    safe_institution = (str(institution_name).strip() if institution_name else "Norzagaray College")
    safe_brand = (str(app_brand_name).strip() if app_brand_name else "iSchedWise")
    safe_reset_url = str(reset_url).strip()
    minutes = _coerce_minutes(expires_minutes, 60)
    expiry_window = _format_expiry_window(minutes)

    content_html = f"""
    <p style="margin:0 0 18px; font-size:15px; line-height:1.7; color:#4b5563;">We received a password reset request for your account <strong style="color:#1e3a5f;">{escape(safe_email)}</strong>.</p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 20px;">
        <tr>
            <td align="center" style="padding:4px 0 8px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td style="border-radius:8px; background-color:#1e3a5f;">
                            <a href="{escape(safe_reset_url)}" target="_blank" style="display:inline-block; padding:14px 44px; font-size:15px; font-weight:600; color:#ffffff; text-decoration:none; border-radius:8px;">Reset Password</a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    <p style="margin:0 0 14px; font-size:14px; color:#4b5563; line-height:1.7;">This link expires in <strong>{escape(expiry_window)}</strong>.</p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 20px;">
        <tr>
            <td style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px 18px;">
                <p style="margin:0 0 6px; font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Alternative Link</p>
                <p style="margin:0; font-size:13px; word-break:break-all;"><a href="{escape(safe_reset_url)}" style="color:#2563eb; text-decoration:underline;">{escape(safe_reset_url)}</a></p>
            </td>
        </tr>
    </table>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td style="background-color:#f8fafc; border-left:3px solid #1e3a5f; border-radius:0 8px 8px 0; padding:14px;">
                <p style="margin:0 0 8px; font-size:13px; font-weight:700; color:#1e3a5f;">Security Reminder</p>
                <p style="margin:0; font-size:13px; line-height:1.6; color:#374151;">If you did not request a password reset, you can ignore this email. Your current password will remain unchanged.</p>
            </td>
        </tr>
    </table>
    """

    text_body = (
        f"Hello {safe_name},\n\n"
        f"We received a password reset request for your {safe_brand} account ({safe_email}).\n\n"
        f"To reset your password, open this link:\n{safe_reset_url}\n\n"
        f"This link expires in {expiry_window}.\n\n"
        "If you did not request a password reset, you can ignore this email. Your current password will remain unchanged.\n\n"
        f"{safe_institution} - {safe_brand}"
    )

    html_body = _render_security_shell(
        preheader=f"Password reset requested for {safe_brand}. Link expires in {expiry_window}.",
        headline="Password Reset Request",
        subheadline=f"{safe_institution} | {safe_brand}",
        greeting_name=safe_name,
        lead_paragraph="Use the secure button below to create a new password for your account.",
        content_html=content_html,
        institution_name=safe_institution,
        app_brand_name=safe_brand,
    )

    return {
        "subject": f"Password Reset Request - {safe_institution}",
        "text_body": text_body,
        "html_body": html_body,
    }


def build_smtp_test_email_payload(*, full_name, recipient_email, institution_name, app_brand_name, sent_by, sent_at_utc_label):
    """Build subject/text/html payload for SMTP configuration test emails."""
    safe_name = (str(full_name).strip() if full_name else "User")
    safe_email = (str(recipient_email).strip() if recipient_email else "")
    safe_institution = (str(institution_name).strip() if institution_name else "Norzagaray College")
    safe_brand = (str(app_brand_name).strip() if app_brand_name else "iSchedWise")
    safe_sent_by = (str(sent_by).strip() if sent_by else "System Administrator")
    safe_sent_at = (str(sent_at_utc_label).strip() if sent_at_utc_label else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

    content_html = f"""
    <p style="margin:0 0 18px; font-size:15px; line-height:1.7; color:#4b5563;">This confirms your SMTP settings are working correctly for <strong style="color:#1e3a5f;">{escape(safe_brand)}</strong>.</p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 18px;">
        <tr>
            <td style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px 18px;">
                <p style="margin:0 0 8px; font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">Delivery Details</p>
                <p style="margin:0 0 6px; font-size:13px; line-height:1.6; color:#374151;"><strong>Recipient:</strong> {escape(safe_email)}</p>
                <p style="margin:0 0 6px; font-size:13px; line-height:1.6; color:#374151;"><strong>Sent by:</strong> {escape(safe_sent_by)}</p>
                <p style="margin:0; font-size:13px; line-height:1.6; color:#374151;"><strong>Sent at:</strong> {escape(safe_sent_at)}</p>
            </td>
        </tr>
    </table>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td style="background-color:#f8fafc; border-left:3px solid #1e3a5f; border-radius:0 8px 8px 0; padding:14px;">
                <p style="margin:0; font-size:13px; line-height:1.6; color:#374151;">No action is required. You may continue with normal system use.</p>
            </td>
        </tr>
    </table>
    """

    text_body = (
        f"Hello {safe_name},\n\n"
        f"This confirms your SMTP settings are working correctly for {safe_brand}.\n\n"
        f"Recipient: {safe_email}\n"
        f"Sent by: {safe_sent_by}\n"
        f"Sent at: {safe_sent_at}\n\n"
        "No action is required. You may continue with normal system use.\n\n"
        f"{safe_institution} - {safe_brand}"
    )

    html_body = _render_security_shell(
        preheader=f"SMTP test email confirmed for {safe_brand}.",
        headline="SMTP Test Email",
        subheadline=f"{safe_institution} | {safe_brand}",
        greeting_name=safe_name,
        lead_paragraph="Your email server configuration has been verified successfully.",
        content_html=content_html,
        institution_name=safe_institution,
        app_brand_name=safe_brand,
    )

    return {
        "subject": f"SMTP Test Email - {safe_institution}",
        "text_body": text_body,
        "html_body": html_body,
    }
