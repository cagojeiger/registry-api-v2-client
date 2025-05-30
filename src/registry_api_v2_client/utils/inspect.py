"""Docker tar file inspection utilities."""

import json
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..exceptions import TarReadError, ValidationError
from ..models import ImageConfig, ImageInspect, LayerInfo
from .validator import validate_docker_tar


def extract_json_file(
    tar: tarfile.TarFile, file_path: str
) -> dict[str, Any] | list[Any] | None:
    """Extract and parse JSON file from tar."""
    try:
        member = tar.extractfile(file_path)
        if member is None:
            return None
        content = member.read().decode("utf-8")
        return json.loads(content)  # type: ignore[no-any-return]
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def validate_manifest_data(manifest_data: Any) -> bool:
    """Validate manifest data structure."""
    return manifest_data is not None and isinstance(manifest_data, list)


def validate_config_data(config_data: Any) -> bool:
    """Validate config data structure."""
    return config_data is not None and isinstance(config_data, dict)


def get_layer_size_from_tar(tar: tarfile.TarFile, layer_path: str) -> int:
    """Get layer size from tar member."""
    try:
        member = tar.getmember(layer_path)
        return member.size
    except KeyError:
        return 0


def extract_digest_from_path(layer_path: str) -> str:
    """Extract digest from layer path."""
    return f"sha256:{layer_path.split('/')[-1]}"


def get_layer_source_key(layer_digest: str) -> str:
    """Get layer source key from digest."""
    return layer_digest.replace("sha256:", "")


def get_layer_media_type(layer_source: dict[str, Any]) -> str:
    """Get layer media type with default fallback."""
    return str(
        layer_source.get("mediaType", "application/vnd.docker.image.rootfs.diff.tar")
    )


def create_layer_info(
    layer_digest: str, layer_source: dict[str, Any], layer_size: int
) -> LayerInfo:
    """Create LayerInfo object from layer data."""
    return LayerInfo(
        digest=layer_digest,
        size=layer_source.get("size", layer_size),
        media_type=get_layer_media_type(layer_source),
    )


def build_layers_info(
    tar: tarfile.TarFile, layer_paths: list[str], layer_sources: dict[str, Any]
) -> tuple[list[LayerInfo], int]:
    """Build layer information and calculate total size."""
    layers = []
    total_size = 0

    for layer_path in layer_paths:
        layer_size = get_layer_size_from_tar(tar, layer_path)
        layer_digest = extract_digest_from_path(layer_path)
        layer_source_key = get_layer_source_key(layer_digest)
        layer_source = layer_sources.get(f"sha256:{layer_source_key}", {})

        layer_info = create_layer_info(layer_digest, layer_source, layer_size)
        layers.append(layer_info)
        total_size += layer_source.get("size", layer_size)

    return layers, total_size


def parse_created_timestamp(created_str: str) -> datetime:
    """Parse created timestamp with fallback."""
    try:
        return datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now()


def get_runtime_config(config_data: dict[str, Any]) -> dict[str, Any]:
    """Extract runtime config from config data."""
    return dict(config_data.get("config", {}))


def get_environment_variables(runtime_config: dict[str, Any]) -> list[str]:
    """Extract environment variables from runtime config."""
    return list(runtime_config.get("Env", []))


def get_exposed_ports(runtime_config: dict[str, Any]) -> dict[str, Any]:
    """Extract exposed ports from runtime config."""
    return dict(runtime_config.get("ExposedPorts", {}))


def get_labels(runtime_config: dict[str, Any]) -> dict[str, str]:
    """Extract labels from runtime config."""
    return runtime_config.get("Labels", {}) or {}


def get_diff_ids(config_data: dict[str, Any]) -> list[str]:
    """Extract diff_ids from rootfs config."""
    rootfs = config_data.get("rootfs", {})
    return list(rootfs.get("diff_ids", []))


def parse_image_config(config_data: dict[str, Any]) -> ImageConfig:
    """Parse Docker image config JSON into ImageConfig model."""
    created_str = config_data.get("created", "")
    created = parse_created_timestamp(created_str)

    runtime_config = get_runtime_config(config_data)
    env_list = get_environment_variables(runtime_config)
    exposed_ports = get_exposed_ports(runtime_config)
    labels = get_labels(runtime_config)
    diff_ids = get_diff_ids(config_data)

    return ImageConfig(
        architecture=config_data.get("architecture", ""),
        os=config_data.get("os", ""),
        created=created,
        cmd=runtime_config.get("Cmd", []) or [],
        entrypoint=runtime_config.get("Entrypoint", []) or [],
        env=env_list,
        user=runtime_config.get("User", ""),
        working_dir=runtime_config.get("WorkingDir"),
        exposed_ports=exposed_ports,
        labels=labels,
        diff_ids=diff_ids,
    )


def extract_config_digest(config_path: str) -> str:
    """Extract config digest from config path."""
    return f"sha256:{config_path.split('/')[-1]}"


def build_image_inspect(
    manifest: dict[str, Any],
    image_config: ImageConfig,
    layers: list[LayerInfo],
    total_size: int,
    config_digest: str,
) -> ImageInspect:
    """Build ImageInspect object from parsed data."""
    repo_tags = manifest.get("RepoTags", [])

    return ImageInspect(
        id=config_digest,
        repo_tags=repo_tags,
        created=image_config.created,
        config=image_config,
        layers=layers,
        size=total_size,
        virtual_size=total_size,
        architecture=image_config.architecture,
        os=image_config.os,
        rootfs_layers=image_config.diff_ids,
    )


def inspect_docker_tar(tar_path: Path) -> ImageInspect:
    """
    Inspect a Docker tar file and return detailed image information.

    Args:
        tar_path: Path to the Docker tar file

    Returns:
        ImageInspect object with complete image information

    Raises:
        ValidationError: If tar file is invalid
        TarReadError: If tar file cannot be read
    """
    if not validate_docker_tar(tar_path):
        raise ValidationError(f"Invalid Docker tar file: {tar_path}")

    try:
        with tarfile.open(tar_path, "r") as tar:
            # Extract manifest
            manifest_data = extract_json_file(tar, "manifest.json")
            if not validate_manifest_data(manifest_data):
                raise TarReadError("Invalid manifest.json")

            # Type guard ensures manifest_data is a list at this point
            assert isinstance(manifest_data, list)
            manifest = manifest_data[0]  # Use first image

            # Extract config
            config_path = manifest["Config"]
            config_data = extract_json_file(tar, config_path)
            if not validate_config_data(config_data):
                raise TarReadError(f"Cannot read config file: {config_path}")

            # Parse layers from manifest
            layer_paths = manifest.get("Layers", [])
            layer_sources = manifest.get("LayerSources", {})

            # Build layer info
            layers, total_size = build_layers_info(tar, layer_paths, layer_sources)

            # Type guard ensures config_data is a dict at this point
            assert isinstance(config_data, dict)
            image_config = parse_image_config(config_data)

            # Calculate config digest
            config_digest = extract_config_digest(config_path)

            # Build final result
            return build_image_inspect(
                manifest, image_config, layers, total_size, config_digest
            )

    except (tarfile.TarError, json.JSONDecodeError, KeyError) as e:
        raise TarReadError(f"Failed to inspect tar file: {e}") from e
