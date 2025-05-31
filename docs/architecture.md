# Architecture Guide

Deep dive into the async functional architecture of the Registry API v2 Client.

## Overview

This Registry API v2 Client is built using **async functional programming** principles, designed for high-performance concurrent operations with Docker registries. Unlike traditional synchronous clients, this implementation leverages Python's asyncio ecosystem for maximum throughput and efficiency.

## Why Async Functional Architecture?

### The Problem with Synchronous Clients

Traditional registry clients suffer from:
- **Sequential operations**: Push one blob, wait, push next blob
- **Blocking I/O**: File operations block the entire thread
- **Poor scalability**: Can't efficiently handle multiple operations
- **Resource waste**: CPU idle during network/disk waits

```python
# ❌ Typical synchronous approach (slow)
def sync_push_tar(tar_path, registry_url, repo, tag):
    # Blocks thread during file I/O
    validate_tar(tar_path)  
    config, layers = process_tar(tar_path)
    
    # Sequential blob uploads (very slow)
    for blob in [config] + layers:
        upload_blob(blob)  # Wait for each upload
    
    # Finally upload manifest
    return upload_manifest(config, layers, repo, tag)
```

### Our Async Solution

```python
# ✅ Our async approach (fast)
async def async_push_tar(tar_path, registry_url, repo, tag):
    # File I/O in thread pool (non-blocking)
    config, layers = await asyncio.get_event_loop().run_in_executor(
        None, process_tar, tar_path
    )
    
    # Concurrent blob uploads (much faster)
    upload_tasks = [upload_blob(blob) for blob in [config] + layers]
    await asyncio.gather(*upload_tasks)
    
    # Upload manifest
    return await upload_manifest(config, layers, repo, tag)
```

### Performance Benefits

**Real-world performance comparison:**
- **Sequential uploads**: 5 layers × 30 seconds = 150 seconds
- **Concurrent uploads**: max(30 seconds) = 30 seconds  
- **Improvement**: 5x faster

## Core Architectural Principles

### 1. Async First

Every main operation is an async function designed for concurrency:

```python
# All main API functions are async
async def push_docker_tar(...) -> str
async def list_repositories(...) -> List[str]  
async def check_registry_connectivity(...) -> bool
async def get_image_info(...) -> dict

# Enables concurrent usage
repos = await list_repositories(registry_url)
info_tasks = [get_image_info(registry_url, repo, "latest") for repo in repos]
all_info = await asyncio.gather(*info_tasks)  # Runs concurrently
```

### 2. Immutable Data Structures

All data types use `@dataclass(frozen=True)` for thread safety and predictability:

```python
@dataclass(frozen=True)
class BlobInfo:
    digest: str
    size: int
    media_type: str = "application/octet-stream"
    
    # Properties are computed, not stored
    @property
    def digest_short(self) -> str:
        return self.digest.split(':')[1][:12] if ':' in self.digest else self.digest[:12]

@dataclass(frozen=True) 
class ManifestInfo:
    config: BlobInfo
    layers: tuple[BlobInfo, ...]  # Tuple, not list (immutable)
    schema_version: int = 2
    media_type: str = "application/vnd.docker.distribution.manifest.v2+json"
```

**Benefits:**
- **Thread safety**: Can be safely shared across async tasks
- **Predictability**: Objects can't be unexpectedly modified
- **Performance**: No defensive copying needed
- **Debugging**: State is consistent and traceable

### 3. Pure Functions

Functions have no side effects and produce predictable outputs:

```python
# ✅ Pure function - predictable, testable
def calculate_digest(data: bytes) -> str:
    """Always returns same output for same input."""
    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"

# ✅ Pure async function - no hidden state
async def check_blob_exists(config: RegistryConfig, repository: str, digest: str) -> bool:
    """Returns True/False based only on inputs."""
    session = await create_session()
    try:
        result = await make_get_request(session, f"{config.base_url}/v2/{repository}/blobs/{digest}", config)
        return result.status_code == 200
    finally:
        await session.close()

# ❌ Impure function - has side effects
global_cache = {}

def impure_check_blob(repository: str, digest: str) -> bool:
    # Side effect: modifies global state
    if digest in global_cache:
        global_cache[digest] += 1
    else:
        global_cache[digest] = 1
    
    # Side effect: I/O operation
    print(f"Checking blob {digest}")
    
    # Depends on external state
    return make_request_somehow()
```

### 4. Thread Pool Integration

Blocking I/O operations run in thread pools to avoid blocking the event loop:

