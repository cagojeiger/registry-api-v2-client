# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

이 프로젝트는 tar 파일 유틸리티와 함께 제공되는 **비동기** Docker Registry API v2 클라이언트 라이브러리입니다. tar 파일 분석 기능(검증, 검사, 매니페스트 추출)과 완전한 Docker Registry API v2 작업(푸시, 풀, 목록, 삭제)을 **비동기 함수형 프로그래밍 접근법**으로 최대 성능을 제공합니다.

## 개발 명령어

```bash
# 의존성 설치
make install                    # 프로덕션 의존성
make dev-install               # 개발 의존성

# 테스트 명령어
make test-unit                 # 단위 테스트만 (레지스트리 불필요)
make test-integration          # 통합 테스트 (레지스트리 필요)
make test-all                  # 모든 테스트 + 커버리지
make test-cov                  # HTML 커버리지 리포트와 함께 테스트
make local-test                # docker-compose 레지스트리와 함께 전체 테스트

# 코드 품질
make lint                      # ruff 린팅 실행
make lint-fix                  # 린팅 문제 자동 수정
make typecheck                 # mypy 타입 검사 실행
make format                    # ruff로 코드 포맷팅
make check                     # 모든 품질 검사 (lint + typecheck + 단위 테스트)

# 레지스트리 관리
make start-registry            # 테스트 레지스트리 컨테이너 시작 (포트 15000)
make stop-registry             # 테스트 레지스트리 컨테이너 중지
make start-registry-compose    # docker-compose로 레지스트리 시작
make stop-registry-compose     # docker-compose로 레지스트리 중지

# 개발 워크플로우
make dev-test                  # 레지스트리 시작, 테스트 실행, 레지스트리 중지
make ci-test                   # CI 테스트 (단위 + 품질 검사)

# 특정 상황을 위한 수동 명령어
uv run pytest tests/test_async_basic.py -v                    # 특정 테스트 파일 실행
uv run pytest tests/test_validator.py::test_function_name -v  # 특정 테스트 실행
uv run pytest -m "not integration"                           # 통합 테스트 제외
REGISTRY_AVAILABLE=true uv run pytest -m integration         # 통합 테스트만

# 문서 생성
uv run pdoc registry_api_v2_client --output-dir docs-api  # API 문서 자동 생성 (한글)

# 빌드 및 정리
uv build                      # 패키지 빌드
make clean                    # 빌드 산물 정리
```

## 아키텍처 개요

### 비동기 함수형 아키텍처

코드베이스는 최적의 I/O 성능을 위해 단일 책임 원칙과 순수 비동기 함수를 가진 **비동기 함수형 프로그래밍 원칙**을 따릅니다:

```
src/registry_api_v2_client/
├── __init__.py          # 메인 비동기 API 내보내기
├── exceptions.py        # RegistryError, TarReadError, ValidationError
├── models.py           # Pydantic 모델 (레거시 tar 검사용)
├── push.py             # 메인 비동기 푸시 API 
├── registry.py         # 메인 비동기 레지스트리 API
├── core/               # 핵심 비동기 컴포넌트
│   ├── types.py        # 불변 데이터 구조 (@dataclass(frozen=True))
│   ├── connectivity.py # 순수 비동기 연결 확인 함수
│   └── session.py      # 비동기 HTTP 세션 관리 (aiohttp)
├── operations/         # 비동기 레지스트리 작업 모듈
│   ├── blobs.py        # 비동기 blob 업로드/다운로드 작업
│   ├── manifests.py    # 비동기 매니페스트 작업 (생성, 업로드, 삭제)
│   ├── repositories.py # 비동기 저장소 목록 작업
│   └── images.py       # 비동기 이미지 정보 및 삭제 작업
├── tar/                # Tar 파일 처리 (스레드 풀에서 실행)
│   ├── processor.py    # Tar 처리 및 매니페스트 생성
│   └── validator.py    # Tar 검증 래퍼
└── utils/              # 레거시 동기 tar 유틸리티
    ├── validator.py    # Tar 검증 및 매니페스트 추출
    └── inspect.py      # 상세 이미지 검사
```

### 비동기 API 사용법

모든 메인 레지스트리 작업은 **비동기 함수**이므로 await를 사용해야 합니다:

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
    
    # 연결 확인
    await check_registry_connectivity(registry_url)
    
    # 저장소 동시 목록 조회
    repos = await list_repositories(registry_url)
    
    # 여러 저장소 정보 동시 조회
    tasks = [get_image_info(registry_url, repo, "latest") for repo in repos]
    results = await asyncio.gather(*tasks)

