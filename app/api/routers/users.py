from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.db.models.user import User as UserModel
from app.services.user import create_user, get_user, update_user, get_all_users, delete_user
from app.schemas.user import UserCreate, User, UserUpdate
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles("admin")),
):
    """
    Create a new user. Only admin users can create users.

    If role_id is not provided, the user will be assigned the "tenant" role by default.
    """
    user = create_user(db, user_data)
    return User.model_validate(user)


@router.get("", response_model=PaginatedResponse[User])
def get_all_users_paginated(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    name: str | None = Query(None, description="Filter users by name (partial match)"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles("admin")),
):
    """
    Get all users with pagination. Only admin users can access this endpoint.

    Optional name filter: filters users by name (case-insensitive partial match).
    """
    users, total = get_all_users(db, page=page, page_size=page_size, name=name)
    return PaginatedResponse(
        items=[User.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=User)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get a user by ID.

    - Admin can get any user
    - Tenant and Accountant can only get themselves
    """
    user = get_user(db, user_id, current_user)
    return User.model_validate(user)


@router.put("/{user_id}", response_model=User)
def update_user_by_id(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Update a user by ID.

    - Admin can update any user (email, name, role), but cannot change their own role
    - Tenant and Accountant can only update themselves (email, name, NOT role)
    - No user can change their own role, regardless of their role
    """
    user = update_user(db, user_id, user_data, current_user)
    return User.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles("admin")),
):
    """
    Delete a user by ID. Only admin users can delete users.

    A user can only be deleted if they have no associated contracts.
    """
    delete_user(db, user_id)