```python
# ✅ Non-blocking file operations
async def process_tar_file(tar_path: str) -> tuple[BlobInfo, list[BlobInfo]]:
    """Process tar file without blocking event loop."""
    loop = asyncio.get_event_loop()
    
    # Heavy file I/O runs in thread pool
    config, layers = await loop.run_in_executor(None, _process_tar_sync, tar_path)
    return config, layers

def _process_tar_sync(tar_path: str) -> tuple[BlobInfo, list[BlobInfo]]:
    """Synchronous tar processing (runs in thread pool)."""
    # This blocks, but in a separate thread
    with tarfile.open(tar_path, 'r') as tar:
        # Extract and process tar contents
        pass

# ❌ Blocking the event loop
async def process_tar_file_bad(tar_path: str) -> tuple[BlobInfo, list[BlobInfo]]:
    """Blocks event loop - all other async operations stop!"""
    with tarfile.open(tar_path, 'r') as tar:  # Blocks everything!
        # This stops ALL async operations
        pass
```

### 5. Function Composition

Complex operations are built from simple, composable functions:

```python
# High-level operation composed of smaller functions
async def push_docker_tar(tar_path: str, registry_url: str, repository: str, tag: str) -> str:
    """Composed from smaller, testable functions."""
    # 1. Validate (thread pool)
    await validate_tar_async(tar_path)
    
    # 2. Process (thread pool)
    config, layers = await process_tar_file(tar_path)
    
    # 3. Upload blobs (concurrent)
    await upload_all_blobs(registry_url, repository, config, layers)
    
    # 4. Create and upload manifest
    manifest = create_manifest(config, layers)
    return await upload_manifest(registry_url, repository, tag, manifest)

# Each function is pure, testable, and composable
async def validate_tar_async(tar_path: str) -> None:
    """Validation in thread pool."""
    valid = await asyncio.get_event_loop().run_in_executor(None, validate_docker_tar, Path(tar_path))
    if not valid:
        raise ValidationError("Invalid Docker tar file")

async def upload_all_blobs(registry_url: str, repository: str, config: BlobInfo, layers: list[BlobInfo]) -> None:
    """Concurrent blob uploads."""
    all_blobs = [config] + layers
    tasks = [upload_blob(registry_url, repository, blob) for blob in all_blobs]
    await asyncio.gather(*tasks)
```

## Module Organization

### Functional Organization by Purpose

```
src/registry_api_v2_client/
├── core/                    # Core async infrastructure
│   ├── types.py            # Immutable data structures
│   ├── connectivity.py     # Pure connectivity functions
│   └── session.py          # HTTP session management
├── operations/             # Registry operation modules  
│   ├── blobs.py           # Blob upload/download
│   ├── manifests.py       # Manifest operations
│   ├── repositories.py    # Repository listing
│   └── images.py          # High-level image operations
├── tar/                   # Tar file processing
│   ├── processor.py       # Main tar processing
│   ├── tags.py           # Tag extraction utilities
│   └── validator.py      # Async validation wrapper
├── utils/                 # Legacy sync utilities
│   ├── validator.py      # Sync validation functions
│   └── inspect.py        # Image inspection utilities
├── push.py               # Main push API facade
├── registry.py           # Main registry API facade
└── exceptions.py         # Exception hierarchy
```

### Design Rationale

#### Core Module (`core/`)
- **`types.py`**: Immutable data structures used throughout
- **`connectivity.py`**: Pure functions for testing registry connectivity
- **`session.py`**: HTTP session management with connection pooling

#### Operations Module (`operations/`)
- **Single responsibility**: Each module handles one type of operation
- **Pure async functions**: No side effects, predictable behavior
- **Composable**: Functions can be combined to build complex workflows

#### Tar Module (`tar/`)
- **Thread pool integration**: File I/O operations that don't block event loop
- **Specialized processing**: Docker tar format handling
- **Tag preservation**: Extract and preserve original image tags

## Performance Architecture

### Concurrent Execution Model

```python
# Sequential execution (slow)
async def sequential_operations():
    result1 = await operation1()  # Wait
    result2 = await operation2()  # Wait  
    result3 = await operation3()  # Wait
    return [result1, result2, result3]

# Concurrent execution (fast)
async def concurrent_operations():
    tasks = [operation1(), operation2(), operation3()]
    return await asyncio.gather(*tasks)  # All run simultaneously
```

### Memory Efficiency

