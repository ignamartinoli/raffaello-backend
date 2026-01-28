from sqlalchemy.orm import Session

import app.repositories.apartment as apartment_repo
import app.repositories.contract as contract_repo
from app.errors import DomainValidationError, NotFoundError


def delete_apartment(db: Session, apartment_id: int) -> None:
    """
    Delete an apartment with business logic validation.

    - Validates apartment exists
    - Validates apartment has no contracts (cannot delete apartments with contracts)

    Raises:
        NotFoundError: If apartment doesn't exist
        DomainValidationError: If apartment has contracts
    """
    # Check if apartment exists
    apartment = apartment_repo.get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError("Apartment not found")

    # Validate apartment has no contracts
    contracts = contract_repo.get_contracts_by_apartment_id(db, apartment_id)
    if contracts:
        raise DomainValidationError(
            "Cannot delete apartment: apartment has associated contracts"
        )

    # Use repository for actual database operation (pure data access)
    apartment_repo.delete_apartment(db, apartment_id)
