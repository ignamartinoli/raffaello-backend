from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models.user import User
import app.repositories.apartment as apartment_repo
from app.services.apartment import delete_apartment, list_apartments_for_user
from app.schemas.apartment import Apartment, ApartmentCreate, ApartmentUpdate
from app.errors import NotFoundError

router = APIRouter(prefix="/apartments", tags=["apartments"])


@router.post("", response_model=Apartment, status_code=status.HTTP_201_CREATED)
def create_new_apartment(
    apartment_data: ApartmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """
    Create a new apartment. Only admin users can create apartments.
    """
    apartment = apartment_repo.create_apartment(
        db,
        floor=apartment_data.floor,
        letter=apartment_data.letter,
        is_mine=apartment_data.is_mine,
        ecogas=apartment_data.ecogas,
        epec_client=apartment_data.epec_client,
        epec_contract=apartment_data.epec_contract,
        water=apartment_data.water,
    )
    return Apartment.model_validate(apartment)


@router.get("", response_model=list[Apartment])
def get_all_apartments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "accountant", "tenant")),
):
    """
    Get all apartments.
    - Admin and Accountant: can see all apartments
    - Tenant: can only see apartments for which they have an open contract
      (as defined by the domain-level ContractActivityPolicy)
    """
    apartments = list_apartments_for_user(db, current_user)
    return [Apartment.model_validate(apt) for apt in apartments]


@router.get("/{apartment_id}", response_model=Apartment)
def get_apartment_by_id(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "accountant")),
):
    """
    Get an apartment by ID. Both admin and accountant users can see apartments.
    """
    apartment = apartment_repo.get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError("Apartment not found")
    return Apartment.model_validate(apartment)


@router.put("/{apartment_id}", response_model=Apartment)
def update_apartment_by_id(
    apartment_id: int,
    apartment_data: ApartmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """
    Update an apartment. Only admin users can update apartments.
    """
    apartment = apartment_repo.update_apartment(
        db,
        apartment_id=apartment_id,
        floor=apartment_data.floor,
        letter=apartment_data.letter,
        is_mine=apartment_data.is_mine,
        ecogas=apartment_data.ecogas,
        epec_client=apartment_data.epec_client,
        epec_contract=apartment_data.epec_contract,
        water=apartment_data.water,
    )
    return Apartment.model_validate(apartment)


@router.delete("/{apartment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_apartment_by_id(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Delete an apartment by ID. Only admin users can delete apartments.

    An apartment can only be deleted if it doesn't have any associated contracts.
    """
    delete_apartment(db, apartment_id)
