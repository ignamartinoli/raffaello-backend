from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models.user import User as UserModel


def get_user_by_email(db: Session, email: str) -> UserModel | None:
    """Get a user by email."""
    return db.query(UserModel).filter(UserModel.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> UserModel | None:
    """Get a user by ID."""
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_user_by_reset_token(db: Session, token: str) -> UserModel | None:
    """Get a user by password reset token."""
    return (
        db.query(UserModel)
        .filter(
            UserModel.password_reset_token == token,
            UserModel.password_reset_expires > datetime.now(timezone.utc),
        )
        .first()
    )


def create_user(
    db: Session,
    email: str,
    name: str,
    password_hash: str,
    role_id: int,
) -> UserModel:
    """Create a new user in the database. Pure data access - no business logic."""
    db_user = UserModel(
        email=email,
        name=name,
        password_hash=password_hash,
        role_id=role_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_password(db: Session, user_id: int, password_hash: str) -> UserModel:
    """Update a user's password."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("User not found")
    
    user.password_hash = password_hash
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    db.refresh(user)
    return user


def set_password_reset_token(
    db: Session, user_id: int, token: str, expires: datetime
) -> UserModel:
    """Set password reset token for a user."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("User not found")
    
    user.password_reset_token = token
    user.password_reset_expires = expires
    db.commit()
    db.refresh(user)
    return user
