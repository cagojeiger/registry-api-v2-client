"""Tests for tar file validation utilities."""

import json
import tarfile

import pytest

from registry_api_v2_client.exceptions import ValidationError
from registry_api_v2_client.utils.validator import get_tar_manifest, validate_docker_tar


class TestValidateDockerTar:
    """Tests for validate_docker_tar function."""

    def test_validate_synthetic_docker_tar(self, tmp_path):
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

    def test_validate_valid_tar(self, tmp_path):
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

    def test_validate_missing_manifest(self, tmp_path):
        """Test validation fails when manifest.json is missing."""
        tar_dir = tmp_path / "no_manifest"
        tar_dir.mkdir()
        (tar_dir / "some_file.txt").write_text("content")

        tar_path = tmp_path / "no_manifest.tar"
        with tarfile.open(tar_path, "w") as tar:
            tar.add(tar_dir, arcname=".")

        assert validate_docker_tar(tar_path) is False

    def test_validate_invalid_manifest_json(self, tmp_path):
        """Test validation fails with invalid JSON in manifest."""
        tar_dir = tmp_path / "invalid_json"
        tar_dir.mkdir()
        (tar_dir / "manifest.json").write_text("invalid json")

        tar_path = tmp_path / "invalid_json.tar"
        with tarfile.open(tar_path, "w") as tar:
            tar.add(tar_dir, arcname=".")

        assert validate_docker_tar(tar_path) is False

    def test_validate_invalid_manifest_structure(self, tmp_path):
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

    def test_validate_missing_config_file(self, tmp_path):
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

    def test_validate_missing_layer_file(self, tmp_path):
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

    def test_validate_not_a_tar_file(self, tmp_path):
        """Test validation fails for non-tar files."""
        not_tar = tmp_path / "not_a_tar.txt"
        not_tar.write_text("This is not a tar file")

        assert validate_docker_tar(not_tar) is False

    def test_validate_nonexistent_file(self, tmp_path):
        """Test validation raises error for nonexistent files."""
        nonexistent = tmp_path / "does_not_exist.tar"

        with pytest.raises(ValidationError, match="does not exist"):
            validate_docker_tar(nonexistent)

    def test_validate_empty_manifest(self, tmp_path):
        """Test validation fails with empty manifest array."""
        tar_dir = tmp_path / "empty_manifest"
        tar_dir.mkdir()
        (tar_dir / "manifest.json").write_text("[]")

        tar_path = tmp_path / "empty_manifest.tar"
        with tarfile.open(tar_path, "w") as tar:
            tar.add(tar_dir, arcname=".")

        assert validate_docker_tar(tar_path) is False


class TestGetTarManifest:
    """Tests for get_tar_manifest function."""

    def test_get_manifest_valid_tar(self, tmp_path):
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

    def test_get_manifest_invalid_tar(self, tmp_path):
        """Test getting manifest from invalid tar raises error."""
        not_tar = tmp_path / "not_a_tar.txt"
        not_tar.write_text("This is not a tar file")

        with pytest.raises(ValidationError, match="Invalid Docker tar file"):
            get_tar_manifest(not_tar)

    def test_get_manifest_synthetic_docker_tar(self, tmp_path):
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
        (blobs_dir / "synthetic_config").write_text(
            '{"os":"linux","architecture":"amd64"}'
        )
        (blobs_dir / "synthetic_layer").write_text("synthetic layer for testing")

        tar_path = tmp_path / "synthetic.tar"
        with tarfile.open(tar_path, "w") as tar:
            tar.add(tar_dir / "manifest.json", arcname="manifest.json")
            tar.add(
                blobs_dir / "synthetic_config", arcname="blobs/sha256/synthetic_config"
            )
            tar.add(
                blobs_dir / "synthetic_layer", arcname="blobs/sha256/synthetic_layer"
            )

        manifest = get_tar_manifest(tar_path)
        assert isinstance(manifest, list)
        assert len(manifest) > 0
        assert "Config" in manifest[0]
        assert "Layers" in manifest[0]
        assert manifest[0]["RepoTags"] == ["test/synthetic:v1.0"]
