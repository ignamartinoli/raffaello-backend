from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.user import User
from app.schemas.apartment import Apartment


class Contract(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    apartment_id: int
    start_date: date
    end_date: date | None = None
    adjustment_months: int | None = None
    user: User | None = None
    apartment: Apartment | None = None


class ContractCreate(BaseModel):
    user_id: int
    apartment_id: int
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    year: int = Field(..., ge=1900, le=2100, description="Year")
    end_date: date | None = None
    adjustment_months: int | None = Field(None, gt=0, description="Adjustment months must be greater than 0")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int) -> int:
        if not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        return v

    @field_validator("adjustment_months")
    @classmethod
    def validate_adjustment_months(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("adjustment_months must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_end_date_after_start_date(self):
        """Ensure end_date doesn't precede start_date."""
        if self.end_date is not None:
            start_date = date(self.year, self.month, 1)
            if self.end_date < start_date:
                raise ValueError(f"end_date ({self.end_date}) cannot precede start_date ({start_date})")
        return self


class ContractUpdate(BaseModel):
    user_id: int | None = None
    apartment_id: int | None = None
    month: int | None = Field(None, ge=1, le=12, description="Month (1-12)")
    year: int | None = Field(None, ge=1900, le=2100, description="Year")
    end_date: date | None = None
    adjustment_months: int | None = Field(None, gt=0, description="Adjustment months must be greater than 0")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        return v

    @field_validator("adjustment_months")
    @classmethod
    def validate_adjustment_months(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("adjustment_months must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_month_year_together(self):
        """Ensure month and year are provided together."""
        if (self.month is None) != (self.year is None):
            raise ValueError("Both month and year must be provided together, or neither")
        return self

    @model_validator(mode="after")
    def validate_end_date_after_start_date(self):
        """Ensure end_date doesn't precede start_date."""
        if self.end_date is not None and (self.month is not None and self.year is not None):
            start_date = date(self.year, self.month, 1)
            if self.end_date < start_date:
                raise ValueError(f"end_date ({self.end_date}) cannot precede start_date ({start_date})")
        return self
