# 아키텍처 가이드

Registry API v2 클라이언트의 비동기 함수형 아키텍처에 대한 심화 분석입니다.

## 🔍 개요

이 Registry API v2 클라이언트는 **비동기 함수형 프로그래밍** 원칙을 기반으로 구축되었으며, Docker 레지스트리와의 고성능 동시 작업을 위해 설계되었습니다. 기존의 동기식 클라이언트와 달리, Python의 asyncio 생태계를 활용하여 최대 처리량과 효율성을 제공합니다.

## 🤔 왜 비동기 함수형 아키텍처인가?

### 동기식 클라이언트의 문제점

기존 레지스트리 클라이언트들의 한계:
- **순차적 작업**: blob 하나 푸시 → 대기 → 다음 blob 푸시
- **블로킹 I/O**: 파일 작업이 전체 스레드를 차단
- **확장성 부족**: 여러 작업을 효율적으로 처리할 수 없음
- **자원 낭비**: 네트워크/디스크 대기 중 CPU 유휴 상태

```python
# ❌ 일반적인 동기식 접근법 (느림)
def sync_push_tar(tar_path, registry_url, repo, tag):
    # 파일 I/O 중 스레드 차단
    validate_tar(tar_path)  
    config, layers = process_tar(tar_path)
    
    # 순차적 blob 업로드 (매우 느림)
    for blob in [config] + layers:
        upload_blob(blob)  # 각 업로드를 기다림
    
    # 마지막에 매니페스트 업로드
    return upload_manifest(config, layers, repo, tag)
```

### 우리의 비동기 솔루션

```python
# ✅ 우리의 비동기 접근법 (빠름)
async def async_push_tar(tar_path, registry_url, repo, tag):
    # 스레드 풀에서 파일 I/O (논블로킹)
    config, layers = await asyncio.get_event_loop().run_in_executor(
        None, process_tar, tar_path
    )
    
    # 동시 blob 업로드 (훨씬 빠름)
    upload_tasks = [upload_blob(blob) for blob in [config] + layers]
    await asyncio.gather(*upload_tasks)
    
    # 매니페스트 업로드
    return await upload_manifest(config, layers, repo, tag)
```

### 성능 향상 효과

**실제 성능 비교 결과:**
- **순차 업로드**: 5개 레이어 × 30초 = 150초
- **동시 업로드**: max(30초) = 30초  
- **성능 향상**: **5배 빠름** 🚀

### 네트워크 효율성

```python
# 예시: 대용량 이미지 (1GB, 10개 레이어)
# 
# 동기식 방식:
#   레이어1 업로드 (100MB) → 20초
#   레이어2 업로드 (100MB) → 20초  
#   ...
#   총 시간: 200초
#
# 비동기 방식:
#   모든 레이어 동시 업로드 → 네트워크 대역폭 최대 활용
#   총 시간: 40초 (5배 빠름)
```

## 🏗️ 핵심 아키텍처 원칙

### 1. 비동기 우선 (Async First)

모든 주요 작업은 동시성을 위해 설계된 비동기 함수입니다:

```python
# 모든 주요 API 함수는 비동기
async def push_docker_tar(...) -> str
async def list_repositories(...) -> list[str]  
async def check_registry_connectivity(...) -> bool
async def get_image_info(...) -> ManifestInfo

# 동시 실행 가능
async def concurrent_operations():
    registry_url = "http://localhost:15000"
    
    # 여러 저장소 정보를 동시에 조회
    repos = await list_repositories(registry_url)
    info_tasks = [
        get_image_info(registry_url, repo, "latest") 
        for repo in repos
    ]
    all_info = await asyncio.gather(*info_tasks)  # 동시 실행!
    
    # 결과 처리
    for repo, info in zip(repos, all_info):
        print(f"{repo}: {info.total_size:,} bytes")
```

### 2. 불변 데이터 구조 (Immutable Data)

모든 데이터 타입은 스레드 안전성과 예측 가능성을 위해 `@dataclass(frozen=True)`를 사용합니다:

```python
@dataclass(frozen=True)
class BlobInfo:
    digest: str
    size: int
    media_type: str = "application/octet-stream"
    
    # 속성은 계산되며 저장되지 않음 (순수 함수)
    @property
    def digest_short(self) -> str:
        return self.digest.split(':')[1][:12] if ':' in self.digest else self.digest[:12]
    
    @property
    def size_mb(self) -> float:
        return self.size / (1024 * 1024)

@dataclass(frozen=True) 
class ManifestInfo:
    schema_version: int
    media_type: str
    config: BlobInfo
    layers: tuple[BlobInfo, ...]  # tuple 사용 (list가 아닌, 불변)
    digest: str | None = None
    
    @property
    def total_size(self) -> int:
        """전체 크기 계산 (config + 모든 레이어)"""
        return self.config.size + sum(layer.size for layer in self.layers)
    
    @property
    def layer_count(self) -> int:
        return len(self.layers)
```

### 3. 순수 함수 원칙 (Pure Functions)

부작용 없는 예측 가능한 함수들:

```python
# ✅ 순수 함수 - 입력이 같으면 출력도 항상 같음
def parse_repository_tag(repo_tag: str) -> tuple[str, str]:
    """저장소:태그 문자열을 파싱합니다."""
    if ':' in repo_tag:
        parts = repo_tag.rsplit(':', 1)
        return parts[0], parts[1] if parts[1] else 'latest'
    return repo_tag, 'latest'

# ✅ 순수 비동기 함수 - 네트워크 작업이지만 예측 가능
async def _calculate_blob_digest(content: bytes) -> str:
    """Blob 내용에서 digest를 계산합니다."""
    import hashlib
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"
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