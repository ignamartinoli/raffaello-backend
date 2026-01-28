"""Auth service: login, password reset token creation, validation, and password update."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_token,
    get_password_hash,
    validate_password,
    verify_password,
)
from app.errors import DomainValidationError, UnauthorizedError
from app.repositories.user import (
    get_user_by_email,
    get_user_by_reset_token,
    set_password_reset_token,
    update_user_password,
)
from app.schemas.user import Token, User
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)


def login(db: Session, email: str, password: str) -> Token:
    """
    Authenticate user by email and password, return JWT access token.

    Raises:
        UnauthorizedError: If email not found or password incorrect.
    """
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password")

    access_token = create_access_token(data={"sub": user.id})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=User.model_validate(user),
    )


async def forgot_password(db: Session, email: str) -> dict[str, str]:
    """
    Request password reset: create token, store in DB, send email.

    Always returns the same success message (no user enumeration).
    Logs but does not raise when SMTP is not configured.
    """
    user = get_user_by_email(db, email)
    if user:
        reset_token = create_password_reset_token(
            data={"sub": user.id, "email": user.email}
        )
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        set_password_reset_token(db, user.id, reset_token, expires)
        try:
            await send_password_reset_email(user.email, reset_token)
        except ValueError as e:
            logger.error("Failed to send password reset email: %s", e)

    return {"message": "If the email exists, a password reset link has been sent."}


def reset_password(db: Session, token: str, new_password: str) -> dict[str, str]:
    """
    Reset password using token from email.

    Raises:
        DomainValidationError: If token invalid/expired, wrong type, or password invalid.
    """
    payload = decode_token(token)
    if payload is None:
        raise DomainValidationError("Invalid or expired token")

    if payload.get("type") != "password_reset":
        raise DomainValidationError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise DomainValidationError("Invalid token")

    user = get_user_by_reset_token(db, token)
    if not user:
        raise DomainValidationError("Invalid or expired token")

    is_valid, error_message = validate_password(new_password)
    if not is_valid:
        raise DomainValidationError(error_message)

    password_hash = get_password_hash(new_password)
    update_user_password(db, user.id, password_hash)
    return {"message": "Password has been reset successfully"}
