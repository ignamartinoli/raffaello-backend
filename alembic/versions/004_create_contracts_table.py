"""create contracts table

Revision ID: 004
Revises: 003
Create Date: 2025-01-24 23:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database type for CHECK constraint syntax
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    # Use database-specific syntax for CHECK constraint
    if dialect_name == "sqlite":
        # SQLite uses strftime for date extraction
        first_of_month_check = "CAST(strftime('%d', start_date) AS INTEGER) = 1"
    else:
        # PostgreSQL and other databases use EXTRACT
        first_of_month_check = "EXTRACT(DAY FROM start_date) = 1"
    
    # Create contracts table
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("apartment_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("adjustment_months", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["apartment_id"], ["apartments.id"]),
        # Unique constraint: cannot have duplicate contract with same month and apartment
        # Since start_date is always the first of the month, this enforces uniqueness per month+year+apartment
        sa.UniqueConstraint("start_date", "apartment_id", name="uq_contracts_start_date_apartment"),
        # CHECK constraint: ensure start_date is always the first of the month
        sa.CheckConstraint(
            first_of_month_check,
            name="ck_contracts_start_date_first_of_month"
        ),
        # CHECK constraint: ensure adjustment_months is greater than 0 if present
        sa.CheckConstraint(
            "adjustment_months IS NULL OR adjustment_months > 0",
            name="ck_contracts_adjustment_months_positive"
        ),
    )
    op.create_index("ix_contracts_id", "contracts", ["id"], unique=False)
    op.create_index("ix_contracts_user_id", "contracts", ["user_id"], unique=False)
    op.create_index("ix_contracts_apartment_id", "contracts", ["apartment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contracts_apartment_id", table_name="contracts")
    op.drop_index("ix_contracts_user_id", table_name="contracts")
    op.drop_index("ix_contracts_id", table_name="contracts")
    op.drop_table("contracts")
