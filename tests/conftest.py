import os

# Set test database URL BEFORE any imports that might use settings
os.environ["DATABASE_URL"] = "sqlite:///./test_raffaello.db"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.main import app


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test and run migrations."""
    # Use a file-based SQLite database for tests (Alembic needs persistent connection)
    test_db_path = "./test_raffaello.db"

    # Remove test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # Set test database URL (already set at module level, but ensure it's correct)
    test_db_url = f"sqlite:///{test_db_path}"
    os.environ["DATABASE_URL"] = test_db_url

    # Create test engine and session
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    # Run Alembic migrations to set up the database schema and seed data
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    command.upgrade(alembic_cfg, "head")

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Dispose the engine to close all connections and release file locks
        test_engine.dispose()
        # Clean up - remove test database file
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


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
