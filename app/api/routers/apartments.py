from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
import app.repositories.apartment as apartment_repo
from app.schemas.apartment import Apartment, ApartmentCreate, ApartmentUpdate
from app.errors import DuplicateResourceError

router = APIRouter(prefix="/apartments", tags=["apartments"])


@router.post("", response_model=Apartment, status_code=status.HTTP_201_CREATED)
def create_new_apartment(
    apartment_data: ApartmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("admin")),
):
    """
    Create a new apartment. Only admin users can create apartments.
    """
    try:
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
    except DuplicateResourceError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    
    return Apartment.model_validate(apartment)


@router.get("", response_model=list[Apartment])
def get_all_apartments(
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("admin", "accountant")),
):
    """
    Get all apartments. Both admin and accountant users can see all apartments.
    """
    apartments = apartment_repo.get_all_apartments(db)
    return [Apartment.model_validate(apt) for apt in apartments]


@router.get("/{apartment_id}", response_model=Apartment)
def get_apartment_by_id(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("admin", "accountant")),
):
    """
    Get an apartment by ID. Both admin and accountant users can see apartments.
    """
    apartment = apartment_repo.get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartment not found",
        )
    return Apartment.model_validate(apartment)


@router.put("/{apartment_id}", response_model=Apartment)
def update_apartment_by_id(
    apartment_id: int,
    apartment_data: ApartmentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("admin")),
):
    """
    Update an apartment. Only admin users can update apartments.
    """
    try:
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
    except DuplicateResourceError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        # ValueError is used for "not found" cases
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return Apartment.model_validate(apartment)
