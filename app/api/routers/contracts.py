from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_user
from app.services.contract import create_contract, update_contract
import app.repositories.contract as contract_repo
from app.schemas.contract import Contract, ContractCreate, ContractUpdate
from app.db.models.user import User

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("", response_model=Contract, status_code=status.HTTP_201_CREATED)
def create_new_contract(
    contract_data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Create a new contract. Only admin users can create contracts.
    """
    try:
        contract = create_contract(
            db,
            user_id=contract_data.user_id,
            apartment_id=contract_data.apartment_id,
            month=contract_data.month,
            year=contract_data.year,
            end_date=contract_data.end_date,
            adjustment_months=contract_data.adjustment_months,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return Contract.model_validate(contract)


@router.get("", response_model=list[Contract])
def get_all_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all contracts.
    - Admin and Accountant: can see all contracts
    - Tenant: can only see contracts with their user_id
    """
    if current_user.role.name in ("admin", "accountant"):
        contracts = contract_repo.get_all_contracts(db)
    elif current_user.role.name == "tenant":
        contracts = contract_repo.get_contracts_by_user_id(db, current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return [Contract.model_validate(contract) for contract in contracts]


@router.get("/{contract_id}", response_model=Contract)
def get_contract_by_id(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a contract by ID.
    - Admin and Accountant: can see any contract
    - Tenant: can only see contracts with their user_id
    """
    contract = contract_repo.get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    
    # Check access: tenant can only see their own contracts
    if current_user.role.name == "tenant" and contract.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return Contract.model_validate(contract)


@router.put("/{contract_id}", response_model=Contract)
def update_contract_by_id(
    contract_id: int,
    contract_data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Update a contract. Only admin users can update contracts.
    
    Fields not included in the request are not updated.
    To clear a field (set to null), explicitly include it with null value.
    """
    try:
        # Get only fields that were explicitly set in the request
        update_data = contract_data.model_dump(exclude_unset=True)
        contract = update_contract(db, contract_id=contract_id, **update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return Contract.model_validate(contract)
