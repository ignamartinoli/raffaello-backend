"""add unique constraint on floor and letter in apartments table

Revision ID: 006
Revises: 005
Create Date: 2025-01-25 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database type for constraint creation
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == "sqlite":
        # SQLite doesn't support ALTER TABLE ADD CONSTRAINT, use batch mode
        with op.batch_alter_table("apartments", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_apartments_floor_letter",
                ["floor", "letter"]
            )
    else:
        # PostgreSQL and other databases support ALTER TABLE ADD CONSTRAINT
        op.create_unique_constraint(
            "uq_apartments_floor_letter",
            "apartments",
            ["floor", "letter"]
        )


def downgrade() -> None:
    # Detect database type for constraint dropping
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == "sqlite":
        # SQLite doesn't support ALTER TABLE DROP CONSTRAINT, use batch mode
        with op.batch_alter_table("apartments", schema=None) as batch_op:
            batch_op.drop_constraint("uq_apartments_floor_letter", type_="unique")
    else:
        # PostgreSQL and other databases support ALTER TABLE DROP CONSTRAINT
        op.drop_constraint("uq_apartments_floor_letter", "apartments", type_="unique")
