"""Async image operations for registry."""

from typing import Any

import aiohttp

from ..core.session import create_session, make_get_request
from ..core.types import RegistryConfig
from ..exceptions import RegistryError
from .manifests import delete_manifest, get_manifest


def calculate_total_size(manifest: dict[str, Any], config_size: int) -> int:
    """Calculate total size of image from manifest.

    Args:
        manifest: Manifest dictionary
        config_size: Size of config blob

    Returns:
        Total size in bytes
    """
    layers_size = sum(layer.get("size", 0) for layer in manifest.get("layers", []))
    return int(config_size + layers_size)


async def get_config_blob(
    session: aiohttp.ClientSession,
    config: RegistryConfig,
    repository: str,
    config_digest: str,
) -> dict[str, Any]:
    """Get config blob from registry.

    Args:
        session: HTTP session
        config: Registry configuration
        repository: Repository name
        config_digest: Config blob digest

    Returns:
        Config blob data
    """
    config_url = f"{config.base_url}/v2/{repository}/blobs/{config_digest}"
    result = await make_get_request(session, config_url, config, expect_json=True)

    if not result.json_data:
        raise RegistryError(f"Invalid config blob response for {config_digest}")

    return result.json_data


def create_image_info(
    repository: str, tag: str, manifest: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Create image info dictionary.

    Args:
        repository: Repository name
        tag: Tag name
        manifest: Manifest data
        config: Config data

    Returns:
        Image info dictionary
    """
    config_info = manifest.get("config", {})
    total_size = calculate_total_size(manifest, config_info.get("size", 0))

    return {
        "repository": repository,
        "tag": tag,
        "digest": manifest.get("digest"),
        "manifest": manifest,
        "config": config,
        "architecture": config.get("architecture"),
        "os": config.get("os"),
        "created": config.get("created"),
        "total_size": total_size,
        "layer_count": len(manifest.get("layers", [])),
    }


async def get_image_info(
    config: RegistryConfig, repository: str, tag: str
) -> dict[str, Any]:
    """Get detailed image information.

    Args:
        config: Registry configuration
        repository: Repository name
        tag: Tag name

    Returns:
        Dictionary with image information

    Raises:
        RegistryError: If request fails
    """
    # Get manifest first
    manifest = await get_manifest(config, repository, tag)

    # Extract config blob info
    config_info = manifest.get("config", {})
    config_digest = config_info.get("digest")

    if not config_digest:
        return {
            "repository": repository,
            "tag": tag,
            "manifest": manifest,
            "config": None,
        }

    # Get config blob
    session = await create_session()
    try:
        config_blob = await get_config_blob(session, config, repository, config_digest)
        return create_image_info(repository, tag, manifest, config_blob)

    except Exception as e:
        raise RegistryError(f"Failed to get config for {repository}:{tag}: {e}") from e
    finally:
        await session.close()


async def delete_image(config: RegistryConfig, repository: str, tag: str) -> bool:
    """Delete an image from registry.

    Args:
        config: Registry configuration
        repository: Repository name
        tag: Tag name

    Returns:
        True if deletion successful

    Raises:
        RegistryError: If deletion fails
    """
    # Get manifest to get digest
    manifest = await get_manifest(config, repository, tag)
    manifest_digest = manifest.get("digest")

    if not manifest_digest:
        raise RegistryError(f"Could not get digest for {repository}:{tag}")

    # Delete using digest
    return await delete_manifest(config, repository, manifest_digest)


async def delete_image_by_digest(
    config: RegistryConfig, repository: str, digest: str
) -> bool:
    """Delete an image by its digest.

    Args:
        config: Registry configuration
        repository: Repository name
        digest: Manifest digest

    Returns:
        True if deletion successful

    Raises:
        RegistryError: If deletion fails
    """
    return await delete_manifest(config, repository, digest)
