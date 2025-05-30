"""Tar file validation utilities for Docker image tar files."""

import json
import tarfile
from pathlib import Path
from typing import Any

from ..exceptions import ValidationError


def is_path_exists(path: Path) -> bool:
    """Check if file path exists."""
    return path.exists()


def is_valid_tarfile(path: Path) -> bool:
    """Check if file is a valid tar file."""
    return tarfile.is_tarfile(path)


def get_tar_members(tar: tarfile.TarFile) -> set[str]:
    """Extract member names from tar file."""
    return {member.name for member in tar.getmembers()}


def has_required_files(tar_members: set[str], required_files: list[str]) -> bool:
    """Check if tar contains all required files."""
    return all(required_file in tar_members for required_file in required_files)


def extract_manifest_content(tar: tarfile.TarFile) -> str | None:
    """Extract manifest.json content from tar file."""
    try:
        manifest_member = tar.extractfile("manifest.json")
        if manifest_member is None:
            return None
        return manifest_member.read().decode("utf-8")
    except (UnicodeDecodeError, KeyError):
        return None


def parse_manifest_json(manifest_content: str) -> list[dict[str, Any]] | None:
    """Parse manifest JSON content."""
    try:
        manifest_data = json.loads(manifest_content)
        if not isinstance(manifest_data, list) or len(manifest_data) == 0:
            return None
        return manifest_data
    except json.JSONDecodeError:
        return None


def has_required_fields(
    manifest_entry: dict[str, Any], required_fields: list[str]
) -> bool:
    """Check if manifest entry has all required fields."""
    return all(field in manifest_entry for field in required_fields)


def is_config_file_exists(config_path: str, tar_members: set[str]) -> bool:
    """Check if config file exists in tar members."""
    return config_path in tar_members


def are_layers_valid(layers: Any) -> bool:
    """Check if layers field is a valid list."""
    return isinstance(layers, list)


def are_all_layers_exist(layers: list[str], tar_members: set[str]) -> bool:
    """Check if all layer files exist in tar members."""
    return all(layer in tar_members for layer in layers)


def validate_manifest_entry(
    manifest_entry: dict[str, Any], tar_members: set[str]
) -> bool:
    """Validate a single manifest entry."""
    required_fields = ["Config", "Layers"]

    if not has_required_fields(manifest_entry, required_fields):
        return False

    config_path = manifest_entry["Config"]
    if not is_config_file_exists(config_path, tar_members):
        return False

    layers = manifest_entry["Layers"]
    if not are_layers_valid(layers):
        return False

    return are_all_layers_exist(layers, tar_members)


def validate_all_manifest_entries(
    manifest_data: list[dict[str, Any]], tar_members: set[str]
) -> bool:
    """Validate all manifest entries."""
    return all(validate_manifest_entry(entry, tar_members) for entry in manifest_data)


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
        if not is_path_exists(tar_path):
            raise ValidationError(f"Tar file does not exist: {tar_path}")

        if not is_valid_tarfile(tar_path):
            return False

        with tarfile.open(tar_path, "r") as tar:
            tar_members = get_tar_members(tar)
            required_files = ["manifest.json"]

            if not has_required_files(tar_members, required_files):
                return False

            manifest_content = extract_manifest_content(tar)
            if manifest_content is None:
                return False

            manifest_data = parse_manifest_json(manifest_content)
            if manifest_data is None:
                return False

            return validate_all_manifest_entries(manifest_data, tar_members)

    except (tarfile.TarError, OSError) as e:
        raise ValidationError(f"Error reading tar file: {e}") from e


def extract_and_parse_manifest(tar: tarfile.TarFile) -> list[dict[str, Any]]:
    """Extract and parse manifest from tar file."""
    manifest_member = tar.extractfile("manifest.json")
    if manifest_member is None:
        raise ValidationError("Cannot extract manifest.json")

    manifest_content = manifest_member.read().decode("utf-8")
    return json.loads(manifest_content)  # type: ignore[no-any-return]


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
            return extract_and_parse_manifest(tar)
    except (tarfile.TarError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValidationError(f"Error reading manifest: {e}") from e
