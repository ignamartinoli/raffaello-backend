from datetime import date
from sqlalchemy.orm import Session

from app.db.models.contract import Contract as ContractModel


def get_contract_by_id(db: Session, contract_id: int) -> ContractModel | None:
    """Get a contract by ID."""
    return db.query(ContractModel).filter(ContractModel.id == contract_id).first()


def get_all_contracts(db: Session) -> list[ContractModel]:
    """Get all contracts."""
    return db.query(ContractModel).all()


def get_contracts_by_user_id(db: Session, user_id: int) -> list[ContractModel]:
    """Get all contracts for a specific user."""
    return db.query(ContractModel).filter(ContractModel.user_id == user_id).all()


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
        raise ValueError("Contract not found")
    
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
    return db.query(ContractModel).filter(
        ContractModel.start_date == start_date,
        ContractModel.apartment_id == apartment_id,
    ).first()
