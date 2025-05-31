# API Reference

Complete reference for the async Registry API v2 Client.

## Overview

This client provides high-performance async operations for Docker Registry API v2, featuring:
- **Concurrent blob uploads** for maximum throughput
- **Original tag preservation** from Docker tar files  
- **Thread pool integration** for file I/O operations
- **Comprehensive error handling** with specific exception types
- **Type safety** with full type hints

## Installation

```bash
pip install registry-api-v2-client
```

## Quick Start

```python
import asyncio
from registry_api_v2_client import check_registry_connectivity, push_docker_tar

async def main():
    # Check registry connectivity
    accessible = await check_registry_connectivity("http://localhost:15000")
    
    if accessible:
        # Push a Docker tar file
        digest = await push_docker_tar(
            "my-image.tar", 
            "http://localhost:15000", 
            "myapp", 
            "latest"
        )
        print(f"Pushed with digest: {digest}")

asyncio.run(main())
```

## Main API Functions

### Connectivity

#### `check_registry_connectivity(registry_url: str, timeout: int = 30) -> bool`

Check if a Docker Registry supports API v2 and is accessible.

```python
async def connectivity_example():
    # Basic connectivity check
    accessible = await check_registry_connectivity("http://localhost:15000")
    print(f"Registry accessible: {accessible}")
    
    # With custom timeout
    accessible = await check_registry_connectivity(
        "http://slow-registry.com", 
        timeout=60
    )
```

**Parameters:**
- `registry_url`: Registry URL (e.g., "http://localhost:15000", "https://registry.io")
- `timeout`: Connection timeout in seconds (default: 30)

**Returns:** `True` if registry is accessible and supports v2 API

**Raises:** `RegistryError` if connection fails or registry doesn't support v2

---

### Push Operations

#### `push_docker_tar(tar_path: str, registry_url: str, repository: str, tag: str, timeout: int = 300) -> str`

Push a Docker tar file to registry with specified repository and tag.

```python
async def push_example():
    # Basic push
    digest = await push_docker_tar(
        "app.tar",               # Docker tar file path
        "http://localhost:15000", # Registry URL
        "mycompany/myapp",       # Repository name
        "v1.2.3"                # Tag
    )
    print(f"Pushed with digest: {digest}")
    
    # With timeout for large images
    digest = await push_docker_tar(
        "large-app.tar",
        "http://localhost:15000",
        "mycompany/large-app", 
        "latest",
        timeout=600  # 10 minutes
    )
```

**Parameters:**
- `tar_path`: Path to Docker tar file (from `docker save`)
- `registry_url`: Registry URL
- `repository`: Repository name (can include namespace like "mycompany/myapp")
- `tag`: Image tag
- `timeout`: Operation timeout in seconds (default: 300)

**Returns:** Manifest digest (sha256:...)

**Raises:** 
- `ValidationError` if tar file is invalid
- `RegistryError` if push fails
- `TarReadError` if tar file cannot be read

#### `push_docker_tar_with_original_tags(tar_path: str, registry_url: str, timeout: int = 300) -> str`

Push preserving the first original tag found in the tar file.

```python
async def push_with_original_tag():
    # Automatically extracts and uses original tag from tar file
    digest = await push_docker_tar_with_original_tags(
        "exported-image.tar",      # Contains original tag info
        "http://localhost:15000"
    )
    print(f"Pushed with original tag, digest: {digest}")
```

**Parameters:**
- `tar_path`: Path to Docker tar file with original tag info
- `registry_url`: Registry URL  
- `timeout`: Operation timeout in seconds (default: 300)

**Returns:** Manifest digest

**Raises:** `TarReadError` if no tags found in tar file

#### `push_docker_tar_with_all_original_tags(tar_path: str, registry_url: str, timeout: int = 300) -> List[str]`

Push with all original tags found in the tar file.

```python
async def push_all_original_tags():
    # Pushes all tags found in tar file
    digests = await push_docker_tar_with_all_original_tags(
        "multi-tag-image.tar",    # Contains multiple tags
        "http://localhost:15000"
    )
    print(f"Pushed {len(digests)} tags: {digests}")
    # All digests will be the same (same image, multiple tags)
```

**Parameters:**
- `tar_path`: Path to Docker tar file
- `registry_url`: Registry URL
- `timeout`: Operation timeout in seconds (default: 300)

**Returns:** List of manifest digests (one per tag)

---

### Repository Operations

#### `list_repositories(registry_url: str, timeout: int = 30) -> List[str]`

