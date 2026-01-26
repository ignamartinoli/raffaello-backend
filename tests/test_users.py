from sqlalchemy.orm import Session

from app.db.models.user import User as UserModel


# ============================================================================
# GET USER BY ID TESTS
# ============================================================================


def test_get_user_by_id_as_admin_success(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test admin can get any user by ID."""
    response = client.get(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tenant_user_dict["id"]
    assert data["email"] == tenant_user_dict["email"]
    assert data["name"] == tenant_user_dict["name"]


def test_get_user_by_id_as_tenant_self_success(
    client, db: Session, tenant_token: str, tenant_user_dict: dict
):
    """Test tenant can get their own user."""
    response = client.get(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tenant_user_dict["id"]
    assert data["email"] == tenant_user_dict["email"]


def test_get_user_by_id_as_tenant_other_user_forbidden(
    client, db: Session, tenant_token: str, admin_user: dict
):
    """Test tenant cannot get another user."""
    response = client.get(
        f"/api/v1/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 400
    assert "You can only access your own user information" in response.json()["detail"]


def test_get_user_by_id_as_accountant_self_success(
    client, db: Session, accountant_token: str, accountant_user_dict: dict
):
    """Test accountant can get their own user."""
    response = client.get(
        f"/api/v1/users/{accountant_user_dict['id']}",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == accountant_user_dict["id"]
    assert data["email"] == accountant_user_dict["email"]


def test_get_user_by_id_as_accountant_other_user_forbidden(
    client, db: Session, accountant_token: str, admin_user: dict
):
    """Test accountant cannot get another user."""
    response = client.get(
        f"/api/v1/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 400
    assert "You can only access your own user information" in response.json()["detail"]


def test_get_user_by_id_not_found(client, db: Session, admin_token: str):
    """Test getting non-existent user returns 404."""
    response = client.get(
        "/api/v1/users/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_get_user_by_id_without_authentication(
    client, db: Session, tenant_user_dict: dict
):
    """Test getting user without authentication fails."""
    response = client.get(f"/api/v1/users/{tenant_user_dict['id']}")
    assert response.status_code == 401


# ============================================================================
# UPDATE USER BY ID TESTS
# ============================================================================


def test_update_user_by_id_as_admin_success(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test admin can update any user (email, name, role)."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={
            "email": "updated@example.com",
            "name": "Updated Name",
            "role_id": 1,  # admin role
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "updated@example.com"
    assert data["name"] == "Updated Name"
    assert data["role"]["id"] == 1


def test_update_user_by_id_as_admin_partial_update(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test admin can update only specific fields."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={"name": "Partially Updated"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Partially Updated"
    # Email should remain unchanged
    assert data["email"] == tenant_user_dict["email"]


def test_update_user_by_id_as_tenant_self_success(
    client, db: Session, tenant_token: str, tenant_user_dict: dict
):
    """Test tenant can update their own user (email, name, NOT role)."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={
            "email": "tenant_updated@example.com",
            "name": "Updated Tenant Name",
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "tenant_updated@example.com"
    assert data["name"] == "Updated Tenant Name"
    # Role should remain unchanged
    assert data["role"]["id"] == tenant_user_dict["role_id"]


def test_update_user_by_id_as_tenant_trying_to_change_role_forbidden(
    client, db: Session, tenant_token: str, tenant_user_dict: dict
):
    """Test tenant cannot modify their role."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={"role_id": 1},  # Trying to become admin
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 400
    assert "You cannot modify your role" in response.json()["detail"]


def test_update_user_by_id_as_tenant_other_user_forbidden(
    client, db: Session, tenant_token: str, admin_user: dict
):
    """Test tenant cannot update another user."""
    response = client.put(
        f"/api/v1/users/{admin_user['id']}",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 400
    assert "You can only update your own user information" in response.json()["detail"]


def test_update_user_by_id_as_accountant_self_success(
    client, db: Session, accountant_token: str, accountant_user_dict: dict
):
    """Test accountant can update their own user (email, name, NOT role)."""
    response = client.put(
        f"/api/v1/users/{accountant_user_dict['id']}",
        json={
            "email": "accountant_updated@example.com",
            "name": "Updated Accountant Name",
        },
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "accountant_updated@example.com"
    assert data["name"] == "Updated Accountant Name"
    # Role should remain unchanged
    assert data["role"]["id"] == accountant_user_dict["role_id"]


def test_update_user_by_id_as_accountant_trying_to_change_role_forbidden(
    client, db: Session, accountant_token: str, accountant_user_dict: dict
):
    """Test accountant cannot modify their role."""
    response = client.put(
        f"/api/v1/users/{accountant_user_dict['id']}",
        json={"role_id": 1},  # Trying to become admin
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 400
    assert "You cannot modify your role" in response.json()["detail"]


def test_update_user_by_id_as_accountant_other_user_forbidden(
    client, db: Session, accountant_token: str, admin_user: dict
):
    """Test accountant cannot update another user."""
    response = client.put(
        f"/api/v1/users/{admin_user['id']}",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 400
    assert "You can only update your own user information" in response.json()["detail"]


def test_update_user_by_id_duplicate_email(
    client, db: Session, admin_token: str, tenant_user_dict: dict, admin_user: dict
):
    """Test updating user with duplicate email fails."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={"email": admin_user["email"]},  # Already exists
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


def test_update_user_by_id_same_email_allowed(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test updating user with same email is allowed (no-op)."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={"email": tenant_user_dict["email"]},  # Same email
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == tenant_user_dict["email"]


def test_update_user_by_id_invalid_role_id(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test updating user with invalid role_id fails."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={"role_id": 999},  # Non-existent role
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_user_by_id_not_found(client, db: Session, admin_token: str):
    """Test updating non-existent user returns 404."""
    response = client.put(
        "/api/v1/users/99999",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_update_user_by_id_without_authentication(
    client, db: Session, tenant_user_dict: dict
):
    """Test updating user without authentication fails."""
    response = client.put(
        f"/api/v1/users/{tenant_user_dict['id']}",
        json={"name": "New Name"},
    )
    assert response.status_code == 401


# ============================================================================
# GET ALL USERS (PAGINATED) TESTS
# ============================================================================


def test_get_all_users_as_admin_success(client, db: Session, admin_token: str):
    """Test admin can get all users with pagination."""
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert data["page"] == 1
    assert data["page_size"] == 100


def test_get_all_users_pagination_page_page_size(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test pagination with page and page_size parameters."""
    # Create a few more users for testing
    from app.core.security import get_password_hash

    for i in range(5):
        user = UserModel(
            email=f"user{i}@example.com",
            name=f"User {i}",
            password_hash=get_password_hash("Password123!"),
            role_id=tenant_user_dict["role_id"],
        )
        db.add(user)
    db.commit()

    # Test with page and page_size
    response = client.get(
        "/api/v1/users?page=2&page_size=3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["page"] == 2
    assert data["page_size"] == 3
    assert data["total"] >= 5  # At least 5 users we just created


def test_get_all_users_sorted_by_name(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test that users are returned sorted by name for stable pagination."""
    from app.core.security import get_password_hash

    # Create users with names that will sort in a specific order
    names = ["Charlie", "Alice", "Bob", "David"]
    for name in names:
        user = UserModel(
            email=f"{name.lower()}@example.com",
            name=name,
            password_hash=get_password_hash("Password123!"),
            role_id=tenant_user_dict["role_id"],
        )
        db.add(user)
    db.commit()

    # Get all users
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Extract names from response (excluding the admin and tenant users that exist)
    user_names = [user["name"] for user in data["items"]]

    # Check that names are sorted alphabetically
    # We need to find our test users in the sorted list
    test_user_names = [name for name in user_names if name in names]
    assert test_user_names == sorted(names), "Users should be sorted by name"


def test_get_all_users_pagination_defaults(client, db: Session, admin_token: str):
    """Test pagination uses default values when not specified."""
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 100


def test_get_all_users_pagination_page_size_max(client, db: Session, admin_token: str):
    """Test pagination respects maximum page_size."""
    response = client.get(
        "/api/v1/users?page_size=1000",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] == 1000


def test_get_all_users_pagination_page_size_exceeds_max(
    client, db: Session, admin_token: str
):
    """Test pagination rejects page_size exceeding maximum."""
    response = client.get(
        "/api/v1/users?page_size=1001",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Validation error


def test_get_all_users_pagination_page_zero(client, db: Session, admin_token: str):
    """Test pagination rejects zero page."""
    response = client.get(
        "/api/v1/users?page=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Validation error


def test_get_all_users_pagination_page_size_zero(client, db: Session, admin_token: str):
    """Test pagination rejects zero page_size."""
    response = client.get(
        "/api/v1/users?page_size=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Validation error


def test_get_all_users_as_tenant_forbidden(client, db: Session, tenant_token: str):
    """Test tenant cannot get all users."""
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_get_all_users_as_accountant_forbidden(
    client, db: Session, accountant_token: str
):
    """Test accountant cannot get all users."""
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_get_all_users_without_authentication(client, db: Session):
    """Test getting all users without authentication fails."""
    response = client.get("/api/v1/users")
    assert response.status_code == 401
