import calendar
from datetime import date
from sqlalchemy.orm import Session

import app.repositories.contract as contract_repo
import app.repositories.user as user_repo
import app.repositories.apartment as apartment_repo
from app.db.models.contract import Contract as ContractModel
from app.errors import DomainValidationError, DuplicateResourceError, NotFoundError


def _get_last_day_of_month(year: int, month: int) -> date:
    """Get the last day of the given month and year."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def create_contract(
    db: Session,
    user_id: int,
    apartment_id: int,
    start_month: int,
    start_year: int,
    end_month: int | None = None,
    end_year: int | None = None,
    adjustment_months: int | None = None,
) -> ContractModel:
    """
    Create a new contract with business logic validation.

    - Converts start_month/start_year to first of month date
    - Converts end_month/end_year to last day of month date
    - Validates user exists and has "tenant" role
    - Validates apartment exists
    - Validates no duplicate contract for same month+year+apartment
    """
    # Convert start_month/start_year to first of month date
    start_date = date(start_year, start_month, 1)

    # Convert end_month/end_year to last day of month date if provided
    end_date = None
    if end_month is not None and end_year is not None:
        end_date = _get_last_day_of_month(end_year, end_month)
        # Validate end_date doesn't precede start_date
        if end_date < start_date:
            raise DomainValidationError(
                f"End date ({end_date}) cannot precede start date ({start_date})"
            )

    # Validate user exists and has tenant role
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with id {user_id} not found")

    if user.role.name != "tenant":
        raise DomainValidationError(f"User with id {user_id} must have 'tenant' role")

    # Validate apartment exists
    apartment = apartment_repo.get_apartment_by_id(db, apartment_id)
    if not apartment:
        raise NotFoundError(f"Apartment with id {apartment_id} not found")

    # Check for duplicate contract (same start_date and apartment_id)
    existing_contract = contract_repo.get_contract_by_start_date_and_apartment(
        db, start_date, apartment_id
    )
    if existing_contract:
        raise DuplicateResourceError(
            f"Contract already exists for apartment {apartment_id} starting on {start_date.strftime('%Y-%m-%d')}"
        )

    # Use repository for actual database operation (pure data access)
    return contract_repo.create_contract(
        db,
        user_id=user_id,
        apartment_id=apartment_id,
        start_date=start_date,
        end_date=end_date,
        adjustment_months=adjustment_months,
    )


def update_contract(
    db: Session,
    contract_id: int,
    **update_fields,
) -> ContractModel:
    """
    Update a contract with business logic validation.

    - Converts start_month/start_year to first of month date if provided
    - Converts end_month/end_year to last day of month date if provided
    - Validates user exists and has "tenant" role if user_id provided
    - Validates apartment exists if apartment_id provided
    - Validates no duplicate contract for same month+year+apartment (excluding current contract)

    Only fields explicitly provided in update_fields will be updated.
    To clear a field (set to None), explicitly include it with None value.
    """
    # Get existing contract
    existing_contract = contract_repo.get_contract_by_id(db, contract_id)
    if not existing_contract:
        raise NotFoundError("Contract not found")

    # Extract fields from update_fields
    user_id = update_fields.get("user_id")
    apartment_id = update_fields.get("apartment_id")
    start_month = update_fields.get("start_month")
    start_year = update_fields.get("start_year")
    end_month = update_fields.get("end_month")
    end_year = update_fields.get("end_year")
    adjustment_months = update_fields.get("adjustment_months")

    # Determine new start_date if start_month/start_year are being updated
    new_start_date = None
    if start_month is not None or start_year is not None:
        # If start_month or start_year is provided, we need both
        if start_month is None or start_year is None:
            raise DomainValidationError(
                "Both start_month and start_year must be provided together"
            )

        # Convert start_month/start_year to first of month date
        new_start_date = date(start_year, start_month, 1)

    # Determine final start_date for end_date validation
    # Use new_start_date if provided, otherwise existing contract's start_date
    final_start_date = (
        new_start_date if new_start_date is not None else existing_contract.start_date
    )

    # Convert end_month/end_year to last day of month date if provided
    new_end_date = None
    if "end_month" in update_fields or "end_year" in update_fields:
        # If end_month or end_year is provided, we need both
        if (end_month is None) != (end_year is None):
            raise DomainValidationError(
                "Both end_month and end_year must be provided together, or neither"
            )

        if end_month is not None and end_year is not None:
            new_end_date = _get_last_day_of_month(end_year, end_month)
            # Validate end_date doesn't precede start_date
            if new_end_date < final_start_date:
                raise DomainValidationError(
                    f"End date ({new_end_date}) cannot precede start date ({final_start_date})"
                )
        # If both are None, new_end_date stays None (to clear the field)

    # Validate user if provided
    if user_id is not None:
        user = user_repo.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")

        if user.role.name != "tenant":
            raise DomainValidationError(
                f"User with id {user_id} must have 'tenant' role"
            )

    # Validate apartment if provided
    if apartment_id is not None:
        apartment = apartment_repo.get_apartment_by_id(db, apartment_id)
        if not apartment:
            raise NotFoundError(f"Apartment with id {apartment_id} not found")

    # Check for duplicate contract if start_date or apartment_id is being changed
    final_apartment_id = (
        apartment_id if apartment_id is not None else existing_contract.apartment_id
    )

    # Only check for duplicates if we're changing start_date or apartment_id
    if new_start_date is not None or apartment_id is not None:
        duplicate_contract = contract_repo.get_contract_by_start_date_and_apartment(
            db, final_start_date, final_apartment_id
        )
        # If duplicate exists and it's not the current contract, raise error
        if duplicate_contract and duplicate_contract.id != contract_id:
            raise DuplicateResourceError(
                f"Contract already exists for apartment {final_apartment_id} starting on {final_start_date.strftime('%Y-%m-%d')}"
            )

    # Build update dict with only fields that were explicitly provided
    # Include start_date if start_month/start_year were provided
    update_dict = {}
    if "user_id" in update_fields:
        update_dict["user_id"] = user_id
    if "apartment_id" in update_fields:
        update_dict["apartment_id"] = apartment_id
    if new_start_date is not None:
        update_dict["start_date"] = new_start_date
    if "end_month" in update_fields or "end_year" in update_fields:
        update_dict["end_date"] = new_end_date  # Can be None to clear
    if "adjustment_months" in update_fields:
        update_dict["adjustment_months"] = adjustment_months  # Can be None to clear

    # Use repository for actual database operation
    return contract_repo.update_contract(db, contract_id=contract_id, **update_dict)
