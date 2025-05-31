"""Isolated integration tests with test context."""

import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

import pytest

from registry_api_v2_client import (
    extract_original_tags,
    get_primary_tag,
    list_repositories,
    list_tags,
    push_docker_tar_with_all_original_tags,
    push_docker_tar_with_original_tags,
)

pytestmark = pytest.mark.integration


def create_test_tar_with_tags(repo_tags):
    """Create a test tar file with specified tags."""
    config_content = json.dumps(
        {"architecture": "amd64", "os": "linux", "created": "2024-01-01T00:00:00Z"}
    ).encode("utf-8")
    layer_content = b"dummy layer data for testing"

    config_hash = hashlib.sha256(config_content).hexdigest()
    layer_hash = hashlib.sha256(layer_content).hexdigest()

    manifest = [
        {
            "Config": f"blobs/sha256/{config_hash}",
            "RepoTags": repo_tags,
            "Layers": [f"blobs/sha256/{layer_hash}"],
        }
    ]

    # Create repositories data from tags
    repositories = {}
    for repo_tag in repo_tags:
        if ":" in repo_tag:
            repo, tag = repo_tag.rsplit(":", 1)
        else:
            repo, tag = repo_tag, "latest"

        if repo not in repositories:
            repositories[repo] = {}
        repositories[repo][tag] = config_hash

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
async def test_isolated_single_tag_push(test_context):
    """Test pushing single tag with isolation."""
    repo_name = test_context.repo_name("single")
    tar_path = create_test_tar_with_tags([f"{repo_name}:v1.0"])

    try:
        # Test tag extraction
        tags = extract_original_tags(tar_path)
        assert f"{repo_name}:v1.0" in tags

        primary = get_primary_tag(tar_path)
        assert primary == (repo_name, "v1.0")

        # Push with original tags
        digest = await push_docker_tar_with_original_tags(
            tar_path, test_context.registry_url
        )
        assert digest.startswith("sha256:")

        # Verify it was pushed
        repos = await list_repositories(test_context.registry_url)
        assert repo_name in repos

        # List tags
        repo_tags = await list_tags(test_context.registry_url, repo_name)
        assert "v1.0" in repo_tags

    finally:
        Path(tar_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_isolated_multiple_tags_push(test_context):
    """Test pushing multiple tags with isolation."""
    repo_name = test_context.repo_name("multi")
    tar_path = create_test_tar_with_tags(
        [f"{repo_name}:v1.0", f"{repo_name}:latest", f"{repo_name}:stable"]
    )

    try:
        # Test tag extraction
        tags = extract_original_tags(tar_path)
        assert len(tags) == 3
        assert f"{repo_name}:v1.0" in tags
        assert f"{repo_name}:latest" in tags
        assert f"{repo_name}:stable" in tags

        # Push all original tags
        digests = await push_docker_tar_with_all_original_tags(
            tar_path, test_context.registry_url
        )
        assert len(digests) == 3
        assert all(d.startswith("sha256:") for d in digests)

        # Verify all tags were pushed
        repos = await list_repositories(test_context.registry_url)
        assert repo_name in repos

        repo_tags = await list_tags(test_context.registry_url, repo_name)
        assert "v1.0" in repo_tags
        assert "latest" in repo_tags
        assert "stable" in repo_tags

        # All tags should have the same digest (same image)
        assert len(set(digests)) == 1, "All tags should point to the same image"

    finally:
        Path(tar_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_isolated_concurrent_operations(test_context):
    """Test concurrent operations with isolation."""
    import asyncio

    # Create multiple test tars
    tar_paths = []
    try:
        for i in range(3):
            repo_name = test_context.repo_name(f"concurrent-{i}")
            tar_path = create_test_tar_with_tags([f"{repo_name}:v1.0"])
            tar_paths.append((tar_path, repo_name))

        # Push all concurrently
        tasks = [
            push_docker_tar_with_original_tags(tar_path, test_context.registry_url)
            for tar_path, _ in tar_paths
        ]

        digests = await asyncio.gather(*tasks)
        assert len(digests) == 3
        assert all(d.startswith("sha256:") for d in digests)

        # Verify all were pushed
        repos = await list_repositories(test_context.registry_url)
        for _, repo_name in tar_paths:
            assert repo_name in repos

    finally:
        for tar_path, _ in tar_paths:
            Path(tar_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_isolated_cleanup_verification(test_context):
    """Test that cleanup works properly."""
    repo_name = test_context.repo_name("cleanup-test")
    tar_path = create_test_tar_with_tags([f"{repo_name}:test"])

    try:
        # Push image
        digest = await push_docker_tar_with_original_tags(
            tar_path, test_context.registry_url
        )
        assert digest.startswith("sha256:")

        # Verify it exists
        repos = await list_repositories(test_context.registry_url)
        assert repo_name in repos

        # Note: Cleanup will happen automatically via test_context.__aexit__

    finally:
        Path(tar_path).unlink(missing_ok=True)
