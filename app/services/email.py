import logging
import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_password_reset_email(email: str, reset_token: str) -> None:
    """
    Send password reset email to user.

    Args:
        email: User's email address
        reset_token: JWT token for password reset
    """
    if not settings.resend_api_key or not settings.resend_from_email:
        missing = []
        if not settings.resend_api_key:
            missing.append("RESEND_API_KEY")
        if not settings.resend_from_email:
            missing.append("RESEND_FROM_EMAIL")
        
        logger.warning(
            f"Resend not configured - cannot send password reset email to {email}. "
            f"Missing: {', '.join(missing)}"
        )
        raise ValueError(
            f"Resend is not configured. Missing environment variables: {', '.join(missing)}. "
            f"Please configure RESEND_API_KEY and RESEND_FROM_EMAIL in your environment variables. "
            f"Note: On Railway, set these in the Railway dashboard, not just in .env file."
        )

    # Initialize Resend client
    resend.api_key = settings.resend_api_key

    # Build email content based on FRONTEND_URL configuration
    if settings.frontend_url:
        # Include full reset link
        reset_link = (
            f"{settings.frontend_url.rstrip('/')}/reset-password?token={reset_token}"
        )
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

    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": email,
            "subject": "Password Reset Request",
            "text": text.strip(),
            "html": html.strip(),
        })
    except Exception as e:
        logger.exception(
            "Failed to send password reset email to %s: %s",
            email,
            e,
        )
        raise


async def send_charge_email(
    email: str,
    apartment_floor: int,
    apartment_letter: str,
    period: str,
    rent: int,
    expenses: int,
    municipal_tax: int,
    provincial_tax: int,
    water_bill: int,
    total: int,
) -> None:
    """
    Send charge information email to user.

    Args:
        email: User's email address
        apartment_floor: Apartment floor number
        apartment_letter: Apartment letter
        period: Charge period (formatted as string, e.g., "January 2025")
        rent: Rent amount
        expenses: Expenses amount
        municipal_tax: Municipal tax amount
        provincial_tax: Provincial tax amount
        water_bill: Water bill amount
        total: Total amount (rent + expenses + municipal_tax + provincial_tax + water_bill)
    """
    if not settings.resend_api_key or not settings.resend_from_email:
        missing = []
        if not settings.resend_api_key:
            missing.append("RESEND_API_KEY")
        if not settings.resend_from_email:
            missing.append("RESEND_FROM_EMAIL")
        
        logger.warning(
            f"Resend not configured - cannot send charge email to {email}. "
            f"Missing: {', '.join(missing)}"
        )
        raise ValueError(
            f"Resend is not configured. Missing environment variables: {', '.join(missing)}. "
            f"Please configure RESEND_API_KEY and RESEND_FROM_EMAIL in your environment variables. "
            f"Note: On Railway, set these in the Railway dashboard, not just in .env file."
        )

    # Initialize Resend client
    resend.api_key = settings.resend_api_key

    # Format amounts with thousands separator
    def format_amount(amount: int) -> str:
        return f"{amount:,}"

    text = f"""
Charge Statement

Apartment: {apartment_floor}{apartment_letter}
Period: {period}

Details:
- Rent: {format_amount(rent)}
- Expenses: {format_amount(expenses)}
- Municipal Tax: {format_amount(municipal_tax)}
- Provincial Tax: {format_amount(provincial_tax)}
- Water Bill: {format_amount(water_bill)}

Total: {format_amount(total)}

Please contact us if you have any questions.
    """

    html = f"""
<html>
  <body>
    <h2>Charge Statement</h2>
    <p><strong>Apartment:</strong> {apartment_floor}{apartment_letter}</p>
    <p><strong>Period:</strong> {period}</p>
    
    <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">Rent:</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{format_amount(rent)}</td>
      </tr>
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">Expenses:</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{format_amount(expenses)}</td>
      </tr>
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">Municipal Tax:</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{format_amount(municipal_tax)}</td>
      </tr>
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">Provincial Tax:</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{format_amount(provincial_tax)}</td>
      </tr>
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">Water Bill:</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{format_amount(water_bill)}</td>
      </tr>
      <tr style="font-weight: bold;">
        <td style="padding: 8px; border-top: 2px solid #000;">Total:</td>
        <td style="padding: 8px; border-top: 2px solid #000; text-align: right;">{format_amount(total)}</td>
      </tr>
    </table>
    
    <p>Please contact us if you have any questions.</p>
  </body>
</html>
    """

    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": email,
            "subject": f"Charge Statement - Apartment {apartment_floor}{apartment_letter} - {period}",
            "text": text.strip(),
            "html": html.strip(),
        })
    except Exception as e:
        logger.exception(
            "Failed to send charge email to %s: %s",
            email,
            e,
        )
        raise
