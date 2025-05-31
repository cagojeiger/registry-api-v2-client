# Registry API v2 Client

고성능 비동기 Docker Registry API v2 클라이언트 라이브러리

## 특징

- **비동기 우선 설계**: asyncio 기반 고성능 동시 작업
- **함수형 프로그래밍**: 불변 데이터 구조와 순수 함수
- **동시 blob 업로드**: 모든 레이어 병렬 업로드로 최대 처리량 달성
- **원본 태그 보존**: Docker tar 파일의 원본 태그 정보 자동 추출 및 보존
- **메모리 효율적**: 청크 기반 스트리밍으로 대용량 파일 처리
- **완전한 타입 안전성**: 포괄적인 타입 힌트와 런타임 검증

## 빠른 시작

### 설치

```bash
pip install registry-api-v2-client
```

### 기본 사용법

```python
import asyncio
from registry_api_v2_client import (
    check_registry_connectivity,
    push_docker_tar,
    list_repositories,
    push_docker_tar_with_original_tags
)

async def main():
    registry_url = "http://localhost:15000"
    
    # 레지스트리 연결 확인
    accessible = await check_registry_connectivity(registry_url)
    print(f"레지스트리 접근 가능: {accessible}")
    
    # Docker tar 파일 푸시
    digest = await push_docker_tar(
        "my-image.tar",      # Docker tar 파일 경로
        registry_url,        # 레지스트리 URL
        "myapp",            # 저장소 이름
        "v1.0.0"            # 태그
    )
    print(f"업로드 완료: {digest}")
    
    # 원본 태그로 푸시 (tar 파일에서 태그 자동 추출)
    digest = await push_docker_tar_with_original_tags(
        "exported-image.tar",
        registry_url
    )
    print(f"원본 태그로 푸시 완료: {digest}")
    
    # 저장소 목록 조회
    repos = await list_repositories(registry_url)
    print(f"저장소 목록: {repos}")

# 비동기 코드 실행
asyncio.run(main())
```

### 동시 작업 예제

```python
async def concurrent_example():
    registry_url = "http://localhost:15000"
    
    # 여러 이미지 동시 푸시
    push_tasks = [
        push_docker_tar("app1.tar", registry_url, "app1", "latest"),
        push_docker_tar("app2.tar", registry_url, "app2", "latest"),
        push_docker_tar("app3.tar", registry_url, "app3", "latest"),
    ]
    
    # 모든 푸시 작업을 동시 실행
    digests = await asyncio.gather(*push_tasks)
    print(f"{len(digests)}개 이미지 푸시 완료")

asyncio.run(concurrent_example())
```

## 성능 비교

### 순차 vs 동시 실행

```python
# ❌ 순차 실행 (느림)
# 5개 레이어 × 30초 = 150초

# ✅ 동시 실행 (빠름) 
# max(30초) = 30초 (5배 빠름)
```

### 실제 성능 측정

- **동시 blob 업로드**: 네트워크 대역폭 최대 활용
- **메모리 효율성**: 5MB 청크 단위 스트리밍
- **연결 풀링**: HTTP 연결 재사용으로 오버헤드 최소화

## 주요 API 함수

### 연결 및 푸시 작업

```python
# 레지스트리 연결 확인
await check_registry_connectivity(registry_url)

# 지정된 태그로 푸시
await push_docker_tar(tar_path, registry_url, repository, tag)

# 원본 태그로 푸시 (첫 번째 태그)
await push_docker_tar_with_original_tags(tar_path, registry_url)

# 모든 원본 태그로 푸시
await push_docker_tar_with_all_original_tags(tar_path, registry_url)
```

### 저장소 및 이미지 관리

```python
# 저장소 목록 조회
repos = await list_repositories(registry_url)

# 태그 목록 조회  
tags = await list_tags(registry_url, repository)

# 이미지 정보 조회
info = await get_image_info(registry_url, repository, tag)

# 이미지 삭제
success = await delete_image(registry_url, repository, tag)
```

### 태그 추출 (동기 함수)

```python
from registry_api_v2_client import extract_original_tags, get_primary_tag

# tar 파일에서 모든 태그 추출
tags = extract_original_tags("image.tar")
print(f"발견된 태그: {tags}")

# 주요 태그 추출
repo, tag = get_primary_tag("image.tar")
print(f"주요 태그: {repo}:{tag}")
```

## 개발 환경 설정

### 요구사항

- **Python 3.11+** (3.12 권장)
- **Docker** (로컬 레지스트리용)
- **uv** (빠른 패키지 관리자)

### 개발 설정

```bash
# 프로젝트 클론
git clone <repository>
cd registry-api-v2-client

# 개발 의존성 설치
uv sync --dev

# 로컬 레지스트리 시작 (포트 15000)
make start-registry-compose

# 테스트 실행
make test-unit           # 단위 테스트 (빠름)
make test-integration    # 통합 테스트 (레지스트리 필요)

# 코드 품질 검사
make lint typecheck
```

### 로컬 레지스트리

```bash
# Docker Compose로 레지스트리 시작 (포트 15000)
make start-registry-compose

# 레지스트리 연결 테스트
curl http://localhost:15000/v2/

# 레지스트리 정지
make stop-registry-compose
```

## 아키텍처

이 클라이언트는 **비동기 함수형 프로그래밍** 원칙을 따릅니다:

- **불변 데이터 구조**: `@dataclass(frozen=True)` 사용
- **순수 비동기 함수**: 부작용 없는 예측 가능한 동작
- **동시 실행**: asyncio를 활용한 최대 성능
- **스레드 풀 통합**: 파일 I/O 작업이 이벤트 루프를 차단하지 않음

```python
# 설계 예시: 동시 blob 업로드
async def upload_all_blobs(config, layers):
    # 모든 blob을 동시에 업로드
    tasks = [upload_blob(blob) for blob in [config] + layers]
    await asyncio.gather(*tasks)  # 병렬 실행
```

## 문서

- **[개발 가이드](docs/development-guide.md)**: 완전한 개발 환경 설정 및 사용법
- **[API 레퍼런스](docs/api-reference.md)**: 모든 함수와 데이터 타입 상세 설명
- **[아키텍처 가이드](docs/architecture.md)**: 비동기 함수형 설계 원칙과 성능 최적화

## Docker tar 파일 생성

```bash
# Docker 이미지 내보내기
docker save myapp:latest -o myapp.tar

# 클라이언트로 푸시
python -c "
import asyncio
from registry_api_v2_client import push_docker_tar_with_original_tags

async def main():
    digest = await push_docker_tar_with_original_tags('myapp.tar', 'http://localhost:15000')
    print(f'푸시 완료: {digest}')

asyncio.run(main())
"
```

## 예외 처리

```python
from registry_api_v2_client import RegistryError, TarReadError, ValidationError

try:
    digest = await push_docker_tar("image.tar", registry_url, "repo", "tag")
except ValidationError as e:
    print(f"잘못된 tar 파일: {e}")
except TarReadError as e:
    print(f"tar 파일 읽기 오류: {e}")
except RegistryError as e:
    print(f"레지스트리 오류: {e}")
```

## 라이선스

MIT License

## 기여

이슈와 풀 리퀘스트를 환영합니다. 기여하기 전에 개발 가이드를 읽어주세요.

---

**고성능 비동기 Docker Registry API v2 클라이언트로 동시 작업의 힘을 경험해보세요!**