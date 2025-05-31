"""Tar file validation utilities for Docker image tar files."""

import json
import tarfile
from pathlib import Path
from typing import Any

from ..exceptions import ValidationError


def is_path_exists(path: Path) -> bool:
    """Check if file path exists."""
    return path.exists()


def is_valid_tarfile(path: Path) -> bool:
    """Check if file is a valid tar file."""
    return tarfile.is_tarfile(path)


def get_tar_members(tar: tarfile.TarFile) -> set[str]:
    """Extract member names from tar file."""
    return {member.name for member in tar.getmembers()}


def has_required_files(tar_members: set[str], required_files: list[str]) -> bool:
    """Check if tar contains all required files."""
    return all(required_file in tar_members for required_file in required_files)


def extract_manifest_content(tar: tarfile.TarFile) -> str | None:
    """Extract manifest.json content from tar file."""
    try:
        manifest_member = tar.extractfile("manifest.json")
        if manifest_member is None:
            return None
        return manifest_member.read().decode("utf-8")
    except (UnicodeDecodeError, KeyError):
        return None


def parse_manifest_json(manifest_content: str) -> list[dict[str, Any]] | None:
    """Parse manifest JSON content."""
    try:
        manifest_data = json.loads(manifest_content)
        if not isinstance(manifest_data, list) or len(manifest_data) == 0:
            return None
        return manifest_data
    except json.JSONDecodeError:
        return None


def has_required_fields(
    manifest_entry: dict[str, Any], required_fields: list[str]
) -> bool:
    """Check if manifest entry has all required fields."""
    return all(field in manifest_entry for field in required_fields)


def is_config_file_exists(config_path: str, tar_members: set[str]) -> bool:
    """Check if config file exists in tar members."""
    return config_path in tar_members


def are_layers_valid(layers: Any) -> bool:
    """Check if layers field is a valid list."""
    return isinstance(layers, list)


def are_all_layers_exist(layers: list[str], tar_members: set[str]) -> bool:
    """Check if all layer files exist in tar members."""
    return all(layer in tar_members for layer in layers)


def validate_manifest_entry(
    manifest_entry: dict[str, Any], tar_members: set[str]
) -> bool:
    """Validate a single manifest entry."""
    required_fields = ["Config", "Layers"]

    if not has_required_fields(manifest_entry, required_fields):
        return False

    config_path = manifest_entry["Config"]
    if not is_config_file_exists(config_path, tar_members):
        return False

    layers = manifest_entry["Layers"]
    if not are_layers_valid(layers):
        return False

    return are_all_layers_exist(layers, tar_members)


def validate_all_manifest_entries(
    manifest_data: list[dict[str, Any]], tar_members: set[str]
) -> bool:
    """Validate all manifest entries."""
    return all(validate_manifest_entry(entry, tar_members) for entry in manifest_data)


def validate_docker_tar(tar_path: Path) -> bool:
    """tar 파일이 유효한 Docker 이미지 tar 파일인지 검증합니다.

    Args:
        tar_path: 검증할 tar 파일 경로
            - Path 객체: Path("/Users/user/images/app.tar")
            - 상대경로도 지원: Path("./docker-images/nginx.tar")

    Returns:
        bool: 유효한 Docker 이미지 tar 파일인 경우 True, 그렇지 않으면 False

    Raises:
        ValidationError: tar 파일이 손상되었거나 잘못된 형식인 경우

    Examples:
        # tar 파일 검증
        from pathlib import Path

        is_valid = validate_docker_tar(Path("nginx.tar"))
        if is_valid:
            print("유효한 Docker 이미지 tar 파일입니다")
        else:
            print("유효하지 않은 tar 파일입니다")
    """
    try:
        if not is_path_exists(tar_path):
            raise ValidationError(f"Tar file does not exist: {tar_path}")

        if not is_valid_tarfile(tar_path):
            return False

        with tarfile.open(tar_path, "r") as tar:
            tar_members = get_tar_members(tar)
            required_files = ["manifest.json"]

            if not has_required_files(tar_members, required_files):
                return False

            manifest_content = extract_manifest_content(tar)
            if manifest_content is None:
                return False

            manifest_data = parse_manifest_json(manifest_content)
            if manifest_data is None:
                return False

            return validate_all_manifest_entries(manifest_data, tar_members)

    except (tarfile.TarError, OSError) as e:
        raise ValidationError(f"Error reading tar file: {e}") from e


def extract_and_parse_manifest(tar: tarfile.TarFile) -> list[dict[str, Any]]:
    """Extract and parse manifest from tar file."""
    manifest_member = tar.extractfile("manifest.json")
    if manifest_member is None:
        raise ValidationError("Cannot extract manifest.json")

    manifest_content = manifest_member.read().decode("utf-8")
    return json.loads(manifest_content)  # type: ignore[no-any-return]


def get_tar_manifest(tar_path: Path) -> list[dict[str, Any]]:
    """Docker tar 파일에서 매니페스트를 추출하여 반환합니다.

    Args:
        tar_path: tar 파일 경로
            - Path 객체: Path("/Users/user/exports/nginx.tar")
            - 상대경로: Path("./docker-exports/app.tar")

    Returns:
        list[dict[str, Any]]: 매니페스트 엔트리 목록 (Docker Registry API v2 형식)

    Raises:
        ValidationError: tar 파일이 유효하지 않거나 매니페스트를 읽을 수 없는 경우

    Examples:
        # Docker tar 파일에서 매니페스트 추출
        from pathlib import Path

        manifest = get_tar_manifest(Path("nginx.tar"))
        for entry in manifest:
            print(f"Config: {entry['Config']}")
            print(f"RepoTags: {entry.get('RepoTags', [])}")
            print(f"Layers: {len(entry['Layers'])}개")
    """
    if not validate_docker_tar(tar_path):
        raise ValidationError(f"Invalid Docker tar file: {tar_path}")

    try:
        with tarfile.open(tar_path, "r") as tar:
            return extract_and_parse_manifest(tar)
    except (tarfile.TarError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValidationError(f"Error reading manifest: {e}") from e
