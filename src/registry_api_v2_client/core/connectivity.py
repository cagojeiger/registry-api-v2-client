"""Async registry connectivity checking functions."""

from aiohttp import ClientConnectorError, ClientResponseError, ClientTimeout

from ..exceptions import RegistryError
from .session import create_session
from .types import RegistryConfig, RequestResult


def check_api_version_header(headers: dict[str, str]) -> bool:
    """Check if response contains valid API v2 header."""
    api_version = headers.get("Docker-Distribution-Api-Version")
    return api_version is not None and "registry/2.0" in api_version


def validate_connectivity_response(result: RequestResult) -> None:
    """Validate registry connectivity response."""
    if result.status_code == 200:
        if not check_api_version_header(result.headers):
            raise RegistryError(
                f"Registry does not support API v2. "
                f"API version: {result.headers.get('Docker-Distribution-Api-Version')}"
            )
    elif result.status_code == 401:
        raise RegistryError(
            "Registry requires authentication. "
            "This client only supports unauthenticated registries."
        )
    else:
        raise RegistryError(
            f"Registry returned unexpected status: {result.status_code}"
        )


async def check_connectivity(config: RegistryConfig) -> bool:
    """Check if registry is accessible and supports API v2.

    Args:
        config: Registry configuration

    Returns:
        True if registry is accessible and supports v2 API

    Raises:
        RegistryError: If registry is not accessible or doesn't support v2
    """
    url = f"{config.base_url}/v2/"

    session = await create_session()

    try:
        timeout = ClientTimeout(total=config.timeout)

        async with session.get(url, timeout=timeout) as response:
            result = RequestResult(
                status_code=response.status, headers=dict(response.headers)
            )

            validate_connectivity_response(result)
            return True

    except ClientConnectorError as e:
        raise RegistryError(f"Failed to connect to registry: {e}") from e
    except ClientResponseError as e:
        # Don't raise for expected status codes, let validate_connectivity_response handle them
        result = RequestResult(
            status_code=e.status, headers=dict(e.headers) if e.headers else {}
        )
        validate_connectivity_response(result)
        return True
    except Exception as e:
        raise RegistryError(f"Failed to connect to registry: {e}") from e
    finally:
        await session.close()
