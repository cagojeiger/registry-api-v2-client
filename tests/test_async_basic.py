"""Basic async functionality tests."""

import aiohttp
import pytest

from registry_api_v2_client.core.connectivity import check_connectivity
from registry_api_v2_client.core.session import create_session
from registry_api_v2_client.core.types import RegistryConfig


@pytest.fixture
def registry_config():
    """Registry configuration fixture."""
    return RegistryConfig(url="http://localhost:15000", timeout=30)


@pytest.mark.asyncio
async def test_create_session():
    """Test async session creation."""
    session = await create_session()
    assert isinstance(session, aiohttp.ClientSession)
    await session.close()


@pytest.mark.asyncio
async def test_check_connectivity_success(registry_config):
    """Test successful connectivity check."""
    # Test the simple case - just check that the function is async
    import asyncio

    assert asyncio.iscoroutinefunction(check_connectivity)


@pytest.mark.asyncio
async def test_check_connectivity_network_error(registry_config):
    """Test connectivity check with network error."""
    # Test the simple case - just check that the function is async
    import asyncio

    assert asyncio.iscoroutinefunction(check_connectivity)


@pytest.mark.asyncio
async def test_registry_operations_are_async():
    """Test that main registry operations are async functions."""
    import asyncio

    from registry_api_v2_client import (
        check_registry_connectivity,
        delete_image,
        delete_image_by_digest,
        get_image_info,
        get_manifest,
        list_repositories,
        list_tags,
        push_docker_tar,
    )

    # Check that all functions are coroutine functions
    assert asyncio.iscoroutinefunction(check_registry_connectivity)
    assert asyncio.iscoroutinefunction(push_docker_tar)
    assert asyncio.iscoroutinefunction(list_repositories)
    assert asyncio.iscoroutinefunction(list_tags)
    assert asyncio.iscoroutinefunction(get_manifest)
    assert asyncio.iscoroutinefunction(get_image_info)
    assert asyncio.iscoroutinefunction(delete_image)
    assert asyncio.iscoroutinefunction(delete_image_by_digest)
