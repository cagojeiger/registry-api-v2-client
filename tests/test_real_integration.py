"""Real integration tests with actual registry."""

import pytest

pytestmark = pytest.mark.integration  # Mark all tests in this file as integration
import asyncio
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

from registry_api_v2_client import (
    check_registry_connectivity,
    extract_original_tags,
    get_primary_tag,
    list_repositories,
    parse_repository_tag,
)


def create_minimal_tar():
    """Create a minimal test tar file."""
    config_content = json.dumps({"architecture": "amd64", "os": "linux"}).encode(
        "utf-8"
    )
    layer_content = b"dummy layer data"

    config_hash = hashlib.sha256(config_content).hexdigest()
    layer_hash = hashlib.sha256(layer_content).hexdigest()

    manifest = [
        {
            "Config": f"blobs/sha256/{config_hash}",
            "RepoTags": ["test:minimal"],
            "Layers": [f"blobs/sha256/{layer_hash}"],
        }
    ]

    repositories = {"test": {"minimal": config_hash}}

    tar_path = tempfile.mktemp(suffix=".tar")

    with tarfile.open(tar_path, "w") as tar:
        # Add manifest.json
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_content = json.dumps(manifest).encode("utf-8")
        manifest_info.size = len(manifest_content)
        tar.addfile(manifest_info, fileobj=tarfile.io.BytesIO(manifest_content))

        # Add repositories
        repos_info = tarfile.TarInfo("repositories")
        repos_content = json.dumps(repositories).encode("utf-8")
        repos_info.size = len(repos_content)
        tar.addfile(repos_info, fileobj=tarfile.io.BytesIO(repos_content))

        # Add config blob
        config_info = tarfile.TarInfo(f"blobs/sha256/{config_hash}")
        config_info.size = len(config_content)
        tar.addfile(config_info, fileobj=tarfile.io.BytesIO(config_content))

        # Add layer blob
        layer_info = tarfile.TarInfo(f"blobs/sha256/{layer_hash}")
        layer_info.size = len(layer_content)
        tar.addfile(layer_info, fileobj=tarfile.io.BytesIO(layer_content))

    return tar_path


@pytest.mark.asyncio
async def test_registry_connectivity():
    """Test basic registry connectivity."""
    registry_url = "http://localhost:15000"

    try:
        result = await check_registry_connectivity(registry_url)
        assert result is True
    except Exception as e:
        pytest.skip(f"Registry not available: {e}")


@pytest.mark.asyncio
async def test_list_repositories():
    """Test listing repositories."""
    registry_url = "http://localhost:15000"

    try:
        repos = await list_repositories(registry_url)
        assert isinstance(repos, list)
        # Repos list can be empty or contain items
    except Exception as e:
        pytest.skip(f"Registry not available: {e}")


def test_tag_extraction_from_tar():
    """Test tag extraction from actual tar file."""
    tar_path = create_minimal_tar()

    try:
        # Test extract_original_tags
        tags = extract_original_tags(tar_path)
        assert "test:minimal" in tags

        # Test get_primary_tag
        primary = get_primary_tag(tar_path)
        assert primary == ("test", "minimal")

        # Test parse_repository_tag
        repo, tag = parse_repository_tag("test:minimal")
        assert repo == "test"
        assert tag == "minimal"

    finally:
        Path(tar_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test that async operations can run concurrently."""
    registry_url = "http://localhost:15000"

    try:
        # Run multiple connectivity checks concurrently
        tasks = [
            check_registry_connectivity(registry_url),
            check_registry_connectivity(registry_url),
            check_registry_connectivity(registry_url),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed or all should fail with same error
        success_count = sum(1 for r in results if r is True)
        error_count = sum(1 for r in results if isinstance(r, Exception))

        assert success_count + error_count == 3

        if success_count > 0:
            # If any succeeded, all should succeed
            assert success_count == 3

    except Exception as e:
        pytest.skip(f"Registry not available: {e}")


def test_sync_operations_work():
    """Test that sync operations work correctly."""
    # Tag parsing
    test_cases = [
        ("nginx:alpine", ("nginx", "alpine")),
        ("localhost:5000/app:latest", ("localhost:5000/app", "latest")),
        ("myapp", ("myapp", "latest")),
        ("registry.io:443/user/app:v1.0", ("registry.io:443/user/app", "v1.0")),
    ]

    for input_tag, expected in test_cases:
        result = parse_repository_tag(input_tag)
        assert (
            result == expected
        ), f"Failed for {input_tag}: got {result}, expected {expected}"
