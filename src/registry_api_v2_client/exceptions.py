"""Custom exceptions for Registry API v2 client."""


class RegistryError(Exception):
    """Base exception for all registry-related errors."""

    pass


class RegistryConnectionError(RegistryError):
    """Raised when unable to connect to the registry."""

    pass


class BlobUploadError(RegistryError):
    """Raised when blob upload fails."""

    pass


class ManifestError(RegistryError):
    """Raised when manifest operations fail."""

    pass


class TarReadError(RegistryError):
    """Raised when unable to read or parse tar file."""

    pass