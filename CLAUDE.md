# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an async Python client library for Docker Registry API v2, specifically designed to push Docker images from tar files to unauthenticated registry:2 containers without requiring Docker daemon.

## Development Commands

```bash
# Install development environment (requires Python 3.11+)
pip install -e ".[dev]"

# Run tests with coverage
pytest

# Run a specific test
pytest tests/path/to/test_file.py::TestClass::test_method -v

# Run tests with specific marker
pytest -m "not integration"

# Type checking
mypy src/

# Linting
ruff check src/
ruff check --fix src/  # Auto-fix issues

# Code formatting
black src/
black --check src/  # Check without modifying

# Run all checks (before committing)
black src/ && ruff check src/ && mypy src/ && pytest

# Build package
python -m build

# Install in development mode with all extras
pip install -e ".[dev]"
```

## Architecture Overview

### Core Design Principles

1. **Functional Programming**: The codebase follows functional programming patterns with pure functions, immutability, and minimal side effects. See `docs/03-coding-style.md` for detailed guidelines.

2. **SOLID Principles**: All modules adhere to SOLID principles, particularly:
   - Single Responsibility: Each module has one clear purpose
   - Dependency Inversion: Code depends on protocols/abstractions, not concrete implementations

3. **Async-First**: All I/O operations are async using `aiohttp` and `aiofiles`.

### Project Structure

```
src/registry_api_v2_client/
├── core/            # Core functionality
│   ├── client.py    # RegistryClient - main API entry point
│   ├── models.py    # Pydantic data models
│   └── exceptions.py # Custom exception hierarchy
├── tar/             # Docker tar file handling
│   ├── reader.py    # TarImageReader - async tar file reader
│   └── models.py    # Tar-specific data models
└── utils/           # Utility functions
    ├── digest.py    # SHA256 digest calculations
    └── helpers.py   # Other helper functions
```

### Key Components and Their Interactions

```
RegistryClient (main entry point)
    ├── push_tar() orchestrates the entire upload process
    │   ├── TarImageReader: Extracts image metadata from tar files
    │   ├── Concurrent blob uploads using asyncio.Semaphore
    │   └── Manifest creation and upload
    │
    ├── HTTP operations (all async)
    │   ├── check_blob_exists(): HEAD request to check blob presence
    │   ├── upload_blob(): Chunked upload with progress tracking
    │   └── upload_manifest(): Final step to register the image
    │
    └── Error handling with custom exception hierarchy
```

### Critical Design Decisions

1. **No Authentication**: By design, this library only supports unauthenticated registry:2 containers. All auth-related code has been intentionally excluded.

2. **Memory Efficiency**: Large files are streamed using async iterators. Never load entire tar files or layers into memory.

3. **Concurrent Uploads**: Layer uploads use semaphore-based concurrency control (default 3, configurable). This balances performance with resource usage.

4. **Progress Tracking**: The progress callback pattern supports both sync and async callbacks, checked via `asyncio.iscoroutinefunction()`.

### Data Flow for push_tar()

1. Read tar file manifest → Extract image metadata
2. For each layer (concurrently):
   - Check if blob exists (HEAD request)
   - If not, stream upload in 5MB chunks
3. Upload config blob
4. Create and upload manifest with all blob references
5. Return manifest digest

### Key Patterns

- **Context Managers**: Both `RegistryClient` and `TarImageReader` are async context managers
- **Stream Processing**: Layer data uses `AsyncIterator[bytes]` for memory efficiency
- **Type Safety**: Extensive use of type hints and protocols for compile-time safety

## Important Implementation Notes

1. **Digest Format**: Always use format `algorithm:hexdigest` (e.g., `sha256:abc123...`)

2. **URL Handling**: Registry responses may return relative URLs in Location headers. Always normalize with `urljoin()`.

3. **Error Recovery**: Network operations should raise specific exceptions (`BlobUploadError`, `ManifestError`, etc.) with context.

4. **Tar File Structure**: Docker save creates tar files with:
   - `manifest.json`: Array of image manifests
   - `{hash}.json`: Image configuration files
   - `{hash}/layer.tar`: Compressed layer data
   - `repositories`: Repository/tag mapping (optional)

5. **Registry API Quirks**:
   - Blob uploads use a three-step process: initiate → upload chunks → finalize
   - Manifest upload returns digest in `Docker-Content-Digest` header
   - Always check blob existence before uploading to avoid redundant transfers

## Testing Strategy

The project uses pytest with async support:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test against real registry:2 container (mark with `@pytest.mark.integration`)
3. **Fixtures**: Use pytest-asyncio fixtures for async setup/teardown
4. **Coverage**: Minimum 80% code coverage target

## Version Management

The project uses `python-semantic-release` with conventional commits:
- `feat:` → minor version bump
- `fix:` → patch version bump
- `feat!:` or `BREAKING CHANGE:` → major version bump

See `docs/10-versioning.md` for detailed versioning guidelines.