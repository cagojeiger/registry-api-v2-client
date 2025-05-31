"""Async functional style push operations."""

import asyncio

from .core.connectivity import check_connectivity
from .core.types import BlobInfo, ManifestInfo, RegistryConfig
from .exceptions import RegistryError
from .operations.blobs import upload_blob
from .operations.manifests import _create_manifest_v2, upload_manifest
from .tar.processor import process_tar_file
from .tar.tags import extract_original_tags, get_primary_tag, parse_repository_tag


async def _upload_all_blobs(
    config: RegistryConfig, repository: str, tar_path: str, blob_infos: list[BlobInfo]
) -> list[str]:
    """Upload all blobs concurrently to registry.

    Args:
        config: Registry configuration
        repository: Repository name
        tar_path: Path to tar file
        blob_infos: List of blob information

    Returns:
        List of uploaded blob digests
    """
    # Upload blobs concurrently for better performance
    tasks = [
        upload_blob(config, repository, tar_path, blob_info) for blob_info in blob_infos
    ]

    return await asyncio.gather(*tasks)


async def _create_and_upload_manifest(
    config: RegistryConfig, repository: str, tag: str, manifest_info: ManifestInfo
) -> str:
    """Create manifest and upload to registry.

    Args:
        config: Registry configuration
        repository: Repository name
        tag: Tag name
        manifest_info: Manifest information

    Returns:
        Manifest digest
    """
    # Create manifest
    manifest = _create_manifest_v2(manifest_info)

    # Upload manifest
    return await upload_manifest(config, repository, tag, manifest)


async def check_registry_connectivity(registry_url: str) -> bool:
    """레지스트리 연결 상태를 확인합니다.

    Args:
        registry_url: 레지스트리 URL (예: "http://localhost:15000", "https://registry.example.com")

    Returns:
        bool: 레지스트리 접근 가능 시 True

    Raises:
        RegistryError: 연결 확인 실패 시

    Examples:
        # 로컬 레지스트리 연결 확인
        accessible = await check_registry_connectivity("http://localhost:15000")

        # 원격 레지스트리 연결 확인
        accessible = await check_registry_connectivity("https://registry.example.com")
    """
    config = RegistryConfig(url=registry_url)
    return await check_connectivity(config)


async def push_docker_tar(
    tar_path: str,
    registry_url: str,
    repository: str | None = None,
    tag: str | None = None,
    timeout: int = 300,
) -> str:
    """Docker tar 파일을 레지스트리에 비동기로 푸시합니다.

    tar 파일에서 자동으로 원본 저장소명과 태그를 추출하여 사용합니다.
    명시적으로 지정하면 해당 값을 우선 사용합니다.

    Args:
        tar_path: Docker tar 파일 경로
            - 상대경로: "my-app.tar", "./images/nginx.tar", "../docker-images/app.tar"
            - 절대경로: "/Users/user/images/my-app.tar", "/home/user/docker/nginx.tar"
            - 현재 디렉토리: "nginx.tar" (현재 작업 디렉토리에서 찾음)
        registry_url: 레지스트리 URL (예: "http://localhost:15000", "https://registry.example.com")
        repository: 저장소 이름 (선택사항, tar에서 자동 추출됨. 예: "mycompany/myapp")
        tag: 이미지 태그 (선택사항, tar에서 자동 추출됨. 예: "latest", "v1.0.0")
        timeout: 요청 타임아웃 (초, 기본값: 300초)

    Returns:
        str: 푸시된 이미지의 매니페스트 digest (예: "sha256:abc123...")

    Raises:
        FileNotFoundError: tar 파일이 존재하지 않는 경우
        RegistryError: 푸시 작업 실패 또는 저장소/태그를 결정할 수 없는 경우

    Examples:
        # 현재 디렉토리의 tar 파일 (상대경로)
        await push_docker_tar("nginx.tar", "http://localhost:15000")

        # 하위 디렉토리의 tar 파일
        await push_docker_tar("./docker-images/app.tar", "http://localhost:15000")

        # 절대경로로 지정
        await push_docker_tar("/Users/user/images/nginx.tar", "http://localhost:15000")

        # 저장소명 덮어쓰기 (원본 태그 유지)
        await push_docker_tar("nginx.tar", "http://localhost:15000", repository="my-nginx")

        # 저장소명과 태그 모두 덮어쓰기
        await push_docker_tar("nginx.tar", "http://localhost:15000", repository="my-nginx", tag="v1.0")
    """
    # Create registry configuration
    config = RegistryConfig(url=registry_url, timeout=timeout)

    # Check connectivity first
    await check_connectivity(config)

    # Extract original tags from tar file if not provided
    original_repo: str | None = None
    original_tag: str | None = None

    if repository is None or tag is None:
        try:
            # Run tag extraction in thread pool since it involves file I/O
            primary_tag = await asyncio.get_event_loop().run_in_executor(
                None, get_primary_tag, tar_path
            )

            if primary_tag:
                original_repo, original_tag = primary_tag
        except Exception:
            # If tag extraction fails, we'll use defaults below
            pass

    # Determine final repository and tag
    final_repository = repository or original_repo
    final_tag = tag or original_tag or "latest"

    if not final_repository:
        raise RegistryError(
            "No repository specified and could not extract repository from tar file. "
            "Please provide a repository name or ensure the tar file contains valid repository tags."
        )

    # Validate and process tar file
    # This runs in thread pool since it involves file I/O
    manifest_info, validated_tar_path = await asyncio.get_event_loop().run_in_executor(
        None, process_tar_file, tar_path
    )

    # Collect all blobs (config + layers)
    all_blobs = [manifest_info.config] + list(manifest_info.layers)

    # Upload all blobs concurrently
    await _upload_all_blobs(config, final_repository, validated_tar_path, all_blobs)

    # Create and upload manifest
    return await _create_and_upload_manifest(
        config, final_repository, final_tag, manifest_info
    )


