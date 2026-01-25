from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.contract import Contract


class Charge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    period: date
    rent: int
    expenses: int
    municipal_tax: int
    provincial_tax: int
    water_bill: int
    is_adjusted: bool
    is_visible: bool
    payment_date: date | None = None
    contract: Contract | None = None


class ChargeCreate(BaseModel):
    contract_id: int
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    year: int = Field(..., ge=1900, le=2100, description="Year")
    rent: int = Field(..., ge=0, description="Rent amount (must be >= 0)")
    expenses: int = Field(..., ge=0, description="Expenses amount (must be >= 0)")
    municipal_tax: int = Field(..., ge=0, description="Municipal tax amount (must be >= 0)")
    provincial_tax: int = Field(..., ge=0, description="Provincial tax amount (must be >= 0)")
    water_bill: int = Field(..., ge=0, description="Water bill amount (must be >= 0)")
    is_adjusted: bool = Field(..., description="Whether this charge is adjusted")
    is_visible: bool = Field(default=False, description="Whether this charge is visible to tenants")
    payment_date: date | None = Field(None, description="Payment date (optional)")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int) -> int:
        if not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        return v


class ChargeUpdate(BaseModel):
    contract_id: int | None = None
    month: int | None = Field(None, ge=1, le=12, description="Month (1-12)")
    year: int | None = Field(None, ge=1900, le=2100, description="Year")
    rent: int | None = Field(None, ge=0, description="Rent amount (must be >= 0)")
    expenses: int | None = Field(None, ge=0, description="Expenses amount (must be >= 0)")
    municipal_tax: int | None = Field(None, ge=0, description="Municipal tax amount (must be >= 0)")
    provincial_tax: int | None = Field(None, ge=0, description="Provincial tax amount (must be >= 0)")
    water_bill: int | None = Field(None, ge=0, description="Water bill amount (must be >= 0)")
    is_adjusted: bool | None = None
    is_visible: bool | None = None
    payment_date: date | None = Field(None, description="Payment date (can be set to null to clear)")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        return v

    @model_validator(mode="after")
    def validate_month_year_together(self):
        """Ensure month and year are provided together."""
        if (self.month is None) != (self.year is None):
            raise ValueError("Both month and year must be provided together, or neither")
        return self
