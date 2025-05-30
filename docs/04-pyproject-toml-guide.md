# pyproject.toml 설정 가이드

`pyproject.toml`은 Python 프로젝트의 메타데이터와 도구 설정을 위한 통합 설정 파일입니다. PEP 517, 518, 621을 따르는 현대적인 Python 패키징 방식입니다.

## 기본 템플릿

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "registry-api-v2-client"
version = "0.1.0"
description = "Python client library for Registry API v2"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
maintainers = [
    {name = "Your Name", email = "your.email@example.com"},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]
requires-python = ">=3.9"
dependencies = [
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "typing-extensions>=4.5.0; python_version<'3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
    "black>=23.0.0",
    "pre-commit>=3.0.0",
]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
    "mkdocstrings[python]>=0.20.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/registry-api-v2-client"
Documentation = "https://registry-api-v2-client.readthedocs.io"
Repository = "https://github.com/yourusername/registry-api-v2-client"
Issues = "https://github.com/yourusername/registry-api-v2-client/issues"
Changelog = "https://github.com/yourusername/registry-api-v2-client/blob/main/CHANGELOG.md"

[project.scripts]
registry-api = "registry_api_v2_client.__main__:main"

[tool.hatch.build]
include = [
    "src/registry_api_v2_client",
    "README.md",
    "LICENSE",
]

[tool.hatch.build.targets.wheel]
packages = ["src/registry_api_v2_client"]

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=registry_api_v2_client",
    "--cov-report=term-missing",
    "--cov-report=html",
]

[tool.coverage.run]
source = ["src/registry_api_v2_client"]
branch = true
parallel = true

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if __name__ == .__main__.:",
    "raise AssertionError",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]

[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true
no_implicit_reexport = true
namespace_packages = true
show_error_codes = true
show_column_numbers = true
pretty = true

[[tool.mypy.overrides]]
module = ["tests.*"]
ignore_errors = true

[tool.ruff]
line-length = 88
target-version = "py39"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "C4",   # flake8-comprehensions
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ARG", "S101"]

[tool.black]
line-length = 88
target-version = ["py39", "py310", "py311", "py312"]

[tool.isort]
profile = "black"
line_length = 88

[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/registry_api_v2_client/__init__.py:__version__"]
branch = "main"
upload_to_pypi = true
upload_to_release = true
build_command = "python -m build"
commit_message = "chore(release): v{version} [skip ci]"
commit_author = "github-actions[bot] <github-actions[bot]@users.noreply.github.com>"
```

## 섹션별 상세 설명

### 1. [build-system]
```toml
[build-system]
requires = ["hatchling"]  # 빌드 시스템 의존성
build-backend = "hatchling.build"  # 빌드 백엔드
```

**빌드 시스템 옵션:**
- `hatchling`: 현대적이고 빠른 빌드 시스템 (권장)
- `setuptools`: 전통적인 빌드 시스템
- `poetry-core`: Poetry 사용 시
- `flit-core`: 간단한 순수 Python 패키지용

### 2. [project] - 핵심 메타데이터

#### 필수 필드
```toml
name = "registry-api-v2-client"  # PyPI 패키지 이름
version = "0.1.0"  # 버전 (SemVer 준수)
description = "Short description"  # 한 줄 설명
```

#### 권장 필드
```toml
readme = "README.md"  # README 파일 경로
license = {text = "MIT"}  # 또는 {file = "LICENSE"}
authors = [{name = "Name", email = "email@example.com"}]
requires-python = ">=3.9"  # Python 버전 요구사항
dependencies = ["package>=1.0.0"]  # 런타임 의존성
```

#### Classifiers
PyPI에서 패키지를 분류하는 데 사용:
```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Typing :: Typed",  # 타입 힌트 지원
]
```

### 3. [project.optional-dependencies]
선택적 기능을 위한 추가 의존성:
```toml
[project.optional-dependencies]
dev = ["pytest", "mypy", "ruff"]  # pip install package[dev]
docs = ["sphinx", "furo"]  # pip install package[docs]
all = ["package[dev]", "package[docs]"]  # 모든 추가 의존성
```

### 4. [project.scripts]
CLI 명령어 등록:
```toml
[project.scripts]
my-command = "package.module:function"
```

### 5. 도구별 설정

#### Pytest
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]  # src 레이아웃 사용 시
addopts = ["--cov=package_name", "-v"]
```

#### Coverage
```toml
[tool.coverage.run]
source = ["src/package_name"]
branch = true  # 분기 커버리지 측정

[tool.coverage.report]
show_missing = true
skip_covered = true
```

#### MyPy (타입 체킹)
```toml
[tool.mypy]
python_version = "3.9"
strict = true  # 엄격한 타입 체킹
show_error_codes = true
```

#### Ruff (린터)
```toml
[tool.ruff]
line-length = 88
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]  # 활성화할 규칙
ignore = ["E501"]  # 무시할 규칙
```

#### Black (포매터)
```toml
[tool.black]
line-length = 88
target-version = ["py39"]
```

## 동적 버전 관리

### 파일에서 버전 읽기
```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/package_name/__init__.py"
```

### Git 태그 기반 버전
```toml
[project]
dynamic = ["version"]

[tool.setuptools_scm]
write_to = "src/package_name/_version.py"
```

## 패키지 포함/제외 설정

### Hatchling 사용 시
```toml
[tool.hatch.build]
include = [
    "src/package_name",
    "README.md",
    "LICENSE",
]
exclude = [
    "*.pyc",
    "__pycache__",
    ".pytest_cache",
]
```

### Setuptools 사용 시
```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["package_name*"]
exclude = ["tests*"]
```

## 환경별 설정 예시

### 최소 설정 (간단한 패키지)
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "simple-package"
version = "0.1.0"
description = "A simple package"
requires-python = ">=3.9"
```

### 풀 설정 (복잡한 프로젝트)
위의 기본 템플릿 참조

## 모범 사례

1. **버전 관리**: 한 곳에서만 버전 정의 (DRY 원칙)
2. **의존성 버전**: 최소 버전 명시 (`>=`)
3. **Python 버전**: 지원하는 최소 버전 명시
4. **도구 설정**: 프로젝트 일관성을 위해 도구 설정 포함
5. **메타데이터**: 가능한 모든 메타데이터 제공

## 검증 및 테스트

```bash
# 패키지 빌드 테스트
python -m build

# 메타데이터 검증
python -m twine check dist/*

# 설치 테스트
pip install -e .  # 개발 모드
pip install .[dev]  # 개발 의존성 포함
```