#### Chunked Uploads
```python
async def upload_blob_chunked(file_path: str, upload_url: str) -> str:
    """Upload large files without loading into memory."""
    chunk_size = 5 * 1024 * 1024  # 5MB chunks
    
    with open(file_path, 'rb') as f:
        offset = 0
        while True:
            chunk = f.read(chunk_size)  # Only 5MB in memory
            if not chunk:
                break
                
            await upload_chunk(upload_url, chunk, offset)
            offset += len(chunk)
            # Previous chunk garbage collected
```

#### Connection Pooling
```python
async def create_session() -> aiohttp.ClientSession:
    """Optimized session with connection pooling."""
    connector = aiohttp.TCPConnector(
        limit=100,              # Total connection limit
        limit_per_host=30,      # Per-host limit
        keepalive_timeout=300,  # Keep connections alive
        enable_cleanup_closed=True
    )
    
    timeout = aiohttp.ClientTimeout(total=300)
    
    return aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": "registry-api-v2-client/1.0"}
    )
```

### Blob Upload Strategy

#### Automatic Concurrency
```python
async def push_docker_tar_internal(config: BlobInfo, layers: list[BlobInfo]) -> str:
    """Automatically uploads all blobs concurrently."""
    
    # All blobs upload simultaneously
    blob_tasks = []
    for blob in [config] + layers:
        task = upload_blob(registry_url, repository, blob)
        blob_tasks.append(task)
    
    # Wait for all uploads to complete
    await asyncio.gather(*blob_tasks)
    
    # Only then upload manifest
    return await upload_manifest(...)
```

**Performance characteristics:**
- **5 layers, 30s each (sequential)**: 150 seconds total
- **5 layers, 30s each (concurrent)**: 30 seconds total
- **Network utilization**: Maximizes bandwidth usage
- **Registry load**: Distributes load across multiple connections

## Error Handling Architecture

### Exception Hierarchy

```python
# Base exception for all registry operations
class RegistryError(Exception):
    """Base exception for registry-related errors."""
    pass

# Specific error types for different failure modes
class TarReadError(Exception):
    """Raised when tar file cannot be read or parsed."""
    pass

class ValidationError(Exception):
    """Raised when tar file structure is invalid."""
    pass
```

### Async Error Propagation

```python
async def robust_operation():
    """Demonstrates proper async error handling."""
    try:
        # Multiple operations that might fail
        await validate_input()
        result = await perform_operation()
        await cleanup_operation()
        return result
        
    except ValidationError as e:
        # Specific handling for validation errors
        logger.error(f"Validation failed: {e}")
        raise
        
    except RegistryError as e:
        # Registry-specific error handling
        logger.error(f"Registry operation failed: {e}")
        await cleanup_on_error()
        raise
        
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error: {e}")
        await emergency_cleanup()
        raise
```

### Concurrent Error Handling

```python
async def concurrent_with_error_handling():
    """Handle errors in concurrent operations."""
    tasks = [
        operation1(),
        operation2(), 
        operation3()
    ]
    
    # Use return_exceptions=True to collect both results and errors
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = []
    failures = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failures.append((i, result))
        else:
            successes.append((i, result))
    
    if failures:
        # Handle partial failures appropriately
        logger.warning(f"{len(failures)} operations failed")
        for task_id, error in failures:
            logger.error(f"Task {task_id} failed: {error}")
    
    return successes
```

## Testing Architecture

### Test Isolation

```python
# Tests use unique repository names to avoid conflicts
class TestContext:
    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.test_id = f"test-{uuid4().hex[:8]}"
        self.created_repos: List[str] = []
    
    def repo_name(self, base_name: str) -> str:
        """Generate unique repository name."""
        unique_name = f"{base_name}-{self.test_id}"
        self.created_repos.append(unique_name)
        return unique_name
    
    async def cleanup(self):
        """Clean up test repositories."""
        for repo in self.created_repos:
            try:
                await delete_repository(self.registry_url, repo)
            except Exception:
                pass  # Best effort cleanup
```

### Async Test Patterns

```python
@pytest.mark.asyncio
async def test_concurrent_push(test_context):
    """Test concurrent push operations."""
    # Create multiple unique repositories
    repos = [test_context.repo_name(f"app{i}") for i in range(3)]
    
    # Concurrent push operations
    tasks = [
        push_docker_tar("test.tar", test_context.registry_url, repo, "latest")
        for repo in repos
    ]
    
    # Verify all succeed
    digests = await asyncio.gather(*tasks)
    assert len(digests) == 3
    assert all(d.startswith("sha256:") for d in digests)
    
    # Cleanup happens automatically via test_context
```

