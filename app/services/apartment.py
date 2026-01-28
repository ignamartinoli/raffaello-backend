from sqlalchemy.orm import Session

import app.repositories.apartment as apartment_repo
import app.repositories.contract as contract_repo
from app.db.models.user import User
from app.db.models.apartment import Apartment as ApartmentModel
from app.errors import DomainValidationError, DuplicateResourceError, NotFoundError


def list_apartments_for_user(db: Session, current_user: User) -> list[ApartmentModel]:
    """
    List apartments visible to the given user (business access rules).

    - Admin/Accountant: can see all apartments
    - Tenant: only apartments with an open contract (ContractActivityPolicy).
    """
    if current_user.role.name in ("admin", "accountant"):
        return apartment_repo.get_all_apartments(db)
    return apartment_repo.get_apartments_with_open_contracts_by_user_id(
        db, current_user.id
    )


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
    """
    Create an apartment with domain validation.

    - Enforces uniqueness of (floor, letter) (domain rule)

    Raises:
        DuplicateResourceError: If (floor, letter) already exists
    """
    existing = apartment_repo.get_apartment_by_floor_letter(db, floor, letter)
    if existing:
        raise DuplicateResourceError(
            f"An apartment with floor {floor} and letter {letter} already exists"
        )
    return apartment_repo.create_apartment(
        db,
        floor=floor,
        letter=letter,
        is_mine=is_mine,
        ecogas=ecogas,
        epec_client=epec_client,
        epec_contract=epec_contract,
        water=water,
    )


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
    """
    Update an apartment with domain validation.

    - Validates apartment exists
    - Enforces uniqueness of (floor, letter) when changed (domain rule)

    Raises:
        NotFoundError: If apartment doesn't exist
        DuplicateResourceError: If new (floor, letter) already exists
    """
    apartment = apartment_repo.get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError("Apartment not found")

    final_floor = floor if floor is not None else apartment.floor
    final_letter = letter if letter is not None else apartment.letter

    if floor is not None or letter is not None:
        existing = apartment_repo.get_apartment_by_floor_letter(
            db, final_floor, final_letter, exclude_id=apartment_id
        )
        if existing:
            raise DuplicateResourceError(
                f"An apartment with floor {final_floor} and letter {final_letter} already exists"
            )

    return apartment_repo.update_apartment(
        db,
        apartment_id=apartment_id,
        floor=floor,
        letter=letter,
        is_mine=is_mine,
        ecogas=ecogas,
        epec_client=epec_client,
        epec_contract=epec_contract,
        water=water,
    )


def delete_apartment(db: Session, apartment_id: int) -> None:
    """
    Delete an apartment with business logic validation.

    - Validates apartment exists
    - Validates apartment has no contracts (cannot delete apartments with contracts)

    Raises:
        NotFoundError: If apartment doesn't exist
        DomainValidationError: If apartment has contracts
    """
    apartment = apartment_repo.get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError("Apartment not found")

    contracts = contract_repo.get_contracts_by_apartment_id(db, apartment_id)
    if contracts:
        raise DomainValidationError(
            "Cannot delete apartment: apartment has associated contracts"
        )

    apartment_repo.delete_apartment(db, apartment_id)
