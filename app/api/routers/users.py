from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.services.user import create_user
from app.schemas.user import UserCreate, User

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Create a new user. Only admin users can create users.
    
    If role_id is not provided, the user will be assigned the "tenant" role by default.
    """
    try:
        user = create_user(db, user_data)
    except ValueError as e:
        # Handle validation errors from service (e.g., invalid role_id, email exists, password validation)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return User.model_validate(user)
