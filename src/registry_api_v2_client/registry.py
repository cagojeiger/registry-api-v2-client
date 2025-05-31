"""Async functional registry operations."""

from typing import Any

from .core.types import RegistryConfig
from .operations.images import delete_image as _delete_image
from .operations.images import delete_image_by_digest as _delete_image_by_digest
from .operations.images import get_image_info as _get_image_info
from .operations.manifests import get_manifest as _get_manifest
from .operations.repositories import list_repositories as _list_repositories
from .operations.repositories import list_tags as _list_tags


async def list_repositories(registry_url: str, timeout: int = 10) -> list[str]:
    """레지스트리의 모든 저장소 목록을 조회합니다.

    Args:
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        timeout: 요청 타임아웃 (초, 기본값: 10초)

    Returns:
        list[str]: 저장소 이름 목록 (예: ["nginx", "myapp", "test/image"])

    Raises:
        RegistryError: 요청 실패 시

    Examples:
        # 모든 저장소 조회
        repos = await list_repositories("http://localhost:15000")
        print(f"발견된 저장소: {repos}")
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _list_repositories(config)


async def list_tags(registry_url: str, repository: str, timeout: int = 10) -> list[str]:
    """특정 저장소의 모든 태그 목록을 조회합니다.

    Args:
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        repository: 저장소 이름 (예: "nginx", "mycompany/myapp")
        timeout: 요청 타임아웃 (초, 기본값: 10초)

    Returns:
        list[str]: 태그 이름 목록 (예: ["latest", "v1.0.0", "alpine"])

    Raises:
        RegistryError: 요청 실패 시

    Examples:
        # 특정 저장소의 태그 조회
        tags = await list_tags("http://localhost:15000", "nginx")
        print(f"nginx 태그: {tags}")
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _list_tags(config, repository)


async def get_manifest(
    registry_url: str, repository: str, tag: str, timeout: int = 10
) -> dict[str, Any]:
    """이미지의 매니페스트를 조회합니다.

    Args:
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        repository: 저장소 이름 (예: "nginx", "mycompany/myapp")
        tag: 태그 이름 (예: "latest", "v1.0.0")
        timeout: 요청 타임아웃 (초, 기본값: 10초)

    Returns:
        dict[str, Any]: 매니페스트 딕셔너리 (Docker Registry API v2 스키마)

    Raises:
        RegistryError: 요청 실패 시

    Examples:
        # 이미지 매니페스트 조회
        manifest = await get_manifest("http://localhost:15000", "nginx", "latest")
        print(f"스키마 버전: {manifest['schemaVersion']}")
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _get_manifest(config, repository, tag)


async def get_image_info(
    registry_url: str, repository: str, tag: str, timeout: int = 10
) -> dict[str, Any]:
    """이미지의 상세 정보를 조회합니다.

    Args:
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        repository: 저장소 이름 (예: "nginx", "mycompany/myapp")
        tag: 태그 이름 (예: "latest", "v1.0.0")
        timeout: 요청 타임아웃 (초, 기본값: 10초)

    Returns:
        dict[str, Any]: 이미지 정보 딕셔너리 (아키텍처, OS, 크기, 생성일 등)

    Raises:
        RegistryError: 요청 실패 시

    Examples:
        # 이미지 상세 정보 조회
        info = await get_image_info("http://localhost:15000", "nginx", "latest")
        print(f"아키텍처: {info.get('architecture', '알 수 없음')}")
        print(f"크기: {info.get('size', 0):,} bytes")
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _get_image_info(config, repository, tag)


async def delete_image(
    registry_url: str, repository: str, tag: str, timeout: int = 10
) -> bool:
    """레지스트리에서 이미지를 삭제합니다.

    Args:
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        repository: 저장소 이름 (예: "nginx", "mycompany/myapp")
        tag: 태그 이름 (예: "latest", "v1.0.0")
        timeout: 요청 타임아웃 (초, 기본값: 10초)

    Returns:
        bool: 삭제 성공 시 True

    Raises:
        RegistryError: 삭제 실패 시

    Note:
        레지스트리에서 REGISTRY_STORAGE_DELETE_ENABLED=true 설정이 필요합니다.

    Examples:
        # 특정 태그 삭제
        success = await delete_image("http://localhost:15000", "nginx", "v1.0")
        if success:
            print("이미지 삭제 완료")
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _delete_image(config, repository, tag)


async def delete_image_by_digest(
    registry_url: str, repository: str, digest: str, timeout: int = 10
) -> bool:
    """매니페스트 digest로 이미지를 삭제합니다.

    Args:
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        repository: 저장소 이름 (예: "nginx", "mycompany/myapp")
        digest: 매니페스트 digest (예: "sha256:abc123...")
        timeout: 요청 타임아웃 (초, 기본값: 10초)

    Returns:
        bool: 삭제 성공 시 True

    Raises:
        RegistryError: 삭제 실패 시

    Note:
        레지스트리에서 REGISTRY_STORAGE_DELETE_ENABLED=true 설정이 필요합니다.
        digest로 삭제하면 해당 매니페스트를 참조하는 모든 태그가 영향받을 수 있습니다.

    Examples:
        # digest로 이미지 삭제
        manifest = await get_manifest("http://localhost:15000", "nginx", "latest")
        digest = manifest.get('digest')
        if digest:
            success = await delete_image_by_digest("http://localhost:15000", "nginx", digest)
    """
    config = RegistryConfig(url=registry_url, timeout=timeout)
    return await _delete_image_by_digest(config, repository, digest)
