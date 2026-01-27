"""add check constraint for letter field in apartments table

Revision ID: 007
Revises: 006
Create Date: 2025-01-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database type for CHECK constraint syntax
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Add CHECK constraint to ensure letter is exactly 1 character (not empty)
    # Since the column is already String(1), this ensures it's not empty
    if dialect_name == "sqlite":
        # SQLite uses LENGTH function and requires batch mode for adding constraints
        letter_check = "LENGTH(letter) = 1"
        with op.batch_alter_table("apartments", schema=None) as batch_op:
            batch_op.create_check_constraint(
                "ck_apartments_letter_exactly_one_char", letter_check
            )
    else:
        # PostgreSQL and other databases can use CHAR_LENGTH
        letter_check = "CHAR_LENGTH(letter) = 1"
        op.create_check_constraint(
            "ck_apartments_letter_exactly_one_char", "apartments", letter_check
        )


def downgrade() -> None:
    # Detect database type for constraint dropping
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "sqlite":
        # SQLite doesn't support ALTER TABLE DROP CONSTRAINT, use batch mode
        with op.batch_alter_table("apartments", schema=None) as batch_op:
            batch_op.drop_constraint(
                "ck_apartments_letter_exactly_one_char", type_="check"
            )
    else:
        # PostgreSQL and other databases support ALTER TABLE DROP CONSTRAINT
        op.drop_constraint(
            "ck_apartments_letter_exactly_one_char", "apartments", type_="check"
        )
