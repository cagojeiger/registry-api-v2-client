"""Comprehensive test coverage for core modules."""

import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

import aiohttp
import pytest

from registry_api_v2_client.core.connectivity import (
    check_api_version_header,
    validate_connectivity_response,
)
from registry_api_v2_client.core.session import create_session, parse_json_response
from registry_api_v2_client.core.types import (
    BlobInfo,
    ManifestInfo,
    RegistryConfig,
    RequestResult,
)
from registry_api_v2_client.exceptions import (
    RegistryError,
    TarReadError,
    ValidationError,
)
from registry_api_v2_client.operations.manifests import (
    calculate_manifest_digest,
    create_manifest_v2,
)
from registry_api_v2_client.tar.tags import (
    extract_original_tags,
    get_primary_tag,
    parse_repository_tag,
)
from registry_api_v2_client.utils.inspect import (
    extract_json_file,
    validate_manifest_data,
)
from registry_api_v2_client.utils.validator import (
    is_path_exists,
    is_valid_tarfile,
    validate_docker_tar,
)


@pytest.fixture
def registry_config():
    """Registry configuration fixture."""
    return RegistryConfig(url="http://localhost:15000", timeout=30)


@pytest.fixture
def test_tar_file():
    """Create a test tar file."""
    config_content = json.dumps(
        {"architecture": "amd64", "os": "linux", "created": "2024-01-01T00:00:00Z"}
    ).encode("utf-8")
    layer_content = b"dummy layer data"

    config_hash = hashlib.sha256(config_content).hexdigest()
    layer_hash = hashlib.sha256(layer_content).hexdigest()

    manifest = [
        {
            "Config": f"blobs/sha256/{config_hash}",
            "RepoTags": ["test:latest"],
            "Layers": [f"blobs/sha256/{layer_hash}"],
        }
    ]

    repositories = {"test": {"latest": config_hash}}

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

    yield tar_path
    Path(tar_path).unlink(missing_ok=True)


class TestCoreTypes:
    """Test core data types."""

    def test_registry_config_creation(self):
        """Test RegistryConfig creation."""
        config = RegistryConfig(url="http://test.com", timeout=60)
        assert config.base_url == "http://test.com"
        assert config.timeout == 60

    def test_blob_info_creation(self):
        """Test BlobInfo creation."""
        blob = BlobInfo(
            digest="sha256:abc123",
            size=1024,
            media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
        )
        assert blob.digest == "sha256:abc123"
        assert blob.size == 1024

    def test_request_result_creation(self):
        """Test RequestResult creation."""
        result = RequestResult(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data=b'{"test": "data"}',
        )
        assert result.status_code == 200
        assert result.headers["Content-Type"] == "application/json"
        assert result.data == b'{"test": "data"}'


class TestSessionOperations:
    """Test session operations."""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        session = await create_session()
        assert isinstance(session, aiohttp.ClientSession)
        await session.close()

    def test_parse_json_response_valid(self):
        """Test JSON response parsing with valid JSON."""
        json_text = '{"key": "value", "number": 42}'
        result = parse_json_response(json_text)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_response_invalid(self):
        """Test JSON response parsing with invalid JSON."""
        result = parse_json_response("invalid json")
        assert result is None

    def test_parse_json_response_empty(self):
        """Test JSON response parsing with empty string."""
        result = parse_json_response("")
        assert result is None


class TestConnectivity:
    """Test connectivity functions."""

    def test_check_api_version_header_valid(self):
        """Test API version header check with valid header."""
        headers = {"Docker-Distribution-Api-Version": "registry/2.0"}
        result = check_api_version_header(headers)
        assert result is True

    def test_check_api_version_header_invalid(self):
        """Test API version header check with invalid header."""
        headers = {"Docker-Distribution-Api-Version": "registry/1.0"}
        result = check_api_version_header(headers)
        assert result is False

    def test_check_api_version_header_missing(self):
        """Test API version header check with missing header."""
        headers = {}
        result = check_api_version_header(headers)
        assert result is False

    def test_validate_connectivity_response_success(self):
        """Test connectivity response validation with success."""
        result = RequestResult(
            status_code=200, headers={"Docker-Distribution-Api-Version": "registry/2.0"}
        )
        # Should not raise
        validate_connectivity_response(result)

    def test_validate_connectivity_response_error(self):
        """Test connectivity response validation with error."""
        result = RequestResult(status_code=500, headers={})
        with pytest.raises(RegistryError):
            validate_connectivity_response(result)


class TestManifestOperations:
    """Test manifest operations."""

    def test_create_manifest_v2(self):
        """Test Docker manifest v2 creation."""
        config = BlobInfo(
            digest="sha256:config123",
            size=1024,
            media_type="application/vnd.docker.container.image.v1+json",
        )
        layers = [
            BlobInfo(
                digest="sha256:layer123",
                size=2048,
                media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
            )
        ]

        manifest_info = ManifestInfo(
            config=config,
            layers=layers,
            schema_version=2,
            media_type="application/vnd.docker.distribution.manifest.v2+json",
        )

        manifest = create_manifest_v2(manifest_info)

        assert manifest["schemaVersion"] == 2
        assert (
            manifest["mediaType"]
            == "application/vnd.docker.distribution.manifest.v2+json"
        )
        assert manifest["config"]["digest"] == "sha256:config123"
        assert len(manifest["layers"]) == 1
        assert manifest["layers"][0]["digest"] == "sha256:layer123"

    def test_calculate_manifest_digest(self):
        """Test manifest digest calculation."""
        manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        }
        digest = calculate_manifest_digest(manifest)
        assert digest.startswith("sha256:")
        assert len(digest) == 71  # "sha256:" + 64 hex chars


