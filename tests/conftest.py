"""Test configuration and fixtures."""

import asyncio
import os
import socket

import pytest
import pytest_asyncio

from registry_api_v2_client import check_registry_connectivity
from tests.helpers import TestContext


def is_port_open(host, port):
    """Check if a port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def registry_port():
    """Get registry port for testing."""
    return int(os.getenv("REGISTRY_PORT", "15000"))


@pytest_asyncio.fixture(scope="session")
async def registry_url(registry_port):
    """Get registry URL and ensure it's available."""
    url = f"http://localhost:{registry_port}"

    # Wait for registry to be available (for CI)
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            if is_port_open("localhost", registry_port):
                result = await check_registry_connectivity(url)
                if result:
                    return url
        except Exception:
            pass

        if attempt < max_attempts - 1:
            await asyncio.sleep(1)

    # Skip if registry not available
    pytest.skip(f"Registry not available at {url}")


@pytest_asyncio.fixture
async def test_context(registry_url):
    """Create isolated test context."""
    async with TestContext(registry_url) as ctx:
        yield ctx


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers and settings."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring registry"
    )
    config.addinivalue_line("markers", "unit: mark test as unit test (default)")


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Skip integration tests if no registry
    skip_integration = pytest.mark.skip(reason="Registry not available")

    for item in items:
        if (
            "integration" in item.keywords
            and os.getenv("REGISTRY_AVAILABLE", "false").lower() != "true"
        ):
            item.add_marker(skip_integration)


# Async event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