List all repositories in the registry.

```python
async def list_repos_example():
    repos = await list_repositories("http://localhost:15000")
    print(f"Found {len(repos)} repositories:")
    for repo in repos:
        print(f"  - {repo}")
```

**Returns:** List of repository names

#### `list_tags(registry_url: str, repository: str, timeout: int = 30) -> List[str]`

List all tags for a specific repository.

```python
async def list_tags_example():
    tags = await list_tags("http://localhost:15000", "mycompany/myapp")
    print(f"Tags for mycompany/myapp: {tags}")
    
    # Common pattern: get all repository info
    repos = await list_repositories("http://localhost:15000")
    for repo in repos:
        tags = await list_tags("http://localhost:15000", repo)
        print(f"{repo}: {len(tags)} tags")
```

**Parameters:**
- `repository`: Repository name

**Returns:** List of tag names

---

### Image Information

#### `get_image_info(registry_url: str, repository: str, reference: str, timeout: int = 30) -> dict`

Get detailed image information including manifest and metadata.

```python
async def image_info_example():
    info = await get_image_info("http://localhost:15000", "myapp", "latest")
    
    print(f"Architecture: {info.get('architecture', 'unknown')}")
    print(f"OS: {info.get('os', 'unknown')}")
    print(f"Size: {info.get('size', 0):,} bytes")
    print(f"Created: {info.get('created', 'unknown')}")
    
    # Check if info contains layers
    if 'layers' in info:
        print(f"Layers: {len(info['layers'])}")
```

**Parameters:**
- `reference`: Tag name or digest

**Returns:** Dictionary with image metadata

#### `get_manifest(registry_url: str, repository: str, reference: str, timeout: int = 30) -> dict`

Get raw manifest for an image by tag or digest.

```python
async def manifest_example():
    manifest = await get_manifest("http://localhost:15000", "myapp", "latest")
    
    print(f"Schema version: {manifest['schemaVersion']}")
    print(f"Media type: {manifest['mediaType']}")
    print(f"Config digest: {manifest['config']['digest']}")
    print(f"Layers: {len(manifest['layers'])}")
    
    # Check if manifest has digest
    if 'digest' in manifest:
        print(f"Manifest digest: {manifest['digest']}")
```

---

### Deletion Operations

#### `delete_image(registry_url: str, repository: str, tag: str, timeout: int = 30) -> bool`

Delete an image by tag (deletes the manifest).

```python
async def delete_example():
    success = await delete_image("http://localhost:15000", "myapp", "v1.0.0")
    if success:
        print("Image deleted successfully")
    else:
        print("Failed to delete image")
```

**Note:** Requires `REGISTRY_STORAGE_DELETE_ENABLED=true` in registry configuration.

#### `delete_image_by_digest(registry_url: str, repository: str, digest: str, timeout: int = 30) -> bool`

Delete an image by manifest digest.

```python
async def delete_by_digest_example():
    # First get the digest
    manifest = await get_manifest("http://localhost:15000", "myapp", "latest")
    digest = manifest.get('digest')
    
    if digest:
        success = await delete_image_by_digest("http://localhost:15000", "myapp", digest)
        print(f"Deletion successful: {success}")
```

---

### Tag Extraction (Sync Functions)

#### `extract_original_tags(tar_path: str) -> List[str]`

Extract all original tags from a Docker tar file.

```python
from registry_api_v2_client import extract_original_tags

# Synchronous function - no await needed
tags = extract_original_tags("exported-image.tar")
print(f"Found tags: {tags}")
# Example output: ['myapp:latest', 'myapp:v1.0.0', 'myregistry.io/myapp:prod']
```

#### `get_primary_tag(tar_path: str) -> Tuple[str, str]`

Get the primary repository and tag from a tar file.

```python
from registry_api_v2_client import get_primary_tag

repo, tag = get_primary_tag("image.tar")
print(f"Primary tag: {repo}:{tag}")
# Example output: myapp:latest
```

**Returns:** Tuple of (repository, tag)

---

## Data Types

### Core Types

#### `RegistryConfig`
```python
@dataclass(frozen=True)
class RegistryConfig:
    url: str
    timeout: int = 30
    
    @property
    def base_url(self) -> str:
        """Get base URL without trailing slash."""
        return self.url.rstrip('/')
```

#### `BlobInfo`
```python
@dataclass(frozen=True)
class BlobInfo:
    digest: str
    size: int
    media_type: str = "application/octet-stream"
    
    @property
    def digest_short(self) -> str:
        """Get short digest (first 12 chars)."""
        return self.digest.split(':')[1][:12] if ':' in self.digest else self.digest[:12]
```

