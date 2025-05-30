"""Tests for tar file validation utilities."""

import json
import tarfile

import pytest

from registry_api_v2_client.exceptions import ValidationError
from registry_api_v2_client.utils.validator import (
    are_all_layers_exist,
    are_layers_valid,
    get_tar_manifest,
    get_tar_members,
    has_required_fields,
    has_required_files,
    is_config_file_exists,
    is_path_exists,
    is_valid_tarfile,
    parse_manifest_json,
    validate_docker_tar,
    validate_manifest_entry,
)


def test_validate_synthetic_docker_tar(tmp_path):
    """Test validation with synthetic Docker tar file."""
    # Create a small valid tar file from test_data
    tar_dir = tmp_path / "synthetic_tar"
    tar_dir.mkdir()

    # Create manifest.json
    manifest = [
        {
            "Config": "blobs/sha256/test_config",
            "RepoTags": ["test/synthetic:latest"],
            "Layers": ["blobs/sha256/test_layer"],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    # Create required files
    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "test_config").write_text('{"os":"linux","architecture":"amd64"}')
    (blobs_dir / "test_layer").write_text("synthetic layer content for testing")

    # Create tar file
    tar_path = tmp_path / "synthetic.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "test_config", arcname="blobs/sha256/test_config")
        tar.add(blobs_dir / "test_layer", arcname="blobs/sha256/test_layer")

    assert validate_docker_tar(tar_path) is True


def test_validate_valid_tar(tmp_path):
    """Test validation with a valid Docker tar structure."""
    # Create a valid tar structure
    tar_dir = tmp_path / "valid_tar"
    tar_dir.mkdir()

    # Create manifest.json
    manifest = [
        {
            "Config": "blobs/sha256/config123",
            "RepoTags": ["test/image:latest"],
            "Layers": ["blobs/sha256/layer123"],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    # Create required files
    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "config123").write_text('{"os":"linux"}')
    (blobs_dir / "layer123").write_text("layer content")

    # Create tar file
    tar_path = tmp_path / "valid.tar"
    with tarfile.open(tar_path, "w") as tar:
        # Add files individually to avoid directory structure issues
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "config123", arcname="blobs/sha256/config123")
        tar.add(blobs_dir / "layer123", arcname="blobs/sha256/layer123")

    assert validate_docker_tar(tar_path) is True


def test_validate_missing_manifest(tmp_path):
    """Test validation fails when manifest.json is missing."""
    tar_dir = tmp_path / "no_manifest"
    tar_dir.mkdir()
    (tar_dir / "some_file.txt").write_text("content")

    tar_path = tmp_path / "no_manifest.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir, arcname=".")

    assert validate_docker_tar(tar_path) is False


def test_validate_invalid_manifest_json(tmp_path):
    """Test validation fails with invalid JSON in manifest."""
    tar_dir = tmp_path / "invalid_json"
    tar_dir.mkdir()
    (tar_dir / "manifest.json").write_text("invalid json")

    tar_path = tmp_path / "invalid_json.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir, arcname=".")

    assert validate_docker_tar(tar_path) is False


def test_validate_invalid_manifest_structure(tmp_path):
    """Test validation fails with invalid manifest structure."""
    tar_dir = tmp_path / "invalid_structure"
    tar_dir.mkdir()

    # Invalid manifest structure (not a list)
    manifest = {"invalid": "structure"}
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    tar_path = tmp_path / "invalid_structure.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir, arcname=".")

    assert validate_docker_tar(tar_path) is False


def test_validate_missing_config_file(tmp_path):
    """Test validation fails when referenced config file is missing."""
    tar_dir = tmp_path / "missing_config"
    tar_dir.mkdir()

    manifest = [
        {
            "Config": "blobs/sha256/missing_config",
            "RepoTags": ["test/image:latest"],
            "Layers": ["blobs/sha256/layer123"],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    # Create layer but not config
    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "layer123").write_text("layer content")

    tar_path = tmp_path / "missing_config.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir, arcname=".")

    assert validate_docker_tar(tar_path) is False


def test_validate_missing_layer_file(tmp_path):
    """Test validation fails when referenced layer file is missing."""
    tar_dir = tmp_path / "missing_layer"
    tar_dir.mkdir()

    manifest = [
        {
            "Config": "blobs/sha256/config123",
            "RepoTags": ["test/image:latest"],
            "Layers": ["blobs/sha256/missing_layer"],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    # Create config but not layer
    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "config123").write_text('{"os":"linux"}')

    tar_path = tmp_path / "missing_layer.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir, arcname=".")

    assert validate_docker_tar(tar_path) is False


def test_validate_not_a_tar_file(tmp_path):
    """Test validation fails for non-tar files."""
    not_tar = tmp_path / "not_a_tar.txt"
    not_tar.write_text("This is not a tar file")

    assert validate_docker_tar(not_tar) is False


def test_validate_nonexistent_file(tmp_path):
    """Test validation raises error for nonexistent files."""
    nonexistent = tmp_path / "does_not_exist.tar"

    with pytest.raises(ValidationError, match="does not exist"):
        validate_docker_tar(nonexistent)


def test_validate_empty_manifest(tmp_path):
    """Test validation fails with empty manifest array."""
    tar_dir = tmp_path / "empty_manifest"
    tar_dir.mkdir()
    (tar_dir / "manifest.json").write_text("[]")

    tar_path = tmp_path / "empty_manifest.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir, arcname=".")

    assert validate_docker_tar(tar_path) is False


def test_get_manifest_valid_tar(tmp_path):
    """Test getting manifest from valid tar file."""
    tar_dir = tmp_path / "valid_tar"
    tar_dir.mkdir()

    manifest_data = [
        {
            "Config": "blobs/sha256/config123",
            "RepoTags": ["test/image:latest"],
            "Layers": ["blobs/sha256/layer123"],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest_data))

    # Create required files
    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "config123").write_text('{"os":"linux"}')
    (blobs_dir / "layer123").write_text("layer content")

    tar_path = tmp_path / "valid.tar"
    with tarfile.open(tar_path, "w") as tar:
        # Add files individually to avoid directory structure issues
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "config123", arcname="blobs/sha256/config123")
        tar.add(blobs_dir / "layer123", arcname="blobs/sha256/layer123")

    result = get_tar_manifest(tar_path)
    assert result == manifest_data


def test_get_manifest_invalid_tar(tmp_path):
    """Test getting manifest from invalid tar raises error."""
    not_tar = tmp_path / "not_a_tar.txt"
    not_tar.write_text("This is not a tar file")

    with pytest.raises(ValidationError, match="Invalid Docker tar file"):
        get_tar_manifest(not_tar)


def test_get_manifest_synthetic_docker_tar(tmp_path):
    """Test getting manifest from a synthetic Docker tar file."""
    # Create a synthetic tar file
    tar_dir = tmp_path / "synthetic_tar"
    tar_dir.mkdir()

    manifest_data = [
        {
            "Config": "blobs/sha256/synthetic_config",
            "RepoTags": ["test/synthetic:v1.0"],
            "Layers": ["blobs/sha256/synthetic_layer"],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest_data))

    # Create required files
    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "synthetic_config").write_text('{"os":"linux","architecture":"amd64"}')
    (blobs_dir / "synthetic_layer").write_text("synthetic layer for testing")

    tar_path = tmp_path / "synthetic.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "synthetic_config", arcname="blobs/sha256/synthetic_config")
        tar.add(blobs_dir / "synthetic_layer", arcname="blobs/sha256/synthetic_layer")

    manifest = get_tar_manifest(tar_path)
    assert isinstance(manifest, list)
    assert len(manifest) > 0
    assert "Config" in manifest[0]
    assert "Layers" in manifest[0]
    assert manifest[0]["RepoTags"] == ["test/synthetic:v1.0"]


