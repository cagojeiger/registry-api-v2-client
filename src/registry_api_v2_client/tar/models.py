"""Data models for tar file handling."""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class LayerInfo:
    """Docker layer information."""

    digest: str
    size: int
    media_type: str
    tar_path: str  # Path within the tar file


@dataclass
class ImageInfo:
    """Docker image information extracted from tar file."""

    repository: str
    tag: str
    config_digest: str
    layers: List[LayerInfo]
    architecture: str
    os: str
    created: datetime
    size: int