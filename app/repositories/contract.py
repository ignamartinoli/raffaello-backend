from datetime import date
from sqlalchemy.orm import Session

from app.db.models.contract import Contract as ContractModel
from app.domain.contract_activity import ContractActivityPolicy
from app.errors import NotFoundError


def get_contract_by_id(db: Session, contract_id: int) -> ContractModel | None:
    """Get a contract by ID."""
    return db.query(ContractModel).filter(ContractModel.id == contract_id).first()


def get_all_contracts(db: Session) -> list[ContractModel]:
    """Get all contracts."""
    return db.query(ContractModel).all()


def get_contracts_by_user_id(db: Session, user_id: int) -> list[ContractModel]:
    """Get all contracts for a specific user."""
    return db.query(ContractModel).filter(ContractModel.user_id == user_id).all()


def get_contracts_by_apartment_id(
    db: Session, apartment_id: int
) -> list[ContractModel]:
    """Get all contracts for a specific apartment."""
    return (
        db.query(ContractModel).filter(ContractModel.apartment_id == apartment_id).all()
    )


def create_contract(
    db: Session,
    user_id: int,
    apartment_id: int,
    start_date: date,
    end_date: date | None = None,
    adjustment_months: int | None = None,
) -> ContractModel:
    """Create a new contract in the database. Pure data access - no business logic."""
    db_contract = ContractModel(
        user_id=user_id,
        apartment_id=apartment_id,
        start_date=start_date,
        end_date=end_date,
        adjustment_months=adjustment_months,
    )
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract


def update_contract(
    db: Session,
    contract_id: int,
    **kwargs,
) -> ContractModel:
    """
    Update a contract. Only updates fields that are explicitly provided.

    To clear a field (set to None), explicitly pass it with None value.
    Fields not provided are not updated.
    """
    contract = get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundError("Contract not found")

    # Update only the fields that were explicitly provided
    if "user_id" in kwargs:
        contract.user_id = kwargs["user_id"]
    if "apartment_id" in kwargs:
        contract.apartment_id = kwargs["apartment_id"]
    if "start_date" in kwargs:
        contract.start_date = kwargs["start_date"]
    if "end_date" in kwargs:
        contract.end_date = kwargs["end_date"]  # Can be None to clear
    if "adjustment_months" in kwargs:
        contract.adjustment_months = kwargs["adjustment_months"]  # Can be None to clear

    db.commit()
    db.refresh(contract)
    return contract


def get_contract_by_start_date_and_apartment(
    db: Session,
    start_date: date,
    apartment_id: int,
) -> ContractModel | None:
    """Get a contract by start_date and apartment_id. Used to check for duplicates."""
    return (
        db.query(ContractModel)
        .filter(
            ContractModel.start_date == start_date,
            ContractModel.apartment_id == apartment_id,
        )
        .first()
    )


def get_all_contracts_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 100,
    user_id: int | None = None,
    apartment_id: int | None = None,
    active: bool = True,
) -> tuple[list[ContractModel], int]:
    """
    Get all contracts with pagination and optional filters.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        user_id: Optional filter by user ID
        apartment_id: Optional filter by apartment ID
        active: Filter by active status (default True). The "active" definition
                is a domain rule centralized in ContractActivityPolicy.

    Returns:
        Tuple of (list of contracts, total count)
    """
    query = db.query(ContractModel)

    # Apply user_id filter if provided
    if user_id is not None:
        query = query.filter(ContractModel.user_id == user_id)

    # Apply apartment_id filter if provided
    if apartment_id is not None:
        query = query.filter(ContractModel.apartment_id == apartment_id)

    # Apply active filter
    policy = ContractActivityPolicy(as_of=date.today())
    if active:
        query = query.filter(
            policy.sqlalchemy_active_predicate(
                start_col=ContractModel.start_date,
                end_col=ContractModel.end_date,
            )
        )
    else:
        query = query.filter(
            policy.sqlalchemy_inactive_predicate(
                start_col=ContractModel.start_date,
                end_col=ContractModel.end_date,
            ),
        )

    total = query.count()
    skip = (page - 1) * page_size
    contracts = (
        query.order_by(ContractModel.start_date.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )
    return contracts, total


def delete_contract(db: Session, contract_id: int) -> None:
    """Delete a contract from the database. Pure data access - no business logic."""
    contract = get_contract_by_id(db, contract_id)
    if not contract:
        raise NotFoundError("Contract not found")

    db.delete(contract)
    db.commit()
