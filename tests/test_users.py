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


def test_update_user_by_id_as_admin_trying_to_change_own_role_forbidden(
    client, db: Session, admin_token: str, admin_user: dict, tenant_user_dict: dict
):
    """Test admin cannot change their own role."""
    # Use tenant role ID to try to change to
    tenant_role_id = tenant_user_dict["role_id"]
    
    response = client.put(
        f"/api/v1/users/{admin_user['id']}",
        json={"role_id": tenant_role_id},  # Trying to change own role
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "You cannot change your own role" in response.json()["detail"]


def test_update_user_by_id_as_admin_self_success(
    client, db: Session, admin_token: str, admin_user: dict
):
    """Test admin can update their own user (email, name, but NOT role)."""
    response = client.put(
        f"/api/v1/users/{admin_user['id']}",
        json={
            "email": "admin_updated@example.com",
            "name": "Updated Admin Name",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin_updated@example.com"
    assert data["name"] == "Updated Admin Name"
    # Role should remain unchanged (admin role)
    assert data["role"]["id"] == admin_user["role_id"]


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


def test_get_all_users_filter_by_name(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test filtering users by name works."""
    from app.core.security import get_password_hash

    # Create users with different names (using names without overlapping substrings)
    test_users = [
        {"name": "John Doe", "email": "john@example.com"},
        {"name": "Jane Smith", "email": "jane@example.com"},
        {"name": "Johnny Appleseed", "email": "johnny@example.com"},
        {"name": "Bob Williams", "email": "bob@example.com"},
    ]
    for user_data in test_users:
        user = UserModel(
            email=user_data["email"],
            name=user_data["name"],
            password_hash=get_password_hash("Password123!"),
            role_id=tenant_user_dict["role_id"],
        )
        db.add(user)
    db.commit()

    # Filter by "John" - should match "John Doe" and "Johnny Appleseed"
    response = client.get(
        "/api/v1/users?name=John",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    user_names = [user["name"] for user in data["items"]]
    assert "John Doe" in user_names
    assert "Johnny Appleseed" in user_names
    assert "Jane Smith" not in user_names
    assert "Bob Williams" not in user_names


def test_get_all_users_filter_by_name_case_insensitive(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test filtering users by name is case-insensitive."""
    from app.core.security import get_password_hash

    # Create a user with a specific name
    user = UserModel(
        email="alice@example.com",
        name="Alice Wonderland",
        password_hash=get_password_hash("Password123!"),
        role_id=tenant_user_dict["role_id"],
    )
    db.add(user)
    db.commit()

    # Filter with lowercase - should still match
    response = client.get(
        "/api/v1/users?name=alice",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    user_names = [user["name"] for user in data["items"]]
    assert "Alice Wonderland" in user_names

    # Filter with uppercase - should still match
    response = client.get(
        "/api/v1/users?name=ALICE",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    user_names = [user["name"] for user in data["items"]]
    assert "Alice Wonderland" in user_names


def test_get_all_users_filter_by_name_partial_match(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test filtering users by name supports partial matching."""
    from app.core.security import get_password_hash

    # Create users
    test_users = [
        {"name": "Michael Jackson", "email": "michael@example.com"},
        {"name": "Michael Jordan", "email": "mj@example.com"},
        {"name": "Mike Tyson", "email": "mike@example.com"},
    ]
    for user_data in test_users:
        user = UserModel(
            email=user_data["email"],
            name=user_data["name"],
            password_hash=get_password_hash("Password123!"),
            role_id=tenant_user_dict["role_id"],
        )
        db.add(user)
    db.commit()

    # Filter by "Michael" - should match both "Michael Jackson" and "Michael Jordan"
    response = client.get(
        "/api/v1/users?name=Michael",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    user_names = [user["name"] for user in data["items"]]
    assert "Michael Jackson" in user_names
    assert "Michael Jordan" in user_names
    assert "Mike Tyson" not in user_names


def test_get_all_users_filter_by_name_with_pagination(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test filtering by name works with pagination."""
    from app.core.security import get_password_hash

    # Create multiple users with "Test" in their name
    for i in range(10):
        user = UserModel(
            email=f"test{i}@example.com",
            name=f"Test User {i}",
            password_hash=get_password_hash("Password123!"),
            role_id=tenant_user_dict["role_id"],
        )
        db.add(user)
    db.commit()

    # Filter by "Test" with pagination
    response = client.get(
        "/api/v1/users?name=Test&page=1&page_size=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert data["total"] >= 10  # At least 10 test users
    # All returned users should have "Test" in their name
    for user in data["items"]:
        assert "Test" in user["name"]


def test_get_all_users_filter_by_name_no_matches(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test filtering by name returns empty list when no matches."""
    # Filter by a name that doesn't exist
    response = client.get(
        "/api/v1/users?name=NonexistentUser12345",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_get_all_users_filter_by_name_optional(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test that name filter is optional and doesn't break existing functionality."""
    # Get users without filter
    response_no_filter = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response_no_filter.status_code == 200
    data_no_filter = response_no_filter.json()
    total_no_filter = data_no_filter["total"]
    assert total_no_filter > 0  # Should have some users

    # Get users with other query params but no name filter
    response_with_pagination = client.get(
        "/api/v1/users?page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response_with_pagination.status_code == 200
    data_with_pagination = response_with_pagination.json()
    assert data_with_pagination["total"] == total_no_filter  # Should return same total
    assert len(data_with_pagination["items"]) <= 10


# ============================================================================
# DELETE USER BY ID TESTS
# ============================================================================


def test_delete_user_by_id_as_admin_success(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test admin can delete a user without contracts."""
    # Verify user exists
    response = client.get(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    # Delete the user
    response = client.delete(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Verify user is deleted
    response = client.get(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_delete_user_by_id_as_admin_with_contracts_forbidden(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test admin cannot delete a user with associated contracts."""
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract

    # Create an apartment
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)

    # Create a contract for the user
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_month=1,
        start_year=2025,
    )

    # Try to delete the user
    response = client.delete(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "associated contracts" in response.json()["detail"].lower()

    # Verify user still exists
    response = client.get(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_delete_user_by_id_as_tenant_forbidden(
    client, db: Session, tenant_token: str, tenant_user_dict: dict
):
    """Test tenant cannot delete users."""
    response = client.delete(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_delete_user_by_id_as_accountant_forbidden(
    client, db: Session, accountant_token: str, tenant_user_dict: dict
):
    """Test accountant cannot delete users."""
    response = client.delete(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_delete_user_by_id_not_found(client, db: Session, admin_token: str):
    """Test deleting non-existent user returns 404."""
    response = client.delete(
        "/api/v1/users/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_delete_user_by_id_without_authentication(
    client, db: Session, tenant_user_dict: dict
):
    """Test deleting user without authentication fails."""
    response = client.delete(f"/api/v1/users/{tenant_user_dict['id']}")
    assert response.status_code == 401


def test_delete_user_by_id_admin_can_delete_accountant(
    client, db: Session, admin_token: str, accountant_user_dict: dict
):
    """Test admin can delete an accountant user without contracts."""
    # Delete the accountant user
    response = client.delete(
        f"/api/v1/users/{accountant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Verify user is deleted
    response = client.get(
        f"/api/v1/users/{accountant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_delete_user_by_id_admin_cannot_delete_self(
    client, db: Session, admin_token: str, admin_user: dict
):
    """Test admin cannot delete themselves."""
    # Admin cannot delete themselves (or any admin user)
    response = client.delete(
        f"/api/v1/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "admin users cannot be deleted" in response.json()["detail"].lower()
    
    # Verify user still exists
    response = client.get(
        f"/api/v1/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_delete_user_by_id_multiple_contracts_forbidden(
    client, db: Session, admin_token: str, tenant_user_dict: dict
):
    """Test admin cannot delete a user with multiple contracts."""
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract

    # Create apartments
    apartment1 = create_apartment(db, floor=1, letter="A", is_mine=True)
    apartment2 = create_apartment(db, floor=2, letter="B", is_mine=False)

    # Create multiple contracts for the user
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment1.id,
        start_month=1,
        start_year=2025,
    )
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment2.id,
        start_month=2,
        start_year=2025,
    )

    # Try to delete the user
    response = client.delete(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "associated contracts" in response.json()["detail"].lower()

    # Verify user still exists
    response = client.get(
        f"/api/v1/users/{tenant_user_dict['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_delete_user_by_id_admin_user_forbidden(
    client, db: Session, admin_token: str, admin_user: dict
):
    """Test admin cannot delete any admin user (including other admins)."""
    # Try to delete the admin user
    response = client.delete(
        f"/api/v1/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "admin users cannot be deleted" in response.json()["detail"].lower()
    
    # Verify user still exists
    response = client.get(
        f"/api/v1/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_delete_user_by_id_another_admin_user_forbidden(
    client, db: Session, admin_token: str
):
    """Test admin cannot delete another admin user."""
    from app.core.security import get_password_hash
    from app.db.models.user import User as UserModel
    from app.db.models.role import Role as RoleModel
    
    # Get admin role
    admin_role = db.query(RoleModel).filter(RoleModel.name == "admin").first()
    if not admin_role:
        raise RuntimeError("Admin role not found")
    
    # Create another admin user
    another_admin = UserModel(
        email="another_admin@example.com",
        name="Another Admin",
        password_hash=get_password_hash("AnotherAdmin123!"),
        role_id=admin_role.id,
    )
    db.add(another_admin)
    db.commit()
    db.refresh(another_admin)
    
    # Try to delete the other admin user
    response = client.delete(
        f"/api/v1/users/{another_admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "admin users cannot be deleted" in response.json()["detail"].lower()
    
    # Verify user still exists
    response = client.get(
        f"/api/v1/users/{another_admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
