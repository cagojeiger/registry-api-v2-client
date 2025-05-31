"""Async repository operations for registry."""

from typing import Any

from ..core.connectivity import check_connectivity
from ..core.session import create_session, make_get_request
from ..core.types import RegistryConfig
from ..exceptions import RegistryError


def extract_repositories_from_response(json_data: dict[str, Any] | None) -> list[str]:
    """Extract repositories list from API response.

    Args:
        json_data: JSON response data

    Returns:
        List of repository names
    """
    if not json_data:
        return []

    repositories = json_data.get("repositories", [])
    return list(repositories) if isinstance(repositories, list) else []


def extract_tags_from_response(json_data: dict[str, Any] | None) -> list[str]:
    """Extract tags list from API response.

    Args:
        json_data: JSON response data

    Returns:
        List of tag names
    """
    if not json_data:
        return []

    tags = json_data.get("tags")
    return tags if tags else []


async def list_repositories(config: RegistryConfig) -> list[str]:
    """List all repositories in registry.

    Args:
        config: Registry configuration

    Returns:
        List of repository names

    Raises:
        RegistryError: If request fails
    """
    # Check connectivity first
    await check_connectivity(config)

    url = f"{config.base_url}/v2/_catalog"

    session = await create_session()
    try:
        result = await make_get_request(session, url, config, expect_json=True)
        return extract_repositories_from_response(result.json_data)

    except Exception as e:
        raise RegistryError(f"Failed to list repositories: {e}") from e
    finally:
        await session.close()


async def list_tags(config: RegistryConfig, repository: str) -> list[str]:
    """List all tags for a repository.

    Args:
        config: Registry configuration
        repository: Repository name

    Returns:
        List of tag names

    Raises:
        RegistryError: If request fails
    """
    # Check connectivity first
    await check_connectivity(config)

    url = f"{config.base_url}/v2/{repository}/tags/list"

    session = await create_session()
    try:
        result = await make_get_request(session, url, config, expect_json=True)
        return extract_tags_from_response(result.json_data)

    except Exception as e:
        raise RegistryError(f"Failed to list tags for {repository}: {e}") from e
    finally:
        await session.close()
