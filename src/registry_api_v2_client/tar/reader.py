"""Docker tar file reader implementation."""

import asyncio
import json
import tarfile
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, Optional

import aiofiles

from ..exceptions import TarReadError
from ..utils.digest import calculate_digest
from .models import ImageInfo, LayerInfo


class TarImageReader:
    """Async reader for Docker save tar files."""

    def __init__(self, tar_path: str) -> None:
        """Initialize tar reader.

        Args:
            tar_path: Path to the tar file
        """
        self.tar_path = Path(tar_path)
        if not self.tar_path.exists():
            raise TarReadError(f"Tar file not found: {tar_path}")
        self._tar_file: Optional[tarfile.TarFile] = None

    async def __aenter__(self) -> "TarImageReader":
        """Enter async context manager."""
        loop = asyncio.get_event_loop()
        self._tar_file = await loop.run_in_executor(
            None, tarfile.open, str(self.tar_path), "r"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()

    async def close(self) -> None:
        """Close the tar file."""
        if self._tar_file:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._tar_file.close)
            self._tar_file = None

    async def get_manifest(self) -> Dict:
        """Get the manifest.json from the tar file.

        Returns:
            Manifest dictionary

        Raises:
            TarReadError: If manifest cannot be read
        """
        try:
            loop = asyncio.get_event_loop()
            manifest_data = await loop.run_in_executor(
                None, self._extract_file_content, "manifest.json"
            )
            return json.loads(manifest_data)
        except Exception as e:
            raise TarReadError(f"Failed to read manifest.json: {e}") from e

    async def get_config(self, config_digest: str) -> bytes:
        """Get image configuration JSON.

        Args:
            config_digest: Config blob digest (with sha256: prefix)

        Returns:
            Config JSON bytes

        Raises:
            TarReadError: If config cannot be read
        """
        # Remove sha256: prefix if present
        config_hash = config_digest.replace("sha256:", "")
        config_filename = f"{config_hash}.json"

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._extract_file_content, config_filename
            )
        except Exception as e:
            raise TarReadError(f"Failed to read config {config_filename}: {e}") from e

    async def get_layer_stream(
        self, layer_path: str, chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """Get layer data as an async stream.

        Args:
            layer_path: Path to layer file in tar
            chunk_size: Size of chunks to yield

        Yields:
            Chunks of layer data

        Raises:
            TarReadError: If layer cannot be read
        """
        try:
            # Extract layer to temporary file
            loop = asyncio.get_event_loop()
            member = await loop.run_in_executor(
                None, self._tar_file.getmember, layer_path
            )
            
            # Use extractfile to get a file-like object
            layer_file = await loop.run_in_executor(
                None, self._tar_file.extractfile, member
            )
            
            if layer_file is None:
                raise TarReadError(f"Could not extract layer {layer_path}")

            # Read and yield chunks
            while True:
                chunk = await loop.run_in_executor(None, layer_file.read, chunk_size)
                if not chunk:
                    break
                yield chunk

            # Close the file
            await loop.run_in_executor(None, layer_file.close)

        except Exception as e:
            raise TarReadError(f"Failed to read layer {layer_path}: {e}") from e

    async def get_repositories(self) -> Dict:
        """Get repositories information.

        Returns:
            Repositories dictionary

        Raises:
            TarReadError: If repositories cannot be read
        """
        try:
            loop = asyncio.get_event_loop()
            repos_data = await loop.run_in_executor(
                None, self._extract_file_content, "repositories"
            )
            return json.loads(repos_data)
        except Exception as e:
            # repositories file is optional
            return {}

    async def extract_image_info(self) -> ImageInfo:
        """Extract complete image information from tar.

        Returns:
            ImageInfo object

        Raises:
            TarReadError: If image info cannot be extracted
        """
        # Get manifest
        manifest_list = await self.get_manifest()
        if not manifest_list:
            raise TarReadError("Empty manifest")

        # Use first manifest entry
        manifest = manifest_list[0]
        config_filename = manifest["Config"]
        config_digest = f"sha256:{config_filename.replace('.json', '')}"

        # Get config
        config_data = await self.get_config(config_digest)
        config = json.loads(config_data)

        # Get repositories
        repos = await self.get_repositories()
        
        # Extract repository and tag
        repository = "unknown"
        tag = "latest"
        
        if repos:
            # repositories file format: {"repo/name": {"tag": "layer_id"}}
            for repo_name, tags in repos.items():
                repository = repo_name
                if tags:
                    tag = list(tags.keys())[0]
                break
        elif manifest.get("RepoTags"):
            # Fallback to RepoTags in manifest
            repo_tag = manifest["RepoTags"][0]
            if ":" in repo_tag:
                repository, tag = repo_tag.rsplit(":", 1)
            else:
                repository = repo_tag

        # Process layers
        layers = []
        layer_paths = manifest["Layers"]
        
        loop = asyncio.get_event_loop()
        for layer_path in layer_paths:
            # Calculate layer digest
            layer_data = await loop.run_in_executor(
                None, self._extract_file_content, layer_path
            )
            layer_digest = calculate_digest(layer_data)
            
            # Get layer size
            member = await loop.run_in_executor(
                None, self._tar_file.getmember, layer_path
            )
            
            layers.append(
                LayerInfo(
                    digest=layer_digest,
                    size=member.size,
                    media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
                    tar_path=layer_path,
                )
            )

        # Calculate total size
        total_size = len(config_data) + sum(layer.size for layer in layers)

        # Parse creation time
        created_str = config.get("created", "")
        if created_str:
            # Docker uses RFC3339 format
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        else:
            created = datetime.now()

        return ImageInfo(
            repository=repository,
            tag=tag,
            config_digest=config_digest,
            layers=layers,
            architecture=config.get("architecture", "amd64"),
            os=config.get("os", "linux"),
            created=created,
            size=total_size,
        )

    def _extract_file_content(self, filename: str) -> bytes:
        """Extract file content from tar (sync helper).

        Args:
            filename: Name of file to extract

        Returns:
            File content as bytes

        Raises:
            TarReadError: If file cannot be extracted
        """
        if not self._tar_file:
            raise TarReadError("Tar file not opened")

        try:
            member = self._tar_file.getmember(filename)
            file_obj = self._tar_file.extractfile(member)
            if file_obj is None:
                raise TarReadError(f"Could not extract {filename}")
            
            content = file_obj.read()
            file_obj.close()
            return content
        except KeyError:
            raise TarReadError(f"File {filename} not found in tar")
        except Exception as e:
            raise TarReadError(f"Failed to extract {filename}: {e}") from e