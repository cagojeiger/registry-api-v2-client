"""Async HTTP session management for registry operations."""

import json
from typing import Any

import aiohttp
from aiohttp import ClientConnectorError, ClientResponseError, ClientTimeout

from ..exceptions import RegistryError
from .types import RegistryConfig, RequestResult


async def create_session() -> aiohttp.ClientSession:
    """Create async HTTP session with retry and timeout configuration."""
    timeout = ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)

    return aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={"User-Agent": "registry-api-v2-client/1.1.0"},
    )


def parse_json_response(text: str) -> dict[str, Any] | None:
    """Parse JSON response safely."""
    try:
        result = json.loads(text)
        # Ensure we return proper Dict type
        return dict(result) if isinstance(result, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


async def make_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    config: RegistryConfig,
    headers: dict[str, str] | None = None,
    data: bytes | str | None = None,
    expect_json: bool = False,
) -> RequestResult:
    """Make async HTTP request and return structured result.

    Args:
        session: Async HTTP session
        method: HTTP method
        url: Request URL
        config: Registry configuration
        headers: Optional request headers
        data: Optional request body
        expect_json: Whether to parse response as JSON

    Returns:
        RequestResult with response data

    Raises:
        RegistryError: If request fails
    """
    try:
        timeout = ClientTimeout(total=config.timeout)

        async with session.request(
            method=method, url=url, headers=headers, data=data, timeout=timeout
        ) as response:
            # Raise for HTTP errors
            response.raise_for_status()

            result_data = None
            json_data = None

            # Read response content
            content = await response.read()
            if content:
                result_data = content
                if expect_json:
                    text = await response.text()
                    json_data = parse_json_response(text)

            return RequestResult(
                status_code=response.status,
                headers=dict(response.headers),
                data=result_data,
                json_data=json_data,
            )

    except ClientConnectorError as e:
        raise RegistryError(f"Connection failed: {e}") from e
    except ClientResponseError as e:
        raise RegistryError(f"HTTP error {e.status}: {e.message}") from e
    except Exception as e:
        raise RegistryError(f"Request failed: {e}") from e


async def make_get_request(
    session: aiohttp.ClientSession,
    url: str,
    config: RegistryConfig,
    headers: dict[str, str] | None = None,
    expect_json: bool = True,
) -> RequestResult:
    """Make async GET request."""
    return await make_request(
        session, "GET", url, config, headers, expect_json=expect_json
    )


async def make_post_request(
    session: aiohttp.ClientSession,
    url: str,
    config: RegistryConfig,
    headers: dict[str, str] | None = None,
    data: bytes | str | None = None,
) -> RequestResult:
    """Make async POST request."""
    return await make_request(session, "POST", url, config, headers, data)


async def make_put_request(
    session: aiohttp.ClientSession,
    url: str,
    config: RegistryConfig,
    headers: dict[str, str] | None = None,
    data: bytes | str | None = None,
) -> RequestResult:
    """Make async PUT request."""
    return await make_request(session, "PUT", url, config, headers, data)


async def make_patch_request(
    session: aiohttp.ClientSession,
    url: str,
    config: RegistryConfig,
    headers: dict[str, str] | None = None,
    data: bytes | str | None = None,
) -> RequestResult:
    """Make async PATCH request."""
    return await make_request(session, "PATCH", url, config, headers, data)


async def make_delete_request(
    session: aiohttp.ClientSession,
    url: str,
    config: RegistryConfig,
    headers: dict[str, str] | None = None,
) -> RequestResult:
    """Make async DELETE request."""
    return await make_request(session, "DELETE", url, config, headers)


async def make_head_request(
    session: aiohttp.ClientSession,
    url: str,
    config: RegistryConfig,
    headers: dict[str, str] | None = None,
) -> RequestResult:
    """Make async HEAD request."""
    return await make_request(session, "HEAD", url, config, headers)
