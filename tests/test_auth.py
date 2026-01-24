from sqlalchemy.orm import Session

from app.db.models.user import User as UserModel
from app.db.models.role import Role as RoleModel
from app.core.security import get_password_hash
from app.repositories.user import get_user_by_email


# ============================================================================
# LOGIN TESTS
# ============================================================================


def test_login_success(client, db: Session, admin_user: dict):
    """Test successful login returns access token and user info."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": admin_user["email"],
            "password": admin_user["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == admin_user["email"]


def test_login_invalid_email(client, db: Session):
    """Test login with non-existent email."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_wrong_password(client, db: Session, admin_user: dict):
    """Test login with wrong password."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": admin_user["email"],
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


# ============================================================================
# USER CREATION TESTS
# ============================================================================


def test_create_user_as_admin_success(client, db: Session, admin_token: str):
    """Test successful user creation by admin."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "NewPassword123!",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "New User"
    assert "password_hash" not in data  # Password hash should not be exposed
    # New user should be assigned "tenant" role by default
    assert data["role_id"] == 2  # tenant role id


def test_create_user_with_specific_role(client, db: Session, admin_token: str):
    """Test user creation with specific role_id."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "accountant@example.com",
            "name": "John Accountant",
            "password": "AccPassword123!",
            "role_id": 3,  # accountant role
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "accountant@example.com"
    assert data["name"] == "John Accountant"
    assert data["role_id"] == 3


def test_create_user_without_authentication(client, db: Session):
    """Test user creation without authentication fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "NewPassword123!",
        },
    )
    assert response.status_code == 401  # Missing authentication credentials


def test_create_user_as_non_admin(client, db: Session, tenant_user_dict: dict, tenant_token: str):
    """Test user creation by non-admin fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "another@example.com",
            "name": "Another User",
            "password": "AnotherPass123!",
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_create_user_email_already_exists(client, db: Session, admin_token: str, admin_user: dict):
    """Test user creation with duplicate email fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": admin_user["email"],  # Already exists
            "name": "Duplicate User",
            "password": "NewPassword123!",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_create_user_invalid_password_too_short(client, db: Session, admin_token: str):
    """Test user creation with password too short fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "Short1!",  # Only 7 chars, needs 8+
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Pydantic validates min_length at request parsing level (422)
    assert response.status_code == 422


def test_create_user_invalid_password_no_uppercase(client, db: Session, admin_token: str):
    """Test user creation with no uppercase letter fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "password123!",  # No uppercase
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "uppercase" in response.json()["detail"]


def test_create_user_invalid_password_no_lowercase(client, db: Session, admin_token: str):
    """Test user creation with no lowercase letter fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "PASSWORD123!",  # No lowercase
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "lowercase" in response.json()["detail"]


def test_create_user_invalid_password_no_number(client, db: Session, admin_token: str):
    """Test user creation with no number fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "Password!",  # No number
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "number" in response.json()["detail"]


def test_create_user_invalid_password_no_symbol(client, db: Session, admin_token: str):
    """Test user creation with no symbol fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "Password123",  # No symbol
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "symbol" in response.json()["detail"]


def test_create_user_invalid_role_id(client, db: Session, admin_token: str):
    """Test user creation with invalid role_id fails."""
    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "NewPassword123!",
            "role_id": 999,  # Non-existent role
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"]


# ============================================================================
# GET CURRENT USER TESTS
# ============================================================================


def test_get_current_user_success(client, db: Session, admin_token: str, admin_user: dict):
    """Test getting current user info with valid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == admin_user["email"]
    assert data["id"] == admin_user["id"]


def test_get_current_user_without_token(client, db: Session):
    """Test getting current user without token fails."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401  # Missing authentication credentials


def test_get_current_user_invalid_token(client, db: Session):
    """Test getting current user with invalid token fails."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


# ============================================================================
# PASSWORD RESET TESTS
# ============================================================================


def test_forgot_password_success(client, db: Session, admin_user: dict):
    """Test password reset request returns generic success even when SMTP not configured."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": admin_user["email"]},
    )
    # Endpoint returns 200 with generic message for security (prevents email enumeration)
    # Even though SMTP is not configured, it catches the error and returns success
    assert response.status_code == 200
    assert "If the email exists" in response.json()["message"]


def test_forgot_password_nonexistent_email(client, db: Session):
    """Test password reset for non-existent email (should not reveal if user exists)."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
    )
    # Returns same generic success message whether user exists or not (security best practice)
    assert response.status_code == 200
    assert "If the email exists" in response.json()["message"]


def test_reset_password_invalid_token(client, db: Session):
    """Test password reset with invalid token fails."""
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "invalid.token.here",
            "new_password": "NewPassword123!",
        },
    )
    assert response.status_code == 400
    assert "Invalid or expired token" in response.json()["detail"]