# Individual function tests


def test_is_path_exists(tmp_path):
    """Test path existence check."""
    existing_file = tmp_path / "existing.txt"
    existing_file.write_text("content")
    non_existing_file = tmp_path / "non_existing.txt"

    assert is_path_exists(existing_file) is True
    assert is_path_exists(non_existing_file) is False


def test_is_valid_tarfile(tmp_path):
    """Test tar file validation."""
    # Create valid tar file
    tar_path = tmp_path / "valid.tar"
    with tarfile.open(tar_path, "w"):
        pass

    # Create non-tar file
    not_tar = tmp_path / "not_tar.txt"
    not_tar.write_text("not a tar")

    assert is_valid_tarfile(tar_path) is True
    assert is_valid_tarfile(not_tar) is False


def test_get_tar_members(tmp_path):
    """Test tar member extraction."""
    tar_dir = tmp_path / "test_tar"
    tar_dir.mkdir()
    (tar_dir / "file1.txt").write_text("content1")
    (tar_dir / "file2.txt").write_text("content2")

    tar_path = tmp_path / "test.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "file1.txt", arcname="file1.txt")
        tar.add(tar_dir / "file2.txt", arcname="file2.txt")

    with tarfile.open(tar_path, "r") as tar:
        members = get_tar_members(tar)
        assert "file1.txt" in members
        assert "file2.txt" in members


