import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_password_reset_email(email: str, reset_token: str) -> None:
    """
    Send password reset email to user.
    
    Args:
        email: User's email address
        reset_token: JWT token for password reset
    """
    if not all([
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        settings.smtp_from_email,
    ]):
        # SMTP not configured - log or raise error
        logger.warning(f"SMTP not configured - cannot send password reset email to {email}")
        raise ValueError("SMTP is not configured. Please configure SMTP settings in .env file.")
    
    # Create email message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Password Reset Request"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    
    # Build email content based on FRONTEND_URL configuration
    if settings.frontend_url:
        # Include full reset link
        reset_link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={reset_token}"
        text = f"""
You requested a password reset for your account.

Please click the following link to reset your password:
{reset_link}

This link will expire in {settings.password_reset_token_expire_minutes} minutes.

If you did not request this, please ignore this email.
        """
        html = f"""
<html>
  <body>
    <p>You requested a password reset for your account.</p>
    <p>Please click the following link to reset your password:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>This link will expire in {settings.password_reset_token_expire_minutes} minutes.</p>
    <p>If you did not request this, please ignore this email.</p>
  </body>
</html>
        """
    else:
        # FRONTEND_URL not configured - just include the token
        text = f"""
You requested a password reset for your account.

Your password reset token is:
{reset_token}

This token will expire in {settings.password_reset_token_expire_minutes} minutes.

Please use this token to reset your password on the password reset page.

If you did not request this, please ignore this email.
        """
        html = f"""
<html>
  <body>
    <p>You requested a password reset for your account.</p>
    <p>Your password reset token is:</p>
    <p><code>{reset_token}</code></p>
    <p>This token will expire in {settings.password_reset_token_expire_minutes} minutes.</p>
    <p>Please use this token to reset your password on the password reset page.</p>
    <p>If you did not request this, please ignore this email.</p>
  </body>
</html>
        """
    
    # Attach parts
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)
    
    # Send email
    send_kwargs = {
        "hostname": settings.smtp_host,
        "port": settings.smtp_port,
        "username": settings.smtp_user,
        "password": settings.smtp_password,
    }
    
    # Handle TLS based on smtp_use_tls configuration
    if settings.smtp_use_tls:
        # Port 587 uses STARTTLS, port 465 uses direct TLS
        if settings.smtp_port == 587:
            send_kwargs["start_tls"] = True
        elif settings.smtp_port == 465:
            send_kwargs["use_tls"] = True
        else:
            # For non-standard ports, default to STARTTLS if TLS is enabled
            send_kwargs["start_tls"] = True
    
    await aiosmtplib.send(message, **send_kwargs)
