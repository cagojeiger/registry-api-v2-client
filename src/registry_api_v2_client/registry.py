"""Async functional registry operations."""

from typing import Any

from .core.types import RegistryConfig
from .operations.images import delete_image as _delete_image
from .operations.images import delete_image_by_digest as _delete_image_by_digest
from .operations.images import get_image_info as _get_image_info
from .operations.manifests import get_manifest as _get_manifest
from .operations.repositories import list_repositories as _list_repositories
from .operations.repositories import list_tags as _list_tags


async def list_repositories(registry_url: str, timeout: int = 10) -> list[str]:
    """List all repositories in registry.

    Args:
        registry_url: Registry URL
        timeout: Request timeout in seconds

    Returns:
        List of repository names

    Raises:
        RegistryError: If request fails
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _list_repositories(config)


async def list_tags(registry_url: str, repository: str, timeout: int = 10) -> list[str]:
    """List all tags for a repository.

    Args:
        registry_url: Registry URL
        repository: Repository name
        timeout: Request timeout in seconds

    Returns:
        List of tag names

    Raises:
        RegistryError: If request fails
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _list_tags(config, repository)


async def get_manifest(
    registry_url: str, repository: str, tag: str, timeout: int = 10
) -> dict[str, Any]:
    """Get manifest for an image.

    Args:
        registry_url: Registry URL
        repository: Repository name
        tag: Tag name
        timeout: Request timeout in seconds

    Returns:
        Manifest dictionary

    Raises:
        RegistryError: If request fails
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _get_manifest(config, repository, tag)


async def get_image_info(
    registry_url: str, repository: str, tag: str, timeout: int = 10
) -> dict[str, Any]:
    """Get detailed image information.

    Args:
        registry_url: Registry URL
        repository: Repository name
        tag: Tag name
        timeout: Request timeout in seconds

    Returns:
        Dictionary with image information

    Raises:
        RegistryError: If request fails
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _get_image_info(config, repository, tag)


async def delete_image(
    registry_url: str, repository: str, tag: str, timeout: int = 10
) -> bool:
    """Delete an image from registry.

    Args:
        registry_url: Registry URL
        repository: Repository name
        tag: Tag name
        timeout: Request timeout in seconds

    Returns:
        True if deletion successful

    Raises:
        RegistryError: If deletion fails
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _delete_image(config, repository, tag)


async def delete_image_by_digest(
    registry_url: str, repository: str, digest: str, timeout: int = 10
) -> bool:
    """Delete an image by its digest.

    Args:
        registry_url: Registry URL
        repository: Repository name
        digest: Manifest digest
        timeout: Request timeout in seconds

    Returns:
        True if deletion successful

    Raises:
        RegistryError: If deletion fails
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _delete_image_by_digest(config, repository, digest)