def test_has_required_files():
    """Test required files check."""
    tar_members = {"manifest.json", "file1.txt", "file2.txt"}
    required_files = ["manifest.json"]
    missing_files = ["manifest.json", "missing.txt"]

    assert has_required_files(tar_members, required_files) is True
    assert has_required_files(tar_members, missing_files) is False


def test_parse_manifest_json():
    """Test manifest JSON parsing."""
    valid_manifest = '[{"Config": "test", "Layers": []}]'
    invalid_json = "invalid json"
    empty_array = "[]"
    not_array = '{"invalid": "structure"}'

    assert parse_manifest_json(valid_manifest) is not None
    assert parse_manifest_json(invalid_json) is None
    assert parse_manifest_json(empty_array) is None
    assert parse_manifest_json(not_array) is None


def test_has_required_fields():
    """Test required fields check."""
    manifest_entry = {"Config": "test", "Layers": [], "Extra": "field"}
    required_fields = ["Config", "Layers"]
    missing_fields = ["Config", "Layers", "Missing"]

    assert has_required_fields(manifest_entry, required_fields) is True
    assert has_required_fields(manifest_entry, missing_fields) is False


def test_is_config_file_exists():
    """Test config file existence check."""
    tar_members = {"blobs/sha256/config123", "other_file.txt"}

    assert is_config_file_exists("blobs/sha256/config123", tar_members) is True
    assert is_config_file_exists("blobs/sha256/missing", tar_members) is False


def test_are_layers_valid():
    """Test layers validation."""
    valid_layers = ["layer1", "layer2"]
    invalid_layers = "not a list"

    assert are_layers_valid(valid_layers) is True
    assert are_layers_valid(invalid_layers) is False


def test_are_all_layers_exist():
    """Test all layers existence check."""
    tar_members = {"layer1", "layer2", "layer3"}
    existing_layers = ["layer1", "layer2"]
    missing_layers = ["layer1", "missing_layer"]

    assert are_all_layers_exist(existing_layers, tar_members) is True
    assert are_all_layers_exist(missing_layers, tar_members) is False


def test_validate_manifest_entry():
    """Test manifest entry validation."""
    tar_members = {"blobs/sha256/config123", "blobs/sha256/layer123"}

    valid_entry = {
        "Config": "blobs/sha256/config123",
        "Layers": ["blobs/sha256/layer123"],
    }

    missing_field_entry = {"Config": "blobs/sha256/config123"}

    missing_config_entry = {
        "Config": "blobs/sha256/missing_config",
        "Layers": ["blobs/sha256/layer123"],
    }

    invalid_layers_entry = {"Config": "blobs/sha256/config123", "Layers": "not a list"}

    missing_layer_entry = {
        "Config": "blobs/sha256/config123",
        "Layers": ["blobs/sha256/missing_layer"],
    }

    assert validate_manifest_entry(valid_entry, tar_members) is True
    assert validate_manifest_entry(missing_field_entry, tar_members) is False
    assert validate_manifest_entry(missing_config_entry, tar_members) is False
    assert validate_manifest_entry(invalid_layers_entry, tar_members) is False
    assert validate_manifest_entry(missing_layer_entry, tar_members) is False
