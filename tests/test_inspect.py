"""Tests for Docker tar file inspection utilities."""

import json
import tarfile
from datetime import datetime

import pytest

from registry_api_v2_client.exceptions import TarReadError, ValidationError
from registry_api_v2_client.models import ImageConfig, ImageInspect, LayerInfo
from registry_api_v2_client.utils.inspect import (
    extract_config_digest,
    extract_digest_from_path,
    extract_json_file,
    get_diff_ids,
    get_environment_variables,
    get_exposed_ports,
    get_labels,
    get_layer_media_type,
    get_layer_source_key,
    get_runtime_config,
    inspect_docker_tar,
    parse_created_timestamp,
    validate_config_data,
    validate_manifest_data,
)


def test_inspect_synthetic_docker_tar(tmp_path):
    """Test inspection of a synthetic Docker tar file."""
    # Create synthetic tar file structure
    tar_dir = tmp_path / "synthetic_image"
    tar_dir.mkdir()

    # Create realistic manifest.json
    manifest_data = [
        {
            "Config": "blobs/sha256/config_abc123",
            "RepoTags": ["test/myapp:v1.0", "test/myapp:latest"],
            "Layers": ["blobs/sha256/layer_def456", "blobs/sha256/layer_ghi789"],
            "LayerSources": {
                "sha256:layer_def456": {
                    "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                    "size": 5242880,
                    "digest": "sha256:layer_def456",
                },
                "sha256:layer_ghi789": {
                    "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                    "size": 1048576,
                    "digest": "sha256:layer_ghi789",
                },
            },
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest_data))

    # Create realistic config file
    config_data = {
        "architecture": "amd64",
        "os": "linux",
        "created": "2025-01-15T10:30:45.123456789Z",
        "config": {
            "Cmd": ["/bin/sh", "-c", "echo hello"],
            "Entrypoint": ["/entrypoint.sh"],
            "Env": [
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "APP_VERSION=1.0.0",
                "NODE_ENV=production",
            ],
            "User": "1001",
            "WorkingDir": "/app",
            "ExposedPorts": {"8080/tcp": {}, "9090/tcp": {}},
            "Labels": {
                "maintainer": "test@example.com",
                "version": "1.0.0",
                "org.opencontainers.image.source": "https://github.com/test/myapp",
            },
        },
        "rootfs": {
            "type": "layers",
            "diff_ids": ["sha256:diff_layer_1_abc", "sha256:diff_layer_2_def"],
        },
    }

    # Create blobs directory structure
    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "config_abc123").write_text(json.dumps(config_data))

    # Create dummy layer files
    (blobs_dir / "layer_def456").write_text("fake layer data 1" * 1000)
    (blobs_dir / "layer_ghi789").write_text("fake layer data 2" * 500)

    # Create tar file
    tar_path = tmp_path / "synthetic_image.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "config_abc123", arcname="blobs/sha256/config_abc123")
        tar.add(blobs_dir / "layer_def456", arcname="blobs/sha256/layer_def456")
        tar.add(blobs_dir / "layer_ghi789", arcname="blobs/sha256/layer_ghi789")

    # Inspect the tar file
    result = inspect_docker_tar(tar_path)

    # Validate basic metadata
    assert isinstance(result, ImageInspect)
    assert result.id == "sha256:config_abc123"
    assert result.repo_tags == ["test/myapp:v1.0", "test/myapp:latest"]
    assert result.architecture == "amd64"
    assert result.os == "linux"
    assert result.rootfs_type == "layers"

    # Validate config
    assert isinstance(result.config, ImageConfig)
    assert result.config.architecture == "amd64"
    assert result.config.os == "linux"
    assert result.config.cmd == ["/bin/sh", "-c", "echo hello"]
    assert result.config.entrypoint == ["/entrypoint.sh"]
    assert result.config.user == "1001"
    assert result.config.working_dir == "/app"
    assert "APP_VERSION=1.0.0" in result.config.env
    assert "8080/tcp" in result.config.exposed_ports
    assert result.config.labels["maintainer"] == "test@example.com"

    # Validate layers
    assert len(result.layers) == 2
    layer1, layer2 = result.layers

    assert isinstance(layer1, LayerInfo)
    assert layer1.digest == "sha256:layer_def456"
    assert layer1.size == 5242880  # From LayerSources
    assert layer1.media_type == "application/vnd.docker.image.rootfs.diff.tar.gzip"

    assert isinstance(layer2, LayerInfo)
    assert layer2.digest == "sha256:layer_ghi789"
    assert layer2.size == 1048576  # From LayerSources

    # Validate size calculations
    assert result.size == 5242880 + 1048576
    assert result.virtual_size == result.size

    # Validate diff_ids
    assert result.rootfs_layers == [
        "sha256:diff_layer_1_abc",
        "sha256:diff_layer_2_def",
    ]