#### `ManifestInfo`
```python
@dataclass(frozen=True)
class ManifestInfo:
    schema_version: int
    media_type: str
    config: BlobInfo
    layers: tuple[BlobInfo, ...]
    digest: str | None = None
    
    @property
    def total_size(self) -> int:
        """Get total size of config + all layers."""
        return self.config.size + sum(layer.size for layer in self.layers)
```

---

## Exception Handling

### Exception Hierarchy

#### `RegistryError`
Base exception for all registry-related errors.

```python
try:
    await check_registry_connectivity("http://invalid-registry")
except RegistryError as e:
    print(f"Registry error: {e}")
    # Handle connection/authentication/protocol errors
```

#### `TarReadError`
Raised when tar file cannot be read or parsed.

```python
try:
    tags = extract_original_tags("corrupted.tar")
except TarReadError as e:
    print(f"Tar file error: {e}")
    # Handle invalid tar files
```

#### `ValidationError`
Raised when tar file structure is invalid for Docker images.

```python
try:
    await push_docker_tar("invalid.tar", registry_url, "repo", "tag")
except ValidationError as e:
    print(f"Invalid Docker tar: {e}")
    # Handle structural issues with Docker tar files
```

### Error Handling Patterns

```python
async def robust_push(tar_path: str, registry_url: str, repo: str, tag: str):
    """Push with comprehensive error handling."""
    try:
        digest = await push_docker_tar(tar_path, registry_url, repo, tag)
        return digest
    except ValidationError as e:
        print(f"Invalid tar file: {e}")
        raise
    except TarReadError as e:
        print(f"Cannot read tar file: {e}")
        raise  
    except RegistryError as e:
        print(f"Registry operation failed: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
```

---

## Concurrent Usage Patterns

### Concurrent Push Operations

```python
async def concurrent_push_example():
    registry_url = "http://localhost:15000"
    
    # Define push operations
    push_ops = [
        ("app1.tar", "company/app1", "v1.0"),
        ("app2.tar", "company/app2", "v1.0"), 
        ("app3.tar", "company/app3", "v1.0"),
    ]
    
    # Create concurrent tasks
    tasks = [
        push_docker_tar(tar_path, registry_url, repo, tag)
        for tar_path, repo, tag in push_ops
    ]
    
    # Execute all pushes concurrently
    start = time.time()
    digests = await asyncio.gather(*tasks)
    duration = time.time() - start
    
    print(f"Pushed {len(digests)} images in {duration:.2f} seconds")
    for (tar_path, repo, tag), digest in zip(push_ops, digests):
        print(f"{repo}:{tag} -> {digest}")
```

### Concurrent Repository Operations

```python
async def bulk_repository_info():
    registry_url = "http://localhost:15000"
    
    # Get all repositories
    repos = await list_repositories(registry_url)
    
    # Concurrently get tags for all repositories
    tag_tasks = [list_tags(registry_url, repo) for repo in repos]
    all_tags = await asyncio.gather(*tag_tasks)
    
    # Concurrently get info for latest tags
    info_tasks = [
        get_image_info(registry_url, repo, "latest")
        for repo in repos
    ]
    
    # Handle potential errors for missing 'latest' tags
    all_info = await asyncio.gather(*info_tasks, return_exceptions=True)
    
    # Process results
    for repo, tags, info in zip(repos, all_tags, all_info):
        print(f"\n{repo}:")
        print(f"  Tags: {len(tags)}")
        
        if isinstance(info, Exception):
            print(f"  Latest: Error - {info}")
        else:
            size = info.get('size', 0)
            print(f"  Latest size: {size:,} bytes")
```

### Error Handling with Concurrent Operations

```python
async def robust_concurrent_operations():
    registry_url = "http://localhost:15000"
    
    operations = [
        push_docker_tar("app1.tar", registry_url, "app1", "latest"),
        push_docker_tar("app2.tar", registry_url, "app2", "latest"),
        push_docker_tar("bad.tar", registry_url, "app3", "latest"),  # May fail
    ]
    
    # Use return_exceptions=True to handle individual failures
    results = await asyncio.gather(*operations, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Operation {i+1} failed: {result}")
        else:
            print(f"Operation {i+1} succeeded: {result}")
```

---

## Performance Considerations

### Automatic Optimizations

The client automatically optimizes performance through:

