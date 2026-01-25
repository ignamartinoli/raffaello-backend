"""Custom domain exceptions for the application."""

# Stable, machine-readable error codes for API consumers.
NOT_FOUND = "NOT_FOUND"
DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
VALIDATION_ERROR = "VALIDATION_ERROR"


class DomainError(Exception):
    """Base exception for domain/business logic errors."""

    pass


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist."""

    pass


class DuplicateResourceError(DomainError):
    """Raised when attempting to create or update a resource that would violate a uniqueness constraint."""

    pass


class DomainValidationError(DomainError):
    """Raised when business rules or domain validation fail (e.g. invalid dates, missing required fields)."""

    pass
