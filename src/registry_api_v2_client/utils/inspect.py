"""Docker tar file inspection utilities."""

import json
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..exceptions import TarReadError, ValidationError
from ..models import ImageConfig, ImageInspect, LayerInfo
from .validator import validate_docker_tar


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
            manifest_data = _extract_json_file(tar, "manifest.json")
            if not manifest_data or not isinstance(manifest_data, list):
                raise TarReadError("Invalid manifest.json")

            manifest = manifest_data[0]  # Use first image

            # Extract config
            config_path = manifest["Config"]
            config_data = _extract_json_file(tar, config_path)
            if not config_data or not isinstance(config_data, dict):
                raise TarReadError(f"Cannot read config file: {config_path}")

            # Parse layers from manifest
            layer_paths = manifest.get("Layers", [])
            layer_sources = manifest.get("LayerSources", {})

            # Build layer info
            layers = []
            total_size = 0

            for layer_path in layer_paths:
                # Get layer size from tar member
                try:
                    member = tar.getmember(layer_path)
                    layer_size = member.size
                except KeyError:
                    layer_size = 0

                # Extract digest from path (format: blobs/sha256/digest)
                layer_digest = f"sha256:{layer_path.split('/')[-1]}"

                # Get additional info from LayerSources if available
                layer_source_key = layer_digest.replace("sha256:", "")
                layer_source = layer_sources.get(f"sha256:{layer_source_key}", {})

                layers.append(
                    LayerInfo(
                        digest=layer_digest,
                        size=layer_source.get("size", layer_size),
                        media_type=layer_source.get(
                            "mediaType", "application/vnd.docker.image.rootfs.diff.tar"
                        ),
                    )
                )
                total_size += layer_source.get("size", layer_size)

            # Parse image config
            image_config = _parse_image_config(config_data)

            # Extract repository tags
            repo_tags = manifest.get("RepoTags", [])

            # Calculate config digest
            config_digest = f"sha256:{config_path.split('/')[-1]}"

            # Build final result
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

    except (tarfile.TarError, json.JSONDecodeError, KeyError) as e:
        raise TarReadError(f"Failed to inspect tar file: {e}") from e


def _extract_json_file(
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


def _parse_image_config(config_data: dict[str, Any]) -> ImageConfig:
    """Parse Docker image config JSON into ImageConfig model."""
    # Parse created timestamp
    created_str = config_data.get("created", "")
    try:
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        created = datetime.now()

    # Parse runtime config
    runtime_config = config_data.get("config", {})

    # Parse environment variables
    env_list = runtime_config.get("Env", [])

    # Parse exposed ports
    exposed_ports = runtime_config.get("ExposedPorts", {})

    # Parse labels
    labels = runtime_config.get("Labels", {}) or {}

    # Parse rootfs diff_ids
    rootfs = config_data.get("rootfs", {})
    diff_ids = rootfs.get("diff_ids", [])

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