def test_inspect_minimal_tar(tmp_path):
    """Test inspection of minimal Docker tar file."""
    tar_dir = tmp_path / "minimal_image"
    tar_dir.mkdir()

    # Minimal manifest
    manifest = [
        {
            "Config": "blobs/sha256/minimal_config",
            "RepoTags": ["minimal:latest"],
            "Layers": ["blobs/sha256/minimal_layer"],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    # Minimal config
    config = {
        "architecture": "arm64",
        "os": "linux",
        "created": "2025-01-01T00:00:00Z",
        "config": {},
        "rootfs": {"type": "layers", "diff_ids": []},
    }

    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "minimal_config").write_text(json.dumps(config))
    (blobs_dir / "minimal_layer").write_text("minimal layer")

    tar_path = tmp_path / "minimal.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "minimal_config", arcname="blobs/sha256/minimal_config")
        tar.add(blobs_dir / "minimal_layer", arcname="blobs/sha256/minimal_layer")

    result = inspect_docker_tar(tar_path)

    assert result.id == "sha256:minimal_config"
    assert result.repo_tags == ["minimal:latest"]
    assert result.architecture == "arm64"
    assert result.config.cmd == []
    assert result.config.entrypoint == []
    assert result.config.env == []
    assert result.config.labels == {}


def test_inspect_invalid_tar(tmp_path):
    """Test inspection fails for invalid tar files."""
    # Test with non-tar file
    not_tar = tmp_path / "not_a_tar.txt"
    not_tar.write_text("This is not a tar file")

    with pytest.raises(ValidationError, match="Invalid Docker tar file"):
        inspect_docker_tar(not_tar)


def test_inspect_missing_config(tmp_path):
    """Test inspection fails when config file is missing."""
    tar_dir = tmp_path / "broken_image"
    tar_dir.mkdir()

    # Manifest pointing to non-existent config (but validator will catch this first)
    manifest = [
        {
            "Config": "blobs/sha256/missing_config",
            "RepoTags": ["broken:latest"],
            "Layers": [],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    tar_path = tmp_path / "broken.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")

    # Since validator runs first, it will fail with ValidationError
    with pytest.raises(ValidationError, match="Invalid Docker tar file"):
        inspect_docker_tar(tar_path)


def test_inspect_malformed_config(tmp_path):
    """Test inspection fails with malformed config JSON."""
    tar_dir = tmp_path / "malformed_image"
    tar_dir.mkdir()

    manifest = [
        {
            "Config": "blobs/sha256/bad_config",
            "RepoTags": ["malformed:latest"],
            "Layers": [],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "bad_config").write_text("invalid json content")

    tar_path = tmp_path / "malformed.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "bad_config", arcname="blobs/sha256/bad_config")

    # The inspect function will detect the malformed config and fail
    with pytest.raises(TarReadError, match="Cannot read config file"):
        inspect_docker_tar(tar_path)


def test_inspect_datetime_parsing(tmp_path):
    """Test various datetime formats are parsed correctly."""
    tar_dir = tmp_path / "datetime_test"
    tar_dir.mkdir()

    manifest = [
        {
            "Config": "blobs/sha256/datetime_config",
            "RepoTags": ["datetime:test"],
            "Layers": [],
        }
    ]
    (tar_dir / "manifest.json").write_text(json.dumps(manifest))

    # Test with malformed datetime (should fallback to current time)
    config = {
        "architecture": "amd64",
        "os": "linux",
        "created": "invalid-datetime",
        "config": {},
        "rootfs": {"type": "layers", "diff_ids": []},
    }

    blobs_dir = tar_dir / "blobs" / "sha256"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "datetime_config").write_text(json.dumps(config))

    tar_path = tmp_path / "datetime_test.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "manifest.json", arcname="manifest.json")
        tar.add(blobs_dir / "datetime_config", arcname="blobs/sha256/datetime_config")

    result = inspect_docker_tar(tar_path)

    # Should not raise error and created should be a valid datetime
    assert isinstance(result.created, datetime)
    assert isinstance(result.config.created, datetime)


# Individual function tests


def test_validate_manifest_data():
    """Test manifest data validation."""
    valid_manifest = [{"Config": "test", "Layers": []}]
    invalid_manifest = {"invalid": "structure"}
    none_manifest = None

    assert validate_manifest_data(valid_manifest) is True
    assert validate_manifest_data(invalid_manifest) is False
    assert validate_manifest_data(none_manifest) is False


def test_validate_config_data():
    """Test config data validation."""
    valid_config = {"architecture": "amd64", "os": "linux"}
    invalid_config = ["invalid", "structure"]
    none_config = None

    assert validate_config_data(valid_config) is True
    assert validate_config_data(invalid_config) is False
    assert validate_config_data(none_config) is False


def test_extract_digest_from_path():
    """Test digest extraction from layer path."""
    layer_path = "blobs/sha256/abc123def456"
    expected_digest = "sha256:abc123def456"

    assert extract_digest_from_path(layer_path) == expected_digest


def test_get_layer_source_key():
    """Test layer source key extraction."""
    layer_digest = "sha256:abc123def456"
    expected_key = "abc123def456"

    assert get_layer_source_key(layer_digest) == expected_key


def test_get_layer_media_type():
    """Test layer media type extraction with default."""
    layer_source_with_type = {"mediaType": "application/custom.type"}
    layer_source_without_type = {}

    assert get_layer_media_type(layer_source_with_type) == "application/custom.type"
    assert (
        get_layer_media_type(layer_source_without_type)
        == "application/vnd.docker.image.rootfs.diff.tar"
    )


def test_parse_created_timestamp():
    """Test timestamp parsing with various formats."""
    valid_timestamp = "2025-01-15T10:30:45.123456789Z"
    invalid_timestamp = "invalid-timestamp"

    result_valid = parse_created_timestamp(valid_timestamp)
    result_invalid = parse_created_timestamp(invalid_timestamp)

    assert isinstance(result_valid, datetime)
    assert isinstance(result_invalid, datetime)  # Should fallback to datetime.now()


def test_get_runtime_config():
    """Test runtime config extraction."""
    config_data = {"config": {"Cmd": ["/bin/sh"], "Env": ["PATH=/usr/bin"]}}
    config_data_no_runtime = {}

    assert get_runtime_config(config_data) == {
        "Cmd": ["/bin/sh"],
        "Env": ["PATH=/usr/bin"],
    }
    assert get_runtime_config(config_data_no_runtime) == {}


def test_get_environment_variables():
    """Test environment variables extraction."""
    runtime_config = {"Env": ["PATH=/usr/bin", "HOME=/root"]}
    runtime_config_no_env = {}

    assert get_environment_variables(runtime_config) == ["PATH=/usr/bin", "HOME=/root"]
    assert get_environment_variables(runtime_config_no_env) == []


def test_get_exposed_ports():
    """Test exposed ports extraction."""
    runtime_config = {"ExposedPorts": {"8080/tcp": {}, "9090/tcp": {}}}
    runtime_config_no_ports = {}

    assert get_exposed_ports(runtime_config) == {"8080/tcp": {}, "9090/tcp": {}}
    assert get_exposed_ports(runtime_config_no_ports) == {}


def test_get_labels():
    """Test labels extraction."""
    runtime_config = {"Labels": {"version": "1.0", "maintainer": "test@example.com"}}
    runtime_config_no_labels = {}
    runtime_config_null_labels = {"Labels": None}

    assert get_labels(runtime_config) == {
        "version": "1.0",
        "maintainer": "test@example.com",
    }
    assert get_labels(runtime_config_no_labels) == {}
    assert get_labels(runtime_config_null_labels) == {}


def test_get_diff_ids():
    """Test diff_ids extraction."""
    config_data = {"rootfs": {"diff_ids": ["sha256:abc123", "sha256:def456"]}}
    config_data_no_rootfs = {}
    config_data_no_diff_ids = {"rootfs": {}}

    assert get_diff_ids(config_data) == ["sha256:abc123", "sha256:def456"]
    assert get_diff_ids(config_data_no_rootfs) == []
    assert get_diff_ids(config_data_no_diff_ids) == []


def test_extract_config_digest():
    """Test config digest extraction."""
    config_path = "blobs/sha256/config_abc123"
    expected_digest = "sha256:config_abc123"

    assert extract_config_digest(config_path) == expected_digest


def test_extract_json_file(tmp_path):
    """Test JSON file extraction from tar."""
    tar_dir = tmp_path / "test_tar"
    tar_dir.mkdir()

    # Create JSON file
    json_data = {"test": "data", "array": [1, 2, 3]}
    (tar_dir / "test.json").write_text(json.dumps(json_data))

    # Create invalid JSON file
    (tar_dir / "invalid.json").write_text("invalid json")

    tar_path = tmp_path / "test.tar"
    with tarfile.open(tar_path, "w") as tar:
        tar.add(tar_dir / "test.json", arcname="test.json")
        tar.add(tar_dir / "invalid.json", arcname="invalid.json")

    with tarfile.open(tar_path, "r") as tar:
        # Test valid JSON
        result = extract_json_file(tar, "test.json")
        assert result == json_data

        # Test invalid JSON
        result = extract_json_file(tar, "invalid.json")
        assert result is None

        # Test missing file
        result = extract_json_file(tar, "missing.json")
        assert result is None