- **Concurrent blob uploads**: All image layers upload simultaneously
- **Chunked transfers**: Large files uploaded in 5MB chunks  
- **Connection pooling**: HTTP connections reused across operations
- **Thread pool integration**: File I/O operations don't block event loop

### Memory Efficiency

```python
# ✅ Memory efficient - streams large files
await push_docker_tar("large-image.tar", registry_url, "repo", "tag")

# ✅ Concurrent uploads don't increase memory usage per operation
tasks = [push_docker_tar(f"image{i}.tar", registry_url, f"repo{i}", "tag") for i in range(10)]
await asyncio.gather(*tasks)  # Memory usage stays constant
```

### Timeout Configuration

```python
# Adjust timeouts for different scenarios
await push_docker_tar("small.tar", registry_url, "repo", "tag", timeout=60)      # Small image
await push_docker_tar("large.tar", registry_url, "repo", "tag", timeout=1800)   # Large image (30 min)
await check_registry_connectivity("slow-registry.com", timeout=120)             # Slow network
```

---

## Registry Configuration

### Local Development Registry

```yaml
# docker-compose.yml
version: '3.8'
services:
  registry:
    image: registry:2
    ports:
      - "15000:5000"  # Port 15000 to avoid conflicts
    environment:
      REGISTRY_STORAGE_DELETE_ENABLED: "true"  # Enable deletion operations
    volumes:
      - registry-data:/var/lib/registry

volumes:
  registry-data:
```

### Environment Variables

```bash
# Registry URL (default: http://localhost:15000)
export REGISTRY_URL=http://localhost:15000

# Request timeout (default: 30 seconds)  
export REGISTRY_TIMEOUT=60

# Enable debug logging
export REGISTRY_DEBUG=true
```

---

## Complete Example: CI/CD Pipeline

```python
"""
Example: Complete CI/CD pipeline using the async client
"""
import asyncio
import time
from pathlib import Path
from registry_api_v2_client import (
    check_registry_connectivity,
    push_docker_tar,
    list_repositories,
    delete_image,
    extract_original_tags
)

async def deploy_pipeline():
    """Complete deployment pipeline example."""
    registry_url = "http://localhost:15000"
    
    print("🔍 Checking registry connectivity...")
    if not await check_registry_connectivity(registry_url):
        print("❌ Registry not accessible")
        return False
    print("✅ Registry is accessible")
    
    # Image files to deploy
    images = [
        ("frontend.tar", "mycompany/frontend"),
        ("backend.tar", "mycompany/backend"), 
        ("worker.tar", "mycompany/worker"),
    ]
    
    print(f"\n🚀 Deploying {len(images)} images...")
    start_time = time.time()
    
    # Deploy all images concurrently
    deploy_tasks = []
    for tar_file, repo in images:
        if Path(tar_file).exists():
            # Extract version from tar or use timestamp
            tags = extract_original_tags(tar_file)
            tag = tags[0].split(':')[1] if tags else f"build-{int(time.time())}"
            
            task = push_docker_tar(tar_file, registry_url, repo, tag)
            deploy_tasks.append((repo, tag, task))
        else:
            print(f"⚠️  Skipping {tar_file} - file not found")
    
    # Wait for all deployments
    results = await asyncio.gather(*[task for _, _, task in deploy_tasks], return_exceptions=True)
    
    # Report results
    print(f"\n📊 Deployment Results ({time.time() - start_time:.1f}s):")
    for (repo, tag, _), result in zip(deploy_tasks, results):
        if isinstance(result, Exception):
            print(f"❌ {repo}:{tag} - Failed: {result}")
        else:
            print(f"✅ {repo}:{tag} - {result[:12]}...")
    
    # Cleanup old images (optional)
    print(f"\n🧹 Cleaning up old images...")
    repos = await list_repositories(registry_url)
    for repo in repos:
        if repo.startswith("mycompany/"):
            # Delete old tags (keep latest 3)
            tags = await list_tags(registry_url, repo)
            if len(tags) > 3:
                for old_tag in tags[3:]:  # Simple cleanup logic
                    try:
                        await delete_image(registry_url, repo, old_tag)
                        print(f"🗑️  Deleted {repo}:{old_tag}")
                    except Exception as e:
                        print(f"⚠️  Could not delete {repo}:{old_tag}: {e}")
    
    print("✅ Pipeline completed!")
    return True

# Run the pipeline
if __name__ == "__main__":
    asyncio.run(deploy_pipeline())
```

This API reference covers all functionality of the async Registry API v2 Client with practical examples and best practices.