import calendar
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
    start_month: int = Field(..., ge=1, le=12, description="Start month (1-12)")
    start_year: int = Field(..., ge=1900, le=2100, description="Start year")
    end_month: int | None = Field(None, ge=1, le=12, description="End month (1-12)")
    end_year: int | None = Field(None, ge=1900, le=2100, description="End year")
    adjustment_months: int | None = Field(
        None, gt=0, description="Adjustment months must be greater than 0"
    )

    @field_validator("start_month")
    @classmethod
    def validate_start_month(cls, v: int) -> int:
        if not (1 <= v <= 12):
            raise ValueError("Start month must be between 1 and 12")
        return v

    @field_validator("end_month")
    @classmethod
    def validate_end_month(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("End month must be between 1 and 12")
        return v

    @field_validator("adjustment_months")
    @classmethod
    def validate_adjustment_months(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("adjustment_months must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_start_month_year_together(self):
        """Ensure start_month and start_year are provided together."""
        # start_month and start_year are required fields, so they should always be together
        # This validator is mainly for consistency
        return self

    @model_validator(mode="after")
    def validate_end_month_year_together(self):
        """Ensure end_month and end_year are provided together."""
        if (self.end_month is None) != (self.end_year is None):
            raise ValueError(
                "Both end_month and end_year must be provided together, or neither"
            )
        return self

    @model_validator(mode="after")
    def validate_end_after_start(self):
        """Ensure end date doesn't precede start date."""
        if self.end_month is not None and self.end_year is not None:
            start_date = date(self.start_year, self.start_month, 1)
            # Calculate last day of end month
            last_day = calendar.monthrange(self.end_year, self.end_month)[1]
            end_date = date(self.end_year, self.end_month, last_day)

            if end_date < start_date:
                raise ValueError(
                    f"End date ({end_date}) cannot precede start date ({start_date})"
                )
        return self


class ContractUpdate(BaseModel):
    user_id: int | None = None
    apartment_id: int | None = None
    start_month: int | None = Field(None, ge=1, le=12, description="Start month (1-12)")
    start_year: int | None = Field(None, ge=1900, le=2100, description="Start year")
    end_month: int | None = Field(None, ge=1, le=12, description="End month (1-12)")
    end_year: int | None = Field(None, ge=1900, le=2100, description="End year")
    adjustment_months: int | None = Field(
        None, gt=0, description="Adjustment months must be greater than 0"
    )

    @field_validator("start_month")
    @classmethod
    def validate_start_month(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("Start month must be between 1 and 12")
        return v

    @field_validator("end_month")
    @classmethod
    def validate_end_month(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("End month must be between 1 and 12")
        return v

    @field_validator("adjustment_months")
    @classmethod
    def validate_adjustment_months(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("adjustment_months must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_start_month_year_together(self):
        """Ensure start_month and start_year are provided together."""
        if (self.start_month is None) != (self.start_year is None):
            raise ValueError(
                "Both start_month and start_year must be provided together, or neither"
            )
        return self

    @model_validator(mode="after")
    def validate_end_month_year_together(self):
        """Ensure end_month and end_year are provided together."""
        if (self.end_month is None) != (self.end_year is None):
            raise ValueError(
                "Both end_month and end_year must be provided together, or neither"
            )
        return self

    @model_validator(mode="after")
    def validate_end_after_start(self):
        """Ensure end date doesn't precede start date."""
        # Only validate if both start and end are provided
        if (
            self.start_month is not None
            and self.start_year is not None
            and self.end_month is not None
            and self.end_year is not None
        ):
            start_date = date(self.start_year, self.start_month, 1)
            # Calculate last day of end month
            last_day = calendar.monthrange(self.end_year, self.end_month)[1]
            end_date = date(self.end_year, self.end_month, last_day)

            if end_date < start_date:
                raise ValueError(
                    f"End date ({end_date}) cannot precede start date ({start_date})"
                )
        return self
