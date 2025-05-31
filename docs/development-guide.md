# 개발 가이드

비동기 Registry API v2 클라이언트 개발을 위한 완전한 가이드입니다.

## 🚀 빠른 시작

### 설치
```bash
# 패키지 설치
pip install registry-api-v2-client

# 개발용 설치
git clone <repository>
cd registry-api-v2-client
make dev-install  # 또는 uv sync --dev
```

### 기본 사용 예제
```python
import asyncio
from registry_api_v2_client import (
    check_registry_connectivity,
    push_docker_tar,
    push_docker_tar_with_original_tags,
    list_repositories,
    list_tags,
    get_image_info,
    extract_original_tags,
    validate_docker_tar
)

async def main():
    registry_url = "http://localhost:15000"
    
    # 1. 레지스트리 접근성 확인
    accessible = await check_registry_connectivity(registry_url)
    print(f"✅ 레지스트리 접근 가능: {accessible}")
    
    # 2. tar 파일 검증 (동기 함수)
    tar_file = "my-image.tar"
    from pathlib import Path
    if validate_docker_tar(Path(tar_file)):
        print(f"✅ 유효한 Docker tar 파일: {tar_file}")
        
        # 원본 태그 추출
        original_tags = extract_original_tags(tar_file)
        print(f"📦 발견된 태그: {original_tags}")
    
    # 3. Docker tar 파일 푸시 (지정된 태그)
    digest = await push_docker_tar(
        tar_file,           # Docker tar 파일 경로
        registry_url,       # 레지스트리 URL
        "myapp",           # 저장소 이름  
        "v1.0.0"           # 태그
    )
    print(f"🚀 푸시 완료, digest: {digest}")
    
    # 4. 원본 태그로 푸시 (자동 태그 추출)
    if original_tags:
        digest = await push_docker_tar_with_original_tags(tar_file, registry_url)
        print(f"🏷️ 원본 태그로 푸시 완료: {digest}")
    
    # 5. 저장소 목록 조회
    repos = await list_repositories(registry_url)
    print(f"📂 저장소 목록: {repos}")
    
    # 6. 특정 저장소의 태그 목록 조회
    if repos:
        tags = await list_tags(registry_url, repos[0])
        print(f"🏷️ {repos[0]} 태그: {tags}")
        
        # 7. 이미지 상세 정보 조회
        if tags:
            info = await get_image_info(registry_url, repos[0], tags[0])
            print(f"ℹ️ 이미지 크기: {info.get('size', 'unknown'):,} bytes")
            print(f"🏗️ 아키텍처: {info.get('architecture', 'unknown')}")

# 비동기 코드 실행
asyncio.run(main())
```

## 🛠️ 개발 환경 설정

### 📋 시스템 요구사항
- **Python 3.11+** (3.12 권장) - 최신 타입 힌트 지원 필요
- **Docker** - 로컬 레지스트리 및 테스트용
- **uv** - 빠른 패키지 관리자 (권장)

### uv 설치 (권장)
```bash
# uv 설치 (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 또는 pip로 설치
pip install uv

# Windows (PowerShell)
powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"

# 설치 확인
uv --version
```

### 프로젝트 설정
```bash
# 1. 저장소 클론
git clone <repository>
cd registry-api-v2-client

# 2. 개발 의존성 설치
make dev-install          # 또는 uv sync --dev

# 3. 설치 확인
python --version          # 3.11+ 확인
uv run python -c \"import registry_api_v2_client; print('✅ 패키지 설치 완료')\"

# 4. 간단한 테스트 실행
uv run pytest tests/test_validator.py -v
```

### 개발 환경 확인
```bash
# Python 버전 및 환경 확인
uv run python --version
uv run python -c \"
import sys
import asyncio
import aiohttp
print(f'Python: {sys.version}')
print(f'asyncio: {asyncio.__version__ if hasattr(asyncio, '__version__') else 'built-in'}')
print(f'aiohttp: {aiohttp.__version__}')
print('✅ 모든 의존성이 올바르게 설치되었습니다')
\"
```"

## 🐳 로컬 레지스트리 설정

### 포트 15000을 사용하는 이유?
포트 **15000**을 사용하는 이유 (표준 5000이 아닌):
- 다른 서비스와의 충돌 방지 (macOS AirPlay 등)
- CI 환경과의 일관성 유지
- 개발 환경 격리

