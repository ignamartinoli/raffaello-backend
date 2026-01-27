import pytest
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


# ============================================================================
# CREATE APARTMENT TESTS
# ============================================================================


def test_create_apartment_as_admin_success(client, db: Session, admin_token: str):
    """Test successful apartment creation by admin."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "A",
            "is_mine": True,
            "ecogas": 12345,
            "epec_client": 67890,
            "epec_contract": 11111,
            "water": 22222,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["floor"] == 1
    assert data["letter"] == "A"
    assert data["is_mine"] is True
    assert data["ecogas"] == 12345
    assert data["epec_client"] == 67890
    assert data["epec_contract"] == 11111
    assert data["water"] == 22222
    assert "id" in data


def test_create_apartment_minimal_fields(client, db: Session, admin_token: str):
    """Test apartment creation with only required fields."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 2,
            "letter": "B",
            "is_mine": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["floor"] == 2
    assert data["letter"] == "B"
    assert data["is_mine"] is False
    assert data["ecogas"] is None
    assert data["epec_client"] is None
    assert data["epec_contract"] is None
    assert data["water"] is None


def test_create_apartment_without_authentication(client, db: Session):
    """Test apartment creation without authentication fails."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "A",
            "is_mine": True,
        },
    )
    assert response.status_code == 401


def test_create_apartment_as_non_admin(client, db: Session, tenant_token: str):
    """Test apartment creation by non-admin fails."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "A",
            "is_mine": True,
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_create_apartment_as_accountant_fails(client, db: Session, accountant_token: str):
    """Test apartment creation by accountant fails (only admin can create)."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "A",
            "is_mine": True,
        },
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_create_apartment_invalid_letter_too_long(client, db: Session, admin_token: str):
    """Test apartment creation with letter longer than 1 character fails."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "AB",  # Too long
            "is_mine": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Pydantic validates max_length at request parsing level (422)
    assert response.status_code == 422


def test_create_apartment_invalid_letter_empty(client, db: Session, admin_token: str):
    """Test apartment creation with empty letter fails."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "",  # Empty string
            "is_mine": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Pydantic validates min_length at request parsing level (422)
    assert response.status_code == 422


def test_create_apartment_missing_required_fields(client, db: Session, admin_token: str):
    """Test apartment creation with missing required fields fails."""
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            # Missing letter and is_mine
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Pydantic validates required fields at request parsing level (422)
    assert response.status_code == 422


def test_create_apartment_duplicate_floor_letter(client, db: Session, admin_token: str):
    """Test apartment creation with duplicate floor and letter fails."""
    from app.repositories.apartment import create_apartment
    
    # Create first apartment
    create_apartment(db, floor=1, letter="A", is_mine=True)
    
    # Try to create another apartment with same floor and letter
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "A",
            "is_mine": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409  # Conflict
    data = response.json()
    assert "already exists" in data["detail"].lower()
    assert data["code"] == "DUPLICATE_RESOURCE"


def test_create_apartment_same_floor_different_letter(client, db: Session, admin_token: str):
    """Test that apartments with same floor but different letter can be created."""
    from app.repositories.apartment import create_apartment
    
    # Create first apartment
    create_apartment(db, floor=1, letter="A", is_mine=True)
    
    # Create another apartment with same floor but different letter (should succeed)
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 1,
            "letter": "B",
            "is_mine": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["floor"] == 1
    assert data["letter"] == "B"


def test_create_apartment_same_letter_different_floor(client, db: Session, admin_token: str):
    """Test that apartments with same letter but different floor can be created."""
    from app.repositories.apartment import create_apartment
    
    # Create first apartment
    create_apartment(db, floor=1, letter="A", is_mine=True)
    
    # Create another apartment with same letter but different floor (should succeed)
    response = client.post(
        "/api/v1/apartments",
        json={
            "floor": 2,
            "letter": "A",
            "is_mine": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["floor"] == 2
    assert data["letter"] == "A"


# ============================================================================
# GET ALL APARTMENTS TESTS
# ============================================================================


def test_get_all_apartments_as_admin(client, db: Session, admin_token: str):
    """Test admin can get all apartments."""
    # Create some apartments first
    from app.repositories.apartment import create_apartment
    
    create_apartment(db, floor=1, letter="A", is_mine=True)
    create_apartment(db, floor=2, letter="B", is_mine=False)
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("id" in apt for apt in data)
    assert all("floor" in apt for apt in data)
    assert all("letter" in apt for apt in data)


def test_get_all_apartments_as_accountant(client, db: Session, accountant_token: str):
    """Test accountant can get all apartments."""
    # Create some apartments first
    from app.repositories.apartment import create_apartment
    
    create_apartment(db, floor=1, letter="A", is_mine=True)
    create_apartment(db, floor=2, letter="B", is_mine=False)
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_all_apartments_empty_list(client, db: Session, admin_token: str):
    """Test getting all apartments when none exist returns empty list."""
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_all_apartments_as_tenant_with_open_contract(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant can get apartments with open contracts (end_date is None)."""
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    # Create open contract (end_date is None)
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_month=1,
        start_year=2025,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == apartment.id
    assert data[0]["floor"] == 1
    assert data[0]["letter"] == "A"


