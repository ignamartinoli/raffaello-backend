from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_user
from app.services.charge import create_charge, update_charge
import app.repositories.charge as charge_repo
from app.schemas.charge import Charge, ChargeCreate, ChargeUpdate
from app.db.models.user import User

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
    try:
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return Charge.model_validate(charge)


@router.get("", response_model=list[Charge])
def get_all_charges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all charges.
    - Admin and Accountant: can see all charges
    - Tenant: can only see visible charges for contracts with their user_id
    """
    if current_user.role.name in ("admin", "accountant"):
        charges = charge_repo.get_all_charges(db)
    elif current_user.role.name == "tenant":
        charges = charge_repo.get_visible_charges_by_user_id(db, current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return [Charge.model_validate(charge) for charge in charges]


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charge not found",
        )
    
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
    try:
        # Get only fields that were explicitly set in the request
        update_data = charge_data.model_dump(exclude_unset=True)
        charge = update_charge(db, charge_id=charge_id, **update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return Charge.model_validate(charge)
