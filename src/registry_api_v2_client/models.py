"""Data models for Registry API v2 client."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ImageConfig(BaseModel):
    """Docker image configuration."""

    # Basic info
    architecture: str
    os: str
    created: datetime

    # Runtime config
    cmd: list[str] = Field(default_factory=list)
    entrypoint: list[str] = Field(default_factory=list)
    env: list[str] = Field(default_factory=list)
    user: str = ""
    working_dir: str | None = None
    exposed_ports: dict[str, Any] = Field(default_factory=dict)

    # Labels and metadata
    labels: dict[str, str] = Field(default_factory=dict)

    # Layer information
    diff_ids: list[str] = Field(default_factory=list)


class LayerInfo(BaseModel):
    """Docker image layer information."""

    digest: str
    size: int
    media_type: str
    created: datetime | None = None
    created_by: str | None = None


class ImageInspect(BaseModel):
    """Complete Docker image inspection result."""

    # Basic image metadata
    id: str = Field(..., description="Config digest")
    repo_tags: list[str] = Field(default_factory=list)
    repo_digests: list[str] = Field(default_factory=list)
    parent: str | None = None
    comment: str = ""
    created: datetime

    # Image configuration
    config: ImageConfig

    # Layer information
    layers: list[LayerInfo] = Field(default_factory=list)

    # Size information
    size: int = 0
    virtual_size: int = 0

    # Metadata
    architecture: str
    os: str
    author: str = ""

    # Root filesystem
    rootfs_type: str = "layers"
    rootfs_layers: list[str] = Field(default_factory=list)
