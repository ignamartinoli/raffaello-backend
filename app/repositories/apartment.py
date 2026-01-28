from datetime import date
from sqlalchemy.orm import Session

from app.db.models.apartment import Apartment as ApartmentModel
from app.db.models.contract import Contract as ContractModel
from app.domain.contract_activity import ContractActivityPolicy
from app.errors import NotFoundError


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
    Apartments for which the user has an open contract.
    "Open" is defined by ContractActivityPolicy (domain); this builds the query.
    """
    policy = ContractActivityPolicy(as_of=date.today())
    return (
        db.query(ApartmentModel)
        .join(ContractModel, ApartmentModel.id == ContractModel.apartment_id)
        .filter(
            ContractModel.user_id == user_id,
            policy.sqlalchemy_active_predicate(
                start_col=ContractModel.start_date,
                end_col=ContractModel.end_date,
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
    """Create a new apartment. Pure persistence; no business logic."""
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
    """Update an apartment by ID. Raises NotFoundError if not found. Pure persistence."""
    apartment = get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError("Apartment not found")

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


def delete_apartment(db: Session, apartment_id: int) -> None:
    """Delete an apartment by ID. Raises NotFoundError if not found. Pure persistence."""
    apartment = get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError("Apartment not found")

    db.delete(apartment)
    db.commit()
