"""Simple async tests that work without complex mocking."""

import asyncio

import pytest

from registry_api_v2_client.core.session import create_session
from registry_api_v2_client.tar.tags import (
    parse_repository_tag,
)


@pytest.mark.asyncio
async def test_create_session():
    """Test async session creation."""
    session = await create_session()
    assert session is not None
    await session.close()


def test_tag_functions_are_sync():
    """Test that tag functions work synchronously."""
    # Test parse_repository_tag
    repo, tag = parse_repository_tag("nginx:alpine")
    assert repo == "nginx"
    assert tag == "alpine"

    repo, tag = parse_repository_tag("localhost:5000/app:latest")
    assert repo == "localhost:5000/app"
    assert tag == "latest"

    repo, tag = parse_repository_tag("myapp")
    assert repo == "myapp"
    assert tag == "latest"


@pytest.mark.asyncio
async def test_async_workflow_concepts():
    """Test that our async concepts work."""

    # Test that we can use asyncio.gather
    async def dummy_task(n):
        await asyncio.sleep(0.001)  # Very short sleep
        return n * 2

    results = await asyncio.gather(dummy_task(1), dummy_task(2), dummy_task(3))

    assert results == [2, 4, 6]


def test_imports_work():
    """Test that all our main imports work."""
    from registry_api_v2_client import (
        check_registry_connectivity,
        extract_original_tags,
        get_primary_tag,
        parse_repository_tag,
        push_docker_tar,
        push_docker_tar_with_all_original_tags,
        push_docker_tar_with_original_tags,
    )

    # Test that functions are callable
    assert callable(extract_original_tags)
    assert callable(parse_repository_tag)
    assert callable(get_primary_tag)
    assert callable(check_registry_connectivity)
    assert callable(push_docker_tar)
    assert callable(push_docker_tar_with_original_tags)
    assert callable(push_docker_tar_with_all_original_tags)
