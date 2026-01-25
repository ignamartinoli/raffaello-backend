"""Custom exceptions for the application."""


class DuplicateResourceError(ValueError):
    """Raised when attempting to create or update a resource that would violate a uniqueness constraint."""
    pass
