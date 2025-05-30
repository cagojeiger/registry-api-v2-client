# Python 패키지 프로젝트 구조 가이드

이 문서는 PyPI에 업로드할 Python 패키지의 기본 템플릿 구조를 설명합니다.

## 권장 디렉토리 구조

```
registry-api-v2-client/
├── src/
│   └── registry_api_v2_client/      # 메인 패키지 디렉토리
│       ├── __init__.py              # 패키지 초기화 및 버전 정보
│       ├── __main__.py              # CLI 진입점 (선택적)
│       ├── py.typed                 # PEP 561 타입 힌트 마커
│       ├── core/                    # 핵심 기능
│       │   ├── __init__.py
│       │   ├── client.py            # API 클라이언트
│       │   ├── models.py            # 데이터 모델
│       │   └── exceptions.py        # 커스텀 예외
│       ├── utils/                   # 유틸리티 함수
│       │   ├── __init__.py
│       │   └── helpers.py
│       └── services/                # 비즈니스 로직
│           ├── __init__.py
│           └── registry.py
├── tests/                           # 테스트 코드
│   ├── __init__.py
│   ├── conftest.py                  # pytest 설정 및 fixtures
│   ├── unit/                        # 단위 테스트
│   │   └── test_client.py
│   └── integration/                 # 통합 테스트
│       └── test_api.py
├── docs/                            # 문서
│   ├── README.md                    # 프로젝트 개요
│   ├── installation.md              # 설치 가이드
│   ├── usage.md                     # 사용법
│   └── api.md                       # API 레퍼런스
├── .github/                         # GitHub 설정
│   └── workflows/                   # GitHub Actions
│       ├── ci.yml                   # CI 파이프라인
│       └── release.yml              # 릴리즈 자동화
├── pyproject.toml                   # 프로젝트 설정 (PEP 621)
├── README.md                        # 프로젝트 README
├── LICENSE                          # 라이선스 파일
├── .gitignore                       # Git 무시 파일
├── .pre-commit-config.yaml          # pre-commit 설정
├── mypy.ini                         # MyPy 타입 체커 설정
└── uv.lock                          # 의존성 잠금 파일 (uv 사용 시)
```

## 주요 구성 요소 설명

### 1. `src/` 레이아웃
- **장점**: 
  - 개발 중 실수로 저장소 루트에서 import하는 것을 방지
  - 설치된 패키지와 개발 중인 코드를 명확히 구분
  - editable install 시 더 안전한 환경 제공

### 2. 패키지 구조
- **`__init__.py`**: 패키지 초기화, 버전 정보 포함
  ```python
  __version__ = "0.1.0"
  ```
- **`py.typed`**: 타입 힌트 지원을 위한 마커 파일 (빈 파일)
- **모듈 구성**: 기능별로 명확히 분리 (core, utils, services)

### 3. 테스트 구조
- **`conftest.py`**: pytest fixtures 및 설정
- **단위 테스트와 통합 테스트 분리**: 테스트 유형별 관리
- **테스트 네이밍**: `test_*.py` 또는 `*_test.py` 패턴 사용

### 4. 문서화
- **`docs/`**: 상세 문서 디렉토리
- **`README.md`**: 프로젝트 개요, 빠른 시작 가이드
- **Markdown 형식**: 가독성과 GitHub 호환성

### 5. 설정 파일
- **`pyproject.toml`**: 모든 프로젝트 메타데이터와 도구 설정 통합
- **`.gitignore`**: Python 전용 무시 패턴
- **`mypy.ini`**: 타입 체킹 설정

## 패키지 명명 규칙

### 디렉토리 vs 패키지 이름
- **디렉토리**: `registry-api-v2-client/` (하이픈 사용)
- **Python 패키지**: `registry_api_v2_client` (언더스코어 사용)
- **PyPI 이름**: `registry-api-v2-client` (하이픈 사용 가능)

### 예시
```python
# 설치
pip install registry-api-v2-client

# 임포트
import registry_api_v2_client
from registry_api_v2_client.core import Client
```

## 필수 파일

### 1. `__init__.py`
```python
"""Registry API v2 Client - Python client for Registry API v2."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.client import RegistryClient

__all__ = ["RegistryClient"]
```

### 2. `py.typed`
- 빈 파일로 생성
- 패키지가 타입 힌트를 포함함을 나타냄

### 3. `README.md`
- 프로젝트 설명
- 설치 방법
- 기본 사용법
- 라이선스 정보
- 기여 가이드라인

## 선택적 구성 요소

### CLI 지원
`__main__.py` 파일을 추가하여 CLI 명령어 제공:
```python
# src/registry_api_v2_client/__main__.py
from .cli import main

if __name__ == "__main__":
    main()
```

### 설정 관리
환경 변수나 설정 파일을 위한 `config/` 디렉토리

### 플러그인 시스템
확장 가능한 아키텍처를 위한 `plugins/` 디렉토리

## 모범 사례

1. **모듈화**: 기능을 논리적 단위로 분리
2. **타입 힌트**: 모든 공개 API에 타입 힌트 추가
3. **문서화**: 모든 공개 함수/클래스에 docstring 작성
4. **테스트**: 최소 80% 이상의 코드 커버리지 목표
5. **버전 관리**: Semantic Versioning (SemVer) 준수