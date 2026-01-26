from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models.apartment import Apartment as ApartmentModel
from app.db.models.contract import Contract as ContractModel
from app.errors import DuplicateResourceError, NotFoundError


def get_apartment_by_id(db: Session, apartment_id: int) -> ApartmentModel | None:
    """Get an apartment by ID."""
    return db.query(ApartmentModel).filter(ApartmentModel.id == apartment_id).first()


def get_all_apartments(db: Session) -> list[ApartmentModel]:
    """Get all apartments."""
    return db.query(ApartmentModel).all()


def get_apartments_with_open_contracts_by_user_id(
    db: Session, user_id: int
) -> list[ApartmentModel]:
    """
    Get apartments for which the user has an open contract.
    An open contract is one where:
    - start_date <= today (contract has started)
    - AND (end_date is None OR end_date >= today) (contract hasn't ended)
    """
    today = date.today()
    return (
        db.query(ApartmentModel)
        .join(ContractModel, ApartmentModel.id == ContractModel.apartment_id)
        .filter(
            ContractModel.user_id == user_id,
            and_(
                ContractModel.start_date <= today,
                or_(
                    ContractModel.end_date.is_(None),
                    ContractModel.end_date >= today,
                ),
            ),
        )
        .distinct()
        .all()
    )


def get_apartment_by_floor_letter(
    db: Session, floor: int, letter: str, exclude_id: int | None = None
) -> ApartmentModel | None:
    """Get an apartment by floor and letter combination."""
    query = db.query(ApartmentModel).filter(
        ApartmentModel.floor == floor, ApartmentModel.letter == letter
    )
    if exclude_id is not None:
        query = query.filter(ApartmentModel.id != exclude_id)
    return query.first()


def create_apartment(
    db: Session,
    floor: int,
    letter: str,
    is_mine: bool,
    ecogas: int | None = None,
    epec_client: int | None = None,
    epec_contract: int | None = None,
    water: int | None = None,
) -> ApartmentModel:
    """Create a new apartment in the database. Pure data access - no business logic."""
    # Check for uniqueness of floor and letter combination
    existing = get_apartment_by_floor_letter(db, floor, letter)
    if existing:
        raise DuplicateResourceError(
            f"An apartment with floor {floor} and letter {letter} already exists"
        )

    db_apartment = ApartmentModel(
        floor=floor,
        letter=letter,
        is_mine=is_mine,
        ecogas=ecogas,
        epec_client=epec_client,
        epec_contract=epec_contract,
        water=water,
    )
    db.add(db_apartment)
    db.commit()
    db.refresh(db_apartment)
    return db_apartment


def update_apartment(
    db: Session,
    apartment_id: int,
    floor: int | None = None,
    letter: str | None = None,
    is_mine: bool | None = None,
    ecogas: int | None = None,
    epec_client: int | None = None,
    epec_contract: int | None = None,
    water: int | None = None,
) -> ApartmentModel:
    """Update an apartment."""
    apartment = get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError("Apartment not found")

    # Determine the final floor and letter values after update
    final_floor = floor if floor is not None else apartment.floor
    final_letter = letter if letter is not None else apartment.letter

    # Check for uniqueness if floor or letter is being changed
    if floor is not None or letter is not None:
        existing = get_apartment_by_floor_letter(
            db, final_floor, final_letter, exclude_id=apartment_id
        )
        if existing:
            raise DuplicateResourceError(
                f"An apartment with floor {final_floor} and letter {final_letter} already exists"
            )

    if floor is not None:
        apartment.floor = floor
    if letter is not None:
        apartment.letter = letter
    if is_mine is not None:
        apartment.is_mine = is_mine
    if ecogas is not None:
        apartment.ecogas = ecogas
    if epec_client is not None:
        apartment.epec_client = epec_client
    if epec_contract is not None:
        apartment.epec_contract = epec_contract
    if water is not None:
        apartment.water = water

    db.commit()
    db.refresh(apartment)
    return apartment
