import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.db.models.user import User as UserModel
from app.db.models.role import Role as RoleModel
from app.core.security import get_password_hash, create_access_token


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def accountant_user_dict(db: Session) -> dict:
    """Create an accountant user for testing."""
    email = "accountant@example.com"
    name = "Test Accountant"
    password = "AccountantPass123!"
    
    # Get accountant role
    accountant_role = db.query(RoleModel).filter(RoleModel.name == "accountant").first()
    if not accountant_role:
        raise RuntimeError("Accountant role not found")
    
    # Create user
    user = UserModel(
        email=email,
        name=name,
        password_hash=get_password_hash(password),
        role_id=accountant_role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": name,
        "password": password,
        "role_id": user.role_id,
    }


@pytest.fixture(scope="function")
def accountant_token(accountant_user_dict: dict) -> str:
    """Get JWT token for accountant user."""
    token = create_access_token(data={"sub": accountant_user_dict["id"]})
    return token


@pytest.fixture(scope="function")
def apartment(db: Session):
    """Create an apartment for testing."""
    from app.repositories.apartment import create_apartment
    return create_apartment(db, floor=1, letter="A", is_mine=True)


@pytest.fixture(scope="function")
def another_tenant_user_dict(db: Session) -> dict:
    """Create another tenant user for testing."""
    email = "tenant2@example.com"
    name = "Test Tenant 2"
    password = "Tenant2Pass123!"
    
    # Get tenant role
    tenant_role = db.query(RoleModel).filter(RoleModel.name == "tenant").first()
    if not tenant_role:
        raise RuntimeError("Tenant role not found")
    
    # Create user
    user = UserModel(
        email=email,
        name=name,
        password_hash=get_password_hash(password),
        role_id=tenant_role.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": name,
        "password": password,
        "role_id": user.role_id,
    }


@pytest.fixture(scope="function")
def another_tenant_token(another_tenant_user_dict: dict) -> str:
    """Get JWT token for another tenant user."""
    token = create_access_token(data={"sub": another_tenant_user_dict["id"]})
    return token


# ============================================================================
# CREATE CONTRACT TESTS
# ============================================================================


