from fastapi import APIRouter, Depends, status
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
    user = create_user(db, user_data)
    return User.model_validate(user)
