# CI/CD 설정 가이드

GitHub Actions를 사용한 지속적 통합(CI) 및 지속적 배포(CD) 설정 방법을 설명합니다.

## GitHub Actions 워크플로우

### 1. CI 워크플로우 (.github/workflows/ci.yml)

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: "3.11"

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install ruff black mypy
    
    - name: Run Ruff
      run: ruff check .
    
    - name: Run Black
      run: black --check .
    
    - name: Run MyPy
      run: |
        pip install -e .
        mypy src/

  test:
    name: Test Python ${{ matrix.python-version }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Run tests
      run: |
        pytest --cov=registry_api_v2_client --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.11'
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  build:
    name: Build distribution
    runs-on: ubuntu-latest
    needs: [lint, test]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install build tools
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Check package
      run: twine check dist/*
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist
        path: dist/

  docs:
    name: Build documentation
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[docs]"
    
    - name: Build docs
      run: |
        mkdocs build --strict
    
    - name: Upload docs
      uses: actions/upload-artifact@v3
      with:
        name: docs
        path: site/
```

### 2. 릴리즈 워크플로우 (.github/workflows/release.yml)

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release (e.g., 1.2.3)'
        required: true

permissions:
  contents: write
  id-token: write

jobs:
  build:
    name: Build distribution
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build
    
    - name: Build package
      run: python -m build
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist
        path: dist/

  test-pypi:
    name: Upload to Test PyPI
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: test-pypi
      url: https://test.pypi.org/project/registry-api-v2-client/
    
    steps:
    - name: Download artifacts
      uses: actions/download-artifact@v3
      with:
        name: dist
        path: dist/
    
    - name: Publish to Test PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        repository-url: https://test.pypi.org/legacy/
        skip-existing: true

  pypi:
    name: Upload to PyPI
    needs: test-pypi
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/project/registry-api-v2-client/
    
    steps:
    - name: Download artifacts
      uses: actions/download-artifact@v3
      with:
        name: dist
        path: dist/
    
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1

  github-release:
    name: Create GitHub Release
    needs: pypi
    runs-on: ubuntu-latest
    permissions:
      contents: write
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Download artifacts
      uses: actions/download-artifact@v3
      with:
        name: dist
        path: dist/
    
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*
        generate_release_notes: true
        draft: false
        prerelease: ${{ contains(github.ref, 'rc') || contains(github.ref, 'a') || contains(github.ref, 'b') }}
```

### 3. 자동 버전 업데이트 (.github/workflows/version-bump.yml)

```yaml
name: Version Bump

on:
  workflow_dispatch:
    inputs:
      bump:
        description: 'Version bump type'
        required: true
        type: choice
        options:
          - patch
          - minor
          - major
          - prepatch
          - preminor
          - premajor

permissions:
  contents: write
  pull-requests: write

jobs:
  bump-version:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
        token: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install bump2version
    
    - name: Configure Git
      run: |
        git config user.name "github-actions[bot]"
        git config user.email "github-actions[bot]@users.noreply.github.com"
    
    - name: Bump version
      run: |
        bump2version ${{ github.event.inputs.bump }} --verbose
    
    - name: Push changes
      run: |
        git push origin HEAD:refs/heads/version-bump-${{ github.event.inputs.bump }}
        git push --tags
    
    - name: Create Pull Request
      uses: peter-evans/create-pull-request@v5
      with:
        branch: version-bump-${{ github.event.inputs.bump }}
        title: "chore: bump version (${{ github.event.inputs.bump }})"
        body: |
          Automated version bump: ${{ github.event.inputs.bump }}
          
          - [ ] Review version changes
          - [ ] Update CHANGELOG.md
        delete-branch: true
```

### 4. 의존성 업데이트 (.github/workflows/dependency-update.yml)

```yaml
name: Dependency Update

on:
  schedule:
    - cron: '0 0 * * 1'  # 매주 월요일
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  update-dependencies:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    
    - name: Install uv
      run: pip install uv
    
    - name: Update dependencies
      run: |
        uv pip compile pyproject.toml -o requirements.txt --upgrade
        uv pip sync requirements.txt
    
    - name: Run tests
      run: |
        pip install -e ".[dev]"
        pytest
    
    - name: Create Pull Request
      uses: peter-evans/create-pull-request@v5
      with:
        branch: dependency-update
        title: "chore: update dependencies"
        body: |
          Automated dependency update.
          
          - [ ] All tests pass
          - [ ] No breaking changes
        commit-message: "chore: update dependencies"
        delete-branch: true
```

## 시크릿 및 환경 설정

### 1. 필수 시크릿
GitHub 저장소 Settings → Secrets and variables → Actions에서 설정:

```
PYPI_API_TOKEN          # PyPI 업로드용 API 토큰
TEST_PYPI_API_TOKEN     # Test PyPI 업로드용 API 토큰
CODECOV_TOKEN           # Codecov 토큰 (선택적)
```

### 2. 환경 설정
Settings → Environments에서 설정:

- **test-pypi**: Test PyPI 배포용
  - Protection rules: Review 필요 (선택적)
- **pypi**: 실제 PyPI 배포용
  - Protection rules: Review 필요 (권장)

## 배지 추가

README.md에 상태 배지 추가:

```markdown
# Registry API v2 Client

[![CI](https://github.com/yourusername/registry-api-v2-client/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/registry-api-v2-client/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/registry-api-v2-client.svg)](https://badge.fury.io/py/registry-api-v2-client)
[![Python versions](https://img.shields.io/pypi/pyversions/registry-api-v2-client.svg)](https://pypi.org/project/registry-api-v2-client/)
[![codecov](https://codecov.io/gh/yourusername/registry-api-v2-client/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/registry-api-v2-client)
[![License](https://img.shields.io/pypi/l/registry-api-v2-client.svg)](https://github.com/yourusername/registry-api-v2-client/blob/main/LICENSE)
```

## 고급 설정

### 1. 매트릭스 테스트 최적화
```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - os: ubuntu-latest
        python-version: "3.11"
        toxenv: "py311,lint,type"
      - os: windows-latest
        python-version: "3.11"
        toxenv: "py311"
      - os: macos-latest
        python-version: "3.11"
        toxenv: "py311"
```

### 2. 조건부 실행
```yaml
- name: Deploy docs
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: mkdocs gh-deploy --force
```

### 3. 캐싱 전략
```yaml
- name: Cache multiple paths
  uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      ~/.cache/pre-commit
      .mypy_cache
      .pytest_cache
    key: ${{ runner.os }}-${{ hashFiles('**/pyproject.toml', '.pre-commit-config.yaml') }}
```

### 4. 병렬 작업
```yaml
jobs:
  tests:
    strategy:
      matrix:
        group: [1, 2, 3, 4]
    steps:
    - name: Run tests
      run: pytest -n auto --group ${{ matrix.group }} --splits 4
```

## 보안 모범 사례

### 1. OIDC를 사용한 PyPI 업로드
```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    # API 토큰 대신 OIDC 사용
    # PyPI에서 Trusted Publisher 설정 필요
```

### 2. 의존성 스캔
```yaml
- name: Run safety check
  run: |
    pip install safety
    safety check --json
```

### 3. CodeQL 분석
```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v2
  with:
    languages: python
```

## 문제 해결

### 1. 워크플로우 디버깅
```yaml
- name: Debug
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "SHA: ${{ github.sha }}"
```

### 2. 실패 시 아티팩트 업로드
```yaml
- name: Upload test results
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: |
      .coverage
      htmlcov/
      test-results.xml
```

### 3. 재시도 로직
```yaml
- name: Retry on failure
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: pytest
```

## 로컬 테스트

### GitHub Actions 로컬 실행
```bash
# act 설치
brew install act  # macOS
# 또는 https://github.com/nektos/act

# 워크플로우 실행
act -j test

# 특정 이벤트
act pull_request

# 시크릿 포함
act -s GITHUB_TOKEN=...
```

## 모니터링 및 알림

### 1. Slack 알림
```yaml
- name: Slack Notification
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'CI Failed: ${{ github.ref }}'
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 2. 이메일 알림
GitHub Settings → Notifications에서 설정

### 3. 상태 체크
Branch protection rules에서 필수 상태 체크 설정