import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.repositories.user import (
    get_user_by_email,
    get_user_by_reset_token,
    update_user_password,
    set_password_reset_token,
)
from app.core.security import (
    verify_password,
    create_access_token,
    create_password_reset_token,
    decode_token,
    validate_password,
    get_password_hash,
)
from app.schemas.user import PasswordResetRequest, PasswordReset, Token, User
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    username: str = Form(...),  # OAuth2 uses "username", but we treat it as email
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Login endpoint - returns JWT token.
    Uses form data for OAuth2 compatibility (Swagger UI authorization).
    The 'username' field should contain the user's email address.
    """
    # Treat username as email (OAuth2 standard uses "username" but we use email)
    email = username
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=User.model_validate(user),
    )


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request password reset - sends email with reset token."""
    user = get_user_by_email(db, request.email)
    
    # Don't reveal if user exists or not (security best practice)
    if user:
        # Create reset token
        reset_token = create_password_reset_token(data={"sub": user.id, "email": user.email})
        
        # Store token in database
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        set_password_reset_token(db, user.id, reset_token, expires)
        
        # Send email
        try:
            await send_password_reset_email(user.email, reset_token)
        except ValueError as e:
            # SMTP not configured - log error but don't fail the request
            # Return the same success message to avoid email enumeration attacks
            logger.error(f"Failed to send password reset email: {e}")
    
    # Always return success (don't reveal if user exists or if email sending failed)
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """Reset password using token from email."""
    # Decode token
    payload = decode_token(reset_data.token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    
    # Check token type
    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type",
        )
    
    # Get user
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )
    
    user = get_user_by_reset_token(db, reset_data.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    
    # Validate new password
    is_valid, error_message = validate_password(reset_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )
    
    # Update password (which also clears the reset token)
    password_hash = get_password_hash(reset_data.new_password)
    update_user_password(db, user.id, password_hash)
    
    return {"message": "Password has been reset successfully"}


@router.get("/me", response_model=User)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return User.model_validate(current_user)
