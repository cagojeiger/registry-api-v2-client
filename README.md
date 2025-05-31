# Registry API v2 Client

고성능 비동기 Docker Registry API v2 클라이언트 라이브러리

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## 특징

- **🚀 비동기 우선 설계**: asyncio 기반 고성능 동시 작업 (최대 5배 성능 향상)
- **🔧 함수형 프로그래밍**: 불변 데이터 구조와 순수 함수로 안정성 보장
- **⚡ 동시 blob 업로드**: 모든 레이어 병렬 업로드로 최대 처리량 달성
- **🏷️ 원본 태그 보존**: Docker tar 파일의 원본 태그 정보 자동 추출 및 보존
- **💾 메모리 효율적**: 청크 기반 스트리밍으로 대용량 파일 처리 (5MB 청크)
- **🛡️ 완전한 타입 안전성**: 포괄적인 타입 힌트와 런타임 검증
- **📚 한글 문서화**: 모든 API 함수 한국어 문서 및 예제 제공
- **🧪 자동 테스트**: 94개 테스트로 85%+ 커버리지 달성

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
    list_tags,
    get_image_info,
    push_docker_tar_with_original_tags,
    extract_original_tags,
    validate_docker_tar
)

async def main():
    registry_url = "http://localhost:15000"
    
    # 1. 레지스트리 연결 확인
    accessible = await check_registry_connectivity(registry_url)
    print(f"✅ 레지스트리 접근 가능: {accessible}")
    
    # 2. tar 파일 검증 (동기 함수)
    tar_file = "my-image.tar"
    from pathlib import Path
    if validate_docker_tar(Path(tar_file)):
        print(f"✅ 유효한 Docker tar 파일: {tar_file}")
        
        # 원본 태그 추출
        original_tags = extract_original_tags(tar_file)
        print(f"📦 발견된 태그: {original_tags}")
    
    # 3. Docker tar 파일 푸시 (지정된 태그)
    digest = await push_docker_tar(
        tar_file,           # Docker tar 파일 경로
        registry_url,       # 레지스트리 URL
        "myapp",           # 저장소 이름
        "v1.0.0"           # 태그
    )
    print(f"🚀 업로드 완료: {digest}")
    
    # 4. 원본 태그로 푸시 (tar 파일에서 태그 자동 추출)
    if original_tags:
        digest = await push_docker_tar_with_original_tags(
            tar_file,
            registry_url
        )
        print(f"🏷️ 원본 태그로 푸시 완료: {digest}")
    
    # 5. 저장소 목록 조회
    repos = await list_repositories(registry_url)
    print(f"📂 저장소 목록: {repos}")
    
    # 6. 특정 저장소의 태그 목록 조회
    if repos:
        tags = await list_tags(registry_url, repos[0])
        print(f"🏷️ {repos[0]} 태그: {tags}")
        
        # 7. 이미지 상세 정보 조회
        if tags:
            image_info = await get_image_info(registry_url, repos[0], tags[0])
            print(f"ℹ️ 이미지 정보: {image_info.digest} ({image_info.size:,} bytes)")

# 비동기 코드 실행
asyncio.run(main())
```

### 동시 작업 예제 (고성능)

```python
import time
from registry_api_v2_client import delete_image

async def concurrent_example():
    registry_url = "http://localhost:15000"
    
    # 여러 이미지 동시 푸시 (병렬 처리)
    start_time = time.time()
    
    push_tasks = [
        push_docker_tar("app1.tar", registry_url, "app1", "latest"),
        push_docker_tar("app2.tar", registry_url, "app2", "latest"),
        push_docker_tar("app3.tar", registry_url, "app3", "latest"),
    ]
    
    # 모든 푸시 작업을 동시 실행 (최대 5배 빠름)
    digests = await asyncio.gather(*push_tasks)
    elapsed = time.time() - start_time
    print(f"⚡ {len(digests)}개 이미지 동시 푸시 완료 ({elapsed:.2f}초)")
    
    # 여러 저장소 정보 동시 조회
    repos = await list_repositories(registry_url)
    info_tasks = [
        get_image_info(registry_url, repo, "latest") 
        for repo in repos[:3]  # 처음 3개 저장소
    ]
    
    image_infos = await asyncio.gather(*info_tasks, return_exceptions=True)
    for repo, info in zip(repos[:3], image_infos):
        if isinstance(info, Exception):
            print(f"❌ {repo}: {info}")
        else:
            print(f"📊 {repo}: {info.size:,} bytes, {len(info.layers)} layers")

