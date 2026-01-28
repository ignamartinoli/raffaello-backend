"""Global exception handlers that map domain exceptions to HTTP responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.errors import (
    DUPLICATE_RESOURCE,
    FORBIDDEN,
    NOT_FOUND,
    UNAUTHORIZED,
    VALIDATION_ERROR,
    DomainValidationError,
    DuplicateResourceError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.schemas.error import ErrorResponse


def _error_response(status_code: int, detail: str, code: str) -> JSONResponse:
    """Return a standardized error response with detail and machine-readable code."""
    body = ErrorResponse(detail=detail, code=code)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def domain_validation_error_handler(
    _request: Request, exc: DomainValidationError
) -> JSONResponse:
    return _error_response(
        status.HTTP_400_BAD_REQUEST,
        str(exc),
        VALIDATION_ERROR,
    )


def duplicate_resource_error_handler(
    _request: Request, exc: DuplicateResourceError
) -> JSONResponse:
    return _error_response(
        status.HTTP_409_CONFLICT,
        str(exc),
        DUPLICATE_RESOURCE,
    )


def not_found_error_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(
        status.HTTP_404_NOT_FOUND,
        str(exc),
        NOT_FOUND,
    )


def forbidden_error_handler(_request: Request, exc: ForbiddenError) -> JSONResponse:
    return _error_response(
        status.HTTP_403_FORBIDDEN,
        str(exc),
        FORBIDDEN,
    )


def unauthorized_error_handler(_request: Request, exc: UnauthorizedError) -> JSONResponse:
    return _error_response(
        status.HTTP_401_UNAUTHORIZED,
        str(exc),
        UNAUTHORIZED,
    )


def register_exception_handlers(app):
    """Register domain exception handlers on the FastAPI app."""
    app.add_exception_handler(DomainValidationError, domain_validation_error_handler)
    app.add_exception_handler(DuplicateResourceError, duplicate_resource_error_handler)
    app.add_exception_handler(ForbiddenError, forbidden_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(UnauthorizedError, unauthorized_error_handler)
