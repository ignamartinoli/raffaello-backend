from sqlalchemy import Column, Integer, Boolean, String

from app.db.base import Base


class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    floor = Column(Integer, nullable=False)
    letter = Column(String(1), nullable=False)
    is_mine = Column(Boolean, nullable=False)
    ecogas = Column(Integer, nullable=True)
    epec_client = Column(Integer, nullable=True)
    epec_contract = Column(Integer, nullable=True)
    water = Column(Integer, nullable=True)
