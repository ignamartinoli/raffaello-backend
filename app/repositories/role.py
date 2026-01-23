from sqlalchemy.orm import Session

from app.db.models.role import Role as RoleModel
from app.schemas.role import Role


def get_all_roles(db: Session) -> list[RoleModel]:
    return db.query(RoleModel).all()
