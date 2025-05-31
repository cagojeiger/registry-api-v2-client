"""Async blob operations for registry."""

import asyncio
import hashlib
import tarfile
from collections.abc import Iterator

import aiohttp

from ..core.session import (
    create_session,
    make_head_request,
    make_patch_request,
    make_post_request,
    make_put_request,
)
from ..core.types import BlobInfo, RegistryConfig, UploadSession
from ..exceptions import RegistryError


async def check_blob_exists(
    config: RegistryConfig, repository: str, digest: str
) -> bool:
    """Check if blob exists in registry.

    Args:
        config: Registry configuration
        repository: Repository name
        digest: Blob digest

    Returns:
        True if blob exists
    """
    url = f"{config.base_url}/v2/{repository}/blobs/{digest}"

    session = await create_session()
    try:
        result = await make_head_request(session, url, config)
        return result.status_code == 200
    except RegistryError:
        return False
    finally:
        await session.close()


async def extract_blob_from_tar(tar_path: str, digest: str) -> bytes:
    """Extract blob data from tar file asynchronously.

    Args:
        tar_path: Path to tar file
        digest: Blob digest

    Returns:
        Blob data as bytes

    Raises:
        RegistryError: If blob not found or digest mismatch
    """
    blob_filename = f"blobs/sha256/{digest.split(':')[1]}"

    # Run tar extraction in thread pool to avoid blocking
    def _extract_blob() -> bytes:
        with tarfile.open(tar_path, "r") as tar:
            try:
                blob_member = tar.getmember(blob_filename)
                extracted_file = tar.extractfile(blob_member)
                if extracted_file is None:
                    raise RegistryError(f"Could not extract blob from tar: {digest}")
                return extracted_file.read()
            except KeyError as e:
                raise RegistryError(f"Blob not found in tar: {digest}") from e

    blob_data: bytes = await asyncio.get_event_loop().run_in_executor(
        None, _extract_blob
    )

    # Verify digest
    calculated_digest = f"sha256:{hashlib.sha256(blob_data).hexdigest()}"
    if calculated_digest != digest:
        raise RegistryError(
            f"Blob digest mismatch. Expected: {digest}, Calculated: {calculated_digest}"
        )

    return blob_data


def chunk_data(data: bytes, chunk_size: int = 5 * 1024 * 1024) -> Iterator[bytes]:
    """Split data into chunks for upload."""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


async def start_upload(
    session: aiohttp.ClientSession, config: RegistryConfig, repository: str
) -> UploadSession:
    """Start blob upload session.

    Args:
        session: HTTP session
        config: Registry configuration
        repository: Repository name

    Returns:
        Upload session information
    """
    url = f"{config.base_url}/v2/{repository}/blobs/uploads/"

    result = await make_post_request(session, url, config)

    location = result.headers.get("Location")
    if not location:
        raise RegistryError("No Location header in upload response")

    if not location.startswith("http"):
        location = f"{config.base_url}{location}"

    upload_uuid = result.headers.get("Docker-Upload-UUID", "")

    return UploadSession(upload_url=location, upload_uuid=upload_uuid)


async def upload_chunk(
    session: aiohttp.ClientSession, location: str, config: RegistryConfig, chunk: bytes
) -> str:
    """Upload single chunk to registry.

    Args:
        session: HTTP session
        location: Upload location URL
        config: Registry configuration
        chunk: Chunk data

    Returns:
        Updated location URL
    """
    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(chunk)),
    }

    result = await make_patch_request(session, location, config, headers, chunk)

    new_location = result.headers.get("Location")
    if not new_location:
        raise RegistryError("No Location header in chunked upload response")

    if not new_location.startswith("http"):
        new_location = f"{config.base_url}{new_location}"

    return new_location


async def complete_upload(
    session: aiohttp.ClientSession, location: str, config: RegistryConfig, digest: str
) -> str:
    """Complete blob upload.

    Args:
        session: HTTP session
        location: Upload location URL
        config: Registry configuration
        digest: Expected blob digest

    Returns:
        Blob digest from registry
    """
    url = f"{location}&digest={digest}"

    headers = {"Content-Type": "application/octet-stream", "Content-Length": "0"}

    result = await make_put_request(session, url, config, headers, b"")

    return result.headers.get("Docker-Content-Digest", digest)


async def upload_blob_chunked(
    session: aiohttp.ClientSession,
    config: RegistryConfig,
    repository: str,
    blob_data: bytes,
    digest: str,
) -> str:
    """Upload blob using chunked upload.

    Args:
        session: HTTP session
        config: Registry configuration
        repository: Repository name
        blob_data: Blob data
        digest: Blob digest

    Returns:
        Blob digest from registry
    """
    # Start upload session
    upload_session = await start_upload(session, config, repository)
    location = upload_session.upload_url

    # Upload chunks
    for chunk in chunk_data(blob_data):
        location = await upload_chunk(session, location, config, chunk)

    # Complete upload
    return await complete_upload(session, location, config, digest)


async def upload_blob_monolithic(
    session: aiohttp.ClientSession,
    config: RegistryConfig,
    repository: str,
    blob_data: bytes,
    digest: str,
) -> str:
    """Upload blob in single request.

    Args:
        session: HTTP session
        config: Registry configuration
        repository: Repository name
        blob_data: Blob data
        digest: Blob digest

    Returns:
        Blob digest from registry
    """
    # Start upload session
    upload_session = await start_upload(session, config, repository)

    # Complete upload with digest
    # Use & if URL already has query parameters, otherwise use ?
    separator = "&" if "?" in upload_session.upload_url else "?"
    url = f"{upload_session.upload_url}{separator}digest={digest}"

    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(blob_data)),
    }

    result = await make_put_request(session, url, config, headers, blob_data)

    return result.headers.get("Docker-Content-Digest", digest)


async def upload_blob(
    config: RegistryConfig, repository: str, tar_path: str, blob_info: BlobInfo
) -> str:
    """Upload blob from tar file to registry.

    Args:
        config: Registry configuration
        repository: Repository name
        tar_path: Path to tar file
        blob_info: Blob information

    Returns:
        Blob digest from registry

    Raises:
        RegistryError: If upload fails
    """
    # Check if blob already exists
    if await check_blob_exists(config, repository, blob_info.digest):
        return blob_info.digest

    # Extract blob data from tar
    blob_data = await extract_blob_from_tar(tar_path, blob_info.digest)

    session = await create_session()
    try:
        # Use chunked upload for large blobs (>5MB), monolithic for smaller ones
        if len(blob_data) > 5 * 1024 * 1024:
            return await upload_blob_chunked(
                session, config, repository, blob_data, blob_info.digest
            )
        else:
            return await upload_blob_monolithic(
                session, config, repository, blob_data, blob_info.digest
            )

    except Exception as e:
        raise RegistryError(f"Failed to upload blob {blob_info.digest}: {e}") from e
    finally:
        await session.close()