## Registry Protocol Implementation

### Docker Registry API v2 Compliance

The client implements the complete Docker Registry API v2 specification:

```python
# API v2 endpoints implemented
GET  /v2/                                    # API version check
GET  /v2/_catalog                           # List repositories
GET  /v2/{name}/tags/list                   # List tags
GET  /v2/{name}/manifests/{reference}       # Get manifest
PUT  /v2/{name}/manifests/{reference}       # Upload manifest
DELETE /v2/{name}/manifests/{reference}     # Delete manifest
HEAD /v2/{name}/blobs/{digest}              # Check blob exists
POST /v2/{name}/blobs/uploads/              # Initiate blob upload
PATCH /v2/{name}/blobs/uploads/{uuid}       # Upload blob chunk
PUT  /v2/{name}/blobs/uploads/{uuid}        # Complete blob upload
```

### Protocol-Specific Optimizations

#### Manifest Upload Strategy
```python
async def upload_manifest(repository: str, tag: str, manifest: dict) -> str:
    """Upload manifest with proper content negotiation."""
    headers = {
        "Content-Type": "application/vnd.docker.distribution.manifest.v2+json",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json"
    }
    
    # Calculate manifest size for Content-Length
    manifest_json = json.dumps(manifest, separators=(',', ':'))
    headers["Content-Length"] = str(len(manifest_json.encode()))
    
    # Upload with proper digest verification
    result = await make_put_request(url, headers, manifest_json)
    
    # Extract digest from response
    return result.headers.get("Docker-Content-Digest", calculate_digest(manifest_json))
```

#### Blob Upload Strategy
```python
async def upload_blob(repository: str, data: bytes, expected_digest: str) -> str:
    """Optimized blob upload with chunking."""
    
    # For small blobs, use monolithic upload
    if len(data) < 5 * 1024 * 1024:  # 5MB threshold
        return await upload_blob_monolithic(repository, data, expected_digest)
    
    # For large blobs, use chunked upload
    return await upload_blob_chunked(repository, data, expected_digest)
```

## Comparison with Other Approaches

### vs. Synchronous Clients

| Aspect | Synchronous | Our Async Approach |
|--------|-------------|-------------------|
| **Blob Uploads** | Sequential (slow) | Concurrent (fast) |
| **Memory Usage** | May load entire files | Streaming chunks |
| **Resource Utilization** | Poor (blocking waits) | Excellent (concurrent) |
| **Error Recovery** | Limited | Comprehensive async handling |
| **Testing** | Simple but slow | Complex but fast |

### vs. Threading Approaches

| Aspect | Threading | Our Approach |
|--------|-----------|--------------|
| **Complexity** | High (locks, races) | Lower (async/await) |
| **Performance** | Good | Better (less overhead) |
| **Debugging** | Difficult | Easier (single thread) |
| **Memory** | High (thread stacks) | Lower |
| **Scalability** | Limited by threads | Limited by I/O |

### vs. Callback-Based Async

| Aspect | Callbacks | async/await |
|--------|-----------|-------------|
| **Readability** | Poor (callback hell) | Excellent |
| **Error Handling** | Complex | Natural try/catch |
| **Composition** | Difficult | Easy |
| **Debugging** | Very difficult | Good |

## Future Architecture Considerations

### Potential Enhancements

1. **Connection Multiplexing**: HTTP/2 support for better connection efficiency
2. **Adaptive Chunking**: Dynamic chunk sizes based on network performance  
3. **Resume Uploads**: Support for resuming interrupted large uploads
4. **Caching Layer**: Intelligent caching of blob existence checks
5. **Rate Limiting**: Built-in rate limiting for registry protection

### Scalability Characteristics

**Current limits:**
- **Concurrent operations**: Limited by aiohttp connection pool (100 total, 30 per host)
- **Memory usage**: O(chunk_size × concurrent_uploads) ≈ 5MB × 30 = 150MB max
- **File handle limits**: Managed by thread pool size
- **Network bandwidth**: Efficiently utilized via concurrency

**Scaling considerations:**
- **Very large files**: Chunked uploads handle files of any size
- **Many concurrent operations**: Connection pooling prevents resource exhaustion
- **High-latency networks**: Concurrency masks latency effectively
- **Registry load**: Distributed across multiple connections

This async functional architecture provides optimal performance, maintainability, and scalability for Docker Registry API v2 operations while maintaining type safety and comprehensive error handling.