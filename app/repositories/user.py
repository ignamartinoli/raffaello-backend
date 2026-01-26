from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models.user import User as UserModel
from app.errors import NotFoundError


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
        raise NotFoundError("User not found")

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
        raise NotFoundError("User not found")

    user.password_reset_token = token
    user.password_reset_expires = expires
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: int,
    email: str | None = None,
    name: str | None = None,
    role_id: int | None = None,
) -> UserModel:
    """Update user fields. Only provided fields will be updated."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")

    if email is not None:
        user.email = email
    if name is not None:
        user.name = name
    if role_id is not None:
        user.role_id = role_id

    db.commit()
    db.refresh(user)
    return user


def get_all_users_paginated(
    db: Session, page: int = 1, page_size: int = 100
) -> tuple[list[UserModel], int]:
    """
    Get all users with pagination, sorted by name for stable pagination.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (list of users, total count)
    """
    query = db.query(UserModel)
    total = query.count()
    skip = (page - 1) * page_size
    users = query.order_by(UserModel.name).offset(skip).limit(page_size).all()
    return users, total
