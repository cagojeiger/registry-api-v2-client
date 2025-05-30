# 로컬 Registry 개발 환경 설정

이 문서는 Registry API v2 클라이언트 개발을 위한 로컬 Docker Registry 설정 방법을 설명합니다.

## 개요

Registry API v2 클라이언트 개발 및 테스트를 위해 로컬 Docker Registry를 설정합니다. 실제 레지스트리 환경에서 API 동작을 검증하고 통합 테스트를 수행할 수 있습니다.

## 로컬 Registry 설정

### 1. Docker Compose를 통한 Registry 시작

프로젝트 루트에 `docker-compose.yml` 파일이 준비되어 있습니다:

```yaml
services:
  registry:
    image: registry:2
    container_name: local-registry
    ports:
      - "5000:5000"
    volumes:
      - registry_data:/var/lib/registry
    environment:
      REGISTRY_STORAGE_DELETE_ENABLED: "true"
      REGISTRY_HTTP_ADDR: "0.0.0.0:5000"
    restart: unless-stopped

volumes:
  registry_data:
    driver: local
```

### 2. Registry 시작 및 관리

```bash
# Registry 시작
docker compose up -d

# Registry 상태 확인
docker compose ps

# Registry 로그 확인
docker compose logs registry

# Registry 정지
docker compose down

# Registry 및 데이터 완전 삭제
docker compose down -v
```

### 3. Registry 동작 확인

```bash
# API 엔드포인트 테스트
curl http://localhost:5000/v2/

# 응답: {}
```

## Registry 사용법

### 1. 이미지 Push 테스트

```bash
# 테스트용 이미지 준비
docker pull alpine:latest
docker tag alpine:latest localhost:5000/test/alpine:latest

# 로컬 registry에 push
docker push localhost:5000/test/alpine:latest
```

### 2. Registry API 직접 호출

```bash
# 카탈로그 조회
curl http://localhost:5000/v2/_catalog

# 태그 목록 조회
curl http://localhost:5000/v2/test/alpine/tags/list

# 매니페스트 조회
curl -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
     http://localhost:5000/v2/test/alpine/manifests/latest
```

## 개발 설정

### 1. 환경 변수 설정

개발 중 사용할 Registry URL을 환경 변수로 설정:

```bash
# .env 파일 또는 개발 환경
export REGISTRY_URL=http://localhost:5000
export REGISTRY_INSECURE=true  # HTTP 사용 시
```

### 2. 클라이언트 코드에서 사용

```python
from registry_api_v2_client import RegistryClient

# 로컬 registry 연결
client = RegistryClient(
    registry_url="http://localhost:5000",
    insecure=True  # HTTP 사용 시
)

# API 호출 테스트
repositories = client.list_repositories()
print(repositories)
```

## 테스트 전략

### 1. 단위 테스트 (Mock 사용)

실제 네트워크 호출 없이 빠른 테스트를 위해 Mock을 사용합니다:

```python
import pytest
from unittest.mock import Mock, patch
from registry_api_v2_client import RegistryClient

class TestRegistryClient:
    @patch('requests.get')
    def test_list_repositories(self, mock_get):
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repositories": ["test/alpine", "test/ubuntu"]
        }
        mock_get.return_value = mock_response
        
        # 클라이언트 테스트
        client = RegistryClient("http://mock-registry")
        repos = client.list_repositories()
        
        assert repos == ["test/alpine", "test/ubuntu"]
        mock_get.assert_called_once_with(
            "http://mock-registry/v2/_catalog",
            headers={"Accept": "application/json"}
        )
```

### 2. 통합 테스트 (실제 Registry 사용)

로컬 Registry를 사용한 전체 워크플로우 테스트:

```python
import pytest
from registry_api_v2_client import RegistryClient

@pytest.mark.integration
class TestRegistryIntegration:
    @pytest.fixture
    def registry_client(self):
        return RegistryClient(
            registry_url="http://localhost:5000",
            insecure=True
        )
    
    def test_full_workflow(self, registry_client):
        # 실제 Registry에 대한 통합 테스트
        # 1. 이미지 push
        # 2. 목록 조회
        # 3. 매니페스트 조회
        # 4. 이미지 pull
        pass
```

### 3. 테스트 실행

```bash
# 단위 테스트만 실행 (빠름)
pytest tests/ -m "not integration"

# 통합 테스트 포함 (Registry 필요)
docker compose up -d
pytest tests/
docker compose down
```

## Mock 라이브러리 추천

### 1. responses 라이브러리

HTTP 요청을 쉽게 Mock할 수 있습니다:

```python
import responses
from registry_api_v2_client import RegistryClient

@responses.activate
def test_with_responses():
    # Mock 응답 등록
    responses.add(
        responses.GET,
        "http://test-registry/v2/_catalog",
        json={"repositories": ["test/app"]},
        status=200
    )
    
    client = RegistryClient("http://test-registry")
    repos = client.list_repositories()
    assert repos == ["test/app"]
```

### 2. httpx mock (httpx 사용 시)

```python
import httpx
from unittest.mock import patch

def test_with_httpx_mock():
    with patch('httpx.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"repositories": []}
        
        # 테스트 실행
        pass
```

## 문제 해결

### 1. 포트 충돌

포트 5000이 사용 중인 경우:

```yaml
# docker-compose.yml 수정
ports:
  - "5001:5000"  # 다른 포트 사용
```

### 2. 권한 문제

Docker 실행 권한 확인:

```bash
# Docker 그룹에 사용자 추가 (Linux)
sudo usermod -aG docker $USER

# 재로그인 후 테스트
docker ps
```

### 3. 데이터 초기화

Registry 데이터 완전 삭제:

```bash
docker compose down -v
docker volume prune -f
```

## 보안 고려사항

- 개발용으로만 사용 (HTTP, 인증 없음)
- 프로덕션에서는 HTTPS와 인증 필수
- 로컬 네트워크에서만 접근 가능하도록 설정