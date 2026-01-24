import os
import tempfile
from pathlib import Path

# Set environment variables BEFORE any imports that might use settings
# Use a temporary directory for test database to avoid permission issues
_test_db_dir = tempfile.mkdtemp()
_test_db_path = os.path.join(_test_db_dir, "test_raffaello.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long-for-testing"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@test.example.com"
os.environ["FIRST_ADMIN_PASSWORD"] = "AdminTest123!"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.main import app
from app.core.security import create_access_token
from app.db.models.user import User as UserModel
from app.db.models.role import Role as RoleModel


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test and run migrations."""
    # Use a temporary file for SQLite database
    temp_db_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_db_dir, "test.db")
    test_db_url = f"sqlite:///{test_db_path}"

    # Create test engine and session with proper SQLite settings
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=None,  # Don't use connection pooling for SQLite
    )

    # Enable WAL mode to reduce locking issues
    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Run Alembic migrations to set up the database schema and seed data
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Migration failed: {e}")
        raise

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Dispose the engine to close all connections
        test_engine.dispose()
        
        # Clean up - remove test database file and directory
        try:
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
            # Also remove WAL files
            for suffix in ["-wal", "-shm"]:
                wal_path = f"{test_db_path}{suffix}"
                if os.path.exists(wal_path):
                    os.remove(wal_path)
            if os.path.exists(temp_db_dir):
                os.rmdir(temp_db_dir)
        except Exception as e:
            print(f"Cleanup failed: {e}")


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.api.deps import get_db

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db(db_session):
    """Alias for db_session to match test naming conventions."""
    return db_session


@pytest.fixture(scope="function")
def admin_user(db: Session) -> dict:
    """Create an admin user for testing."""
    # The admin user is already created by the migration (002_create_users_table.py)
    # Get it from the database
    from app.repositories.user import get_user_by_email
    from app.core.config import settings
    
    user = get_user_by_email(db, settings.first_admin_email)
    if not user:
        raise RuntimeError("Admin user not found. Check migration 002.")
    
    return {
        "id": user.id,
        "email": user.email,
        "password": settings.first_admin_password,  # Plaintext password from env
        "role_id": user.role_id,
    }


@pytest.fixture(scope="function")
def admin_token(admin_user: dict) -> str:
    """Get JWT token for admin user."""
    token = create_access_token(data={"sub": admin_user["id"]})
    return token


@pytest.fixture(scope="function")
def tenant_user_dict(db: Session) -> dict:
    """Create a tenant user for testing."""
    from app.core.security import get_password_hash
    
    email = "tenant@example.com"
    password = "TenantPass123!"
    
    # Get tenant role
    tenant_role = db.query(RoleModel).filter(RoleModel.name == "tenant").first()
    if not tenant_role:
        raise RuntimeError("Tenant role not found")
    
    # Create user
    user = UserModel(
        email=email,
        password_hash=get_password_hash(password),
        role_id=tenant_role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "password": password,
        "role_id": user.role_id,
    }


@pytest.fixture(scope="function")
def tenant_token(tenant_user_dict: dict) -> str:
    """Get JWT token for tenant user."""
    token = create_access_token(data={"sub": tenant_user_dict["id"]})
    return token
