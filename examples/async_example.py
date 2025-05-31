"""Example usage of async registry API client."""

import asyncio
import logging
import sys

# Add parent directory to path
sys.path.insert(0, "src")

from registry_api_v2_client import (
    RegistryError,
    check_registry_connectivity,
    list_repositories,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Example async operations."""
    registry_url = "http://localhost:15000"

    try:
        # Check connectivity
        logger.info("Checking registry connectivity...")
        await check_registry_connectivity(registry_url)
        logger.info("✓ Registry is accessible")

        # List repositories
        logger.info("Listing repositories...")
        repos = await list_repositories(registry_url)
        logger.info(f"Found {len(repos)} repositories: {repos}")

        # If there are repositories, show their tags
        for repo in repos[:3]:  # Show first 3 repos
            logger.info(f"Getting tags for repository: {repo}")
            from registry_api_v2_client import list_tags

            tags = await list_tags(registry_url, repo)
            logger.info(f"  Tags: {tags}")

    except RegistryError as e:
        logger.error(f"Registry error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


async def concurrent_operations():
    """Example of concurrent async operations."""
    registry_url = "http://localhost:15000"

    try:
        # Run multiple operations concurrently
        logger.info("Running concurrent operations...")

        tasks = [
            check_registry_connectivity(registry_url),
            list_repositories(registry_url),
        ]

        connectivity, repos = await asyncio.gather(*tasks)

        logger.info(f"Connectivity: {connectivity}")
        logger.info(f"Repositories: {repos}")

        # Concurrent tag listing for multiple repos
        if repos:
            from registry_api_v2_client import list_tags

            tag_tasks = [list_tags(registry_url, repo) for repo in repos[:3]]

            if tag_tasks:
                tag_results = await asyncio.gather(*tag_tasks)
                for repo, tags in zip(repos[:3], tag_results, strict=False):
                    logger.info(f"Repository {repo}: {tags}")

    except RegistryError as e:
        logger.error(f"Registry error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    print("=== Basic Async Operations ===")
    asyncio.run(main())

    print("\n=== Concurrent Async Operations ===")
    asyncio.run(concurrent_operations())
