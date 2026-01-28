from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_user
from app.services.charge import (
    create_charge,
    update_charge,
    delete_charge,
    send_charge_email,
    get_latest_adjusted_charge_by_contract_id,
)
import app.repositories.charge as charge_repo
from app.schemas.charge import Charge, ChargeCreate, ChargeUpdate
from app.db.models.user import User
from app.errors import NotFoundError

router = APIRouter(prefix="/charges", tags=["charges"])


@router.post("", response_model=Charge, status_code=status.HTTP_201_CREATED)
def create_new_charge(
    charge_data: ChargeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Create a new charge. Only admin users can create charges.
    """
    charge = create_charge(
        db,
        contract_id=charge_data.contract_id,
        month=charge_data.month,
        year=charge_data.year,
        rent=charge_data.rent,
        expenses=charge_data.expenses,
        municipal_tax=charge_data.municipal_tax,
        provincial_tax=charge_data.provincial_tax,
        water_bill=charge_data.water_bill,
        is_adjusted=charge_data.is_adjusted,
        is_visible=charge_data.is_visible,
        payment_date=charge_data.payment_date,
    )
    return Charge.model_validate(charge)


@router.get("", response_model=list[Charge])
def get_all_charges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: int | None = Query(
        None, ge=1900, le=2100, description="Year to filter by (1900-2100)"
    ),
    month: int | None = Query(
        None, ge=1, le=12, description="Month to filter by (1-12)"
    ),
    unpaid: bool | None = Query(
        None, description="Filter by unpaid charges (payment_date is None)"
    ),
    apartment: int | None = Query(None, description="Filter by apartment ID"),
):
    """
    Get all charges.
    - Admin and Accountant: can see all charges
    - Tenant: can only see visible charges for contracts with their user_id

    Optional query parameters:
    - year: Filter charges by year (must be provided with month)
    - month: Filter charges by month (must be provided with year)
    - unpaid: Filter by unpaid charges (when True, returns only charges with payment_date is None)
    - apartment: Filter by apartment ID
    """
    # Validate that both year and month are provided together if one is provided
    if (year is None) != (month is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both year and month must be provided together, or neither",
        )

    if current_user.role.name in ("admin", "accountant"):
        charges = charge_repo.get_all_charges(
            db, year=year, month=month, unpaid=unpaid, apartment_id=apartment
        )
    elif current_user.role.name == "tenant":
        charges = charge_repo.get_visible_charges_by_user_id(
            db,
            current_user.id,
            year=year,
            month=month,
            unpaid=unpaid,
            apartment_id=apartment,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return [Charge.model_validate(charge) for charge in charges]


@router.get("/latest-adjusted", response_model=Charge)
def get_latest_adjusted_charge(
    contract_id: int = Query(
        ..., description="Contract ID to get the latest adjusted charge for"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Get the latest charge with is_adjusted=True for a specific contract.
    Only admin users can access this endpoint.
    """
    charge = get_latest_adjusted_charge_by_contract_id(db, contract_id)
    return Charge.model_validate(charge)


@router.get("/{charge_id}", response_model=Charge)
def get_charge_by_id(
    charge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a charge by ID.
    - Admin and Accountant: can see any charge
    - Tenant: can only see visible charges for contracts with their user_id
    """
    charge = charge_repo.get_charge_by_id(db, charge_id)
    if not charge:
        raise NotFoundError("Charge not found")

    # Check access: tenant can only see visible charges for their contracts
    if current_user.role.name == "tenant":
        if not charge.is_visible or charge.contract.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    return Charge.model_validate(charge)


@router.put("/{charge_id}", response_model=Charge)
def update_charge_by_id(
    charge_id: int,
    charge_data: ChargeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Update a charge. Only admin users can update charges.

    Fields not included in the request are not updated.
    To clear a field (set to null), explicitly include it with null value.
    """
    update_data = charge_data.model_dump(exclude_unset=True)
    charge = update_charge(db, charge_id=charge_id, **update_data)
    return Charge.model_validate(charge)


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_charge_by_id(
    charge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Delete a charge by ID. Only admin users can delete charges.

    A charge can only be deleted if it has not been paid (payment_date is None).
    """
    delete_charge(db, charge_id)


@router.post("/{charge_id}/send-email", status_code=status.HTTP_200_OK)
async def send_charge_email_by_id(
    charge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Send an email to the user associated with the charge's contract containing charge information.
    Only admin users can send charge emails.

    The email includes:
    - Apartment floor and letter
    - Period
    - Rent
    - Expenses
    - Municipal tax
    - Provincial tax
    - Water bill
    - Total
    """
    return await send_charge_email(db, charge_id)