asyncio.run(concurrent_example())
```

### tar 파일 검사 예제

```python
from pathlib import Path
from registry_api_v2_client import (
    validate_docker_tar,
    inspect_docker_tar,
    get_tar_manifest,
    extract_original_tags,
    parse_repository_tag
)

# tar 파일 종합 검사
def inspect_tar_file(tar_path: str):
    path = Path(tar_path)
    
    # 1. 기본 검증
    if not validate_docker_tar(path):
        print(f"❌ 유효하지 않은 tar 파일: {tar_path}")
        return
    
    print(f"✅ 유효한 Docker tar 파일: {tar_path}")
    
    # 2. 원본 태그 추출
    tags = extract_original_tags(tar_path)
    print(f"🏷️ 원본 태그: {tags}")
    
    # 3. 태그 파싱
    if tags:
        for tag in tags:
            repo, tag_name = parse_repository_tag(tag)
            print(f"  📦 저장소: {repo}, 태그: {tag_name}")
    
    # 4. 매니페스트 추출
    manifest = get_tar_manifest(path)
    print(f"📋 매니페스트 엔트리 수: {len(manifest)}")
    
    # 5. 상세 검사
    inspect_result = inspect_docker_tar(path)
    print(f"🏗️ 아키텍처: {inspect_result.architecture}")
    print(f"💻 OS: {inspect_result.os}")
    print(f"📏 크기: {inspect_result.size:,} bytes")
    print(f"🥞 레이어 수: {len(inspect_result.layers)}")

# 사용 예제
inspect_tar_file("nginx.tar")
```

## 성능 비교

### 동시 실행의 성능 이점

| 작업 | 순차 실행 | 동시 실행 | 성능 향상 |
|-----|---------|---------|-----------|
| 5개 blob 업로드 | 150초 (30초×5) | 30초 (max) | **5배 빠름** |
| 3개 저장소 조회 | 0.15초 (0.05초×3) | 0.05초 (max) | **3배 빠름** |
| 멀티 이미지 푸시 | 300초 (100초×3) | 100초 (max) | **3배 빠름** |

### 실제 성능 측정 결과

```bash
# examples/performance_comparison.py 실행 결과
$ python examples/performance_comparison.py

순차 작업 (5개 요청):
  소요 시간: 0.089초
  평균 응답: 0.018초

동시 작업 (5개 요청):
  소요 시간: 0.019초  ⚡ 4.7배 빠름!
  평균 응답: 0.019초
```

### 최적화 기술

- **🔄 동시 blob 업로드**: 모든 레이어를 병렬로 업로드하여 네트워크 대역폭 최대 활용
- **💾 스트리밍 처리**: 5MB 청크 단위로 메모리 효율적 업로드
- **🔗 연결 풀링**: aiohttp의 HTTP 연결 재사용으로 오버헤드 최소화
- **🧵 스레드 풀 통합**: 파일 I/O 작업이 이벤트 루프를 차단하지 않음
- **⚡ 동시 요청**: asyncio.gather()로 네트워크 작업 병렬 실행

## 전체 API 레퍼런스

### 🚀 비동기 레지스트리 API

#### 연결 및 푸시 작업
```python
# 레지스트리 연결성 확인
accessible: bool = await check_registry_connectivity(registry_url)

# Docker tar 파일 푸시 (사용자 지정 태그)
digest: str = await push_docker_tar(tar_path, registry_url, repository, tag)

