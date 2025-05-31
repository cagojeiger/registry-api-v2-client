"""Simple demonstration of tag preservation functionality."""

import asyncio
import hashlib
import json
import logging
import sys
import tarfile
import tempfile

# Add parent directory to path
sys.path.insert(0, "src")

from registry_api_v2_client import (
    extract_original_tags,
    get_primary_tag,
    parse_repository_tag,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_simple_tar():
    """Create a simple test tar file."""
    # Create dummy data
    config_content = json.dumps({"architecture": "amd64", "os": "linux"}).encode(
        "utf-8"
    )
    layer_content = b"dummy layer data"

    config_hash = hashlib.sha256(config_content).hexdigest()
    layer_hash = hashlib.sha256(layer_content).hexdigest()

    # Create manifest
    manifest = [
        {
            "Config": f"blobs/sha256/{config_hash}",
            "RepoTags": ["demo:v1.0", "demo:latest"],
            "Layers": [f"blobs/sha256/{layer_hash}"],
        }
    ]

    # Create repositories data
    repositories = {"demo": {"v1.0": config_hash, "latest": config_hash}}

    # Create tar file
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


async def main():
    """Demonstrate tag extraction functionality."""
    logger.info("Creating simple test tar file...")
    tar_path = create_simple_tar()

    try:
        # Extract all original tags
        original_tags = extract_original_tags(tar_path)
        logger.info(f"Original tags: {original_tags}")

        # Parse each tag
        for tag in original_tags:
            repo, tag_name = parse_repository_tag(tag)
            logger.info(f"  {tag} -> repository: '{repo}', tag: '{tag_name}'")

        # Get primary tag
        primary = get_primary_tag(tar_path)
        if primary:
            logger.info(f"Primary tag: {primary[0]}:{primary[1]}")

        logger.info("Tag extraction working correctly!")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
    finally:
        # Clean up
        import os

        try:
            os.unlink(tar_path)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
