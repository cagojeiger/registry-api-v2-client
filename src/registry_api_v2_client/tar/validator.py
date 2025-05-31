"""Tar file validation functions."""

from pathlib import Path

from ..exceptions import TarReadError, ValidationError
from ..utils.validator import validate_docker_tar as _validate_docker_tar


def validate_tar_structure(tar_path: str) -> bool:
    """Validate Docker tar file structure.

    Args:
        tar_path: Path to tar file

    Returns:
        True if valid

    Raises:
        ValidationError: If tar structure is invalid
        TarReadError: If tar file cannot be read
    """
    try:
        _validate_docker_tar(Path(tar_path) if isinstance(tar_path, str) else tar_path)
        return True
    except (ValidationError, TarReadError):
        raise
    except Exception as e:
        raise TarReadError(f"Failed to validate tar file: {e}") from e
