from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.role import get_all_roles
from app.schemas.role import Role

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[Role])
def get_roles(db: Session = Depends(get_db)):
    roles = get_all_roles(db)
    return roles