def test_create_contract_as_admin_success(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test successful contract creation by admin."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
            "end_month": 12,
            "end_year": 2025,
            "adjustment_months": 3,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == tenant_user_dict["id"]
    assert data["apartment_id"] == apartment.id
    assert data["start_date"] == "2025-01-01"
    assert data["end_date"] == "2025-12-31"
    assert data["adjustment_months"] == 3
    assert "id" in data


def test_create_contract_minimal_fields(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with only required fields."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 6,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["start_date"] == "2025-06-01"
    assert data["end_date"] is None
    assert data["adjustment_months"] is None


def test_create_contract_without_authentication(client, db: Session, tenant_user_dict: dict, apartment):
    """Test contract creation without authentication fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
        },
    )
    assert response.status_code == 401


def test_create_contract_as_tenant_fails(client, db: Session, tenant_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation by tenant fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_create_contract_as_accountant_fails(client, db: Session, accountant_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation by accountant fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_create_contract_invalid_month_zero(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with start_month=0 fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 0,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_invalid_month_negative(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with negative month fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": -1,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_invalid_month_too_large(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with start_month=13 fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 13,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_invalid_month_100(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with month=100 fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 100,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_missing_required_fields(client, db: Session, admin_token: str):
    """Test contract creation with missing required fields fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "start_month": 1,
            "start_year": 2025,
            # Missing user_id and apartment_id
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_user_not_found(client, db: Session, admin_token: str, apartment):
    """Test contract creation with non-existent user fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": 99999,
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_contract_user_not_tenant(client, db: Session, admin_token: str, accountant_user_dict: dict, apartment):
    """Test contract creation with non-tenant user fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": accountant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "tenant" in response.json()["detail"].lower()


def test_create_contract_apartment_not_found(client, db: Session, admin_token: str, tenant_user_dict: dict):
    """Test contract creation with non-existent apartment fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": 99999,
            "start_month": 1,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_contract_duplicate(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test creating duplicate contract (same month+year+apartment) fails."""
    # Create first contract
    response1 = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 3,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 3,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower() or "duplicate" in response2.json()["detail"].lower()


def test_create_contract_duplicate_different_user_same_apartment(client, db: Session, admin_token: str, tenant_user_dict: dict, another_tenant_user_dict: dict, apartment):
    """Test creating duplicate contract with different user but same apartment+month fails."""
    # Create first contract
    response1 = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 4,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 201
    
    # Try to create duplicate with different user
    response2 = client.post(
        "/api/v1/contracts",
        json={
            "user_id": another_tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 4,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower() or "duplicate" in response2.json()["detail"].lower()


def test_create_contract_same_month_different_year_success(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test creating contracts with same month but different year succeeds."""
    # Create first contract
    response1 = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 5,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 201
    
    # Create contract with same month but different year
    response2 = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 5,
            "start_year": 2026,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 201


def test_create_contract_invalid_adjustment_months_zero(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with adjustment_months=0 fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
            "adjustment_months": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_invalid_adjustment_months_negative(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with negative adjustment_months fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
            "adjustment_months": -5,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


# ============================================================================
# GET ALL CONTRACTS TESTS
# ============================================================================


def test_get_all_contracts_as_admin(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test admin can get all contracts (paginated)."""
    from app.services.contract import create_contract

    # Use 2024 dates so contracts are active (start_date <= today, no end_date)
    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2024)
    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=2, start_year=2024)

    response = client.get(
        "/api/v1/contracts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert len(data["items"]) == 2
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 100


def test_get_all_contracts_as_accountant_forbidden(client, db: Session, accountant_token: str, tenant_user_dict: dict, apartment):
    """Test accountant cannot access GET /contracts."""
    from app.services.contract import create_contract

    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2024)

    response = client.get(
        "/api/v1/contracts",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_get_all_contracts_as_tenant_only_own(client, db: Session, tenant_token: str, tenant_user_dict: dict, another_tenant_user_dict: dict, apartment):
    """Test tenant can only see their own contracts."""
    from app.services.contract import create_contract

    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2024)
    create_contract(db, another_tenant_user_dict["id"], apartment.id, start_month=2, start_year=2024)

    response = client.get(
        "/api/v1/contracts",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["user_id"] == tenant_user_dict["id"]
    assert data["total"] == 1


def test_get_all_contracts_empty_list(client, db: Session, admin_token: str):
    """Test getting all contracts when none exist returns paginated empty list."""
    response = client.get(
        "/api/v1/contracts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 100


def test_get_all_contracts_without_authentication(client, db: Session):
    """Test getting all contracts without authentication fails."""
    response = client.get("/api/v1/contracts")
    assert response.status_code == 401


def test_get_all_contracts_pagination(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test pagination with page and page_size."""
    from app.services.contract import create_contract

    for m in range(1, 6):
        create_contract(db, tenant_user_dict["id"], apartment.id, start_month=m, start_year=2024)

    response = client.get(
        "/api/v1/contracts",
        params={"page": 1, "page_size": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2

    response2 = client.get(
        "/api/v1/contracts",
        params={"page": 2, "page_size": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 2
    assert data2["page"] == 2


def test_get_all_contracts_filter_by_user_admin(client, db: Session, admin_token: str, tenant_user_dict: dict, another_tenant_user_dict: dict, apartment):
    """Test admin can filter contracts by user ID."""
    from app.services.contract import create_contract

    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2024)
    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=2, start_year=2024)
    create_contract(db, another_tenant_user_dict["id"], apartment.id, start_month=3, start_year=2024)

    response = client.get(
        "/api/v1/contracts",
        params={"user": tenant_user_dict["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert all(c["user_id"] == tenant_user_dict["id"] for c in data["items"])


def test_get_all_contracts_filter_by_apartment_admin(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test admin can filter contracts by apartment ID."""
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract

    apt2 = create_apartment(db, floor=2, letter="B", is_mine=False)
    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2024)
    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=2, start_year=2024)
    create_contract(db, tenant_user_dict["id"], apt2.id, start_month=3, start_year=2024)

    response = client.get(
        "/api/v1/contracts",
        params={"apartment": apartment.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert all(c["apartment_id"] == apartment.id for c in data["items"])


def test_get_all_contracts_filter_active_admin(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test admin can filter by active status (default True shows only active)."""
    from app.services.contract import create_contract

    # Active: 2024, no end_date
    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2024)
    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=2, start_year=2024)
    # Inactive: ended contract (2022–2023)
    create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2022,
        end_month=6,
        end_year=2023,
    )

    response = client.get(
        "/api/v1/contracts",
        params={"active": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2

    response_inactive = client.get(
        "/api/v1/contracts",
        params={"active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response_inactive.status_code == 200
    data_inactive = response_inactive.json()
    assert len(data_inactive["items"]) == 1
    assert data_inactive["items"][0]["start_date"] == "2022-01-01"
    assert data_inactive["items"][0]["end_date"] == "2023-06-30"


def test_get_all_contracts_tenant_cannot_use_filters(client, db: Session, tenant_token: str, tenant_user_dict: dict, another_tenant_user_dict: dict, apartment):
    """Test tenant cannot use user, apartment, or active filters."""
    from app.services.contract import create_contract

    create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2024)

    for params in [
        {"user": another_tenant_user_dict["id"]},
        {"apartment": apartment.id},
        {"active": False},
    ]:
        response = client.get(
            "/api/v1/contracts",
            params=params,
            headers={"Authorization": f"Bearer {tenant_token}"},
        )
        assert response.status_code == 403, f"Expected 403 for params {params}"
        assert "Filters are only allowed for admin users" in response.json()["detail"]


# ============================================================================
# GET CONTRACT BY ID TESTS
# ============================================================================


def test_get_contract_by_id_as_admin(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test admin can get contract by ID."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.get(
        f"/api/v1/contracts/{contract.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == contract.id
    assert data["start_date"] == "2025-01-01"


def test_get_contract_by_id_as_accountant(client, db: Session, accountant_token: str, tenant_user_dict: dict, apartment):
    """Test accountant can get contract by ID."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.get(
        f"/api/v1/contracts/{contract.id}",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == contract.id


def test_get_contract_by_id_as_tenant_own_contract(client, db: Session, tenant_token: str, tenant_user_dict: dict, apartment):
    """Test tenant can get their own contract by ID."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.get(
        f"/api/v1/contracts/{contract.id}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == contract.id
    assert data["user_id"] == tenant_user_dict["id"]


def test_get_contract_by_id_as_tenant_other_tenant_contract_fails(client, db: Session, tenant_token: str, another_tenant_user_dict: dict, apartment):
    """Test tenant cannot get another tenant's contract."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, another_tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.get(
        f"/api/v1/contracts/{contract.id}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_get_contract_by_id_not_found(client, db: Session, admin_token: str):
    """Test getting non-existent contract returns 404."""
    response = client.get(
        "/api/v1/contracts/999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "Contract not found" in response.json()["detail"]


def test_get_contract_by_id_without_authentication(client, db: Session):
    """Test getting contract by ID without authentication fails."""
    response = client.get("/api/v1/contracts/1")
    assert response.status_code == 401


# ============================================================================
# UPDATE CONTRACT TESTS
# ============================================================================


def test_update_contract_as_admin_success(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test successful contract update by admin."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 6,
            "start_year": 2025,
            "end_month": 12,
            "end_year": 2025,
            "adjustment_months": 2,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2025-06-01"
    assert data["end_date"] == "2025-12-31"
    assert data["adjustment_months"] == 2


def test_update_contract_partial_update(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test partial contract update (only some fields)."""
    from app.services.contract import create_contract
    
    # Create contract with end_date set
    contract = create_contract(
        db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025, end_month=12, end_year=2025
    )
    
    # Update only adjustment_months, other fields should remain unchanged
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": 5,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["adjustment_months"] == 5
    assert data["start_date"] == "2025-01-01"  # Unchanged
    assert data["end_date"] == "2025-12-31"  # Unchanged
    assert data["user_id"] == tenant_user_dict["id"]  # Unchanged
    assert data["apartment_id"] == apartment.id  # Unchanged


def test_update_contract_not_found(client, db: Session, admin_token: str):
    """Test updating non-existent contract returns 404."""
    response = client.put(
        "/api/v1/contracts/999",
        json={
            "adjustment_months": 3,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_contract_as_accountant_fails(client, db: Session, accountant_token: str, tenant_user_dict: dict, apartment):
    """Test accountant cannot update contracts."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": 3,
        },
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_update_contract_as_tenant_fails(client, db: Session, tenant_token: str, tenant_user_dict: dict, apartment):
    """Test tenant cannot update contracts."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": 3,
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_update_contract_without_authentication(client, db: Session):
    """Test updating contract without authentication fails."""
    response = client.put(
        "/api/v1/contracts/1",
        json={
            "adjustment_months": 3,
        },
    )
    assert response.status_code == 401


def test_update_contract_invalid_month_zero(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with month=0 fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 0,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_invalid_month_too_large(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with month=13 fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 13,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_month_without_year_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with month but no year fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 6,
            # Missing start_year
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_year_without_month_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with year but no month fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_year": 2026,
            # Missing start_month
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_user_not_tenant(client, db: Session, admin_token: str, tenant_user_dict: dict, accountant_user_dict: dict, apartment):
    """Test contract update with non-tenant user fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "user_id": accountant_user_dict["id"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "tenant" in response.json()["detail"].lower()


def test_update_contract_duplicate(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test updating contract to duplicate month+year+apartment fails."""
    from app.services.contract import create_contract
    
    # Create two contracts
    contract1 = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    contract2 = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=2, start_year=2025)
    
    # Try to update contract2 to have same month+year as contract1
    response = client.put(
        f"/api/v1/contracts/{contract2.id}",
        json={
            "start_month": 1,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower() or "duplicate" in response.json()["detail"].lower()


def test_update_contract_invalid_adjustment_months_zero(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with adjustment_months=0 fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_invalid_adjustment_months_negative(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with negative adjustment_months fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": -3,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_clear_end_date(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test clearing end_date by setting it to null."""
    from app.services.contract import create_contract
    
    # Create contract with end_date
    contract = create_contract(
        db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025, end_month=12, end_year=2025
    )
    assert contract.end_date == date(2025, 12, 31)
    
    # Clear end_date by setting to null
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_month": None,
            "end_year": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["end_date"] is None
    assert data["start_date"] == "2025-01-01"  # Unchanged


def test_update_contract_clear_adjustment_months(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test clearing adjustment_months by setting it to null."""
    from app.services.contract import create_contract
    
    # Create contract with adjustment_months
    contract = create_contract(
        db, tenant_user_dict["id"], apartment.id, 1, 2025, adjustment_months=5
    )
    assert contract.adjustment_months == 5
    
    # Clear adjustment_months by setting to null
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["adjustment_months"] is None
    assert data["start_date"] == "2025-01-01"  # Unchanged


def test_update_contract_fields_not_provided_unchanged(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test that fields not provided in update request remain unchanged."""
    from app.services.contract import create_contract
    
    # Create contract with all fields set
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=12,
        end_year=2025,
        adjustment_months=3,
    )
    
    # Update only adjustment_months, other fields should remain unchanged
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": 7,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["adjustment_months"] == 7
    assert data["end_date"] == "2025-12-31"  # Unchanged
    assert data["start_date"] == "2025-01-01"  # Unchanged
    assert data["user_id"] == tenant_user_dict["id"]  # Unchanged
    assert data["apartment_id"] == apartment.id  # Unchanged


def test_update_contract_clear_both_nullable_fields(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test clearing both end_date and adjustment_months in one request."""
    from app.services.contract import create_contract
    
    # Create contract with both nullable fields set
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=12,
        end_year=2025,
        adjustment_months=5,
    )
    
    # Clear both fields
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_month": None,
            "end_year": None,
            "adjustment_months": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["end_date"] is None
    assert data["adjustment_months"] is None
    assert data["start_date"] == "2025-01-01"  # Unchanged


def test_update_contract_partial_update_with_clear(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test partial update where we update one field and clear another."""
    from app.services.contract import create_contract
    
    # Create contract with end_date and adjustment_months
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=12,
        end_year=2025,
        adjustment_months=3,
    )
    
    # Update adjustment_months and clear end_date
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "adjustment_months": 10,
            "end_month": None,
            "end_year": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["adjustment_months"] == 10
    assert data["end_date"] is None
    assert data["start_date"] == "2025-01-01"  # Unchanged


def test_update_contract_empty_request_no_changes(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test that empty update request doesn't change anything."""
    from app.services.contract import create_contract
    
    # Create contract with all fields set
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=12,
        end_year=2025,
        adjustment_months=3,
    )
    
    # Send empty update request
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # All fields should remain unchanged
    assert data["start_date"] == "2025-01-01"
    assert data["end_date"] == "2025-12-31"
    assert data["adjustment_months"] == 3
    assert data["user_id"] == tenant_user_dict["id"]
    assert data["apartment_id"] == apartment.id


def test_update_contract_end_date_precedes_start_date_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test that updating end_date to precede start_date fails."""
    from app.services.contract import create_contract
    
    # Create contract starting in June
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=6, start_year=2025)
    
    # Try to set end_date before start_date
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_month": 5,
            "end_year": 2025,  # Before June 1
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "cannot precede" in response.json()["detail"].lower()


def test_create_contract_start_month_without_start_year_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with start_month but no start_year fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            # Missing start_year
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_start_year_without_start_month_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with start_year but no start_month fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_year": 2025,
            # Missing start_month
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_end_month_without_end_year_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with end_month but no end_year fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
            "end_month": 12,
            # Missing end_year
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_contract_end_year_without_end_month_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract creation with end_year but no end_month fails."""
    response = client.post(
        "/api/v1/contracts",
        json={
            "user_id": tenant_user_dict["id"],
            "apartment_id": apartment.id,
            "start_month": 1,
            "start_year": 2025,
            "end_year": 2025,
            # Missing end_month
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_end_month_without_end_year_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with end_month but no end_year fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_month": 12,
            # Missing end_year
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_contract_end_year_without_end_month_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test contract update with end_year but no end_month fails."""
    from app.services.contract import create_contract
    
    contract = create_contract(db, tenant_user_dict["id"], apartment.id, start_month=1, start_year=2025)
    
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_year": 2025,
            # Missing end_month
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


# ============================================================================
# CONTRACT UPDATE VALIDATION TESTS (Charge Period Constraints)
# ============================================================================


def test_update_contract_start_date_with_charge_before_new_start_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test updating contract start_date to later date when charge exists before new start fails."""
    from app.services.contract import create_contract
    
    # Create contract starting in January 2025
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
    )
    
    # Create charge for January 2025
    from app.services.charge import create_charge
    charge = create_charge(
        db,
        contract_id=contract.id,
        month=1,
        year=2025,
        rent=1000,
        expenses=200,
        municipal_tax=50,
        provincial_tax=30,
        water_bill=40,
        is_adjusted=False,
    )
    
    # Try to update contract start_date to March 2025 (charge for January would be before new start)
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 3,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "would be before contract start date" in response.json()["detail"].lower()


def test_update_contract_end_date_with_charge_after_new_end_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test updating contract end_date to earlier date when charge exists after new end fails."""
    from app.services.contract import create_contract
    
    # Create contract with end_date (January to June 2025)
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=6,
        end_year=2025,
    )
    
    # Create charge for June 2025
    from app.services.charge import create_charge
    charge = create_charge(
        db,
        contract_id=contract.id,
        month=6,
        year=2025,
        rent=1000,
        expenses=200,
        municipal_tax=50,
        provincial_tax=30,
        water_bill=40,
        is_adjusted=False,
    )
    
    # Try to update contract end_date to April 2025 (charge for June would be after new end)
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_month": 4,
            "end_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "would be after contract end date" in response.json()["detail"].lower()


def test_update_contract_start_date_when_all_charges_within_new_range_success(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test updating contract start_date when all charges are within new range succeeds."""
    from app.services.contract import create_contract
    
    # Create contract starting in January 2025
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
    )
    
    # Create charge for March 2025
    from app.services.charge import create_charge
    charge = create_charge(
        db,
        contract_id=contract.id,
        month=3,
        year=2025,
        rent=1000,
        expenses=200,
        municipal_tax=50,
        provincial_tax=30,
        water_bill=40,
        is_adjusted=False,
    )
    
    # Update contract start_date to February 2025 (charge for March is still within range)
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 2,
            "start_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2025-02-01"


def test_update_contract_end_date_when_all_charges_within_new_range_success(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test updating contract end_date when all charges are within new range succeeds."""
    from app.services.contract import create_contract
    
    # Create contract with end_date (January to June 2025)
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=6,
        end_year=2025,
    )
    
    # Create charge for March 2025
    from app.services.charge import create_charge
    charge = create_charge(
        db,
        contract_id=contract.id,
        month=3,
        year=2025,
        rent=1000,
        expenses=200,
        municipal_tax=50,
        provincial_tax=30,
        water_bill=40,
        is_adjusted=False,
    )
    
    # Update contract end_date to May 2025 (charge for March is still within range)
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_month": 5,
            "end_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["end_date"] == "2025-05-31"


def test_update_contract_clear_end_date_with_charges_success(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test clearing contract end_date when charges exist succeeds (no end_date means ongoing)."""
    from app.services.contract import create_contract
    
    # Create contract with end_date (January to June 2025)
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=6,
        end_year=2025,
    )
    
    # Create charge for March 2025
    from app.services.charge import create_charge
    charge = create_charge(
        db,
        contract_id=contract.id,
        month=3,
        year=2025,
        rent=1000,
        expenses=200,
        municipal_tax=50,
        provincial_tax=30,
        water_bill=40,
        is_adjusted=False,
    )
    
    # Clear end_date (set to None) - charge is still within range (no end_date means ongoing)
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "end_month": None,
            "end_year": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["end_date"] is None


def test_update_contract_start_and_end_date_with_multiple_charges_success(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test updating contract dates when all charges are within new range succeeds."""
    from app.services.contract import create_contract
    
    # Create contract (January to December 2025)
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=12,
        end_year=2025,
    )
    
    # Create charges for March, April, and May 2025
    from app.services.charge import create_charge
    for month in [3, 4, 5]:
        create_charge(
            db,
            contract_id=contract.id,
            month=month,
            year=2025,
            rent=1000,
            expenses=200,
            municipal_tax=50,
            provincial_tax=30,
            water_bill=40,
            is_adjusted=False,
        )
    
    # Update contract to February to June 2025 (all charges still within range)
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 2,
            "start_year": 2025,
            "end_month": 6,
            "end_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2025-02-01"
    assert data["end_date"] == "2025-06-30"


def test_update_contract_start_and_end_date_with_charge_outside_range_fails(client, db: Session, admin_token: str, tenant_user_dict: dict, apartment):
    """Test updating contract dates when a charge would be outside new range fails."""
    from app.services.contract import create_contract
    
    # Create contract (January to December 2025)
    contract = create_contract(
        db,
        tenant_user_dict["id"],
        apartment.id,
        start_month=1,
        start_year=2025,
        end_month=12,
        end_year=2025,
    )
    
    # Create charges for January, March, and May 2025
    from app.services.charge import create_charge
    for month in [1, 3, 5]:
        create_charge(
            db,
            contract_id=contract.id,
            month=month,
            year=2025,
            rent=1000,
            expenses=200,
            municipal_tax=50,
            provincial_tax=30,
            water_bill=40,
            is_adjusted=False,
        )
    
    # Try to update contract to February to April 2025 (charge for January would be before new start)
    response = client.put(
        f"/api/v1/contracts/{contract.id}",
        json={
            "start_month": 2,
            "start_year": 2025,
            "end_month": 4,
            "end_year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "would be before contract start date" in response.json()["detail"].lower()
