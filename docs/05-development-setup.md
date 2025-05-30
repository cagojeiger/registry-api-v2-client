# 개발 환경 설정 가이드

Python 패키지 개발을 위한 로컬 개발 환경 설정 방법을 설명합니다.

## Python 버전 관리

### pyenv 설치 및 설정 (권장)
```bash
# macOS
brew install pyenv

# Linux
curl https://pyenv.run | bash

# .bashrc/.zshrc에 추가
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Python 설치
pyenv install 3.11.7
pyenv local 3.11.7
```

### 여러 Python 버전 테스트
```bash
# 여러 버전 설치
pyenv install 3.9.18 3.10.13 3.11.7 3.12.1

# 프로젝트에서 사용
pyenv local 3.11.7 3.9.18 3.10.13 3.12.1
```

## 가상환경 설정

### venv 사용 (기본)
```bash
# 가상환경 생성
python -m venv venv

# 활성화
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 비활성화
deactivate
```

### pyenv-virtualenv 사용
```bash
# 가상환경 생성
pyenv virtualenv 3.11.7 registry-api-env

# 자동 활성화
pyenv local registry-api-env
```

### uv 사용 (빠른 패키지 관리자)
```bash
# uv 설치
pip install uv

# 가상환경 생성
uv venv

# 의존성 설치
uv pip install -e ".[dev]"

# 의존성 동기화
uv pip sync requirements.txt
```

## 프로젝트 설정

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/registry-api-v2-client.git
cd registry-api-v2-client
```

### 2. 개발 모드 설치
```bash
# 기본 설치
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"

# 모든 추가 의존성
pip install -e ".[dev,docs]"
```

### 3. pre-commit 설정
```bash
# pre-commit 설치
pip install pre-commit

# Git hooks 설치
pre-commit install

# 모든 파일에 대해 실행
pre-commit run --all-files
```

#### .pre-commit-config.yaml 예시
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict]
```

## 개발 도구 설정

### 1. 코드 포매터 (Black)
```bash
# 실행
black src/ tests/

# 검사만
black --check src/ tests/

# 설정 (pyproject.toml)
[tool.black]
line-length = 88
target-version = ["py39"]
```

### 2. 린터 (Ruff)
```bash
# 실행
ruff check .

# 자동 수정
ruff check --fix .

# watch 모드
ruff check --watch .
```

### 3. 타입 체커 (MyPy)
```bash
# 실행
mypy src/

# 엄격 모드
mypy --strict src/

# 캐시 지우기
mypy --no-incremental src/
```

### 4. 테스트 (Pytest)
```bash
# 기본 실행
pytest

# 상세 출력
pytest -v

# 특정 테스트
pytest tests/test_client.py::test_connection

# 커버리지
pytest --cov=registry_api_v2_client --cov-report=html

# 병렬 실행
pytest -n auto

# 실패한 테스트만 재실행
pytest --lf
```

## IDE/에디터 설정

### VS Code
`.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

### PyCharm
1. Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Enable pytest: Settings → Tools → Python Integrated Tools
4. Configure Black: Settings → Tools → External Tools

## 개발 워크플로우

### 1. 브랜치 생성
```bash
# 기능 브랜치
git checkout -b feature/add-retry-logic

# 버그 수정 브랜치
git checkout -b fix/connection-timeout
```

### 2. 코드 작성
```bash
# 변경사항 확인
git status

# 테스트 실행
pytest tests/

# 코드 품질 검사
ruff check .
mypy src/
black --check .
```

### 3. 커밋
```bash
# pre-commit 실행
pre-commit run

# 스테이징
git add .

# 커밋 (Conventional Commits)
git commit -m "feat: add retry logic for API calls"
```

### 4. 푸시 및 PR
```bash
# 푸시
git push origin feature/add-retry-logic

# PR 생성 (GitHub CLI)
gh pr create --title "Add retry logic" --body "..."
```

## 디버깅

### 1. Python 디버거 (pdb)
```python
# 코드에 삽입
import pdb; pdb.set_trace()

# Python 3.7+
breakpoint()
```

### 2. IPython 사용
```bash
# 설치
pip install ipython

# 대화형 셸
ipython

# 코드에서 사용
from IPython import embed; embed()
```

### 3. 로깅 설정
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

## 문서 개발

### 1. Sphinx 설정
```bash
# 설치
pip install sphinx sphinx-rtd-theme

# 초기화
sphinx-quickstart docs/
```

### 2. MkDocs 설정
```bash
# 설치
pip install mkdocs mkdocs-material

# 초기화
mkdocs new .

# 개발 서버
mkdocs serve

# 빌드
mkdocs build
```

### 3. 문서 자동 생성
```bash
# API 문서 생성
sphinx-apidoc -o docs/api src/registry_api_v2_client
```

## 성능 프로파일링

### 1. cProfile
```bash
# 스크립트 프로파일링
python -m cProfile -s cumtime myscript.py

# 결과 저장
python -m cProfile -o profile.stats myscript.py
```

### 2. memory_profiler
```bash
# 설치
pip install memory-profiler

# 사용
python -m memory_profiler myscript.py
```

## 지속적 통합 로컬 테스트

### 1. tox 사용
```bash
# 설치
pip install tox

# 실행
tox

# 특정 환경
tox -e py311
```

#### tox.ini 예시
```ini
[tox]
envlist = py{39,310,311,312},lint,type

[testenv]
deps =
    pytest
    pytest-cov
commands =
    pytest {posargs}

[testenv:lint]
deps = ruff
commands = ruff check .

[testenv:type]
deps = mypy
commands = mypy src/
```

### 2. nox 사용
```python
# noxfile.py
import nox

@nox.session(python=["3.9", "3.10", "3.11", "3.12"])
def tests(session):
    session.install("-e", ".[dev]")
    session.run("pytest")

@nox.session
def lint(session):
    session.install("ruff")
    session.run("ruff", "check", ".")
```

## 문제 해결

### 의존성 충돌
```bash
# 의존성 트리 확인
pip install pipdeptree
pipdeptree

# 충돌 확인
pipdeptree --warn conflict
```

### 캐시 정리
```bash
# pip 캐시
pip cache purge

# pytest 캐시
pytest --cache-clear

# mypy 캐시
rm -rf .mypy_cache/

# Python 바이트코드
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 재설치
```bash
# 가상환경 재생성
deactivate
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```