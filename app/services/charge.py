import calendar
import math
from datetime import date
from sqlalchemy.orm import Session
import httpx

import app.repositories.charge as charge_repo
import app.repositories.contract as contract_repo
from app.core.config import settings
from app.db.models.charge import Charge as ChargeModel
from app.db.models.contract import Contract as ContractModel
from app.db.models.user import User
from app.errors import (
    DomainValidationError,
    DuplicateResourceError,
    ForbiddenError,
    NotFoundError,
)
from app.services.email import send_charge_email as send_charge_email_service


def list_charges_for_user(
    db: Session,
    current_user: User,
    year: int | None = None,
    month: int | None = None,
    unpaid: bool | None = None,
    apartment_id: int | None = None,
) -> list[ChargeModel]:
    """
    List charges visible to the given user (business access rules).

    - Admin and Accountant: can see all charges
    - Tenant: can only see visible charges for contracts with their user_id
    - Other roles: not allowed

    Raises:
        ForbiddenError: If user role is not allowed.
    """
    if current_user.role.name in ("admin", "accountant"):
        return charge_repo.get_all_charges(
            db,
            year=year,
            month=month,
            unpaid=unpaid,
            apartment_id=apartment_id,
        )
    if current_user.role.name == "tenant":
        return charge_repo.get_visible_charges_by_user_id(
            db,
            current_user.id,
            year=year,
            month=month,
            unpaid=unpaid,
            apartment_id=apartment_id,
        )
    raise ForbiddenError("Not enough permissions")


def get_charge_for_user(
    db: Session,
    charge_id: int,
    current_user: User,
) -> ChargeModel:
    """
    Get a charge by ID if the user is allowed to see it (business access rules).

    - Admin and Accountant: can see any charge
    - Tenant: can only see visible charges for contracts with their user_id

    Raises:
        NotFoundError: If charge does not exist.
        ForbiddenError: If tenant tries to access a charge they are not allowed to see.
    """
    charge = charge_repo.get_charge_by_id(db, charge_id)
    if not charge:
        raise NotFoundError("Charge not found")

    if current_user.role.name == "tenant":
        if not charge.is_visible or charge.contract.user_id != current_user.id:
            raise ForbiddenError("Not enough permissions")

    return charge


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


def delete_charge(db: Session, charge_id: int) -> None:
    """
    Delete a charge with business logic validation.

    - Validates charge exists (raises NotFoundError if not)
    - Validates charge is not paid (raises DomainValidationError if payment_date is set)
    """
    charge = charge_repo.get_charge_by_id(db, charge_id)
    if not charge:
        raise NotFoundError("Charge not found")

    if charge.payment_date is not None:
        raise DomainValidationError(
            "Cannot delete charge: charge has been paid (payment_date is set)"
        )

    charge_repo.delete_charge(db, charge_id)


async def estimate_adjustment_by_contract_id(
    db: Session,
    contract_id: int,
) -> int:
    """
    Estimate the adjustment for a contract by calling RapidAPI.

    Business logic:
    - Validates contract exists
    - Gets the latest adjusted charge for the contract
    - Validates RapidAPI key is configured
    - Validates contract has adjustment_months set
    - Calls RapidAPI to calculate the adjustment
    - Extracts the amount from the last item in the data array
    - Returns the amount rounded up

    Args:
        db: Database session
        contract_id: ID of the contract to estimate adjustment for

    Returns:
        The adjusted amount rounded up (integer)

    Raises:
        NotFoundError: If contract not found or no adjusted charge exists
        DomainValidationError: If RapidAPI key is not configured, contract doesn't have adjustment_months, or API response is invalid
    """
    # Validate contract exists
    contract = contract_repo.get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundError(f"Contract with id {contract_id} not found")

    # Validate RapidAPI key is configured
    if not settings.rapidapi_key:
        raise DomainValidationError(
            "RapidAPI key is not configured. Please configure RAPIDAPI_KEY in .env file."
        )

    # Validate contract has adjustment_months set
    if contract.adjustment_months is None:
        raise DomainValidationError(
            f"Contract with id {contract_id} does not have adjustment_months configured"
        )

    # Get the latest adjusted charge
    charge = get_latest_adjusted_charge_by_contract_id(db, contract_id)

    # Prepare the request body for RapidAPI
    request_body = {
        "amount": charge.rent,
        "date": charge.period.strftime("%Y-%m-%d"),
        "months": contract.adjustment_months,
        "rate": "ipc",
    }

    # Call RapidAPI
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "arquilerapi1.p.rapidapi.com",
        "x-rapidapi-key": settings.rapidapi_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://arquilerapi1.p.rapidapi.com/calculate",
                json=request_body,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            api_response = response.json()

            # Validate response structure
            if not isinstance(api_response, dict) or "data" not in api_response:
                raise DomainValidationError(
                    "Invalid response from RapidAPI: missing 'data' field"
                )

            data = api_response.get("data", [])
            if not isinstance(data, list) or len(data) == 0:
                raise DomainValidationError(
                    "Invalid response from RapidAPI: 'data' is empty or not a list"
                )

            # Get the last item from the data array
            last_item = data[-1]
            if not isinstance(last_item, dict) or "amount" not in last_item:
                raise DomainValidationError(
                    "Invalid response from RapidAPI: last item in 'data' missing 'amount' field"
                )

            # Extract amount and round up
            amount = last_item["amount"]
            if not isinstance(amount, (int, float)):
                raise DomainValidationError(
                    "Invalid response from RapidAPI: 'amount' is not a number"
                )

            return math.ceil(amount)

    except httpx.HTTPStatusError as e:
        raise DomainValidationError(
            f"RapidAPI request failed with status {e.response.status_code}: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise DomainValidationError(f"RapidAPI request failed: {str(e)}")