def test_get_all_apartments_as_tenant_with_future_end_date(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant can get apartments with open contracts (end_date in the future)."""
    from datetime import date, timedelta
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=2, letter="B", is_mine=False)
    
    # Create open contract (end_date in the future)
    future_date = date.today() + timedelta(days=30)
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_month=1,
        start_year=2025,
        end_month=future_date.month,
        end_year=future_date.year,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == apartment.id
    assert data[0]["floor"] == 2
    assert data[0]["letter"] == "B"


def test_get_all_apartments_as_tenant_with_end_date_today(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant can get apartments with contracts ending today (end_date == today is considered open)."""
    from datetime import date
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=5, letter="E", is_mine=True)
    
    # Create contract with end_date equal to today (should be considered open)
    today = date.today()
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_month=1,
        start_year=2025,
        end_month=today.month,
        end_year=today.year,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == apartment.id
    assert data[0]["floor"] == 5
    assert data[0]["letter"] == "E"


def test_get_all_apartments_as_tenant_excludes_closed_contracts(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant cannot see apartments with closed contracts (end_date in the past)."""
    from datetime import date
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=3, letter="C", is_mine=True)
    
    # Create closed contract (end_date in the past)
    # Use previous month to ensure the last day of that month is definitely in the past
    today = date.today()
    if today.month == 1:
        end_month = 12
        end_year = today.year - 1
    else:
        end_month = today.month - 1
        end_year = today.year
    
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_month=1,
        start_year=2024,
        end_month=end_month,
        end_year=end_year,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Should not see apartment with closed contract


def test_get_all_apartments_as_tenant_excludes_future_contracts(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant cannot see apartments with contracts that haven't started yet (start_date in the future)."""
    from datetime import date
    from app.repositories.apartment import create_apartment
    from app.repositories.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=6, letter="F", is_mine=False)
    
    # Create contract with start_date in the future (must be first of month)
    # Get next month's first day
    today = date.today()
    if today.month == 12:
        future_start = date(today.year + 1, 1, 1)
    else:
        future_start = date(today.year, today.month + 1, 1)
    
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_date=future_start,
        end_date=None,  # No end date, but contract hasn't started
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Should not see apartment with future contract


