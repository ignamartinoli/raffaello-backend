"""create charges table

Revision ID: 005
Revises: 004
Create Date: 2025-01-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database type for CHECK constraint syntax
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    # Use database-specific syntax for CHECK constraint
    if dialect_name == "sqlite":
        # SQLite uses strftime for date extraction
        first_of_month_check = "CAST(strftime('%d', period) AS INTEGER) = 1"
    else:
        # PostgreSQL and other databases use EXTRACT
        first_of_month_check = "EXTRACT(DAY FROM period) = 1"
    
    # Create charges table
    op.create_table(
        "charges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("rent", sa.Integer(), nullable=False),
        sa.Column("expenses", sa.Integer(), nullable=False),
        sa.Column("municipal_tax", sa.Integer(), nullable=False),
        sa.Column("provincial_tax", sa.Integer(), nullable=False),
        sa.Column("water_bill", sa.Integer(), nullable=False),
        sa.Column("is_adjusted", sa.Boolean(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        # Unique constraint: cannot have duplicate charge for same contract and period
        # Since period is always the first of the month, this enforces uniqueness per contract+month+year
        sa.UniqueConstraint("contract_id", "period", name="uq_charges_contract_period"),
        # CHECK constraint: ensure period is always the first of the month
        sa.CheckConstraint(
            first_of_month_check,
            name="ck_charges_period_first_of_month"
        ),
        # CHECK constraints: ensure financial fields are non-negative
        sa.CheckConstraint(
            "rent >= 0",
            name="ck_charges_rent_non_negative"
        ),
        sa.CheckConstraint(
            "expenses >= 0",
            name="ck_charges_expenses_non_negative"
        ),
        sa.CheckConstraint(
            "municipal_tax >= 0",
            name="ck_charges_municipal_tax_non_negative"
        ),
        sa.CheckConstraint(
            "provincial_tax >= 0",
            name="ck_charges_provincial_tax_non_negative"
        ),
        sa.CheckConstraint(
            "water_bill >= 0",
            name="ck_charges_water_bill_non_negative"
        ),
    )
    op.create_index("ix_charges_id", "charges", ["id"], unique=False)
    op.create_index("ix_charges_contract_id", "charges", ["contract_id"], unique=False)
    op.create_index("ix_charges_period", "charges", ["period"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_charges_period", table_name="charges")
    op.drop_index("ix_charges_contract_id", table_name="charges")
    op.drop_index("ix_charges_id", table_name="charges")
    op.drop_table("charges")