class TestTagOperations:
    """Test tag operations."""

    def test_extract_original_tags(self, test_tar_file):
        """Test tag extraction from tar file."""
        tags = extract_original_tags(test_tar_file)
        assert "test:latest" in tags

    def test_get_primary_tag(self, test_tar_file):
        """Test primary tag extraction."""
        repo, tag = get_primary_tag(test_tar_file)
        assert repo == "test"
        assert tag == "latest"

    def test_parse_repository_tag_with_tag(self):
        """Test repository tag parsing with tag."""
        repo, tag = parse_repository_tag("myrepo:v1.0")
        assert repo == "myrepo"
        assert tag == "v1.0"

    def test_parse_repository_tag_without_tag(self):
        """Test repository tag parsing without tag."""
        repo, tag = parse_repository_tag("myrepo")
        assert repo == "myrepo"
        assert tag == "latest"

    def test_parse_repository_tag_with_registry(self):
        """Test repository tag parsing with registry."""
        repo, tag = parse_repository_tag("registry.io/user/repo:v2.0")
        assert repo == "registry.io/user/repo"
        assert tag == "v2.0"


class TestValidationOperations:
    """Test validation operations."""

    def test_validate_docker_tar(self, test_tar_file):
        """Test Docker tar validation."""
        result = validate_docker_tar(Path(test_tar_file))
        assert result is True

    def test_is_path_exists_true(self, test_tar_file):
        """Test path existence check with existing file."""
        result = is_path_exists(Path(test_tar_file))
        assert result is True

    def test_is_path_exists_false(self):
        """Test path existence check with non-existing file."""
        result = is_path_exists(Path("/fake/path.tar"))
        assert result is False

    def test_is_valid_tarfile(self, test_tar_file):
        """Test tarfile validation."""
        result = is_valid_tarfile(Path(test_tar_file))
        assert result is True

    def test_is_valid_tarfile_false(self):
        """Test tarfile validation with non-tar file."""
        # Create a temporary non-tar file
        temp_file = tempfile.mktemp()
        with open(temp_file, "w") as f:
            f.write("not a tar file")
        try:
            result = is_valid_tarfile(Path(temp_file))
            assert result is False
        finally:
            Path(temp_file).unlink(missing_ok=True)


class TestInspectOperations:
    """Test inspect operations."""

    def test_validate_manifest_data_valid(self):
        """Test manifest data validation with valid data."""
        manifest_data = [
            {
                "Config": "config.json",
                "RepoTags": ["test:latest"],
                "Layers": ["layer1.tar"],
            }
        ]
        result = validate_manifest_data(manifest_data)
        assert result is True

    def test_validate_manifest_data_invalid(self):
        """Test manifest data validation with invalid data."""
        result = validate_manifest_data("not a list")
        assert result is False

    def test_extract_json_file(self, test_tar_file):
        """Test JSON file extraction from tar."""
        with tarfile.open(test_tar_file, "r") as tar:
            data = extract_json_file(tar, "manifest.json")
            assert data is not None
            assert isinstance(data, list)
            assert len(data) == 1
            assert "Config" in data[0]


class TestExceptionHandling:
    """Test exception handling."""

    def test_registry_error_creation(self):
        """Test RegistryError creation."""
        error = RegistryError("Test error message")
        assert str(error) == "Test error message"

    def test_tar_read_error_creation(self):
        """Test TarReadError creation."""
        error = TarReadError("Tar read failed")
        assert str(error) == "Tar read failed"

    def test_validation_error_creation(self):
        """Test ValidationError creation."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"


class TestAsyncFunctions:
    """Test async function behavior."""

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self):
        """Test async session context manager."""
        session = await create_session()
        try:
            assert session is not None
            assert isinstance(session, aiohttp.ClientSession)
        finally:
            await session.close()


class TestErrorConditions:
    """Test error conditions for better coverage."""

    def test_request_result_with_json_data(self):
        """Test RequestResult with JSON data property."""
        json_data = {"test": "data"}
        result = RequestResult(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data=b'{"test": "data"}',
            json_data=json_data,
        )
        assert result.json_data == {"test": "data"}

    def test_request_result_with_invalid_json_data(self):
        """Test RequestResult with invalid JSON data."""
        result = RequestResult(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data=b"invalid json",
            json_data=None,
        )
        assert result.json_data is None

    def test_request_result_with_no_data(self):
        """Test RequestResult with no data."""
        result = RequestResult(status_code=200, headers={}, data=None, json_data=None)
        assert result.json_data is None


class TestManifestInfo:
    """Test ManifestInfo data class."""

    def test_manifest_info_creation(self):
        """Test ManifestInfo creation."""
        config = BlobInfo(
            digest="sha256:config123",
            size=1024,
            media_type="application/vnd.docker.container.image.v1+json",
        )
        layers = [
            BlobInfo(
                digest="sha256:layer123",
                size=2048,
                media_type="application/vnd.docker.image.rootfs.diff.tar.gzip",
            )
        ]

        manifest_info = ManifestInfo(
            config=config,
            layers=layers,
            schema_version=2,
            media_type="application/vnd.docker.distribution.manifest.v2+json",
        )

        assert manifest_info.config == config
        assert manifest_info.layers == layers
        assert manifest_info.schema_version == 2
        assert (
            manifest_info.media_type
            == "application/vnd.docker.distribution.manifest.v2+json"
        )
