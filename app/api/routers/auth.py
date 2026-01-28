from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.db.models.user import User as UserModel
from app.schemas.user import PasswordReset, PasswordResetRequest, Token, User
from app.services.auth import forgot_password, login, reset_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login_endpoint(
    username: str = Form(...),  # OAuth2 uses "username", but we treat it as email
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Login endpoint - returns JWT token.
    Uses form data for OAuth2 compatibility (Swagger UI authorization).
    The 'username' field should contain the user's email address.
    """
    return login(db, username, password)


@router.post("/forgot-password")
async def forgot_password_endpoint(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request password reset - sends email with reset token."""
    return await forgot_password(db, request.email)


@router.post("/reset-password")
def reset_password_endpoint(
    reset_data: PasswordReset,
    db: Session = Depends(get_db),
):
    """Reset password using token from email."""
    return reset_password(db, reset_data.token, reset_data.new_password)


@router.get("/me", response_model=User)
def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    """Get current authenticated user information."""
    return User.model_validate(current_user)
