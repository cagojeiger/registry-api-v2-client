"""Tar file validation utilities for Docker image tar files."""

import json
import tarfile
from pathlib import Path
from typing import Any

from ..exceptions import ValidationError


def validate_docker_tar(tar_path: Path) -> bool:
    """
    Validate if a tar file is a valid Docker image tar file.

    Args:
        tar_path: Path to the tar file to validate

    Returns:
        True if valid Docker image tar file, False otherwise

    Raises:
        ValidationError: If tar file is corrupted or invalid format
    """
    try:
        if not tar_path.exists():
            raise ValidationError(f"Tar file does not exist: {tar_path}")

        if not tarfile.is_tarfile(tar_path):
            return False

        with tarfile.open(tar_path, "r") as tar:
            # Check for required files
            required_files = ["manifest.json"]
            tar_members = {member.name for member in tar.getmembers()}

            for required_file in required_files:
                if required_file not in tar_members:
                    return False

            # Validate manifest.json structure
            try:
                manifest_member = tar.extractfile("manifest.json")
                if manifest_member is None:
                    return False

                manifest_content = manifest_member.read().decode("utf-8")
                manifest_data = json.loads(manifest_content)

                if not isinstance(manifest_data, list) or len(manifest_data) == 0:
                    return False

                # Validate each image in manifest
                for image in manifest_data:
                    if not _validate_manifest_entry(image, tar_members):
                        return False

            except (json.JSONDecodeError, UnicodeDecodeError):
                return False

        return True

    except (tarfile.TarError, OSError) as e:
        raise ValidationError(f"Error reading tar file: {e}") from e


def _validate_manifest_entry(
    manifest_entry: dict[str, Any], tar_members: set[str]
) -> bool:
    """Validate a single manifest entry."""
    required_fields = ["Config", "Layers"]

    for field in required_fields:
        if field not in manifest_entry:
            return False

    # Check if config file exists in tar
    config_path = manifest_entry["Config"]
    if config_path not in tar_members:
        return False

    # Check if all layer files exist in tar
    layers = manifest_entry["Layers"]
    if not isinstance(layers, list):
        return False

    return all(layer in tar_members for layer in layers)


def get_tar_manifest(tar_path: Path) -> list[dict[str, Any]]:
    """
    Extract and return the manifest from a Docker tar file.

    Args:
        tar_path: Path to the tar file

    Returns:
        List of manifest entries

    Raises:
        ValidationError: If tar file is invalid or manifest cannot be read
    """
    if not validate_docker_tar(tar_path):
        raise ValidationError(f"Invalid Docker tar file: {tar_path}")

    try:
        with tarfile.open(tar_path, "r") as tar:
            manifest_member = tar.extractfile("manifest.json")
            if manifest_member is None:
                raise ValidationError("Cannot extract manifest.json")

            manifest_content = manifest_member.read().decode("utf-8")
            return json.loads(manifest_content)  # type: ignore[no-any-return]

    except (tarfile.TarError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValidationError(f"Error reading manifest: {e}") from e