# 원본 태그로 푸시 (tar에서 첫 번째 태그 사용)
digest: str = await push_docker_tar_with_original_tags(tar_path, registry_url)

# 모든 원본 태그로 푸시 (tar의 모든 태그 사용)
digests: list[str] = await push_docker_tar_with_all_original_tags(tar_path, registry_url)
```

#### 저장소 및 이미지 관리
```python
# 저장소 목록 조회
repositories: list[str] = await list_repositories(registry_url)

# 특정 저장소의 태그 목록 조회
tags: list[str] = await list_tags(registry_url, repository)

# 이미지 매니페스트 조회
manifest: ManifestInfo = await get_manifest(registry_url, repository, tag)

# 이미지 상세 정보 조회 (크기, 레이어 등)
info: ManifestInfo = await get_image_info(registry_url, repository, tag)

# 이미지 삭제 (태그 기준)
success: bool = await delete_image(registry_url, repository, tag)

# 이미지 삭제 (digest 기준, 더 안전)
success: bool = await delete_image_by_digest(registry_url, repository, digest)
```

### 📁 동기 tar 파일 유틸리티

#### tar 검증 및 검사
```python
from pathlib import Path

# tar 파일 유효성 검증
is_valid: bool = validate_docker_tar(Path(tar_path))

# tar 파일 상세 검사 (아키텍처, OS, 레이어 등)
inspect_result: ImageInspect = inspect_docker_tar(Path(tar_path))

# tar 파일에서 매니페스트 추출
manifest: list[dict] = get_tar_manifest(Path(tar_path))
```

#### 태그 추출 및 파싱
```python
# tar 파일에서 모든 원본 태그 추출
tags: list[str] = extract_original_tags(tar_path)

# tar 파일에서 주요 태그 추출
primary: tuple[str, str] | None = get_primary_tag(tar_path)  # (repo, tag)

# 저장소:태그 문자열 파싱
repository, tag = parse_repository_tag("nginx:alpine")  # ("nginx", "alpine")
```

### 🛡️ 예외 처리

```python
from registry_api_v2_client import RegistryError, TarReadError, ValidationError

try:
    digest = await push_docker_tar("app.tar", registry_url, "app", "latest")
except ValidationError as e:
    print(f"❌ 잘못된 tar 파일: {e}")
except TarReadError as e:
    print(f"❌ tar 읽기 오류: {e}")
except RegistryError as e:
    print(f"❌ 레지스트리 오류: {e}")
```

### 📊 데이터 타입

```python
from registry_api_v2_client import (
    RegistryConfig,    # 레지스트리 설정
    BlobInfo,          # Blob 메타데이터
    ManifestInfo,      # 매니페스트 정보
    ImageConfig,       # 이미지 설정
    ImageInspect,      # 상세 이미지 정보
    LayerInfo          # 레이어 정보
)
```

## 개발 환경 설정

### 📋 시스템 요구사항

- **Python 3.11+** (3.12 권장) - 최신 타입 힌트 지원
- **Docker** - 로컬 레지스트리 및 테스트용
- **uv** - 빠른 패키지 관리자 ([설치 가이드](https://docs.astral.sh/uv/))

### 🚀 빠른 설정

```bash
# 1. 프로젝트 클론
git clone <repository>
cd registry-api-v2-client

# 2. 개발 환경 설정 (의존성 설치)
make dev-install  # 또는 uv sync --dev

# 3. 로컬 레지스트리 시작 (포트 15000)
make start-registry-compose

# 4. 전체 테스트 실행
make test-all

# 5. 코드 품질 검사
make check  # lint + typecheck + 단위 테스트
```

### 📝 개발 명령어 요약

```bash
# 테스트 관련
make test-unit           # 단위 테스트만 (레지스트리 불필요)
make test-integration    # 통합 테스트 (레지스트리 필요)
make test-all           # 모든 테스트 + 커버리지
make test-cov           # HTML 커버리지 리포트

