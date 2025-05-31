# Registry API v2 Client - Tests

이 디렉토리에는 Registry API v2 Client 라이브러리의 테스트 코드가 포함되어 있습니다.

## 테스트 구조

```
tests/
├── conftest.py              # Pytest 설정 및 공통 fixtures
├── test_push.py            # Push 기능 단위 테스트
├── test_registry.py        # Registry 조회/삭제 기능 단위 테스트
├── test_integration.py     # 통합 테스트 (실제 레지스트리 필요)
├── test_inspect.py         # 기존 inspect 기능 테스트
├── test_validator.py       # 기존 validator 기능 테스트
└── README.md              # 이 파일
```

## 테스트 유형

### 1. Unit Tests (단위 테스트)
- **파일**: `test_push.py`, `test_registry.py`
- **설명**: 개별 함수의 동작을 mock을 사용하여 테스트
- **특징**: 
  - 외부 의존성 없음 (레지스트리 불필요)
  - 빠른 실행
  - 모든 에러 케이스 커버

### 2. Integration Tests (통합 테스트)
- **파일**: `test_integration.py`
- **설명**: 실제 레지스트리와의 전체 워크플로우 테스트
- **특징**:
  - 실제 레지스트리 필요
  - 실제 네트워크 통신
  - End-to-end 시나리오 검증

## 테스트 실행 방법

### 사전 준비

1. **테스트 의존성 설치**:
   ```bash
   uv add --dev pytest pytest-cov pytest-mock
   ```

2. **레지스트리 시작** (통합 테스트용):
   ```bash
   docker-compose up -d
   ```

### 모든 테스트 실행

```bash
# 프로젝트 루트에서
uv run pytest

# 또는 상세한 출력
uv run pytest -v
```

### 단위 테스트만 실행

```bash
# 통합 테스트 제외
uv run pytest -m "not integration"

# 특정 파일만
uv run pytest tests/test_push.py
uv run pytest tests/test_registry.py
```

### 통합 테스트만 실행

```bash
# 레지스트리가 실행 중이어야 함
uv run pytest -m integration

# 또는 특정 파일
uv run pytest tests/test_integration.py
```

### 커버리지와 함께 실행

```bash
# 커버리지 측정
uv run pytest --cov=src/registry_api_v2_client

# 커버리지 리포트 생성
uv run pytest --cov=src/registry_api_v2_client --cov-report=html
```

### 특정 테스트 실행

```bash
# 특정 테스트 클래스
uv run pytest tests/test_push.py::TestCheckRegistryConnectivity

# 특정 테스트 메서드
uv run pytest tests/test_push.py::TestCheckRegistryConnectivity::test_successful_connectivity

# 패턴으로 필터링
uv run pytest -k "connectivity"
uv run pytest -k "push and not integration"
```

## 환경 변수

### 통합 테스트 설정

```bash
# 다른 레지스트리 사용
export REGISTRY_URL=http://localhost:5000

# 타임아웃 설정
export TEST_TIMEOUT=60

# 통합 테스트 실행
uv run pytest -m integration
```

### 테스트 모드별 실행

```bash
# 빠른 테스트만 (단위 테스트)
uv run pytest -m "not slow and not integration"

# 느린 테스트 포함
uv run pytest -m "not integration"

# 모든 테스트 (레지스트리 필요)
uv run pytest
```

## 테스트 세부 내용

### test_push.py

**TestCheckRegistryConnectivity**:
- 성공적인 연결 확인
- 인증 필요한 레지스트리 처리
- v2 API 미지원 레지스트리 처리
- 네트워크 연결 오류 처리

**TestPushBlobFromTar**:
- 기존 블롭 존재 확인
- 작은 블롭 업로드 (단일 PUT)
- 대용량 블롭 업로드 (청크 PATCH)
- tar에서 블롭 누락 오류
- 다이제스트 불일치 오류

**TestPushManifest**:
- 성공적인 매니페스트 업로드
- 다이제스트 헤더 없는 응답 처리

**TestPushDockerTar**:
- 전체 푸시 워크플로우
- 파일 존재하지 않음 오류
- 디렉토리 경로 오류
- 연결 실패 처리

### test_registry.py

**TestListRepositories**:
- 성공적인 저장소 목록 조회
- 빈 목록 처리
- 응답 키 누락 처리
- 요청 오류 및 JSON 파싱 오류

**TestListTags**:
- 성공적인 태그 목록 조회
- null 태그 처리
- 누락된 키 처리

**TestGetManifest**:
- 성공적인 매니페스트 조회
- 다이제스트 헤더 처리

**TestGetImageInfo**:
- 완전한 이미지 정보 조회
- 설정 없는 매니페스트 처리
- 설정 요청 오류 처리

**TestDeleteImage & TestDeleteImageByDigest**:
- 성공적인 이미지 삭제
- 다이제스트 누락 오류
- 삭제 요청 오류

### test_integration.py

**TestRegistryIntegration**:
- 레지스트리 연결 확인
- 빈 레지스트리 목록 조회
- 전체 워크플로우 (푸시→조회→삭제)
- 동일 이미지 재푸시 (멱등성)
- 다중 태그 지원
- 다이제스트로 삭제
- 존재하지 않는 이미지 처리

**TestTarValidationIntegration**:
- 잘못된 tar 파일 처리
- 빈 tar 파일 처리
- 매니페스트 없는 tar 파일 처리

## 모범 사례

### 새 테스트 작성시

1. **단위 테스트 우선**: 새 기능은 먼저 단위 테스트로 커버
2. **Mock 사용**: 외부 의존성은 mock으로 대체
3. **에러 케이스 포함**: 정상 케이스뿐만 아니라 오류 상황도 테스트
4. **통합 테스트 추가**: 중요한 워크플로우는 통합 테스트로 검증

### 테스트 실행 전략

```bash
# 개발 중: 빠른 피드백을 위해 단위 테스트만
uv run pytest -m "not integration" --tb=line

# 커밋 전: 모든 단위 테스트 + 커버리지
uv run pytest -m "not integration" --cov=src/registry_api_v2_client

# PR 전: 전체 테스트 스위트
docker-compose up -d
uv run pytest --cov=src/registry_api_v2_client
docker-compose down
```

### CI/CD 설정 예시

```yaml
# GitHub Actions
- name: Run unit tests
  run: uv run pytest -m "not integration" --cov=src/registry_api_v2_client

- name: Start registry
  run: docker-compose up -d

- name: Run integration tests
  run: uv run pytest -m integration

- name: Stop registry
  run: docker-compose down
```

## 문제 해결

### 일반적인 오류

1. **레지스트리 연결 실패**:
   ```bash
   # 레지스트리 상태 확인
   curl http://localhost:15000/v2/
   
   # Docker Compose 로그 확인
   docker-compose logs registry
   ```

2. **Import 오류**:
   ```bash
   # PYTHONPATH 설정
   export PYTHONPATH=src:$PYTHONPATH
   
   # 또는 editable install
   uv pip install -e .
   ```

3. **권한 오류**:
   ```bash
   # 파일 권한 확인
   chmod -R 755 tests/
   ```

### 테스트 디버깅

```bash
# 특정 테스트 디버그 모드
uv run pytest tests/test_push.py::test_specific -v -s --tb=long

# 실패시 즉시 중단
uv run pytest -x

# 로그 출력 포함
uv run pytest -s --log-cli-level=DEBUG
```