def test_get_all_apartments_as_tenant_excludes_future_contracts_with_end_date(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant cannot see apartments with future contracts even if end_date is in the future."""
    from datetime import date
    from app.repositories.apartment import create_apartment
    from app.repositories.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=7, letter="G", is_mine=True)
    
    # Create contract with start_date in the future and end_date also in future (both must be first of month)
    # Get next month's first day
    today = date.today()
    if today.month == 12:
        future_start = date(today.year + 1, 1, 1)
        future_end = date(today.year + 1, 2, 1)
    else:
        future_start = date(today.year, today.month + 1, 1)
        if today.month == 11:
            future_end = date(today.year + 1, 1, 1)
        else:
            future_end = date(today.year, today.month + 2, 1)
    
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_date=future_start,
        end_date=future_end,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Should not see apartment with future contract


def test_get_all_apartments_as_tenant_includes_contract_starting_today(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant can see apartments with contracts starting today (if today is first of month) or this month."""
    from datetime import date
    from app.repositories.apartment import create_apartment
    from app.repositories.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=8, letter="H", is_mine=False)
    
    # Create contract with start_date equal to this month's first day (must be first of month)
    today = date.today()
    start_date = date(today.year, today.month, 1)
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_date=start_date,
        end_date=None,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == apartment.id
    assert data[0]["floor"] == 8
    assert data[0]["letter"] == "H"


def test_get_all_apartments_as_tenant_includes_contract_started_in_past(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant can see apartments with contracts that started in the past."""
    from datetime import date
    from app.repositories.apartment import create_apartment
    from app.repositories.contract import create_contract
    
    # Create apartment
    apartment = create_apartment(db, floor=9, letter="I", is_mine=True)
    
    # Create contract with start_date in the past (must be first of month)
    today = date.today()
    if today.month == 1:
        past_start = date(today.year - 1, 12, 1)
    else:
        past_start = date(today.year, today.month - 1, 1)
    
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        start_date=past_start,
        end_date=None,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == apartment.id
    assert data[0]["floor"] == 9
    assert data[0]["letter"] == "I"


def test_get_all_apartments_as_tenant_excludes_no_contracts(client, db: Session, tenant_token: str):
    """Test tenant cannot see apartments without contracts."""
    from app.repositories.apartment import create_apartment
    
    # Create apartment without contract
    create_apartment(db, floor=4, letter="D", is_mine=False)
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Should not see apartment without contract


def test_get_all_apartments_as_tenant_only_own_apartments(client, db: Session, tenant_token: str, tenant_user_dict: dict, another_tenant_user_dict: dict):
    """Test tenant only sees their own apartments, not other tenants' apartments."""
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract
    
    # Create two apartments
    apartment1 = create_apartment(db, floor=1, letter="A", is_mine=True)
    apartment2 = create_apartment(db, floor=2, letter="B", is_mine=False)
    
    # Create open contract for tenant_user_dict with apartment1
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment1.id,
        start_month=1,
        start_year=2025,
    )
    
    # Create open contract for another_tenant_user_dict with apartment2
    create_contract(
        db,
        user_id=another_tenant_user_dict["id"],
        apartment_id=apartment2.id,
        start_month=1,
        start_year=2025,
    )
    
    # Tenant should only see apartment1 (their own)
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == apartment1.id
    assert data[0]["floor"] == 1
    assert data[0]["letter"] == "A"


def test_get_all_apartments_as_tenant_empty_list_no_contracts(client, db: Session, tenant_token: str):
    """Test tenant sees empty list when they have no open contracts."""
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_all_apartments_as_tenant_multiple_open_contracts(client, db: Session, tenant_token: str, tenant_user_dict: dict):
    """Test tenant can see multiple apartments with open contracts."""
    from app.repositories.apartment import create_apartment
    from app.services.contract import create_contract
    
    # Create multiple apartments
    apartment1 = create_apartment(db, floor=1, letter="A", is_mine=True)
    apartment2 = create_apartment(db, floor=2, letter="B", is_mine=False)
    apartment3 = create_apartment(db, floor=3, letter="C", is_mine=True)
    
    # Create open contracts for all three apartments
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
    create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment3.id,
        start_month=3,
        start_year=2025,
    )
    
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    apartment_ids = {apt["id"] for apt in data}
    assert apartment1.id in apartment_ids
    assert apartment2.id in apartment_ids
    assert apartment3.id in apartment_ids


