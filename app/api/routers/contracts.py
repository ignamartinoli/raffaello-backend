from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles, get_current_user
from app.services.contract import (
    create_contract,
    update_contract,
    delete_contract,
    list_contracts_for_user,
    get_contract_for_user,
)
from app.schemas.contract import Contract, ContractCreate, ContractUpdate
from app.schemas.pagination import PaginatedResponse
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
    contract = create_contract(
        db,
        user_id=contract_data.user_id,
        apartment_id=contract_data.apartment_id,
        start_month=contract_data.start_month,
        start_year=contract_data.start_year,
        end_month=contract_data.end_month,
        end_year=contract_data.end_year,
        adjustment_months=contract_data.adjustment_months,
    )
    return Contract.model_validate(contract)


@router.get("", response_model=PaginatedResponse[Contract])
def get_all_contracts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    user: int | None = Query(
        None, description="Filter contracts by user ID (admin only)"
    ),
    apartment: int | None = Query(
        None, description="Filter contracts by apartment ID (admin only)"
    ),
    active: bool = Query(
        True, description="Filter by active status (default: True, admin only)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all contracts with pagination and optional filters.
    - Admin: can see all contracts and use all filters (user, apartment, active)
    - Tenant: can only see contracts with their user_id (no filters allowed)
    - Accountant: not allowed to access this endpoint
    """
    contracts, total = list_contracts_for_user(
        db,
        current_user,
        page=page,
        page_size=page_size,
        user_id=user,
        apartment_id=apartment,
        active=active,
    )
    return PaginatedResponse(
        items=[Contract.model_validate(c) for c in contracts],
        total=total,
        page=page,
        page_size=page_size,
    )


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
    contract = get_contract_for_user(db, contract_id, current_user)
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
    update_data = contract_data.model_dump(exclude_unset=True)
    contract = update_contract(db, contract_id=contract_id, **update_data)
    return Contract.model_validate(contract)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract_by_id(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Delete a contract by ID. Only admin users can delete contracts.

    A contract can only be deleted if it has no associated charges.
    """
    delete_contract(db, contract_id)
