# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python library for Docker tar file operations, currently providing validation and inspection utilities for Docker image tar files created by `docker save`. The project focuses on tar file analysis without requiring Docker daemon or network operations.

## Development Commands

```bash
# Install development environment (requires Python 3.11+)
uv add --dev pytest pytest-cov mypy ruff black pre-commit

# Run tests with coverage
uv run pytest

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
```

## Architecture Overview

### Current Functionality

The library currently provides three main operations:

1. **Tar Validation** (`validate_docker_tar`): Validates Docker tar file structure and manifest integrity
2. **Manifest Extraction** (`get_tar_manifest`): Extracts manifest.json from tar files
3. **Image Inspection** (`inspect_docker_tar`): Provides detailed image metadata analysis

### Project Structure

```
src/registry_api_v2_client/
├── __init__.py          # Main API exports
├── exceptions.py        # RegistryError, TarReadError, ValidationError
├── models.py           # Pydantic models (ImageInspect, ImageConfig, LayerInfo)
└── utils/              # Core utilities
    ├── validator.py    # Tar validation and manifest extraction
    └── inspect.py      # Detailed image inspection
```

### Data Models

The library uses Pydantic models for type safety and serialization:

- **ImageInspect**: Complete image inspection result with metadata, config, and layers
- **ImageConfig**: Docker image configuration (architecture, OS, environment, etc.)
- **LayerInfo**: Individual layer information (digest, size, media type)

### Key Design Principles

1. **Pure Functions**: All operations are stateless and deterministic
2. **Memory Efficiency**: Tar files are processed without loading entire contents into memory
3. **Type Safety**: Extensive use of Pydantic models and type hints
4. **Synthetic Testing**: Tests use small generated tar files rather than large real images

## Important Implementation Notes

1. **Tar File Structure**: Docker save creates tar files with:
   - `manifest.json`: Array of image manifests with Config and Layers references
   - `blobs/sha256/{hash}`: Config files (JSON) and layer data
   - `repositories`: Repository/tag mapping (optional)

2. **Validation Logic**: 
   - Checks tar file format validity
   - Validates manifest.json structure and content
   - Verifies all referenced config and layer files exist in tar
   - Supports both OCI and Docker manifest formats

3. **Error Handling**: 
   - `ValidationError`: Invalid tar structure or missing files
   - `TarReadError`: File system or JSON parsing errors
   - All exceptions inherit from `RegistryError` base class

4. **Testing Strategy**:
   - Synthetic tar files for fast, deterministic tests
   - No dependency on large test images or external resources
   - Comprehensive edge case coverage (malformed JSON, missing files, etc.)

## Future Registry API Integration

The current codebase is structured to eventually support Docker Registry API v2 operations. The foundation for tar file analysis provides the building blocks for future registry push/pull functionality.