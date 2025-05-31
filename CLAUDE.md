# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python library for **async** Docker Registry API v2 client operations with tar file utilities. The project provides both tar file analysis capabilities (validation, inspection, manifest extraction) and full Docker Registry API v2 operations (push, pull, list, delete) using an **async functional programming approach** for maximum performance.

## Development Commands

```bash
# Install development environment (requires Python 3.11+)
uv add --dev pytest pytest-cov mypy ruff black pre-commit

# Run tests with coverage
uv run pytest

# Run tests excluding integration tests
uv run pytest -m "not integration"

# Run async tests specifically
uv run pytest tests/test_async_basic.py -v

# Run a specific test
uv run pytest tests/test_validator.py::TestValidateDockerTar::test_validate_valid_tar -v

# Type checking
uv run mypy src/

# Linting and formatting
uv run ruff check src/
uv run ruff check --fix src/  # Auto-fix issues
uv run black src/

# Run all pre-commit checks
uv run pre-commit run --all-files

# Build package
uv build

# Start local Docker registry for testing (port 15000)
docker compose up -d

# Test async performance
uv run python examples/performance_comparison.py
```

## Architecture Overview

### Async Functional Architecture

The codebase follows **async functional programming principles** with single responsibility and pure async functions for optimal I/O performance:

```
src/registry_api_v2_client/
├── __init__.py          # Main async API exports
├── exceptions.py        # RegistryError, TarReadError, ValidationError
├── models.py           # Pydantic models (legacy tar inspection)
├── push.py             # Main async push API 
├── registry.py         # Main async registry API
├── core/               # Core async components
│   ├── types.py        # Immutable data structures (@dataclass(frozen=True))
│   ├── connectivity.py # Pure async connectivity checking functions
│   └── session.py      # Async HTTP session management (aiohttp)
├── operations/         # Async registry operation modules
│   ├── blobs.py        # Async blob upload/download operations
│   ├── manifests.py    # Async manifest operations (create, upload, delete)
│   ├── repositories.py # Async repository listing operations
│   └── images.py       # Async image info and deletion operations
├── tar/                # Tar file processing (runs in thread pool)
│   ├── processor.py    # Tar processing and manifest creation
│   └── validator.py    # Tar validation wrapper
└── utils/              # Legacy sync tar utilities
    ├── validator.py    # Tar validation and manifest extraction
    └── inspect.py      # Detailed image inspection
```

### Async API Usage

All main registry operations are **async functions** that must be awaited:

```python
import asyncio
from registry_api_v2_client import (
    check_registry_connectivity,
    push_docker_tar,
    list_repositories,
    list_tags,
    get_manifest,
    get_image_info,
    delete_image,
    delete_image_by_digest,
)

async def main():
    registry_url = "http://localhost:15000"
    
    # Check connectivity
    await check_registry_connectivity(registry_url)
    
    # List repositories concurrently
    repos = await list_repositories(registry_url)
    
    # Get info for multiple repos concurrently
    tasks = [get_image_info(registry_url, repo, "latest") for repo in repos]
    results = await asyncio.gather(*tasks)

# Run async code
asyncio.run(main())
```

### Core Data Types

The library uses immutable dataclasses for functional programming:

- **RegistryConfig**: Registry connection configuration (frozen dataclass)
- **BlobInfo**: Blob metadata (digest, size, media type) 
- **ManifestInfo**: Complete manifest information with config and layers
- **RequestResult**: HTTP request result with status, headers, data
- **UploadSession**: Blob upload session information

### Main Async API Functions

**Push Operations**:
- `async push_docker_tar()`: Complete tar file push to registry with concurrent blob uploads
- `async check_registry_connectivity()`: Verify registry accessibility

**Registry Operations**:
- `async list_repositories()`: List all repositories
- `async list_tags()`: List tags for a repository
- `async get_manifest()`: Get image manifest
- `async get_image_info()`: Get detailed image information
- `async delete_image()`: Delete image by tag
- `async delete_image_by_digest()`: Delete image by digest

### Async Performance Benefits

1. **Concurrent Operations**: Multiple network requests execute simultaneously
2. **Non-blocking I/O**: CPU can work on other tasks while waiting for network/disk I/O
3. **Blob Upload Concurrency**: All image layers upload in parallel
4. **Thread Pool Integration**: File I/O operations run in thread pools to avoid blocking

Example performance improvements:
- Sequential calls: 5 operations in ~0.10 seconds
- Concurrent calls: 5 operations in ~0.02 seconds (5x faster)

### Key Design Principles

1. **Async Functional Architecture**: Pure async functions, immutable data structures, concurrent execution
2. **Single Responsibility**: Each module/function has one clear async purpose
3. **Type Safety**: Extensive use of type hints and Pydantic models
4. **Memory Efficiency**: Chunked blob uploads (5MB chunks), streaming with aiohttp
5. **Error Handling**: Comprehensive async exception hierarchy with context

### Registry Protocol Implementation

- **Docker Registry API v2 compliance**: Full async implementation of push/pull protocol
- **Concurrent blob handling**: Multiple blob uploads with chunked support and digest verification
- **Async manifest operations**: Docker v2 schema with proper digest calculation
- **Session management**: aiohttp with connection pooling and retry strategies

### Testing Strategy

- **Async unit tests**: pytest-asyncio with comprehensive async mocking
- **Integration tests**: Real async registry operations (requires `docker compose up -d`)
- **Performance tests**: Concurrent vs sequential operation comparisons
- **Synthetic data**: Generated tar files for deterministic async testing
- **Coverage**: Full async coverage reporting with HTML output

## Important Implementation Notes

1. **Async Context**: All main API functions are async and must be awaited
2. **Concurrency**: Blob uploads happen concurrently for maximum throughput
3. **Thread Pool**: File I/O operations run in thread pools to avoid blocking the event loop
4. **Registry Configuration**: Default registry runs on port 15000 (not 5000) to avoid conflicts
5. **Session Management**: Uses aiohttp with proper connection pooling and timeout handling
6. **Error Context**: All registry errors include async context and suggestions

## Docker Registry Setup

For development and testing, use the included Docker registry:

```bash
# Start registry on port 15000
docker compose up -d

# Registry will be available at http://localhost:15000
# Supports deletion operations (REGISTRY_STORAGE_DELETE_ENABLED=true)
```

The registry configuration uses port 15000 instead of the standard 5000 to avoid conflicts with other services.

## Async Usage Examples

See `examples/` directory for:
- `async_example.py`: Basic async operations
- `performance_comparison.py`: Performance comparison between concurrent and sequential calls