async def push_docker_tar_with_original_tags(
    tar_path: str, registry_url: str, timeout: int = 300
) -> str:
    """Docker tar 파일을 원본 저장소명과 태그로 푸시합니다.

    tar 파일에서 자동으로 추출된 원본 태그를 사용하는 편의 함수입니다.

    Args:
        tar_path: Docker tar 파일 경로
            - 상대경로: "my-app.tar", "./images/nginx.tar"
            - 절대경로: "/Users/user/images/my-app.tar"
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        timeout: 요청 타임아웃 (초, 기본값: 300초)

    Returns:
        str: 푸시된 이미지의 매니페스트 digest

    Raises:
        FileNotFoundError: tar 파일이 존재하지 않는 경우
        RegistryError: 푸시 작업 실패 또는 원본 태그를 찾을 수 없는 경우

    Examples:
        # 원본 태그 그대로 푸시
        digest = await push_docker_tar_with_original_tags(
            "nginx-exported.tar",
            "http://localhost:15000"
        )
    """
    return await push_docker_tar(
        tar_path=tar_path,
        registry_url=registry_url,
        repository=None,  # Force extraction from tar
        tag=None,  # Force extraction from tar
        timeout=timeout,
    )


async def push_docker_tar_with_all_original_tags(
    tar_path: str, registry_url: str, timeout: int = 300
) -> list[str]:
    """Docker tar 파일의 모든 원본 태그를 보존하여 푸시합니다.

    tar 파일에서 모든 원본 태그를 추출하여 각각의 태그로 이미지를 푸시하며,
    완전한 원본 이미지 메타데이터를 보존합니다.

    Args:
        tar_path: Docker tar 파일 경로
            - 상대경로: "multi-tag-image.tar", "./exports/app.tar"
            - 절대경로: "/Users/user/exports/multi-tag-image.tar"
        registry_url: 레지스트리 URL (예: "http://localhost:15000")
        timeout: 요청 타임아웃 (초, 기본값: 300초)

    Returns:
        list[str]: 각 태그별 매니페스트 digest 목록 (모든 digest는 동일한 이미지)

    Raises:
        FileNotFoundError: tar 파일이 존재하지 않는 경우
        RegistryError: 푸시 작업 실패 또는 원본 태그를 찾을 수 없는 경우

    Examples:
        # 여러 태그로 동시 푸시
        digests = await push_docker_tar_with_all_original_tags(
            "app-v1.0-multi.tar",
            "http://localhost:15000"
        )
        print(f"{len(digests)}개 태그로 푸시 완료: {digests}")

    Note:
        원본 tar 파일에 ['myapp:latest', 'myapp:v1.0', 'registry.io/myapp:prod'] 태그가 있다면
        세 개의 태그 모두로 푸시됩니다.

    Example:
        # If tar contains ["nginx:alpine", "nginx:1.21-alpine"]
        # Both tags will be pushed to the registry
        digests = await push_docker_tar_with_all_original_tags("nginx.tar", "http://localhost:15000")
    """
    # Create registry configuration
    config = RegistryConfig(url=registry_url, timeout=timeout)

    # Check connectivity first
    await check_connectivity(config)

    # Extract all original tags from tar file
    try:
        original_tags = await asyncio.get_event_loop().run_in_executor(
            None, extract_original_tags, tar_path
        )
    except Exception as e:
        raise RegistryError(
            f"Failed to extract original tags from tar file: {e}"
        ) from e

    if not original_tags:
        raise RegistryError(
            "No original tags found in tar file. "
            "Please ensure the tar file contains valid repository tags."
        )

    # Validate and process tar file once (shared for all tags)
    manifest_info, validated_tar_path = await asyncio.get_event_loop().run_in_executor(
        None, process_tar_file, tar_path
    )

    # Collect all blobs (config + layers)
    all_blobs = [manifest_info.config] + list(manifest_info.layers)

    # Upload all blobs once (they're the same for all tags)
    # We'll use the first repository for blob upload, but blobs are shared
    first_repo, _ = parse_repository_tag(original_tags[0])
    await _upload_all_blobs(config, first_repo, validated_tar_path, all_blobs)

    # Push manifest for each original tag concurrently
    manifest_tasks = []
    for repo_tag in original_tags:
        repository, tag = parse_repository_tag(repo_tag)
        task = _create_and_upload_manifest(config, repository, tag, manifest_info)
        manifest_tasks.append(task)

    # Execute all manifest uploads concurrently
    return await asyncio.gather(*manifest_tasks)
