from sqlalchemy.orm import Session

from app.db.models.apartment import Apartment as ApartmentModel


def get_apartment_by_id(db: Session, apartment_id: int) -> ApartmentModel | None:
    """Get an apartment by ID."""
    return db.query(ApartmentModel).filter(ApartmentModel.id == apartment_id).first()


def get_all_apartments(db: Session) -> list[ApartmentModel]:
    """Get all apartments."""
    return db.query(ApartmentModel).all()


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
        raise ValueError("Apartment not found")
    
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