def test_get_all_apartments_without_authentication(client, db: Session):
    """Test getting all apartments without authentication fails."""
    response = client.get("/api/v1/apartments")
    assert response.status_code == 401


# ============================================================================
# GET APARTMENT BY ID TESTS
# ============================================================================


def test_get_apartment_by_id_as_admin(client, db: Session, admin_token: str):
    """Test admin can get apartment by ID."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=3, letter="C", is_mine=True, ecogas=12345)
    
    response = client.get(
        f"/api/v1/apartments/{apartment.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == apartment.id
    assert data["floor"] == 3
    assert data["letter"] == "C"
    assert data["is_mine"] is True
    assert data["ecogas"] == 12345


def test_get_apartment_by_id_as_accountant(client, db: Session, accountant_token: str):
    """Test accountant can get apartment by ID."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=4, letter="D", is_mine=False)
    
    response = client.get(
        f"/api/v1/apartments/{apartment.id}",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == apartment.id
    assert data["floor"] == 4
    assert data["letter"] == "D"


def test_get_apartment_by_id_not_found(client, db: Session, admin_token: str):
    """Test getting non-existent apartment returns 404."""
    response = client.get(
        "/api/v1/apartments/999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    data = response.json()
    assert "Apartment not found" in data["detail"]
    assert data["code"] == "NOT_FOUND"


def test_get_apartment_by_id_as_tenant_fails(client, db: Session, tenant_token: str):
    """Test tenant cannot get apartment by ID."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    response = client.get(
        f"/api/v1/apartments/{apartment.id}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_get_apartment_by_id_without_authentication(client, db: Session):
    """Test getting apartment by ID without authentication fails."""
    response = client.get("/api/v1/apartments/1")
    assert response.status_code == 401


# ============================================================================
# UPDATE APARTMENT TESTS
# ============================================================================


def test_update_apartment_as_admin_success(client, db: Session, admin_token: str):
    """Test successful apartment update by admin."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "floor": 2,
            "letter": "B",
            "is_mine": False,
            "ecogas": 99999,
            "water": 88888,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == apartment.id
    assert data["floor"] == 2
    assert data["letter"] == "B"
    assert data["is_mine"] is False
    assert data["ecogas"] == 99999
    assert data["water"] == 88888


def test_update_apartment_partial_update(client, db: Session, admin_token: str):
    """Test partial apartment update (only some fields)."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(
        db, floor=1, letter="A", is_mine=True, ecogas=11111, water=22222
    )
    
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "floor": 5,
            "ecogas": 33333,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["floor"] == 5
    assert data["letter"] == "A"  # Unchanged
    assert data["is_mine"] is True  # Unchanged
    assert data["ecogas"] == 33333
    assert data["water"] == 22222  # Unchanged


def test_update_apartment_not_found(client, db: Session, admin_token: str):
    """Test updating non-existent apartment returns 404."""
    response = client.put(
        "/api/v1/apartments/999",
        json={
            "floor": 1,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    data = response.json()
    assert "Apartment not found" in data["detail"]
    assert data["code"] == "NOT_FOUND"


def test_update_apartment_as_accountant_fails(client, db: Session, accountant_token: str):
    """Test accountant cannot update apartments."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "floor": 2,
        },
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_update_apartment_as_tenant_fails(client, db: Session, tenant_token: str):
    """Test tenant cannot update apartments."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "floor": 2,
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_update_apartment_without_authentication(client, db: Session):
    """Test updating apartment without authentication fails."""
    response = client.put(
        "/api/v1/apartments/1",
        json={
            "floor": 2,
        },
    )
    assert response.status_code == 401


def test_update_apartment_duplicate_floor_letter(client, db: Session, admin_token: str):
    """Test updating apartment to duplicate floor and letter fails."""
    from app.repositories.apartment import create_apartment
    
    # Create two apartments
    apartment1 = create_apartment(db, floor=1, letter="A", is_mine=True)
    apartment2 = create_apartment(db, floor=2, letter="B", is_mine=False)
    
    # Try to update apartment2 to have same floor and letter as apartment1
    response = client.put(
        f"/api/v1/apartments/{apartment2.id}",
        json={
            "floor": 1,
            "letter": "A",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409  # Conflict
    data = response.json()
    assert "already exists" in data["detail"].lower()
    assert data["code"] == "DUPLICATE_RESOURCE"


def test_update_apartment_duplicate_floor_only(client, db: Session, admin_token: str):
    """Test updating apartment to duplicate floor (but different letter) succeeds."""
    from app.repositories.apartment import create_apartment
    
    # Create two apartments
    apartment1 = create_apartment(db, floor=1, letter="A", is_mine=True)
    apartment2 = create_apartment(db, floor=2, letter="B", is_mine=False)
    
    # Update apartment2 to have same floor as apartment1 but keep its own letter
    # This should succeed since (1, B) is different from (1, A)
    response = client.put(
        f"/api/v1/apartments/{apartment2.id}",
        json={
            "floor": 1,
            # letter stays "B", so final combination is (1, B) which is different from (1, A)
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["floor"] == 1
    assert data["letter"] == "B"


def test_update_apartment_duplicate_letter_only(client, db: Session, admin_token: str):
    """Test updating apartment to duplicate letter (but different floor) succeeds."""
    from app.repositories.apartment import create_apartment
    
    # Create two apartments
    apartment1 = create_apartment(db, floor=1, letter="A", is_mine=True)
    apartment2 = create_apartment(db, floor=2, letter="B", is_mine=False)
    
    # Try to update apartment2 to have same letter as apartment1 but different floor
    response = client.put(
        f"/api/v1/apartments/{apartment2.id}",
        json={
            "letter": "A",
            # floor stays 2, so final is (2, A) which is different from (1, A)
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # This should succeed since (2, A) is different from (1, A)
    assert response.status_code == 200
    data = response.json()
    assert data["floor"] == 2
    assert data["letter"] == "A"


def test_update_apartment_same_floor_letter_no_change(client, db: Session, admin_token: str):
    """Test updating apartment without changing floor and letter succeeds."""
    from app.repositories.apartment import create_apartment
    
    # Create apartment
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    # Update other fields without changing floor and letter
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "is_mine": False,
            "ecogas": 12345,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["floor"] == 1
    assert data["letter"] == "A"
    assert data["is_mine"] is False
    assert data["ecogas"] == 12345


def test_update_apartment_to_same_floor_letter(client, db: Session, admin_token: str):
    """Test updating apartment to explicitly set same floor and letter it already has succeeds."""
    from app.repositories.apartment import create_apartment
    
    # Create apartment
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    # Update to same floor and letter (should succeed - no conflict with itself)
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "floor": 1,
            "letter": "A",
            "is_mine": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["floor"] == 1
    assert data["letter"] == "A"
    assert data["is_mine"] is False


def test_update_apartment_invalid_letter_too_long(client, db: Session, admin_token: str):
    """Test apartment update with letter longer than 1 character fails."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "letter": "AB",  # Too long
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Pydantic validates max_length at request parsing level (422)
    assert response.status_code == 422


def test_update_apartment_invalid_letter_empty(client, db: Session, admin_token: str):
    """Test apartment update with empty letter fails."""
    from app.repositories.apartment import create_apartment
    
    apartment = create_apartment(db, floor=1, letter="A", is_mine=True)
    
    response = client.put(
        f"/api/v1/apartments/{apartment.id}",
        json={
            "letter": "",  # Empty string
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Pydantic validates min_length at request parsing level (422)
    assert response.status_code == 422