### Docker Compose로 빠른 시작
```bash
# 레지스트리 시작 (권장 방법)
make start-registry-compose

# 레지스트리 상태 확인
curl http://localhost:15000/v2/

# 레지스트리 중지
make stop-registry-compose

# Registry is now available at http://localhost:15000
curl http://localhost:15000/v2/

# Stop registry  
make stop-registry-compose
```

### Manual Registry Setup
```bash
# Start registry manually
docker run -d -p 15000:5000 --name test-registry \
  -e REGISTRY_STORAGE_DELETE_ENABLED=true \
  registry:2

# Wait for it to be ready
timeout 30 bash -c 'until curl -f http://localhost:15000/v2/ > /dev/null 2>&1; do sleep 2; done'

# Test
curl http://localhost:15000/v2/
# Expected: {}
```

### Environment Variables
```bash
# Set for development
export REGISTRY_URL=http://localhost:15000
export REGISTRY_PORT=15000
export REGISTRY_AVAILABLE=true  # Enables integration tests
```

## Development Workflow

### 1. Code Quality Checks
```bash
# Run all quality checks
make check

# Individual checks
make lint          # Ruff linting
make typecheck     # MyPy type checking  
make test-unit     # Unit tests (fast, no registry needed)
```

### 2. Testing

#### Unit Tests (Fast)
```bash
# No registry required - uses mocking
make test-unit

# Or directly
uv run pytest tests/test_validator.py tests/test_inspect.py tests/test_tags.py -v
```

#### Integration Tests (Real Registry)
```bash
# Start registry first
make start-registry-compose

# Run integration tests
make test-integration

# Or combined
make local-test  # Starts registry, runs tests, stops registry
```

#### Test Coverage
```bash
# Generate coverage report
make test-cov

# View HTML report
open htmlcov/index.html
```

### 3. Development Cycle
```bash
# 1. Make code changes

# 2. Quick checks
make test-unit
make lint-fix      # Auto-fix linting issues
make typecheck

# 3. Integration testing (if needed)
make start-registry-compose
make test-integration  
make stop-registry-compose

# 4. Commit
git add .
git commit -m "feat: add new feature"
```

## Advanced Usage Examples

### Concurrent Operations
```python
import asyncio
from registry_api_v2_client import push_docker_tar, list_repositories

async def concurrent_example():
    registry_url = "http://localhost:15000"
    
    # Push multiple images concurrently
    push_tasks = [
        push_docker_tar("app1.tar", registry_url, "app1", "latest"),
        push_docker_tar("app2.tar", registry_url, "app2", "latest"), 
        push_docker_tar("app3.tar", registry_url, "app3", "latest"),
    ]
    
    # Execute all pushes concurrently
    start = time.time()
    digests = await asyncio.gather(*push_tasks)
    duration = time.time() - start
    
    print(f"Pushed {len(digests)} images in {duration:.2f} seconds")
    for i, digest in enumerate(digests):
        print(f"App {i+1} digest: {digest}")

asyncio.run(concurrent_example())
```

### Tag Preservation from Docker Exports
```python
from registry_api_v2_client import (
    push_docker_tar_with_original_tags,
    push_docker_tar_with_all_original_tags,
    extract_original_tags
)

async def tag_preservation_example():
    registry_url = "http://localhost:15000"
    tar_file = "exported-image.tar"  # From docker save
    
    # Check what tags are in the tar file
    tags = extract_original_tags(tar_file)
    print(f"Original tags: {tags}")
    
    # Push with first original tag
    digest = await push_docker_tar_with_original_tags(tar_file, registry_url)
    print(f"Pushed with original tag: {digest}")
    
    # Or push ALL original tags
    digests = await push_docker_tar_with_all_original_tags(tar_file, registry_url)
    print(f"Pushed {len(digests)} tags: {digests}")

asyncio.run(tag_preservation_example())
```

### Bulk Repository Management
```python
async def bulk_management_example():
    registry_url = "http://localhost:15000"
    
    # Get all repositories and their tags concurrently
    repos = await list_repositories(registry_url)
    
    # Concurrently get tags for all repos
    tag_tasks = [list_tags(registry_url, repo) for repo in repos]
    all_tags = await asyncio.gather(*tag_tasks)
    
    # Display results
    for repo, tags in zip(repos, all_tags):
        print(f"{repo}: {len(tags)} tags")
        
    # Get detailed info for latest tags concurrently
    info_tasks = [
        get_image_info(registry_url, repo, "latest")
        for repo in repos
    ]
    
    all_info = await asyncio.gather(*info_tasks, return_exceptions=True)
    
    for repo, info in zip(repos, all_info):
        if isinstance(info, Exception):
            print(f"{repo}: No 'latest' tag or error")
        else:
            size = info.get('size', 0)
            print(f"{repo}: {size:,} bytes")

asyncio.run(bulk_management_example())
```

