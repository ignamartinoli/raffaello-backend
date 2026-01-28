from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, extract

from app.db.models.charge import Charge as ChargeModel
from app.db.models.contract import Contract as ContractModel
from app.errors import NotFoundError


def get_charge_by_id(db: Session, charge_id: int) -> ChargeModel | None:
    """Get a charge by ID with contract relationship loaded."""
    return (
        db.query(ChargeModel)
        .options(joinedload(ChargeModel.contract).joinedload(ContractModel.user))
        .options(joinedload(ChargeModel.contract).joinedload(ContractModel.apartment))
        .filter(ChargeModel.id == charge_id)
        .first()
    )


def get_all_charges(
    db: Session,
    year: int | None = None,
    month: int | None = None,
    unpaid: bool | None = None,
    apartment_id: int | None = None,
) -> list[ChargeModel]:
    """Get all charges, optionally filtered by year, month, unpaid status, and apartment ID."""
    query = db.query(ChargeModel)

    if apartment_id is not None:
        query = query.join(ContractModel).filter(
            ContractModel.apartment_id == apartment_id
        )

    if year is not None and month is not None:
        query = query.filter(
            and_(
                extract("year", ChargeModel.period) == year,
                extract("month", ChargeModel.period) == month,
            )
        )

    if unpaid is not None:
        if unpaid:
            query = query.filter(ChargeModel.payment_date.is_(None))
        else:
            query = query.filter(ChargeModel.payment_date.isnot(None))

    return query.all()


def get_charges_by_contract_id(db: Session, contract_id: int) -> list[ChargeModel]:
    """Get all charges for a specific contract."""
    return db.query(ChargeModel).filter(ChargeModel.contract_id == contract_id).all()


def get_visible_charges_by_user_id(
    db: Session,
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    unpaid: bool | None = None,
    apartment_id: int | None = None,
) -> list[ChargeModel]:
    """
    Get all visible charges for contracts belonging to a specific user.
    Used for tenant access - tenants can only see charges that are visible and belong to their contracts.
    Optionally filtered by year, month, unpaid status, and apartment ID.
    """
    query = (
        db.query(ChargeModel)
        .join(ContractModel)
        .filter(and_(ContractModel.user_id == user_id, ChargeModel.is_visible == True))
    )

    if apartment_id is not None:
        query = query.filter(ContractModel.apartment_id == apartment_id)

    if year is not None and month is not None:
        query = query.filter(
            and_(
                extract("year", ChargeModel.period) == year,
                extract("month", ChargeModel.period) == month,
            )
        )

    if unpaid is not None:
        if unpaid:
            query = query.filter(ChargeModel.payment_date.is_(None))
        else:
            query = query.filter(ChargeModel.payment_date.isnot(None))

    return query.all()


def get_charge_by_contract_and_period(
    db: Session,
    contract_id: int,
    period: date,
) -> ChargeModel | None:
    """Get a charge by contract_id and period. Used to check for duplicates."""
    return (
        db.query(ChargeModel)
        .filter(
            ChargeModel.contract_id == contract_id,
            ChargeModel.period == period,
        )
        .first()
    )


def create_charge(
    db: Session,
    contract_id: int,
    period: date,
    rent: int,
    expenses: int,
    municipal_tax: int,
    provincial_tax: int,
    water_bill: int,
    is_adjusted: bool,
    is_visible: bool = False,
    payment_date: date | None = None,
) -> ChargeModel:
    """Create a new charge in the database. Pure data access - no business logic."""
    db_charge = ChargeModel(
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
    db.add(db_charge)
    db.commit()
    db.refresh(db_charge)
    return db_charge


def update_charge(
    db: Session,
    charge_id: int,
    **kwargs,
) -> ChargeModel:
    """
    Update a charge. Only updates fields that are explicitly provided.

    To clear a field (set to None), explicitly pass it with None value.
    Fields not provided are not updated.
    """
    charge = get_charge_by_id(db, charge_id)
    if not charge:
        raise NotFoundError("Charge not found")

    # Update only the fields that were explicitly provided
    if "contract_id" in kwargs:
        charge.contract_id = kwargs["contract_id"]
    if "period" in kwargs:
        charge.period = kwargs["period"]
    if "rent" in kwargs:
        charge.rent = kwargs["rent"]
    if "expenses" in kwargs:
        charge.expenses = kwargs["expenses"]
    if "municipal_tax" in kwargs:
        charge.municipal_tax = kwargs["municipal_tax"]
    if "provincial_tax" in kwargs:
        charge.provincial_tax = kwargs["provincial_tax"]
    if "water_bill" in kwargs:
        charge.water_bill = kwargs["water_bill"]
    if "is_adjusted" in kwargs:
        charge.is_adjusted = kwargs["is_adjusted"]
    if "is_visible" in kwargs:
        charge.is_visible = kwargs["is_visible"]
    if "payment_date" in kwargs:
        charge.payment_date = kwargs["payment_date"]  # Can be None to clear

    db.commit()
    db.refresh(charge)
    return charge
