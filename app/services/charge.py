from datetime import date
from sqlalchemy.orm import Session

import app.repositories.charge as charge_repo
import app.repositories.contract as contract_repo
from app.db.models.charge import Charge as ChargeModel
from app.errors import DomainValidationError, DuplicateResourceError, NotFoundError


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
    - Validates no duplicate charge for same contract+period
    """
    # Convert month/year to first of month date
    period = date(year, month, 1)
    
    # Validate contract exists
    contract = contract_repo.get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundError(f"Contract with id {contract_id} not found")
    
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
    if contract_id is not None:
        contract = contract_repo.get_contract_by_id(db, contract_id)
        if not contract:
            raise NotFoundError(f"Contract with id {contract_id} not found")
    
    # Check for duplicate charge if period or contract_id is being changed
    final_contract_id = contract_id if contract_id is not None else existing_charge.contract_id
    final_period = new_period if new_period is not None else existing_charge.period
    
    # Only check for duplicates if we're changing period or contract_id
    if new_period is not None or contract_id is not None:
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