# 코드 품질
make lint               # ruff 린팅
make lint-fix           # 린팅 문제 자동 수정
make typecheck          # mypy 타입 검사
make format             # 코드 포맷팅
make check              # 전체 품질 검사

# 레지스트리 관리
make start-registry-compose  # 레지스트리 시작
make stop-registry-compose   # 레지스트리 중지

# 문서 생성
uv run pdoc registry_api_v2_client --output-dir docs-api
```

### 🐳 로컬 레지스트리 설정

```bash
# Docker Compose로 레지스트리 시작 (포트 15000)
make start-registry-compose

# 레지스트리 상태 확인
curl http://localhost:15000/v2/
# 응답: {"errors":[{"code":"UNAUTHORIZED",...}]} (정상)

# 저장소 목록 확인 (빈 레지스트리)
curl http://localhost:15000/v2/_catalog
# 응답: {"repositories":[]}

# 레지스트리 정지 및 정리
make stop-registry-compose
```

### 🧪 테스트 전략

- **94개 테스트**: 단위 테스트 + 통합 테스트
- **85%+ 커버리지**: 모든 핵심 기능 커버
- **비동기 테스트**: pytest-asyncio 사용
- **격리된 통합 테스트**: 각 테스트마다 고유 저장소 사용

## 🏗️ 아키텍처 개요

이 클라이언트는 **비동기 함수형 프로그래밍** 원칙을 따르며 최고 성능을 위해 설계되었습니다:

### 핵심 설계 원칙

- **🔒 불변 데이터 구조**: `@dataclass(frozen=True)`로 스레드 안전성 보장
- **🔄 순수 비동기 함수**: 부작용 없는 예측 가능한 동작
- **⚡ 동시 실행 우선**: asyncio를 활용한 최대 성능
- **🧵 스레드 풀 통합**: 파일 I/O가 이벤트 루프를 차단하지 않음
- **📏 단일 책임 원칙**: 각 함수는 하나의 명확한 목적

### 성능 최적화 구조

```python
# 비동기 함수형 설계 예시
async def _upload_all_blobs(config: BlobInfo, layers: list[BlobInfo]) -> None:
    """모든 blob을 동시에 업로드하여 최대 성능 달성"""
    upload_tasks = [
        _upload_blob_with_retry(blob) 
        for blob in [config] + layers
    ]
    await asyncio.gather(*upload_tasks)  # 병렬 실행
```

### 모듈 구조

```
src/registry_api_v2_client/
├── 🚀 push.py              # 메인 비동기 푸시 API
├── 🔍 registry.py          # 메인 비동기 레지스트리 API  
├── core/                   # 핵심 비동기 컴포넌트
│   ├── types.py           # 불변 데이터 구조
│   ├── connectivity.py    # 순수 연결 확인 함수
│   └── session.py         # 비동기 HTTP 세션 관리
├── operations/             # 비동기 레지스트리 작업
│   ├── blobs.py           # 청크 기반 blob 업로드
│   ├── manifests.py       # 매니페스트 생성/업로드
│   ├── repositories.py    # 저장소 목록 조회
│   └── images.py          # 이미지 정보/삭제
├── tar/                    # tar 파일 처리 (스레드 풀)
└── utils/                  # 레거시 동기 유틸리티
```

## 📚 문서

- **[📖 개발 가이드](docs/development-guide.md)**: 완전한 개발 환경 설정 및 사용법
- **[📋 API 레퍼런스](docs/api-reference.md)**: 모든 함수와 데이터 타입 상세 설명  
- **[🏗️ 아키텍처 가이드](docs/architecture.md)**: 비동기 함수형 설계 원칙과 성능 최적화
- **[🤖 자동 생성 API 문서](docs-api/index.html)**: pdoc으로 생성된 실시간 API 문서

## 🐳 Docker tar 파일 생성 및 사용

### Docker 이미지 내보내기

```bash
# 단일 이미지 내보내기
docker save nginx:alpine -o nginx.tar

# 여러 이미지 함께 내보내기
docker save nginx:alpine ubuntu:20.04 -o multi-images.tar

