from pydantic import BaseModel, ConfigDict, Field


class Apartment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floor: int
    letter: str = Field(..., max_length=1)
    is_mine: bool
    ecogas: int | None = None
    epec_client: int | None = None
    epec_contract: int | None = None
    water: int | None = None


class ApartmentCreate(BaseModel):
    floor: int
    letter: str = Field(..., max_length=1)
    is_mine: bool
    ecogas: int | None = None
    epec_client: int | None = None
    epec_contract: int | None = None
    water: int | None = None


class ApartmentUpdate(BaseModel):
    floor: int | None = None
    letter: str | None = Field(None, max_length=1)
    is_mine: bool | None = None
    ecogas: int | None = None
    epec_client: int | None = None
    epec_contract: int | None = None
    water: int | None = None
