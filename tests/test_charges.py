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
def contract(db: Session, tenant_user_dict: dict, apartment):
    """Create a contract for testing."""
    from app.services.contract import create_contract
    return create_contract(
        db,
        user_id=tenant_user_dict["id"],
        apartment_id=apartment.id,
        month=1,
        year=2025,
    )


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


@pytest.fixture(scope="function")
def another_contract(db: Session, another_tenant_user_dict: dict, apartment):
    """Create another contract for testing."""
    from app.services.contract import create_contract
    return create_contract(
        db,
        user_id=another_tenant_user_dict["id"],
        apartment_id=apartment.id,
        month=2,
        year=2025,
    )


# ============================================================================
# CREATE CHARGE TESTS
# ============================================================================


def test_create_charge_as_admin_success(client, db: Session, admin_token: str, contract):
    """Test successful charge creation by admin."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
            "payment_date": "2025-01-15",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["contract_id"] == contract.id
    assert data["period"] == "2025-01-01"
    assert data["rent"] == 1000
    assert data["expenses"] == 200
    assert data["municipal_tax"] == 50
    assert data["provincial_tax"] == 30
    assert data["water_bill"] == 40
    assert data["is_adjusted"] is False
    assert data["is_visible"] is True
    assert data["payment_date"] == "2025-01-15"
    assert "id" in data


def test_create_charge_minimal_fields(client, db: Session, admin_token: str, contract):
    """Test charge creation with only required fields."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 6,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["period"] == "2025-06-01"
    assert data["is_visible"] is False  # Default value
    assert data["payment_date"] is None


def test_create_charge_without_authentication(client, db: Session, contract):
    """Test charge creation without authentication fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
    )
    assert response.status_code == 401


def test_create_charge_as_tenant_fails(client, db: Session, tenant_token: str, contract):
    """Test charge creation by tenant fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_create_charge_as_accountant_fails(client, db: Session, accountant_token: str, contract):
    """Test charge creation by accountant fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_create_charge_invalid_month_zero(client, db: Session, admin_token: str, contract):
    """Test charge creation with month=0 fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 0,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_invalid_month_13(client, db: Session, admin_token: str, contract):
    """Test charge creation with month=13 fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 13,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_missing_required_fields(client, db: Session, admin_token: str):
    """Test charge creation with missing required fields fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "month": 1,
            "year": 2025,
            # Missing contract_id and other required fields
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_contract_not_found(client, db: Session, admin_token: str):
    """Test charge creation with non-existent contract fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": 99999,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_charge_duplicate(client, db: Session, admin_token: str, contract):
    """Test creating duplicate charge (same contract+period) fails."""
    # Create first charge
    response1 = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 3,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 3,
            "year": 2025,
            "rent": 1200,
            "expenses": 250,
            "municipal_tax": 60,
            "provincial_tax": 35,
            "water_bill": 45,
            "is_adjusted": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower() or "duplicate" in response2.json()["detail"].lower()


def test_create_charge_same_period_different_contract_success(client, db: Session, admin_token: str, contract, another_contract):
    """Test creating charges with same period but different contract succeeds."""
    # Create first charge
    response1 = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 5,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 201
    
    # Create charge with same period but different contract
    response2 = client.post(
        "/api/v1/charges",
        json={
            "contract_id": another_contract.id,
            "month": 5,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 201


def test_create_charge_negative_rent_fails(client, db: Session, admin_token: str, contract):
    """Test charge creation with negative rent fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": -100,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_negative_expenses_fails(client, db: Session, admin_token: str, contract):
    """Test charge creation with negative expenses fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": -50,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_negative_municipal_tax_fails(client, db: Session, admin_token: str, contract):
    """Test charge creation with negative municipal_tax fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": -10,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_negative_provincial_tax_fails(client, db: Session, admin_token: str, contract):
    """Test charge creation with negative provincial_tax fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": -5,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_negative_water_bill_fails(client, db: Session, admin_token: str, contract):
    """Test charge creation with negative water_bill fails."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": -20,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_charge_zero_values_success(client, db: Session, admin_token: str, contract):
    """Test charge creation with zero values succeeds (zero is allowed)."""
    response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 0,
            "expenses": 0,
            "municipal_tax": 0,
            "provincial_tax": 0,
            "water_bill": 0,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rent"] == 0
    assert data["expenses"] == 0
    assert data["municipal_tax"] == 0
    assert data["provincial_tax"] == 0
    assert data["water_bill"] == 0


