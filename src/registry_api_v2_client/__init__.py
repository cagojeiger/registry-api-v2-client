"""Registry API v2 Client - Async Docker Registry API v2 client with tar file utilities."""

__version__ = "1.2.0"
__author__ = "Kang Hee Yong"
__email__ = "cagojeiger@naver.com"

# Exceptions
# Core types for advanced usage
from .core.types import BlobInfo, ManifestInfo, RegistryConfig
from .exceptions import (
    RegistryError,
    TarReadError,
    ValidationError,
)

# Legacy models (kept for tar inspection)
from .models import ImageConfig, ImageInspect, LayerInfo

# Main Async API
from .push import (
    check_registry_connectivity,
    push_docker_tar,
    push_docker_tar_with_all_original_tags,
    push_docker_tar_with_original_tags,
)
from .registry import (
    delete_image,
    delete_image_by_digest,
    get_image_info,
    get_manifest,
    list_repositories,
    list_tags,
)
from .tar.tags import extract_original_tags, get_primary_tag, parse_repository_tag

# Utilities (sync, for tar file operations)
from .utils import get_tar_manifest, inspect_docker_tar, validate_docker_tar

__all__ = [
    # Exceptions
    "RegistryError",
    "TarReadError",
    "ValidationError",
    # Models
    "ImageConfig",
    "ImageInspect",
    "LayerInfo",
    # Utilities (sync)
    "validate_docker_tar",
    "get_tar_manifest",
    "inspect_docker_tar",
    "extract_original_tags",
    "parse_repository_tag",
    "get_primary_tag",
    # Main Async API
    "check_registry_connectivity",
    "push_docker_tar",
    "push_docker_tar_with_original_tags",
    "push_docker_tar_with_all_original_tags",
    "list_repositories",
    "list_tags",
    "get_manifest",
    "get_image_info",
    "delete_image",
    "delete_image_by_digest",
    # Core types
    "RegistryConfig",
    "BlobInfo",
    "ManifestInfo",
]
