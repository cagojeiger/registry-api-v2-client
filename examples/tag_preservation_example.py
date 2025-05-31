"""Example of tag preservation when pushing Docker tar files."""

import asyncio
import json
import logging
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, "src")

from registry_api_v2_client import (
    RegistryError,
    extract_original_tags,
    get_primary_tag,
    list_repositories,
    list_tags,
    parse_repository_tag,
    push_docker_tar,
    push_docker_tar_with_all_original_tags,
    push_docker_tar_with_original_tags,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_tar_with_multiple_tags():
    """Create a test tar file with multiple tags."""
    import hashlib
    import tarfile

    # Create dummy data and calculate actual digests
    config_content = json.dumps({"architecture": "amd64", "os": "linux"}).encode(
        "utf-8"
    )
    layer_content = b"dummy layer data"

    config_hash = hashlib.sha256(config_content).hexdigest()
    layer_hash = hashlib.sha256(layer_content).hexdigest()
    config_digest = f"sha256:{config_hash}"
    layer_digest = f"sha256:{layer_hash}"

    # Create a minimal manifest with multiple tags
    manifest = [
        {
            "Config": f"blobs/sha256/{config_hash}",
            "RepoTags": ["nginx:alpine", "nginx:1.21-alpine", "my-nginx:latest"],
            "Layers": [f"blobs/sha256/{layer_hash}"],
        }
    ]

    # Create repositories data
    repositories = {
        "nginx": {"alpine": config_hash, "1.21-alpine": config_hash},
        "my-nginx": {"latest": config_hash},
    }

    # Create test tar file
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

        # Add config blob with correct digest
        config_info = tarfile.TarInfo(f"blobs/sha256/{config_hash}")
        config_info.size = len(config_content)
        tar.addfile(config_info, fileobj=tarfile.io.BytesIO(config_content))

        # Add layer blob with correct digest
        layer_info = tarfile.TarInfo(f"blobs/sha256/{layer_hash}")
        layer_info.size = len(layer_content)
        tar.addfile(layer_info, fileobj=tarfile.io.BytesIO(layer_content))

    return tar_path


async def demonstrate_tag_extraction(tar_path: str):
    """Demonstrate tag extraction from tar file."""
    logger.info("=== Tag Extraction Demo ===")

    # Extract all original tags
    try:
        original_tags = extract_original_tags(tar_path)
        logger.info(f"Original tags found: {original_tags}")

        # Parse each tag
        for tag in original_tags:
            repo, tag_name = parse_repository_tag(tag)
            logger.info(f"  {tag} -> repository: '{repo}', tag: '{tag_name}'")

        # Get primary tag
        primary = get_primary_tag(tar_path)
        if primary:
            logger.info(f"Primary tag: {primary[0]}:{primary[1]}")

    except Exception as e:
        logger.error(f"Tag extraction failed: {e}")


async def demonstrate_push_variations(tar_path: str, registry_url: str):
    """Demonstrate different push strategies."""
    logger.info("=== Push Strategies Demo ===")

    try:
        # 1. Manual override (traditional way)
        logger.info("1. Manual repository/tag override:")
        digest1 = await push_docker_tar(
            tar_path, registry_url, repository="test-manual", tag="v1.0"
        )
        logger.info(f"   Pushed to test-manual:v1.0 -> {digest1[:16]}...")

        # 2. Auto-extract first tag
        logger.info("2. Auto-extract primary tag:")
        digest2 = await push_docker_tar_with_original_tags(tar_path, registry_url)
        logger.info(f"   Pushed with original primary tag -> {digest2[:16]}...")

        # 3. Preserve ALL original tags
        logger.info("3. Preserve ALL original tags:")
        digests = await push_docker_tar_with_all_original_tags(tar_path, registry_url)
        logger.info(f"   Pushed {len(digests)} tags:")
        for i, digest in enumerate(digests):
            logger.info(f"     Tag {i + 1}: {digest[:16]}...")

    except RegistryError as e:
        logger.error(f"Push failed: {e}")


async def verify_pushed_images(registry_url: str):
    """Verify that all images were pushed correctly."""
    logger.info("=== Verification ===")

    try:
        repos = await list_repositories(registry_url)
        logger.info(f"Repositories after push: {repos}")

        for repo in repos:
            if any(name in repo for name in ["nginx", "my-nginx", "test-manual"]):
                tags = await list_tags(registry_url, repo)
                logger.info(f"  {repo}: {tags}")

    except RegistryError as e:
        logger.error(f"Verification failed: {e}")


async def main():
    """Main demonstration."""
    registry_url = "http://localhost:15000"

    # Create test tar file with multiple tags
    logger.info("Creating test tar file with multiple tags...")
    tar_path = create_test_tar_with_multiple_tags()

    try:
        # Demonstrate tag extraction
        await demonstrate_tag_extraction(tar_path)

        # Demonstrate different push strategies
        await demonstrate_push_variations(tar_path, registry_url)

        # Verify results
        await verify_pushed_images(registry_url)

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
