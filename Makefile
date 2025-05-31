.PHONY: test test-unit test-integration test-all lint typecheck format clean install dev-install

# Default registry URL for local testing
REGISTRY_URL ?= http://localhost:15000
REGISTRY_PORT ?= 15000

# Install dependencies
install:
	uv sync

# Install development dependencies
dev-install:
	uv sync --dev

# Run unit tests only (no registry required)
test-unit:
	uv run pytest tests/test_validator.py tests/test_inspect.py tests/test_tags.py tests/test_async_simple.py tests/test_async_basic.py tests/test_comprehensive.py -v

# Run integration tests (requires registry)
test-integration:
	@echo "Checking if registry is running on $(REGISTRY_URL)..."
	@curl -f $(REGISTRY_URL)/v2/ > /dev/null 2>&1 || (echo "Registry not running. Start with: make start-registry" && exit 1)
	REGISTRY_AVAILABLE=true REGISTRY_PORT=$(REGISTRY_PORT) uv run pytest tests/test_real_integration.py tests/test_isolated_integration.py -v -m integration

# Run all tests with coverage
test-all:
	uv run pytest tests/test_validator.py tests/test_inspect.py tests/test_tags.py tests/test_async_simple.py tests/test_async_basic.py tests/test_comprehensive.py tests/test_real_integration.py -v --cov=src/registry_api_v2_client --cov-report=term-missing

# Run tests with coverage report
test-cov:
	uv run pytest tests/test_validator.py tests/test_inspect.py tests/test_tags.py tests/test_async_simple.py tests/test_async_basic.py tests/test_comprehensive.py -v --cov=src/registry_api_v2_client --cov-report=term-missing --cov-report=html

# Start registry for testing
start-registry:
	docker run -d -p $(REGISTRY_PORT):5000 --name test-registry-$(REGISTRY_PORT) \
		-e REGISTRY_STORAGE_DELETE_ENABLED=true \
		registry:2
	@echo "Waiting for registry to start..."
	@timeout 30 bash -c 'until curl -f $(REGISTRY_URL)/v2/ > /dev/null 2>&1; do sleep 2; done' || (echo "Registry failed to start" && exit 1)
	@echo "Registry is running at $(REGISTRY_URL)"

# Stop registry
stop-registry:
	docker stop test-registry-$(REGISTRY_PORT) || true
	docker rm test-registry-$(REGISTRY_PORT) || true

# Start registry with docker-compose
start-registry-compose:
	docker-compose up -d
	@echo "Waiting for registry to start..."
	@timeout 30 bash -c 'until curl -f http://localhost:15000/v2/ > /dev/null 2>&1; do sleep 2; done' || (echo "Registry failed to start" && exit 1)
	@echo "Registry is running at http://localhost:15000"

# Stop registry with docker-compose
stop-registry-compose:
	docker-compose down

# Run linting
lint:
	uv run ruff check src/

# Fix linting issues
lint-fix:
	uv run ruff check --fix src/

# Run type checking
typecheck:
	uv run mypy src/

# Format code
format:
	uv run ruff format src/

# Run all quality checks
check: lint typecheck test-unit

# Clean up
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Development workflow: start registry and run tests
dev-test: start-registry test-all stop-registry

# CI workflow: just unit tests (no registry)
ci-test: test-unit lint typecheck

# Full local test including integration
local-test: start-registry-compose
	@echo "Running full test suite..."
	REGISTRY_AVAILABLE=true REGISTRY_PORT=15000 uv run pytest \
		tests/test_validator.py \
		tests/test_inspect.py \
		tests/test_tags.py \
		tests/test_async_simple.py \
		tests/test_real_integration.py \
		tests/test_isolated_integration.py \
		-v --cov=src/registry_api_v2_client --cov-report=term-missing
	$(MAKE) stop-registry-compose

# Test parallel execution (simulate CI)
test-parallel: start-registry
	@echo "Testing parallel execution..."
	REGISTRY_AVAILABLE=true REGISTRY_PORT=$(REGISTRY_PORT) uv run pytest \
		tests/test_isolated_integration.py \
		-v -m integration -n auto
	$(MAKE) stop-registry

# Help
help:
	@echo "Available targets:"
	@echo "  install           - Install dependencies"
	@echo "  dev-install       - Install development dependencies" 
	@echo "  test-unit         - Run unit tests (no registry required)"
	@echo "  test-integration  - Run integration tests (requires registry)"
	@echo "  test-all          - Run all tests with coverage"
	@echo "  test-cov          - Run tests with HTML coverage report"
	@echo "  start-registry    - Start test registry container"
	@echo "  stop-registry     - Stop test registry container"
	@echo "  start-registry-compose - Start registry with docker-compose"
	@echo "  stop-registry-compose  - Stop registry with docker-compose"
	@echo "  lint              - Run linting"
	@echo "  lint-fix          - Fix linting issues"
	@echo "  typecheck         - Run type checking"
	@echo "  format            - Format code"
	@echo "  check             - Run all quality checks"
	@echo "  clean             - Clean up build artifacts"
	@echo "  dev-test          - Start registry, run tests, stop registry"
	@echo "  ci-test           - Run CI tests (unit + quality checks)"
	@echo "  local-test        - Full local test with docker-compose"
	@echo "  help              - Show this help"