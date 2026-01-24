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


def test_get_all_apartments_as_tenant_fails(client, db: Session, tenant_token: str):
    """Test tenant cannot get all apartments."""
    response = client.get(
        "/api/v1/apartments",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


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
    assert "Apartment not found" in response.json()["detail"]


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
    assert "Apartment not found" in response.json()["detail"]


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
