"""Custom exceptions for Registry API v2 client."""


class RegistryError(Exception):
    """Base exception for all registry-related errors."""

    pass


class TarReadError(RegistryError):
    """Raised when unable to read or parse tar file."""

    pass


class ValidationError(RegistryError):
    """Raised when validation fails."""

    pass
