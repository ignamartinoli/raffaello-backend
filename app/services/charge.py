import calendar
from datetime import date
from sqlalchemy.orm import Session

import app.repositories.charge as charge_repo
import app.repositories.contract as contract_repo
from app.db.models.charge import Charge as ChargeModel
from app.db.models.contract import Contract as ContractModel
from app.errors import DomainValidationError, DuplicateResourceError, NotFoundError
from app.services.email import send_charge_email as send_charge_email_service


def _validate_charge_period_in_contract_range(
    period: date, contract: ContractModel
) -> None:
    """
    Validate that a charge period is within the contract's available period range.

    Args:
        period: The charge period (first day of month)
        contract: The contract to validate against

    Raises:
        DomainValidationError: If the period is outside the contract's date range
    """
    # Check that period is not before contract start_date
    if period < contract.start_date:
        raise DomainValidationError(
            f"Charge period {period.strftime('%Y-%m-%d')} is before contract start date {contract.start_date.strftime('%Y-%m-%d')}"
        )

    # Check that period is not after contract end_date (if end_date exists)
    if contract.end_date is not None and period > contract.end_date:
        raise DomainValidationError(
            f"Charge period {period.strftime('%Y-%m-%d')} is after contract end date {contract.end_date.strftime('%Y-%m-%d')}"
        )


def create_charge(
    db: Session,
    contract_id: int,
    month: int,
    year: int,
    rent: int,
    expenses: int,
    municipal_tax: int,
    provincial_tax: int,
    water_bill: int,
    is_adjusted: bool,
    is_visible: bool = False,
    payment_date: date | None = None,
) -> ChargeModel:
    """
    Create a new charge with business logic validation.

    - Converts month/year to first of month date
    - Validates contract exists
    - Validates charge period is within contract's date range
    - Validates no duplicate charge for same contract+period
    """
    # Convert month/year to first of month date
    period = date(year, month, 1)

    # Validate contract exists
    contract = contract_repo.get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundError(f"Contract with id {contract_id} not found")

    # Validate charge period is within contract's date range
    _validate_charge_period_in_contract_range(period, contract)

    # Check for duplicate charge (same contract_id and period)
    existing_charge = charge_repo.get_charge_by_contract_and_period(
        db, contract_id, period
    )
    if existing_charge:
        raise DuplicateResourceError(
            f"Charge already exists for contract {contract_id} with period {period.strftime('%Y-%m-%d')}"
        )

    # Use repository for actual database operation (pure data access)
    return charge_repo.create_charge(
        db,
        contract_id=contract_id,
        period=period,
        rent=rent,
        expenses=expenses,
        municipal_tax=municipal_tax,
        provincial_tax=provincial_tax,
        water_bill=water_bill,
        is_adjusted=is_adjusted,
        is_visible=is_visible,
        payment_date=payment_date,
    )


def update_charge(
    db: Session,
    charge_id: int,
    **update_fields,
) -> ChargeModel:
    """
    Update a charge with business logic validation.

    - Converts month/year to first of month date if provided
    - Validates contract exists if contract_id provided
    - Validates charge period is within contract's date range (if period or contract_id changes)
    - Validates no duplicate charge for same contract+period (excluding current charge)

    Only fields explicitly provided in update_fields will be updated.
    To clear a field (set to None), explicitly include it with None value.
    """
    # Get existing charge
    existing_charge = charge_repo.get_charge_by_id(db, charge_id)
    if not existing_charge:
        raise NotFoundError("Charge not found")

    # Extract fields from update_fields
    contract_id = update_fields.get("contract_id")
    month = update_fields.get("month")
    year = update_fields.get("year")
    payment_date = update_fields.get("payment_date")

    # Determine new period if month/year are being updated
    new_period = None
    if month is not None or year is not None:
        # If month or year is provided, we need both
        if month is None or year is None:
            raise DomainValidationError("Both month and year must be provided together")

        # Convert month/year to first of month date
        new_period = date(year, month, 1)

    # Validate contract if provided
    final_contract = None
    if contract_id is not None:
        final_contract = contract_repo.get_contract_by_id(db, contract_id)
        if not final_contract:
            raise NotFoundError(f"Contract with id {contract_id} not found")

    # Check for duplicate charge if period or contract_id is being changed
    final_contract_id = (
        contract_id if contract_id is not None else existing_charge.contract_id
    )
    final_period = new_period if new_period is not None else existing_charge.period

    # Get the contract we'll be using for validation
    if final_contract is None:
        final_contract = contract_repo.get_contract_by_id(db, final_contract_id)
        if not final_contract:
            raise NotFoundError(f"Contract with id {final_contract_id} not found")

    # Validate charge period is within contract's date range if period or contract_id is being changed
    if new_period is not None or contract_id is not None:
        _validate_charge_period_in_contract_range(final_period, final_contract)

        duplicate_charge = charge_repo.get_charge_by_contract_and_period(
            db, final_contract_id, final_period
        )
        # If duplicate exists and it's not the current charge, raise error
        if duplicate_charge and duplicate_charge.id != charge_id:
            raise DuplicateResourceError(
                f"Charge already exists for contract {final_contract_id} with period {final_period.strftime('%Y-%m-%d')}"
            )

    # Build update dict with only fields that were explicitly provided
    # Include period if month/year were provided
    update_dict = {}
    if "contract_id" in update_fields:
        update_dict["contract_id"] = contract_id
    if new_period is not None:
        update_dict["period"] = new_period
    if "rent" in update_fields:
        update_dict["rent"] = update_fields["rent"]
    if "expenses" in update_fields:
        update_dict["expenses"] = update_fields["expenses"]
    if "municipal_tax" in update_fields:
        update_dict["municipal_tax"] = update_fields["municipal_tax"]
    if "provincial_tax" in update_fields:
        update_dict["provincial_tax"] = update_fields["provincial_tax"]
    if "water_bill" in update_fields:
        update_dict["water_bill"] = update_fields["water_bill"]
    if "is_adjusted" in update_fields:
        update_dict["is_adjusted"] = update_fields["is_adjusted"]
    if "is_visible" in update_fields:
        update_dict["is_visible"] = update_fields["is_visible"]
    if "payment_date" in update_fields:
        update_dict["payment_date"] = payment_date  # Can be None to clear

    # Use repository for actual database operation
    return charge_repo.update_charge(db, charge_id=charge_id, **update_dict)


