"""Tests for tag extraction from Docker tar files."""

import json
import tarfile
import tempfile
from pathlib import Path

import pytest

from registry_api_v2_client.exceptions import TarReadError, ValidationError
from registry_api_v2_client.tar.tags import (
    extract_original_tags,
    extract_repo_tags_from_manifest,
    extract_repo_tags_from_repositories,
    get_primary_tag,
    parse_repository_tag,
)


def create_test_tar_with_manifest(repo_tags):
    """Create test tar with manifest.json containing specified repo tags."""
    tar_path = tempfile.mktemp(suffix=".tar")

    manifest = [
        {
            "Config": "blobs/sha256/config123",
            "RepoTags": repo_tags,
            "Layers": ["blobs/sha256/layer123"],
        }
    ]

    with tarfile.open(tar_path, "w") as tar:
        # Add manifest.json
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_content = json.dumps(manifest).encode("utf-8")
        manifest_info.size = len(manifest_content)
        tar.addfile(manifest_info, fileobj=tarfile.io.BytesIO(manifest_content))

        # Add dummy blobs
        for blob_name in ["blobs/sha256/config123", "blobs/sha256/layer123"]:
            blob_info = tarfile.TarInfo(blob_name)
            blob_content = b"dummy"
            blob_info.size = len(blob_content)
            tar.addfile(blob_info, fileobj=tarfile.io.BytesIO(blob_content))

    return tar_path


def create_test_tar_with_repositories(repositories):
    """Create test tar with repositories file containing specified repos."""
    tar_path = tempfile.mktemp(suffix=".tar")

    with tarfile.open(tar_path, "w") as tar:
        # Add repositories
        repos_info = tarfile.TarInfo("repositories")
        repos_content = json.dumps(repositories).encode("utf-8")
        repos_info.size = len(repos_content)
        tar.addfile(repos_info, fileobj=tarfile.io.BytesIO(repos_content))

    return tar_path


def test_extract_repo_tags_from_manifest():
    """Test extracting repo tags from manifest.json."""
    repo_tags = ["nginx:alpine", "nginx:latest", "my-nginx:v1.0"]
    tar_path = create_test_tar_with_manifest(repo_tags)

    try:
        extracted_tags = extract_repo_tags_from_manifest(tar_path)
        assert extracted_tags == repo_tags
    finally:
        Path(tar_path).unlink(missing_ok=True)


def test_extract_repo_tags_from_manifest_empty():
    """Test extracting from manifest with empty RepoTags."""
    tar_path = create_test_tar_with_manifest([])

    try:
        extracted_tags = extract_repo_tags_from_manifest(tar_path)
        assert extracted_tags == []
    finally:
        Path(tar_path).unlink(missing_ok=True)


def test_extract_repo_tags_from_repositories():
    """Test extracting repo tags from repositories file."""
    repositories = {
        "nginx": {"alpine": "abc123", "latest": "def456"},
        "my-app": {"v1.0": "ghi789"},
    }
    tar_path = create_test_tar_with_repositories(repositories)

    try:
        extracted_tags = extract_repo_tags_from_repositories(tar_path)
        # Order may vary, so use set comparison
        expected_tags = {"nginx:alpine", "nginx:latest", "my-app:v1.0"}
        assert set(extracted_tags) == expected_tags
    finally:
        Path(tar_path).unlink(missing_ok=True)


def test_extract_original_tags_prefers_manifest():
    """Test that extract_original_tags prefers manifest.json over repositories."""
    # Create tar with both manifest and repositories
    tar_path = tempfile.mktemp(suffix=".tar")

    manifest = [
        {
            "Config": "blobs/sha256/config123",
            "RepoTags": ["nginx:alpine"],
            "Layers": ["blobs/sha256/layer123"],
        }
    ]

    repositories = {"different": {"tag": "xyz789"}}

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

    try:
        extracted_tags = extract_original_tags(tar_path)
        # Should prefer manifest.json
        assert extracted_tags == ["nginx:alpine"]
    finally:
        Path(tar_path).unlink(missing_ok=True)


def test_parse_repository_tag():
    """Test parsing repository:tag strings."""
    # Simple cases
    assert parse_repository_tag("nginx:alpine") == ("nginx", "alpine")
    assert parse_repository_tag("my-app:latest") == ("my-app", "latest")

    # No tag specified (should default to latest)
    assert parse_repository_tag("nginx") == ("nginx", "latest")

    # Registry URLs
    assert parse_repository_tag("localhost:5000/nginx:alpine") == (
        "localhost:5000/nginx",
        "alpine",
    )
    assert parse_repository_tag("registry.io:443/user/app:v1.0") == (
        "registry.io:443/user/app",
        "v1.0",
    )

    # Edge cases
    assert parse_repository_tag("app:") == ("app", "latest")  # Empty tag


def test_get_primary_tag():
    """Test getting primary (first) tag from tar file."""
    repo_tags = ["nginx:alpine", "nginx:latest"]
    tar_path = create_test_tar_with_manifest(repo_tags)

    try:
        primary = get_primary_tag(tar_path)
        assert primary == ("nginx", "alpine")
    finally:
        Path(tar_path).unlink(missing_ok=True)


def test_get_primary_tag_no_tags():
    """Test getting primary tag when no tags exist."""
    tar_path = create_test_tar_with_manifest([])

    try:
        primary = get_primary_tag(tar_path)
        assert primary is None
    finally:
        Path(tar_path).unlink(missing_ok=True)


def test_extract_tags_invalid_tar():
    """Test error handling for invalid tar files."""
    # Create invalid tar file (empty file)
    invalid_tar = tempfile.mktemp(suffix=".tar")
    Path(invalid_tar).touch()

    try:
        with pytest.raises(TarReadError):
            extract_repo_tags_from_manifest(invalid_tar)
    finally:
        Path(invalid_tar).unlink(missing_ok=True)


def test_extract_tags_missing_manifest():
    """Test error handling when manifest.json is missing."""
    # Create tar without manifest.json
    tar_path = tempfile.mktemp(suffix=".tar")

    with tarfile.open(tar_path, "w") as tar:
        # Add dummy file instead of manifest
        dummy_info = tarfile.TarInfo("dummy.txt")
        dummy_content = b"dummy"
        dummy_info.size = len(dummy_content)
        tar.addfile(dummy_info, fileobj=tarfile.io.BytesIO(dummy_content))

    try:
        with pytest.raises(ValidationError, match="manifest.json not found"):
            extract_repo_tags_from_manifest(tar_path)
    finally:
        Path(tar_path).unlink(missing_ok=True)
