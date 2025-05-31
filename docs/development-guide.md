# Development Guide

Complete guide for developing with the async Registry API v2 Client.

## Quick Start

### Installation
```bash
# Install the package
pip install registry-api-v2-client

# For development
git clone <repository>
cd registry-api-v2-client
uv sync --dev
```

### Basic Usage Example
```python
import asyncio
from registry_api_v2_client import (
    check_registry_connectivity,
    push_docker_tar,
    list_repositories,
    list_tags,
    get_image_info
)

async def main():
    registry_url = "http://localhost:15000"
    
    # Check if registry is accessible
    accessible = await check_registry_connectivity(registry_url)
    print(f"Registry accessible: {accessible}")
    
    # Push a Docker tar file
    digest = await push_docker_tar(
        "my-image.tar",      # Docker tar file path
        registry_url,        # Registry URL
        "myapp",            # Repository name  
        "v1.0.0"            # Tag
    )
    print(f"Pushed image with digest: {digest}")
    
    # List all repositories
    repos = await list_repositories(registry_url)
    print(f"Repositories: {repos}")
    
    # List tags for a repository
    tags = await list_tags(registry_url, "myapp")
    print(f"Tags for myapp: {tags}")
    
    # Get detailed image information
    info = await get_image_info(registry_url, "myapp", "v1.0.0")
    print(f"Image size: {info.get('size', 'unknown')} bytes")

# Run the async code
asyncio.run(main())
```

## Development Environment Setup

### Prerequisites
- **Python 3.11+** (3.12 recommended)
- **Docker** for local registry
- **uv** for fast package management

### Install uv (Recommended)
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv
```

### Project Setup
```bash
# Clone and setup
git clone <repository>
cd registry-api-v2-client

# Install development dependencies
uv sync --dev

# Verify installation
python --version  # Should be 3.11+
uv run pytest tests/test_validator.py -v
```

## Local Registry Setup

### Why Port 15000?
We use port **15000** (not 5000) to avoid conflicts with other services and match our CI setup.

### Quick Start with Docker Compose
```bash
# Start registry
make start-registry-compose

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