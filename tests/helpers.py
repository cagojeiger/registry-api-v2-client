"""Test helper functions for isolation and cleanup."""

import os
import time
import uuid

from registry_api_v2_client import delete_image, list_repositories, list_tags


def generate_test_id() -> str:
    """Generate unique test identifier."""
    timestamp = int(time.time() * 1000) % 10000  # Last 4 digits of ms timestamp
    uuid_part = str(uuid.uuid4())[:8]
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
    return f"{worker_id}-{timestamp}-{uuid_part}"


def make_repo_name(base_name: str, test_id: str) -> str:
    """Create isolated repository name."""
    return f"test-{test_id}-{base_name}"


async def cleanup_test_repositories(registry_url: str, test_id: str) -> None:
    """Clean up all repositories created during test."""
    try:
        repos = await list_repositories(registry_url)
        test_repos = [repo for repo in repos if test_id in repo]

        for repo in test_repos:
            try:
                tags = await list_tags(registry_url, repo)
                for tag in tags:
                    try:
                        await delete_image(registry_url, repo, tag)
                    except:
                        pass  # Ignore cleanup errors
            except:
                pass  # Ignore cleanup errors
    except:
        pass  # Ignore cleanup errors


class TestContext:
    """Context manager for test isolation."""

    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.test_id = generate_test_id()
        self.created_repos: list[str] = []

    def repo_name(self, base_name: str) -> str:
        """Get isolated repository name."""
        name = make_repo_name(base_name, self.test_id)
        self.created_repos.append(name)
        return name

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Clean up created repositories
        await cleanup_test_repositories(self.registry_url, self.test_id)