# 비동기 코드 실행
asyncio.run(main())
```

### 핵심 데이터 타입

라이브러리는 함수형 프로그래밍을 위해 불변 데이터클래스를 사용합니다:

- **RegistryConfig**: 레지스트리 연결 설정 (고정된 데이터클래스)
- **BlobInfo**: Blob 메타데이터 (digest, size, media type) 
- **ManifestInfo**: config와 layer를 포함한 완전한 매니페스트 정보
- **RequestResult**: status, headers, data를 포함한 HTTP 요청 결과
- **UploadSession**: Blob 업로드 세션 정보

### 주요 비동기 API 함수

**푸시 작업**:
- `async push_docker_tar()`: 동시 blob 업로드로 tar 파일을 레지스트리에 완전 푸시
- `async check_registry_connectivity()`: 레지스트리 접근 가능성 확인

**레지스트리 작업**:
- `async list_repositories()`: 모든 저장소 목록 조회
- `async list_tags()`: 저장소의 태그 목록 조회
- `async get_manifest()`: 이미지 매니페스트 조회
- `async get_image_info()`: 상세 이미지 정보 조회
- `async delete_image()`: 태그로 이미지 삭제
- `async delete_image_by_digest()`: digest로 이미지 삭제

### 비동기 성능 이점

1. **동시 작업**: 여러 네트워크 요청을 동시에 실행
2. **논블로킹 I/O**: 네트워크/디스크 I/O 대기 중에 CPU가 다른 작업 수행
3. **Blob 업로드 동시성**: 모든 이미지 레이어를 병렬로 업로드
4. **스레드 풀 통합**: 파일 I/O 작업이 스레드 풀에서 실행되어 블로킹 방지

성능 개선 예시:
- 순차 호출: 5개 작업에 ~0.10초
- 동시 호출: 5개 작업에 ~0.02초 (5배 빠름)

### 주요 설계 원칙

1. **비동기 함수형 아키텍처**: 순수 비동기 함수, 불변 데이터 구조, 동시 실행
2. **단일 책임**: 각 모듈/함수는 하나의 명확한 비동기 목적을 가짐
3. **타입 안전성**: 타입 힌트와 Pydantic 모델의 광범위한 사용
4. **메모리 효율성**: 청크 blob 업로드 (5MB 청크), aiohttp로 스트리밍
5. **오류 처리**: 컨텍스트가 포함된 포괄적인 비동기 예외 계층
6. **내부 함수 숨김**: 내부 구현 함수는 `_` 접두사를 사용하여 공개 API에서 숨김
7. **한글 문서화**: 모든 공개 API 함수는 한글 docstring과 상세한 경로 예시 제공

### 레지스트리 프로토콜 구현

- **Docker Registry API v2 호환**: 푸시/풀 프로토콜의 완전한 비동기 구현
- **동시 blob 처리**: 청크 지원과 digest 검증을 통한 다중 blob 업로드
- **비동기 매니페스트 작업**: 적절한 digest 계산을 통한 Docker v2 스키마
- **세션 관리**: 연결 풀링과 재시도 전략을 가진 aiohttp

### 테스트 전략

- **비동기 단위 테스트**: 포괄적인 비동기 모킹을 가진 pytest-asyncio (외부 의존성 없음)
- **통합 테스트**: 포트 15000의 Docker 레지스트리를 사용한 실제 비동기 레지스트리 작업
- **테스트 격리**: 각 통합 테스트는 충돌을 피하기 위해 고유한 저장소 이름 사용
- **비동기 픽스처**: 적절한 비동기 테스트 설정을 위한 `@pytest_asyncio.fixture`
- **성능 테스트**: 동시 vs 순차 작업 비교
- **합성 데이터**: 결정적인 비동기 테스트를 위한 생성된 tar 파일
- **커버리지**: HTML 출력을 가진 완전한 비동기 커버리지 보고 (목표: 85%+)
- **병렬 실행**: CI에서 충돌 없이 동시 실행되도록 설계된 테스트

## 중요한 구현 참고사항

1. **비동기 컨텍스트**: 모든 메인 API 함수는 비동기이므로 await해야 함
2. **동시성**: 최대 처리량을 위해 blob 업로드가 동시에 발생  
3. **스레드 풀**: 이벤트 루프 블로킹을 피하기 위해 파일 I/O 작업이 스레드 풀에서 실행
4. **레지스트리 설정**: 기본 레지스트리는 충돌을 피하기 위해 포트 15000에서 실행 (5000이 아님)
5. **세션 관리**: 적절한 연결 풀링과 타임아웃 처리를 가진 aiohttp 사용
6. **오류 컨텍스트**: 모든 레지스트리 오류에 비동기 컨텍스트와 제안 포함
7. **Docker Registry API v2 프로토콜**: 적절한 2단계 blob 업로드 (POST로 시작, PUT으로 완료)
8. **원본 태그 보존**: Docker tar 파일 태그의 자동 추출 및 보존
9. **메모리 효율성**: 대용량 파일을 위한 스트리밍과 5MB 청크 업로드
10. **예외 체이닝**: 디버깅을 위한 적절한 `from e` 체이닝을 사용하는 모든 예외
11. **자동 문서 생성**: pre-commit 훅이 코드 변경 시 한글 API 문서를 자동 생성
12. **내부 함수 규칙**: `operations/`, `core/` 폴더의 헬퍼 함수는 `_함수명` 형태로 명명

## Docker 레지스트리 설정

개발 및 테스트를 위해 포함된 Docker 레지스트리를 사용하세요:

```bash
# 선호 방법: docker-compose 사용
make start-registry-compose     # http://localhost:15000에서 레지스트리 시작
make stop-registry-compose      # 중지 및 정리

# 대안: 직접 docker 명령어  
make start-registry             # 테스트 컨테이너 시작
make stop-registry              # 테스트 컨테이너 중지

# 수동 docker-compose
docker compose up -d            # 레지스트리 시작
docker compose down             # 레지스트리 중지
```

**레지스트리 설정**:
- **포트**: 15000 (표준 5000이 아님) 충돌 방지용
- **삭제 활성화**: `REGISTRY_STORAGE_DELETE_ENABLED=true`
- **상태 검사**: 레지스트리가 `/v2/` 엔드포인트에서 응답
- **데이터 지속성**: 명명된 볼륨 `registry_data` 사용

## 문서 구조

- **README.md**: 사용 예제가 포함된 한국어 주요 문서
- **docs/development-guide.md**: 포괄적인 개발 설정 및 사용 가이드
- **docs/api-reference.md**: 모든 함수와 타입이 포함된 완전한 API 레퍼런스  
- **docs/architecture.md**: 비동기 함수형 아키텍처와 성능에 대한 심화 분석

## 비동기 사용 예제

`examples/` 디렉토리 참조:
- `async_example.py`: 기본 비동기 작업
- `performance_comparison.py`: 동시 vs 순차 호출 성능 비교