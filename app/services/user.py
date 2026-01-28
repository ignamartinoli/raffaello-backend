from sqlalchemy.orm import Session

import app.repositories.user as user_repo
import app.repositories.contract as contract_repo
from app.db.models.role import Role as RoleModel
from app.db.models.user import User as UserModel
from app.errors import DomainValidationError, DuplicateResourceError, NotFoundError
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import validate_password, get_password_hash


def create_user(db: Session, user_data: UserCreate) -> UserModel:
    """
    Create a new user with business logic validation.

    - Validates email uniqueness
    - Validates password requirements
    - Validates role_id exists (if provided)
    - Defaults to "tenant" role if role_id not provided
    """
    # Check if email already exists
    existing_user = user_repo.get_user_by_email(db, user_data.email)
    if existing_user:
        raise DuplicateResourceError("Email already registered")

    # Validate password
    is_valid, error_message = validate_password(user_data.password)
    if not is_valid:
        raise DomainValidationError(error_message)

    # Handle role assignment
    if user_data.role_id is None:
        # Default to "tenant" role
        tenant_role = db.query(RoleModel).filter(RoleModel.name == "tenant").first()
        if not tenant_role:
            raise NotFoundError("Tenant role not found")
        role_id = tenant_role.id
    else:
        # Validate that the provided role_id exists
        role = db.query(RoleModel).filter(RoleModel.id == user_data.role_id).first()
        if not role:
            raise NotFoundError(f"Role with id {user_data.role_id} not found")
        role_id = user_data.role_id

    # Hash password
    password_hash = get_password_hash(user_data.password)

    # Use repository for actual database operation (pure data access)
    return user_repo.create_user(
        db,
        email=user_data.email,
        name=user_data.name,
        password_hash=password_hash,
        role_id=role_id,
    )


def get_user(db: Session, user_id: int, current_user: UserModel) -> UserModel:
    """
    Get a user by ID with authorization checks.

    - Admin can get any user
    - Tenant and Accountant can only get themselves

    Raises:
        NotFoundError: If user doesn't exist
        DomainValidationError: If tenant or accountant tries to access another user
    """
    # Check if user exists
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")

    # Authorization check: tenant and accountant can only access themselves
    if (
        current_user.role.name in ("tenant", "accountant")
        and current_user.id != user_id
    ):
        raise DomainValidationError("You can only access your own user information")

    return user


def update_user(
    db: Session,
    user_id: int,
    user_data: UserUpdate,
    current_user: UserModel,
) -> UserModel:
    """
    Update a user with authorization checks and business logic validation.

    - Admin can update any user (email, name, role), but cannot change their own role
    - Tenant and Accountant can only update themselves (email, name, NOT role)
    - No user can change their own role, regardless of their role

    Raises:
        NotFoundError: If user doesn't exist
        DuplicateResourceError: If email is already taken by another user
        DomainValidationError: If tenant or accountant tries to update another user or modify role,
                              or if any user tries to change their own role
    """
    # Check if user exists
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")

    # Authorization check: tenant and accountant can only update themselves
    if (
        current_user.role.name in ("tenant", "accountant")
        and current_user.id != user_id
    ):
        raise DomainValidationError("You can only update your own user information")

    # Authorization check: tenant and accountant cannot modify role
    if (
        current_user.role.name in ("tenant", "accountant")
        and user_data.role_id is not None
    ):
        raise DomainValidationError("You cannot modify your role")

    # Prevent users from changing their own role (applies to all roles including admin)
    if current_user.id == user_id and user_data.role_id is not None:
        raise DomainValidationError("You cannot change your own role")

    # Validate email uniqueness if email is being updated
    if user_data.email is not None and user_data.email != user.email:
        existing_user = user_repo.get_user_by_email(db, user_data.email)
        if existing_user:
            raise DuplicateResourceError("Email already registered")

    # Validate role_id exists if provided
    if user_data.role_id is not None:
        role = db.query(RoleModel).filter(RoleModel.id == user_data.role_id).first()
        if not role:
            raise NotFoundError(f"Role with id {user_data.role_id} not found")

    # Use repository for actual database operation (pure data access)
    return user_repo.update_user(
        db,
        user_id=user_id,
        email=user_data.email,
        name=user_data.name,
        role_id=user_data.role_id,
    )


def get_all_users(
    db: Session, page: int = 1, page_size: int = 100, name: str | None = None
) -> tuple[list[UserModel], int]:
    """
    Get all users with pagination.

    This is admin-only functionality, so no authorization checks are needed here
    (authorization is handled at the controller level).

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        name: Optional name filter (case-insensitive partial match)

    Returns:
        Tuple of (list of users, total count)
    """
    return user_repo.get_all_users_paginated(
        db, page=page, page_size=page_size, name=name
    )


def delete_user(db: Session, user_id: int) -> None:
    """
    Delete a user with business logic validation.

    - Validates user exists
    - Validates user is not an admin (cannot delete admin users)
    - Validates user has no contracts (cannot delete users with contracts)

    Raises:
        NotFoundError: If user doesn't exist
        DomainValidationError: If user is an admin or has contracts
    """
    # Check if user exists
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("User not found")

    # Validate user is not an admin
    if user.role.name == "admin":
        raise DomainValidationError("Cannot delete user: admin users cannot be deleted")

    # Validate user has no contracts
    contracts = contract_repo.get_contracts_by_user_id(db, user_id)
    if contracts:
        raise DomainValidationError("Cannot delete user: user has associated contracts")

    # Use repository for actual database operation (pure data access)
    user_repo.delete_user(db, user_id)
