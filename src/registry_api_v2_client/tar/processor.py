"""Tar file processing functions."""

from pathlib import Path
from typing import Any

from ..core.types import BlobInfo, ManifestInfo
from ..exceptions import RegistryError
from ..utils.inspect import inspect_docker_tar
from ..utils.validator import validate_docker_tar


def validate_tar_file(tar_path: str) -> None:
    """Validate tar file exists and is readable.

    Args:
        tar_path: Path to tar file

    Raises:
        FileNotFoundError: If file doesn't exist
        RegistryError: If path is not a file
    """
    tar_file = Path(tar_path)

    if not tar_file.exists():
        raise FileNotFoundError(f"Tar file not found: {tar_path}")

    if not tar_file.is_file():
        raise RegistryError(f"Path is not a file: {tar_path}")


def convert_layer_to_blob_info(layer: Any) -> BlobInfo:
    """Convert layer info to blob info.

    Args:
        layer: Layer information object

    Returns:
        BlobInfo instance
    """
    return BlobInfo(digest=layer.digest, size=layer.size, media_type=layer.media_type)


def convert_config_to_blob_info(config_digest: str, config_size: int) -> BlobInfo:
    """Convert config info to blob info.

    Args:
        config_digest: Config digest
        config_size: Config size in bytes

    Returns:
        BlobInfo instance
    """
    return BlobInfo(
        digest=config_digest,
        size=config_size,
        media_type="application/vnd.docker.container.image.v1+json",
    )


def create_manifest_info(image_info: Any) -> ManifestInfo:
    """Create manifest info from image inspection result.

    Args:
        image_info: Image inspection result

    Returns:
        ManifestInfo instance
    """
    config_blob = convert_config_to_blob_info(image_info.id, image_info.size)
    layer_blobs = tuple(
        convert_layer_to_blob_info(layer) for layer in image_info.layers
    )

    return ManifestInfo(
        schema_version=2,
        media_type="application/vnd.docker.distribution.manifest.v2+json",
        config=config_blob,
        layers=layer_blobs,
    )


def process_tar_file(tar_path: str) -> tuple[ManifestInfo, str]:
    """Process tar file and extract manifest information.

    Args:
        tar_path: Path to tar file

    Returns:
        Tuple of (ManifestInfo, tar_path)

    Raises:
        FileNotFoundError: If tar file doesn't exist
        RegistryError: If tar file is invalid
        ValidationError: If tar structure is invalid
    """
    # Validate file existence
    validate_tar_file(tar_path)

    # Validate tar structure
    validate_docker_tar(Path(tar_path))

    # Extract image information
    image_info = inspect_docker_tar(Path(tar_path))

    # Create manifest info
    manifest_info = create_manifest_info(image_info)

    return manifest_info, tar_path


def extract_image_info_from_tar(tar_path: str) -> Any:
    """Extract image information from tar file.

    Args:
        tar_path: Path to tar file

    Returns:
        Image inspection result
    """
    validate_tar_file(tar_path)
    validate_docker_tar(Path(tar_path))
    return inspect_docker_tar(Path(tar_path))