## Performance and Debugging

### Performance Tips
```python
# ✅ Good - Concurrent operations
async def fast_operations():
    tasks = [operation1(), operation2(), operation3()]
    results = await asyncio.gather(*tasks)  # Runs concurrently

# ❌ Slow - Sequential operations  
async def slow_operations():
    result1 = await operation1()  # Wait for each one
    result2 = await operation2()  # Sequential execution
    result3 = await operation3()
```

### Debugging Async Issues
```python
import logging
import asyncio

# Enable async debugging
logging.basicConfig(level=logging.DEBUG)
asyncio.get_event_loop().set_debug(True)

async def debug_example():
    try:
        digest = await push_docker_tar("test.tar", "http://localhost:15000", "test", "debug")
        print(f"Success: {digest}")
    except Exception as e:
        print(f"Error: {e}")
        # Use breakpoint() for debugging
        breakpoint()
```

### Registry Debugging
```bash
# Check registry status
docker ps | grep registry

# View registry logs
docker logs test-registry

# Test endpoints manually
curl -v http://localhost:15000/v2/
curl -v http://localhost:15000/v2/_catalog
curl -v http://localhost:15000/v2/myapp/tags/list
```

## Creating Test Data

### Generate Test Tar File
```python
import tempfile
import tarfile
import json
import hashlib

def create_test_tar(repo_tag="test:latest"):
    """Create a minimal test Docker tar file."""
    config = {"architecture": "amd64", "os": "linux"}
    config_json = json.dumps(config).encode()
    config_hash = hashlib.sha256(config_json).hexdigest()
    
    layer_data = b"test layer content"
    layer_hash = hashlib.sha256(layer_data).hexdigest()
    
    manifest = [{
        "Config": f"blobs/sha256/{config_hash}",
        "RepoTags": [repo_tag],
        "Layers": [f"blobs/sha256/{layer_hash}"]
    }]
    
    tar_path = tempfile.mktemp(suffix='.tar')
    with tarfile.open(tar_path, 'w') as tar:
        # Add manifest.json
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_content = json.dumps(manifest).encode()
        manifest_info.size = len(manifest_content)
        tar.addfile(manifest_info, fileobj=tarfile.io.BytesIO(manifest_content))
        
        # Add config
        config_info = tarfile.TarInfo(f"blobs/sha256/{config_hash}")
        config_info.size = len(config_json)
        tar.addfile(config_info, fileobj=tarfile.io.BytesIO(config_json))
        
        # Add layer
        layer_info = tarfile.TarInfo(f"blobs/sha256/{layer_hash}")
        layer_info.size = len(layer_data)
        tar.addfile(layer_info, fileobj=tarfile.io.BytesIO(layer_data))
    
    return tar_path

# Usage
tar_file = create_test_tar("mytest:v1.0")
# Now you can use tar_file with push_docker_tar()
```

### Export Real Docker Image
```bash
# Pull and export a real image
docker pull alpine:latest
docker save alpine:latest -o alpine.tar

# Use with the client
python -c "
import asyncio
from registry_api_v2_client import push_docker_tar_with_original_tags

async def test():
    digest = await push_docker_tar_with_original_tags('alpine.tar', 'http://localhost:15000')
    print(f'Pushed alpine with digest: {digest}')

asyncio.run(test())
"
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using port 15000
lsof -i :15000

# Kill the process
kill $(lsof -t -i:15000)

# Restart registry
make start-registry-compose
```

#### Import Errors
```bash
# Reinstall in development mode
uv sync --dev

# Check Python path
python -c "import registry_api_v2_client; print('OK')"
```

#### Async Test Issues
```bash
# Check pytest configuration
cat pytest.ini

# Run specific test with debug
uv run pytest tests/test_specific.py::test_function -v -s --pdb
```

#### Performance Issues
```bash
# Check if operations are running concurrently
# Add timing logs to your code:
import time

start = time.time()
result = await your_async_operation()
print(f"Operation took {time.time() - start:.2f} seconds")
```

### Clean Reset
```bash
# Complete cleanup and restart
make stop-registry-compose
docker compose down -v  # Removes volumes too
rm -rf .venv
uv sync --dev
make start-registry-compose
```

This development guide covers everything you need to effectively develop with and contribute to the async Registry API v2 Client.