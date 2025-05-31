"""Async manifest operations for registry."""

import hashlib
import json
from typing import Any

from ..core.session import (
    create_session,
    make_delete_request,
    make_get_request,
    make_put_request,
)
from ..core.types import ManifestInfo, RegistryConfig, RequestResult
from ..exceptions import RegistryError


def create_manifest_headers(accept_type: str | None = None) -> dict[str, str]:
    """Create headers for manifest requests."""
    headers = {}
    if accept_type:
        headers["Accept"] = accept_type
    return headers


def create_manifest_v2(manifest_info: ManifestInfo) -> dict[str, Any]:
    """Create Docker manifest v2 from manifest info.

    Args:
        manifest_info: Manifest information

    Returns:
        Manifest dictionary
    """
    return {
        "schemaVersion": manifest_info.schema_version,
        "mediaType": manifest_info.media_type,
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": manifest_info.config.size,
            "digest": manifest_info.config.digest,
        },
        "layers": [
            {"mediaType": layer.media_type, "size": layer.size, "digest": layer.digest}
            for layer in manifest_info.layers
        ],
    }


def parse_manifest_response(result: RequestResult) -> dict[str, Any]:
    """Parse manifest from response.

    Args:
        result: Request result

    Returns:
        Manifest with optional digest
    """
    if not result.json_data:
        raise RegistryError("Invalid manifest response")

    manifest = result.json_data.copy()

    # Add digest from header if available
    manifest_digest = result.headers.get("Docker-Content-Digest")
    if manifest_digest:
        manifest["digest"] = manifest_digest

    return manifest


def calculate_manifest_digest(manifest: dict[str, Any]) -> str:
    """Calculate manifest digest.

    Args:
        manifest: Manifest dictionary

    Returns:
        SHA256 digest
    """
    manifest_json = json.dumps(manifest, separators=(",", ":")).encode()
    digest = hashlib.sha256(manifest_json).hexdigest()
    return f"sha256:{digest}"


async def get_manifest(
    config: RegistryConfig,
    repository: str,
    reference: str,
    media_type: str = "application/vnd.docker.distribution.manifest.v2+json",
) -> dict[str, Any]:
    """Get manifest from registry.

    Args:
        config: Registry configuration
        repository: Repository name
        reference: Tag or digest
        media_type: Accept media type

    Returns:
        Manifest dictionary
    """
    url = f"{config.base_url}/v2/{repository}/manifests/{reference}"
    headers = create_manifest_headers(media_type)

    session = await create_session()
    try:
        result = await make_get_request(session, url, config, headers, expect_json=True)
        return parse_manifest_response(result)
    finally:
        await session.close()


async def upload_manifest(
    config: RegistryConfig, repository: str, reference: str, manifest: dict[str, Any]
) -> str:
    """Upload manifest to registry.

    Args:
        config: Registry configuration
        repository: Repository name
        reference: Tag or digest
        manifest: Manifest dictionary

    Returns:
        Manifest digest
    """
    url = f"{config.base_url}/v2/{repository}/manifests/{reference}"
    manifest_json = json.dumps(manifest, separators=(",", ":"))

    headers = {"Content-Type": "application/vnd.docker.distribution.manifest.v2+json"}

    session = await create_session()
    try:
        result = await make_put_request(session, url, config, headers, manifest_json)

        # Return digest from header or calculate it
        manifest_digest = result.headers.get("Docker-Content-Digest")
        return manifest_digest or calculate_manifest_digest(manifest)

    finally:
        await session.close()


async def delete_manifest(config: RegistryConfig, repository: str, digest: str) -> bool:
    """Delete manifest from registry.

    Args:
        config: Registry configuration
        repository: Repository name
        digest: Manifest digest

    Returns:
        True if deletion successful
    """
    url = f"{config.base_url}/v2/{repository}/manifests/{digest}"

    session = await create_session()
    try:
        await make_delete_request(session, url, config)
        return True
    finally:
        await session.close()
