"""Docker Registry API v2 async client implementation."""

import asyncio
import json
from typing import AsyncIterator, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin

import aiohttp

from ..exceptions import (
    BlobUploadError,
    ManifestError,
    RegistryConnectionError,
    RegistryError,
)
from ..tar.reader import TarImageReader
from ..utils.digest import validate_digest


class RegistryClient:
    """Docker Registry API v2 async client for unauthenticated registry:2 containers."""

    def __init__(
        self,
        registry_url: str,
        timeout: int = 30,
        connector: Optional[aiohttp.TCPConnector] = None,
    ) -> None:
        """Initialize the registry client.

        Args:
            registry_url: Registry URL (e.g., http://localhost:5000)
            timeout: Request timeout in seconds
            connector: aiohttp connector for connection pooling
        """
        self.registry_url = registry_url.rstrip("/")
        self.timeout = timeout
        self.connector = connector
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "RegistryClient":
        """Enter async context manager."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()

    async def close(self) -> None:
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def check_registry_v2(self) -> bool:
        """Check if the registry supports v2 API.

        Returns:
            True if v2 API is supported
        """
        try:
            async with self.session.get(f"{self.registry_url}/v2/") as resp:
                return resp.status == 200
        except aiohttp.ClientError:
            return False

    async def push_tar(
        self,
        tar_path: str,
        repository: str,
        tag: str = "latest",
        progress_callback: Optional[Callable] = None,
        concurrent_uploads: int = 3,
    ) -> str:
        """Push a Docker tar archive to the registry.

        Args:
            tar_path: Path to the tar file created by docker save
            repository: Repository name (e.g., myapp)
            tag: Tag name
            progress_callback: Optional progress callback function
            concurrent_uploads: Number of concurrent layer uploads

        Returns:
            Manifest digest

        Raises:
            TarReadError: If unable to read the tar file
            BlobUploadError: If blob upload fails
            ManifestError: If manifest upload fails
        """
        # Check registry availability
        if not await self.check_registry_v2():
            raise RegistryConnectionError(
                f"Registry at {self.registry_url} does not support v2 API"
            )

        # Read tar file
        async with TarImageReader(tar_path) as reader:
            image_info = await reader.extract_image_info()

            # Create semaphore for concurrent uploads
            semaphore = asyncio.Semaphore(concurrent_uploads)

            async def upload_layer(layer) -> Dict:
                """Upload a single layer with concurrency control."""
                async with semaphore:
                    # Check if blob already exists
                    if not await self.check_blob_exists(repository, layer.digest):
                        # Get layer stream
                        layer_stream = reader.get_layer_stream(layer.tar_path)
                        await self.upload_blob(
                            repository,
                            layer_stream,
                            layer.digest,
                            progress_callback,
                        )

                    return {
                        "mediaType": layer.media_type,
                        "size": layer.size,
                        "digest": layer.digest,
                    }

            # Upload all layers concurrently
            upload_tasks = [upload_layer(layer) for layer in image_info.layers]
            uploaded_layers = await asyncio.gather(*upload_tasks)

            # Upload config blob
            config_data = await reader.get_config(image_info.config_digest)
            if not await self.check_blob_exists(repository, image_info.config_digest):
                await self.upload_blob(
                    repository,
                    config_data,
                    image_info.config_digest,
                    progress_callback,
                )

            # Create and upload manifest
            manifest = {
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "config": {
                    "mediaType": "application/vnd.docker.container.image.v1+json",
                    "size": len(config_data),
                    "digest": image_info.config_digest,
                },
                "layers": uploaded_layers,
            }

            return await self.upload_manifest(repository, tag, manifest)

    async def check_blob_exists(self, repository: str, digest: str) -> bool:
        """Check if a blob exists in the registry.

        Args:
            repository: Repository name
            digest: Blob digest

        Returns:
            True if blob exists
        """
        try:
            url = f"{self.registry_url}/v2/{repository}/blobs/{digest}"
            async with self.session.head(url) as resp:
                return resp.status == 200
        except aiohttp.ClientError:
            return False

    async def upload_blob(
        self,
        repository: str,
        data: Union[bytes, AsyncIterator[bytes]],
        digest: str,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """Upload a blob to the registry.

        Args:
            repository: Repository name
            data: Blob data (bytes or async iterator)
            digest: Expected blob digest
            progress_callback: Optional progress callback

        Returns:
            Blob digest

        Raises:
            BlobUploadError: If upload fails
        """
        # Validate digest format
        if not validate_digest(digest):
            raise ValueError(f"Invalid digest format: {digest}")

        try:
            # Start upload session
            url = f"{self.registry_url}/v2/{repository}/blobs/uploads/"
            async with self.session.post(url) as resp:
                resp.raise_for_status()
                upload_url = resp.headers.get("Location", "")
                if not upload_url.startswith("http"):
                    upload_url = urljoin(self.registry_url, upload_url)

            # Upload data in chunks
            chunk_size = 5 * 1024 * 1024  # 5MB
            uploaded_bytes = 0
            total_size = 0

            if hasattr(data, "__aiter__"):
                # Handle async iterator
                async for chunk in data:
                    async with self.session.patch(
                        upload_url,
                        data=chunk,
                        headers={
                            "Content-Type": "application/octet-stream",
                            "Content-Length": str(len(chunk)),
                        },
                    ) as resp:
                        resp.raise_for_status()
                        upload_url = resp.headers.get("Location", "")
                        if not upload_url.startswith("http"):
                            upload_url = urljoin(self.registry_url, upload_url)

                    uploaded_bytes += len(chunk)
                    if progress_callback:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(
                                uploaded_bytes,
                                total_size,
                                f"Uploading {digest[:12]}...",
                            )
                        else:
                            progress_callback(
                                uploaded_bytes,
                                total_size,
                                f"Uploading {digest[:12]}...",
                            )
            else:
                # Handle bytes
                total_size = len(data)
                for i in range(0, len(data), chunk_size):
                    chunk = data[i : i + chunk_size]
                    async with self.session.patch(
                        upload_url,
                        data=chunk,
                        headers={
                            "Content-Type": "application/octet-stream",
                            "Content-Length": str(len(chunk)),
                        },
                    ) as resp:
                        resp.raise_for_status()
                        upload_url = resp.headers.get("Location", "")
                        if not upload_url.startswith("http"):
                            upload_url = urljoin(self.registry_url, upload_url)

                    uploaded_bytes += len(chunk)
                    if progress_callback:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(
                                uploaded_bytes,
                                total_size,
                                f"Uploading {digest[:12]}...",
                            )
                        else:
                            progress_callback(
                                uploaded_bytes,
                                total_size,
                                f"Uploading {digest[:12]}...",
                            )

            # Finalize upload
            final_url = (
                f"{upload_url}&digest={digest}"
                if "?" in upload_url
                else f"{upload_url}?digest={digest}"
            )
            async with self.session.put(
                final_url, headers={"Content-Length": "0"}
            ) as resp:
                resp.raise_for_status()

            return digest

        except aiohttp.ClientError as e:
            raise BlobUploadError(f"Failed to upload blob: {e}") from e

    async def upload_manifest(
        self,
        repository: str,
        reference: str,
        manifest: Dict,
        media_type: str = "application/vnd.docker.distribution.manifest.v2+json",
    ) -> str:
        """Upload a manifest to the registry.

        Args:
            repository: Repository name
            reference: Tag or digest reference
            manifest: Manifest dictionary
            media_type: Manifest media type

        Returns:
            Manifest digest

        Raises:
            ManifestError: If upload fails
        """
        try:
            url = f"{self.registry_url}/v2/{repository}/manifests/{reference}"
            manifest_data = json.dumps(manifest).encode("utf-8")

            async with self.session.put(
                url,
                data=manifest_data,
                headers={
                    "Content-Type": media_type,
                    "Content-Length": str(len(manifest_data)),
                },
            ) as resp:
                resp.raise_for_status()
                return resp.headers.get("Docker-Content-Digest", "")

        except aiohttp.ClientError as e:
            raise ManifestError(f"Failed to upload manifest: {e}") from e

    async def get_manifest(
        self,
        repository: str,
        reference: str,
        accept: str = "application/vnd.docker.distribution.manifest.v2+json",
    ) -> Dict:
        """Retrieve a manifest from the registry.

        Args:
            repository: Repository name
            reference: Tag or digest reference
            accept: Accepted media type

        Returns:
            Manifest dictionary

        Raises:
            ManifestError: If retrieval fails
        """
        try:
            url = f"{self.registry_url}/v2/{repository}/manifests/{reference}"
            async with self.session.get(url, headers={"Accept": accept}) as resp:
                resp.raise_for_status()
                return await resp.json()

        except aiohttp.ClientError as e:
            raise ManifestError(f"Failed to get manifest: {e}") from e

    async def delete_manifest(self, repository: str, digest: str) -> None:
        """Delete a manifest from the registry.

        Args:
            repository: Repository name
            digest: Manifest digest

        Raises:
            ManifestError: If deletion fails
        """
        try:
            url = f"{self.registry_url}/v2/{repository}/manifests/{digest}"
            async with self.session.delete(url) as resp:
                resp.raise_for_status()

        except aiohttp.ClientError as e:
            raise ManifestError(f"Failed to delete manifest: {e}") from e

    async def list_tags(self, repository: str) -> List[str]:
        """List tags for a repository.

        Args:
            repository: Repository name

        Returns:
            List of tag names

        Raises:
            RegistryError: If listing fails
        """
        try:
            url = f"{self.registry_url}/v2/{repository}/tags/list"
            async with self.session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("tags", [])

        except aiohttp.ClientError as e:
            raise RegistryError(f"Failed to list tags: {e}") from e