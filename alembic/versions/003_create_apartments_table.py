"""create apartments table

Revision ID: 003
Revises: 002
Create Date: 2025-01-24 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create apartments table
    op.create_table(
        "apartments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("letter", sa.String(1), nullable=False),
        sa.Column("is_mine", sa.Boolean(), nullable=False),
        sa.Column("ecogas", sa.Integer(), nullable=True),
        sa.Column("epec_client", sa.Integer(), nullable=True),
        sa.Column("epec_contract", sa.Integer(), nullable=True),
        sa.Column("water", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_apartments_id", "apartments", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_apartments_id", table_name="apartments")
    op.drop_table("apartments")
