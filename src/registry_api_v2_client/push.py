"""Async functional style push operations."""

import asyncio

from .core.connectivity import check_connectivity
from .core.types import BlobInfo, ManifestInfo, RegistryConfig
from .exceptions import RegistryError
from .operations.blobs import upload_blob
from .operations.manifests import create_manifest_v2, upload_manifest
from .tar.processor import process_tar_file
from .tar.tags import extract_original_tags, get_primary_tag, parse_repository_tag


async def upload_all_blobs(
    config: RegistryConfig, repository: str, tar_path: str, blob_infos: list[BlobInfo]
) -> list[str]:
    """Upload all blobs concurrently to registry.

    Args:
        config: Registry configuration
        repository: Repository name
        tar_path: Path to tar file
        blob_infos: List of blob information

    Returns:
        List of uploaded blob digests
    """
    # Upload blobs concurrently for better performance
    tasks = [
        upload_blob(config, repository, tar_path, blob_info) for blob_info in blob_infos
    ]

    return await asyncio.gather(*tasks)


async def create_and_upload_manifest(
    config: RegistryConfig, repository: str, tag: str, manifest_info: ManifestInfo
) -> str:
    """Create manifest and upload to registry.

    Args:
        config: Registry configuration
        repository: Repository name
        tag: Tag name
        manifest_info: Manifest information

    Returns:
        Manifest digest
    """
    # Create manifest
    manifest = create_manifest_v2(manifest_info)

    # Upload manifest
    return await upload_manifest(config, repository, tag, manifest)


async def check_registry_connectivity(registry_url: str) -> bool:
    """Check registry connectivity.

    Args:
        registry_url: Registry URL

    Returns:
        True if registry is accessible

    Raises:
        RegistryError: If connectivity check fails
    """
    config = RegistryConfig(url=registry_url)
    return await check_connectivity(config)


async def push_docker_tar(
    tar_path: str,
    registry_url: str,
    repository: str | None = None,
    tag: str | None = None,
    timeout: int = 300,
) -> str:
    """Push Docker tar file to registry asynchronously.

    This function automatically extracts the original repository and tag from the tar file
    if not explicitly provided. This allows pushing images with their original tags.

    Args:
        tar_path: Path to Docker tar file
        registry_url: Registry URL
        repository: Repository name (optional, extracted from tar if not provided)
        tag: Tag name (optional, extracted from tar if not provided)
        timeout: Request timeout in seconds

    Returns:
        Manifest digest of pushed image

    Raises:
        FileNotFoundError: If tar file doesn't exist
        RegistryError: If push operation fails or no repository/tag can be determined

    Examples:
        # Use original tags from tar file
        await push_docker_tar("nginx.tar", "http://localhost:15000")

        # Override repository but keep original tag
        await push_docker_tar("nginx.tar", "http://localhost:15000", repository="my-nginx")

        # Override both repository and tag
        await push_docker_tar("nginx.tar", "http://localhost:15000", repository="my-nginx", tag="v1.0")
    """
    # Create registry configuration
    config = RegistryConfig(url=registry_url, timeout=timeout)

    # Check connectivity first
    await check_connectivity(config)

    # Extract original tags from tar file if not provided
    original_repo: str | None = None
    original_tag: str | None = None

    if repository is None or tag is None:
        try:
            # Run tag extraction in thread pool since it involves file I/O
            primary_tag = await asyncio.get_event_loop().run_in_executor(
                None, get_primary_tag, tar_path
            )

            if primary_tag:
                original_repo, original_tag = primary_tag
        except Exception:
            # If tag extraction fails, we'll use defaults below
            pass

    # Determine final repository and tag
    final_repository = repository or original_repo
    final_tag = tag or original_tag or "latest"

    if not final_repository:
        raise RegistryError(
            "No repository specified and could not extract repository from tar file. "
            "Please provide a repository name or ensure the tar file contains valid repository tags."
        )

    # Validate and process tar file
    # This runs in thread pool since it involves file I/O
    manifest_info, validated_tar_path = await asyncio.get_event_loop().run_in_executor(
        None, process_tar_file, tar_path
    )

    # Collect all blobs (config + layers)
    all_blobs = [manifest_info.config] + list(manifest_info.layers)

    # Upload all blobs concurrently
    await upload_all_blobs(config, final_repository, validated_tar_path, all_blobs)

    # Create and upload manifest
    return await create_and_upload_manifest(
        config, final_repository, final_tag, manifest_info
    )


async def push_docker_tar_with_original_tags(
    tar_path: str, registry_url: str, timeout: int = 300
) -> str:
    """Push Docker tar file using its original repository and tag.

    This is a convenience function that always uses the original tags from the tar file.

    Args:
        tar_path: Path to Docker tar file
        registry_url: Registry URL
        timeout: Request timeout in seconds

    Returns:
        Manifest digest of pushed image

    Raises:
        FileNotFoundError: If tar file doesn't exist
        RegistryError: If push operation fails or no original tags found
    """
    return await push_docker_tar(
        tar_path=tar_path,
        registry_url=registry_url,
        repository=None,  # Force extraction from tar
        tag=None,  # Force extraction from tar
        timeout=timeout,
    )


async def push_docker_tar_with_all_original_tags(
    tar_path: str, registry_url: str, timeout: int = 300
) -> list[str]:
    """Push Docker tar file with ALL original repository tags preserved.

    This function extracts all original tags from the tar file and pushes the image
    to the registry with each of those tags, preserving the complete original image metadata.

    Args:
        tar_path: Path to Docker tar file
        registry_url: Registry URL
        timeout: Request timeout in seconds

    Returns:
        List of manifest digests for each pushed tag

    Raises:
        FileNotFoundError: If tar file doesn't exist
        RegistryError: If push operation fails or no original tags found

    Example:
        # If tar contains ["nginx:alpine", "nginx:1.21-alpine"]
        # Both tags will be pushed to the registry
        digests = await push_docker_tar_with_all_original_tags("nginx.tar", "http://localhost:15000")
    """
    # Create registry configuration
    config = RegistryConfig(url=registry_url, timeout=timeout)

    # Check connectivity first
    await check_connectivity(config)

    # Extract all original tags from tar file
    try:
        original_tags = await asyncio.get_event_loop().run_in_executor(
            None, extract_original_tags, tar_path
        )
    except Exception as e:
        raise RegistryError(
            f"Failed to extract original tags from tar file: {e}"
        ) from e

    if not original_tags:
        raise RegistryError(
            "No original tags found in tar file. "
            "Please ensure the tar file contains valid repository tags."
        )

    # Validate and process tar file once (shared for all tags)
    manifest_info, validated_tar_path = await asyncio.get_event_loop().run_in_executor(
        None, process_tar_file, tar_path
    )

    # Collect all blobs (config + layers)
    all_blobs = [manifest_info.config] + list(manifest_info.layers)

    # Upload all blobs once (they're the same for all tags)
    # We'll use the first repository for blob upload, but blobs are shared
    first_repo, _ = parse_repository_tag(original_tags[0])
    await upload_all_blobs(config, first_repo, validated_tar_path, all_blobs)

    # Push manifest for each original tag concurrently
    manifest_tasks = []
    for repo_tag in original_tags:
        repository, tag = parse_repository_tag(repo_tag)
        task = create_and_upload_manifest(config, repository, tag, manifest_info)
        manifest_tasks.append(task)

    # Execute all manifest uploads concurrently
    return await asyncio.gather(*manifest_tasks)