async def send_charge_email(db: Session, charge_id: int) -> dict[str, str]:
    """
    Send an email to the user associated with the charge's contract containing charge information.

    Business logic:
    - Validates charge exists
    - Validates charge has contract, user, and apartment relationships
    - Validates charge is visible
    - Formats period as "Month Year"
    - Calculates total from all charge components
    - Sends email with charge details

    Args:
        db: Database session
        charge_id: ID of the charge to send email for

    Returns:
        Dictionary with success message including recipient email

    Raises:
        NotFoundError: If charge not found
        DomainValidationError: If charge is not visible or relationships are missing
    """
    # Get charge with all necessary relationships loaded
    charge = charge_repo.get_charge_by_id(db, charge_id)
    if not charge:
        raise NotFoundError("Charge not found")

    # Verify relationships are loaded
    if not charge.contract:
        raise DomainValidationError("Contract not found for this charge")

    if not charge.contract.user:
        raise DomainValidationError("User not found for this contract")

    if not charge.contract.apartment:
        raise DomainValidationError("Apartment not found for this contract")

    # Verify charge is visible before sending email
    if not charge.is_visible:
        raise DomainValidationError(
            "Cannot send email for a charge that is not visible"
        )

    # Format period as "Month Year" (e.g., "January 2025")
    period_str = f"{calendar.month_name[charge.period.month]} {charge.period.year}"

    # Calculate total
    total = (
        charge.rent
        + charge.expenses
        + charge.municipal_tax
        + charge.provincial_tax
        + charge.water_bill
    )

    # Send email
    try:
        await send_charge_email_service(
            email=charge.contract.user.email,
            apartment_floor=charge.contract.apartment.floor,
            apartment_letter=charge.contract.apartment.letter,
            period=period_str,
            rent=charge.rent,
            expenses=charge.expenses,
            municipal_tax=charge.municipal_tax,
            provincial_tax=charge.provincial_tax,
            water_bill=charge.water_bill,
            total=total,
        )
    except ValueError as e:
        # Convert ValueError from email service to DomainValidationError
        raise DomainValidationError(str(e))

    return {
        "message": f"Charge email sent successfully to {charge.contract.user.email}"
    }


def get_latest_adjusted_charge_by_contract_id(
    db: Session,
    contract_id: int,
) -> ChargeModel:
    """
    Get the latest charge with is_adjusted=True for a specific contract.

    Business logic:
    - Validates contract exists
    - Retrieves the latest adjusted charge for the contract
    - Returns the charge if found

    Args:
        db: Database session
        contract_id: ID of the contract to get the latest adjusted charge for

    Returns:
        The latest charge with is_adjusted=True for the contract

    Raises:
        NotFoundError: If contract not found or no adjusted charge exists for the contract
    """
    # Validate contract exists
    contract = contract_repo.get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundError(f"Contract with id {contract_id} not found")

    # Get the latest adjusted charge
    charge = charge_repo.get_latest_adjusted_charge_by_contract_id(db, contract_id)
    if not charge:
        raise NotFoundError(
            f"No adjusted charge found for contract with id {contract_id}"
        )

    return charge
