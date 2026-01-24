from sqlalchemy.orm import Session

from app.repositories.user import (
    get_user_by_email,
    create_user as create_user_repo,
)
from app.db.models.role import Role as RoleModel
from app.schemas.user import UserCreate
from app.core.security import validate_password, get_password_hash
from app.db.models.user import User as UserModel


def create_user(db: Session, user_data: UserCreate) -> UserModel:
    """
    Create a new user with business logic validation.
    
    - Validates email uniqueness
    - Validates password requirements
    - Validates role_id exists (if provided)
    - Defaults to "tenant" role if role_id not provided
    """
    # Check if email already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise ValueError("Email already registered")
    
    # Validate password
    is_valid, error_message = validate_password(user_data.password)
    if not is_valid:
        raise ValueError(error_message)
    
    # Handle role assignment
    if user_data.role_id is None:
        # Default to "tenant" role
        tenant_role = db.query(RoleModel).filter(RoleModel.name == "tenant").first()
        if not tenant_role:
            raise ValueError("Tenant role not found")
        role_id = tenant_role.id
    else:
        # Validate that the provided role_id exists
        role = db.query(RoleModel).filter(RoleModel.id == user_data.role_id).first()
        if not role:
            raise ValueError(f"Role with id {user_data.role_id} not found")
        role_id = user_data.role_id
    
    # Hash password
    password_hash = get_password_hash(user_data.password)
    
    # Use repository for actual database operation (pure data access)
    return create_user_repo(
        db,
        email=user_data.email,
        password_hash=password_hash,
        role_id=role_id,
    )
