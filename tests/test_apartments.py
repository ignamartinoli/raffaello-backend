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
    assert "already exists" in response.json()["detail"].lower()


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
    assert "already exists" in response.json()["detail"].lower()


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
