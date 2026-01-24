from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
import app.repositories.role as role_repo
from app.schemas.role import Role

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[Role])
def get_roles(db: Session = Depends(get_db)):
    roles = role_repo.get_all_roles(db)
    return roles
