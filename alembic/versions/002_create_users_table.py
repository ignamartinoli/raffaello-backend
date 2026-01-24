"""create users table

Revision ID: 002
Revises: 001
Create Date: 2025-01-22 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("password_reset_token", sa.String(), nullable=True),
        sa.Column("password_reset_expires", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_password_reset_token", "users", ["password_reset_token"], unique=False)

    # Get settings from environment (will be loaded by Alembic env.py)
    from app.core.config import settings

    # Get admin role_id
    connection = op.get_bind()
    admin_role_result = connection.execute(
        sa.text("SELECT id FROM roles WHERE name = 'admin'")
    ).fetchone()
    
    if not admin_role_result:
        raise ValueError("Admin role not found. Make sure migration 001 has been run.")
    
    admin_role_id = admin_role_result[0]

    # Hash the password from settings
    password_hash = pwd_context.hash(settings.first_admin_password)

    # Insert first admin user
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, password_hash, role_id)
            VALUES (:email, :password_hash, :role_id)
            """
        ).bindparams(
            email=settings.first_admin_email,
            password_hash=password_hash,
            role_id=admin_role_id,
        )
    )


def downgrade() -> None:
    op.drop_index("ix_users_password_reset_token", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
