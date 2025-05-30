"""Digest calculation and validation utilities."""

import hashlib
import re
from typing import Union

# Regex pattern for valid digest format (algorithm:hex)
DIGEST_PATTERN = re.compile(r"^[a-z0-9]+:[a-f0-9]+$")


def calculate_digest(data: Union[bytes, bytearray], algorithm: str = "sha256") -> str:
    """Calculate digest of data.

    Args:
        data: Data to hash
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Digest string in format "algorithm:hex"

    Raises:
        ValueError: If algorithm is not supported
        ValueError: If data is not bytes-like
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("Data must be bytes or bytearray")

    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return f"{algorithm}:{hasher.hexdigest()}"


def validate_digest(digest: str) -> bool:
    """Validate digest format.

    Args:
        digest: Digest string to validate

    Returns:
        True if valid digest format
    """
    if not isinstance(digest, str):
        return False

    if not DIGEST_PATTERN.match(digest):
        return False

    # Check if algorithm is valid
    algorithm, _ = digest.split(":", 1)
    return algorithm in ["sha256", "sha512", "sha1", "md5"]


def verify_digest(data: Union[bytes, bytearray], expected_digest: str) -> bool:
    """Verify data matches expected digest.

    Args:
        data: Data to verify
        expected_digest: Expected digest string

    Returns:
        True if data matches digest

    Raises:
        ValueError: If digest format is invalid
    """
    if not validate_digest(expected_digest):
        raise ValueError(f"Invalid digest format: {expected_digest}")

    algorithm, _ = expected_digest.split(":", 1)
    actual_digest = calculate_digest(data, algorithm)
    return actual_digest == expected_digest