# 태그 여러 개 포함하여 내보내기  
docker tag myapp:latest myapp:v1.0
docker save myapp:latest myapp:v1.0 -o myapp-multi-tag.tar
```

### 원스텝 푸시 스크립트

```bash
# 이미지 내보내기 + 레지스트리 푸시
docker save myapp:latest -o myapp.tar && python -c "
import asyncio
from registry_api_v2_client import push_docker_tar_with_original_tags

async def main():
    try:
        digest = await push_docker_tar_with_original_tags(
            'myapp.tar', 
            'http://localhost:15000'
        )
        print(f'✅ 푸시 완료: {digest}')
    except Exception as e:
        print(f'❌ 푸시 실패: {e}')

asyncio.run(main())
"
```

## 🛠️ 실제 사용 사례

### CI/CD 파이프라인에서 사용

```python
# ci_deploy.py - GitHub Actions나 GitLab CI에서 사용
import asyncio
import os
from registry_api_v2_client import push_docker_tar_with_all_original_tags

async def deploy_to_registry():
    registry_url = os.getenv("REGISTRY_URL", "http://localhost:15000")
    tar_file = os.getenv("TAR_FILE", "app.tar")
    
    try:
        digests = await push_docker_tar_with_all_original_tags(tar_file, registry_url)
        print(f"🚀 {len(digests)}개 태그 배포 완료:")
        for i, digest in enumerate(digests, 1):
            print(f"  {i}. {digest}")
    except Exception as e:
        print(f"❌ 배포 실패: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(deploy_to_registry())
```

### 멀티 환경 배포

```python
# multi_env_deploy.py
async def deploy_to_multiple_environments():
    tar_file = "production-app.tar"
    environments = {
        "staging": "http://staging-registry:5000",
        "production": "http://prod-registry:5000",
        "backup": "http://backup-registry:5000",
    }
    
    # 모든 환경에 동시 배포
    deploy_tasks = [
        push_docker_tar_with_original_tags(tar_file, registry_url)
        for env, registry_url in environments.items()
    ]
    
    results = await asyncio.gather(*deploy_tasks, return_exceptions=True)
    
    for env, result in zip(environments.keys(), results):
        if isinstance(result, Exception):
            print(f"❌ {env}: {result}")
        else:
            print(f"✅ {env}: {result}")
```

## 🔧 고급 설정

### 커스텀 타임아웃 및 재시도

```python
# 큰 이미지나 느린 네트워크를 위한 설정 조정은
# aiohttp ClientSession 설정을 통해 가능
# (내부적으로 적절한 타임아웃이 설정되어 있음)

# 현재 기본 설정:
# - 연결 타임아웃: 10초
# - 읽기 타임아웃: 300초 (5분)
# - 청크 크기: 5MB
```

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

## 🤝 기여하기

이슈와 풀 리퀘스트를 환영합니다! 

### 기여 가이드라인

1. 이슈 생성하여 기능 요청 또는 버그 신고
2. 포크 후 피처 브랜치 생성
3. 테스트 작성 및 통과 확인 (`make test-all`)  
4. 코드 품질 검사 통과 (`make check`)
5. 풀 리퀘스트 생성

### 개발자 빠른 시작

```bash
# 개발 환경 설정
make dev-install
make start-registry-compose

# 개발 - 테스트 - 품질검사 사이클
make test-unit && make lint-fix && make typecheck

# 풀 리퀘스트 전 최종 검사
make check && make test-integration
```

---

## ⚡ 성능과 안정성을 겸비한 Docker Registry API v2 클라이언트

**동시 작업으로 최대 5배 빠른 성능을 경험해보세요!**

- 🚀 **비동기 우선**: 최고 성능 동시 업로드  
- 🛡️ **타입 안전**: 완전한 타입 힌트와 검증
- 📚 **한글 문서**: 상세한 한국어 가이드 제공
- 🧪 **높은 신뢰성**: 94개 테스트, 85%+ 커버리지