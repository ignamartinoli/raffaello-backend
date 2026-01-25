"""Standardized error response schema."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error body for domain exceptions (4xx)."""

    detail: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code")
