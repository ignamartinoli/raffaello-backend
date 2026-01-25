from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Charge(Base):
    __tablename__ = "charges"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    period = Column(Date, nullable=False)
    rent = Column(Integer, nullable=False)
    expenses = Column(Integer, nullable=False)
    municipal_tax = Column(Integer, nullable=False)
    provincial_tax = Column(Integer, nullable=False)
    water_bill = Column(Integer, nullable=False)
    is_adjusted = Column(Boolean, nullable=False)
    is_visible = Column(Boolean, nullable=False, default=False)
    payment_date = Column(Date, nullable=True)

    # Relationships
    contract = relationship("Contract", backref="charges")
