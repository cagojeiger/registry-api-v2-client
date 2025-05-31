"""Type definitions for registry operations."""

from dataclasses import dataclass
from typing import Any, NamedTuple


@dataclass(frozen=True)
class RegistryConfig:
    """Registry configuration."""

    url: str
    timeout: int = 30

    @property
    def base_url(self) -> str:
        """Get base URL without trailing slash."""
        return self.url.rstrip("/")


class RequestResult(NamedTuple):
    """Result of an HTTP request."""

    status_code: int
    headers: dict[str, str]
    data: bytes | None = None
    json_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class BlobInfo:
    """Information about a blob."""

    digest: str
    size: int
    media_type: str = "application/octet-stream"

    @property
    def digest_short(self) -> str:
        """Get short digest (first 12 chars)."""
        return (
            self.digest.split(":")[1][:12] if ":" in self.digest else self.digest[:12]
        )


@dataclass(frozen=True)
class ManifestInfo:
    """Information about a manifest."""

    schema_version: int
    media_type: str
    config: BlobInfo
    layers: tuple[BlobInfo, ...]
    digest: str | None = None

    @property
    def total_size(self) -> int:
        """Calculate total size of all blobs."""
        return self.config.size + sum(layer.size for layer in self.layers)


@dataclass(frozen=True)
class UploadSession:
    """Upload session information."""

    upload_url: str
    upload_uuid: str
