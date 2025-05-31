"""Tag extraction from Docker tar files."""

import json
import tarfile

from ..exceptions import TarReadError, ValidationError


def extract_repo_tags_from_manifest(tar_path: str) -> list[str]:
    """Extract RepoTags from manifest.json in tar file.

    Args:
        tar_path: Path to Docker tar file

    Returns:
        List of repository tags (e.g., ["nginx:alpine", "myapp:latest"])

    Raises:
        TarReadError: If tar file cannot be read
        ValidationError: If manifest.json is invalid or missing
    """
    try:
        with tarfile.open(tar_path, "r") as tar:
            # Extract manifest.json
            try:
                manifest_member = tar.extractfile("manifest.json")
                if manifest_member is None:
                    raise ValidationError("manifest.json not found in tar file")

                manifest_content = manifest_member.read().decode("utf-8")
                manifest_data = json.loads(manifest_content)

            except KeyError as e:
                raise ValidationError("manifest.json not found in tar file") from e
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON in manifest.json: {e}") from e
            except UnicodeDecodeError as e:
                raise ValidationError(f"Cannot decode manifest.json: {e}") from e

        # Validate manifest structure
        if not isinstance(manifest_data, list) or not manifest_data:
            raise ValidationError("manifest.json must be a non-empty array")

        # Extract RepoTags from first manifest entry
        first_manifest = manifest_data[0]
        if not isinstance(first_manifest, dict):
            raise ValidationError("Invalid manifest entry structure")

        repo_tags = first_manifest.get("RepoTags", [])
        if not isinstance(repo_tags, list):
            raise ValidationError("RepoTags must be a list")

        return repo_tags

    except tarfile.TarError as e:
        raise TarReadError(f"Cannot read tar file: {e}") from e


def extract_repo_tags_from_repositories(tar_path: str) -> list[str]:
    """Extract repository tags from repositories file in tar.

    Args:
        tar_path: Path to Docker tar file

    Returns:
        List of repository tags (e.g., ["nginx:alpine", "myapp:latest"])

    Raises:
        TarReadError: If tar file cannot be read
        ValidationError: If repositories file is invalid or missing
    """
    try:
        with tarfile.open(tar_path, "r") as tar:
            # Extract repositories file
            try:
                repos_member = tar.extractfile("repositories")
                if repos_member is None:
                    raise ValidationError("repositories file not found in tar file")

                repos_content = repos_member.read().decode("utf-8")
                repos_data = json.loads(repos_content)

            except KeyError as e:
                raise ValidationError("repositories file not found in tar file") from e
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON in repositories file: {e}") from e
            except UnicodeDecodeError as e:
                raise ValidationError(f"Cannot decode repositories file: {e}") from e

        # Extract tags from repositories structure: {"repo": {"tag": "digest"}}
        repo_tags = []
        for repo_name, tag_dict in repos_data.items():
            if isinstance(tag_dict, dict):
                for tag_name in tag_dict:
                    repo_tags.append(f"{repo_name}:{tag_name}")

        return repo_tags

    except tarfile.TarError as e:
        raise TarReadError(f"Cannot read tar file: {e}") from e


def extract_original_tags(tar_path: str) -> list[str]:
    """Extract original image tags from Docker tar file.

    This function tries multiple methods to extract the original tags:
    1. RepoTags from manifest.json (preferred)
    2. Repository tags from repositories file (fallback)

    Args:
        tar_path: Path to Docker tar file

    Returns:
        List of original repository tags

    Raises:
        TarReadError: If tar file cannot be read
        ValidationError: If no valid tags can be extracted
    """
    # Try manifest.json first (more reliable)
    try:
        repo_tags = extract_repo_tags_from_manifest(tar_path)
        if repo_tags:
            return repo_tags
    except (TarReadError, ValidationError):
        pass

    # Try repositories file as fallback
    try:
        repo_tags = extract_repo_tags_from_repositories(tar_path)
        if repo_tags:
            return repo_tags
    except (TarReadError, ValidationError):
        pass

    # If no tags found, return empty list
    return []


def parse_repository_tag(repo_tag: str) -> tuple[str, str]:
    """Parse repository:tag string into repository and tag components.

    Args:
        repo_tag: Repository tag string (e.g., "nginx:alpine", "localhost:5000/myapp:latest")

    Returns:
        Tuple of (repository, tag)

    Examples:
        "nginx:alpine" -> ("nginx", "alpine")
        "localhost:5000/myapp:latest" -> ("localhost:5000/myapp", "latest")
        "myapp" -> ("myapp", "latest")  # default tag
    """
    if ":" in repo_tag:
        # Split only on the last ':' to handle registry URLs like localhost:5000/repo:tag
        parts = repo_tag.rsplit(":", 1)
        if len(parts) == 2 and parts[1]:  # Ensure tag is not empty
            return parts[0], parts[1]
        else:
            # Empty tag after colon (e.g., "app:")
            return parts[0], "latest"

    # No tag specified, use default
    return repo_tag, "latest"


def get_primary_tag(tar_path: str) -> tuple[str, str] | None:
    """Get the primary (first) repository and tag from tar file.

    Args:
        tar_path: Path to Docker tar file

    Returns:
        Tuple of (repository, tag) or None if no tags found
    """
    try:
        original_tags = extract_original_tags(tar_path)
        if original_tags:
            return parse_repository_tag(original_tags[0])
        return None
    except (TarReadError, ValidationError):
        return None