# ============================================================================
# GET ALL CHARGES TESTS
# ============================================================================


def test_get_all_charges_as_admin(client, db: Session, admin_token: str, contract):
    """Test admin can get all charges."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    
    # Get all charges
    response = client.get(
        "/api/v1/charges",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(charge["id"] == create_response.json()["id"] for charge in data)


def test_get_all_charges_as_accountant(client, db: Session, admin_token: str, accountant_token: str, contract):
    """Test accountant can get all charges."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    
    # Get all charges as accountant
    response = client.get(
        "/api/v1/charges",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_all_charges_as_tenant_only_visible(client, db: Session, admin_token: str, tenant_token: str, contract):
    """Test tenant can only see visible charges for their contracts."""
    # Create visible charge
    visible_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert visible_response.status_code == 201
    
    # Create non-visible charge
    hidden_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 2,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert hidden_response.status_code == 201
    
    # Get charges as tenant
    response = client.get(
        "/api/v1/charges",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Should only see the visible charge
    assert len(data) == 1
    assert data[0]["id"] == visible_response.json()["id"]
    assert data[0]["is_visible"] is True


def test_get_all_charges_as_tenant_no_access_other_contracts(client, db: Session, admin_token: str, tenant_token: str, another_contract):
    """Test tenant cannot see charges for other tenants' contracts."""
    # Create charge for another tenant's contract
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": another_contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    
    # Get charges as tenant
    response = client.get(
        "/api/v1/charges",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Should not see the charge for another tenant's contract
    assert not any(charge["id"] == create_response.json()["id"] for charge in data)


def test_get_all_charges_filter_by_period_success(client, db: Session, admin_token: str, contract):
    """Test filtering charges by year and month."""
    # Create charges for different periods
    charge1_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 3,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert charge1_response.status_code == 201
    charge1_id = charge1_response.json()["id"]
    
    charge2_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 4,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert charge2_response.status_code == 201
    charge2_id = charge2_response.json()["id"]
    
    # Filter by March 2025
    response = client.get(
        "/api/v1/charges?year=2025&month=3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Should only return charge for March 2025
    assert len(data) == 1
    assert data[0]["id"] == charge1_id
    assert data[0]["period"] == "2025-03-01"


def test_get_all_charges_filter_by_period_no_matches(client, db: Session, admin_token: str, contract):
    """Test filtering charges by period with no matches returns empty list."""
    # Create a charge for March 2025
    client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 3,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Filter by a different period
    response = client.get(
        "/api/v1/charges?year=2026&month=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_get_all_charges_filter_by_period_only_year_fails(client, db: Session, admin_token: str):
    """Test filtering with only year parameter fails validation."""
    response = client.get(
        "/api/v1/charges?year=2025",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "Both year and month must be provided together" in response.json()["detail"]


def test_get_all_charges_filter_by_period_only_month_fails(client, db: Session, admin_token: str):
    """Test filtering with only month parameter fails validation."""
    response = client.get(
        "/api/v1/charges?month=3",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "Both year and month must be provided together" in response.json()["detail"]


def test_get_all_charges_filter_by_period_invalid_month_zero(client, db: Session, admin_token: str):
    """Test filtering with month=0 fails validation."""
    response = client.get(
        "/api/v1/charges?year=2025&month=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_get_all_charges_filter_by_period_invalid_month_13(client, db: Session, admin_token: str):
    """Test filtering with month=13 fails validation."""
    response = client.get(
        "/api/v1/charges?year=2025&month=13",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_get_all_charges_filter_by_period_invalid_year_too_low(client, db: Session, admin_token: str):
    """Test filtering with year < 1900 fails validation."""
    response = client.get(
        "/api/v1/charges?year=1899&month=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_get_all_charges_filter_by_period_invalid_year_too_high(client, db: Session, admin_token: str):
    """Test filtering with year > 2100 fails validation."""
    response = client.get(
        "/api/v1/charges?year=2101&month=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_get_all_charges_filter_by_period_as_accountant(client, db: Session, admin_token: str, accountant_token: str, contract):
    """Test accountant can filter charges by period."""
    # Create charges for different periods
    charge1_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 5,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert charge1_response.status_code == 201
    charge1_id = charge1_response.json()["id"]
    
    client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 6,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Filter by period as accountant
    response = client.get(
        "/api/v1/charges?year=2025&month=5",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == charge1_id


def test_get_all_charges_filter_by_period_as_tenant(client, db: Session, admin_token: str, tenant_token: str, contract):
    """Test tenant can filter visible charges by period."""
    # Create visible charges for different periods
    visible_charge1 = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 7,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert visible_charge1.status_code == 201
    charge1_id = visible_charge1.json()["id"]
    
    # Create another visible charge for different period
    client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 8,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Filter by period as tenant
    response = client.get(
        "/api/v1/charges?year=2025&month=7",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == charge1_id
    assert data[0]["is_visible"] is True


def test_get_all_charges_filter_by_period_tenant_hidden_charge_not_included(client, db: Session, admin_token: str, tenant_token: str, contract):
    """Test tenant filtering by period excludes hidden charges."""
    # Create visible charge
    visible_charge = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 9,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert visible_charge.status_code == 201
    visible_charge_id = visible_charge.json()["id"]
    
    # Create hidden charge for same period
    client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 9,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Filter by period as tenant - should only see visible charge
    response = client.get(
        "/api/v1/charges?year=2025&month=9",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == visible_charge_id
    assert data[0]["is_visible"] is True


# ============================================================================
# GET CHARGE BY ID TESTS
# ============================================================================


def test_get_charge_by_id_as_admin(client, db: Session, admin_token: str, contract):
    """Test admin can get any charge by ID."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Get charge by ID
    response = client.get(
        f"/api/v1/charges/{charge_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == charge_id


def test_get_charge_by_id_as_accountant(client, db: Session, admin_token: str, accountant_token: str, contract):
    """Test accountant can get any charge by ID."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Get charge by ID as accountant
    response = client.get(
        f"/api/v1/charges/{charge_id}",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == charge_id


def test_get_charge_by_id_as_tenant_visible(client, db: Session, admin_token: str, tenant_token: str, contract):
    """Test tenant can get visible charge for their contract."""
    # Create visible charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Get charge by ID as tenant
    response = client.get(
        f"/api/v1/charges/{charge_id}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == charge_id


def test_get_charge_by_id_as_tenant_not_visible_fails(client, db: Session, admin_token: str, tenant_token: str, contract):
    """Test tenant cannot get non-visible charge."""
    # Create non-visible charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to get charge by ID as tenant
    response = client.get(
        f"/api/v1/charges/{charge_id}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_get_charge_by_id_as_tenant_other_contract_fails(client, db: Session, admin_token: str, tenant_token: str, another_contract):
    """Test tenant cannot get charge for another tenant's contract."""
    # Create charge for another tenant's contract
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": another_contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to get charge by ID as tenant
    response = client.get(
        f"/api/v1/charges/{charge_id}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_get_charge_by_id_not_found(client, db: Session, admin_token: str):
    """Test getting non-existent charge returns 404."""
    response = client.get(
        "/api/v1/charges/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# UPDATE CHARGE TESTS
# ============================================================================


def test_update_charge_as_admin_success(client, db: Session, admin_token: str, contract):
    """Test successful charge update by admin."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Update charge
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "rent": 1200,
            "is_visible": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rent"] == 1200
    assert data["is_visible"] is True
    # Other fields should remain unchanged
    assert data["expenses"] == 200
    assert data["municipal_tax"] == 50


def test_update_charge_partial_update(client, db: Session, admin_token: str, contract):
    """Test partial charge update only updates provided fields."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "is_visible": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    original_expenses = create_response.json()["expenses"]
    
    # Update only rent
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "rent": 1500,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rent"] == 1500
    assert data["expenses"] == original_expenses  # Should remain unchanged


def test_update_charge_set_payment_date_to_null(client, db: Session, admin_token: str, contract):
    """Test setting payment_date to null explicitly."""
    # Create a charge with payment_date
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
            "payment_date": "2025-01-15",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    assert create_response.json()["payment_date"] == "2025-01-15"
    
    # Update to set payment_date to null
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "payment_date": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["payment_date"] is None


def test_update_charge_set_payment_date(client, db: Session, admin_token: str, contract):
    """Test setting payment_date to a date."""
    # Create a charge without payment_date
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    assert create_response.json()["payment_date"] is None
    
    # Update to set payment_date
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "payment_date": "2025-01-20",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["payment_date"] == "2025-01-20"


def test_update_charge_update_period(client, db: Session, admin_token: str, contract):
    """Test updating charge period (month/year)."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Update period
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "month": 6,
            "year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "2025-06-01"


def test_update_charge_month_year_together_required(client, db: Session, admin_token: str, contract):
    """Test updating period requires both month and year."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update with only month
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "month": 6,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_charge_duplicate_period_fails(client, db: Session, admin_token: str, contract):
    """Test updating charge to duplicate period fails."""
    # Create first charge
    create_response1 = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 3,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response1.status_code == 201
    
    # Create second charge
    create_response2 = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 4,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response2.status_code == 201
    charge_id2 = create_response2.json()["id"]
    
    # Try to update second charge to same period as first
    response = client.put(
        f"/api/v1/charges/{charge_id2}",
        json={
            "month": 3,
            "year": 2025,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_update_charge_as_tenant_fails(client, db: Session, admin_token: str, tenant_token: str, contract):
    """Test charge update by tenant fails."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update as tenant
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "rent": 1200,
        },
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_update_charge_as_accountant_fails(client, db: Session, admin_token: str, accountant_token: str, contract):
    """Test charge update by accountant fails."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update as accountant
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "rent": 1200,
        },
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_update_charge_not_found(client, db: Session, admin_token: str):
    """Test updating non-existent charge returns 404."""
    response = client.put(
        "/api/v1/charges/99999",
        json={
            "rent": 1200,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_charge_negative_rent_fails(client, db: Session, admin_token: str, contract):
    """Test charge update with negative rent fails."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update with negative rent
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "rent": -100,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_charge_negative_expenses_fails(client, db: Session, admin_token: str, contract):
    """Test charge update with negative expenses fails."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update with negative expenses
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "expenses": -50,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_charge_negative_municipal_tax_fails(client, db: Session, admin_token: str, contract):
    """Test charge update with negative municipal_tax fails."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update with negative municipal_tax
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "municipal_tax": -10,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_charge_negative_provincial_tax_fails(client, db: Session, admin_token: str, contract):
    """Test charge update with negative provincial_tax fails."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update with negative provincial_tax
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "provincial_tax": -5,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_charge_negative_water_bill_fails(client, db: Session, admin_token: str, contract):
    """Test charge update with negative water_bill fails."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Try to update with negative water_bill
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "water_bill": -20,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_update_charge_zero_values_success(client, db: Session, admin_token: str, contract):
    """Test charge update with zero values succeeds (zero is allowed)."""
    # Create a charge
    create_response = client.post(
        "/api/v1/charges",
        json={
            "contract_id": contract.id,
            "month": 1,
            "year": 2025,
            "rent": 1000,
            "expenses": 200,
            "municipal_tax": 50,
            "provincial_tax": 30,
            "water_bill": 40,
            "is_adjusted": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    charge_id = create_response.json()["id"]
    
    # Update with zero values
    response = client.put(
        f"/api/v1/charges/{charge_id}",
        json={
            "rent": 0,
            "expenses": 0,
            "municipal_tax": 0,
            "provincial_tax": 0,
            "water_bill": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rent"] == 0
    assert data["expenses"] == 0
    assert data["municipal_tax"] == 0
    assert data["provincial_tax"] == 0
    assert data["water_bill"] == 0
