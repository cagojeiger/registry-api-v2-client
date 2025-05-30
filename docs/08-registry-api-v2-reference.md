# Docker Registry API v2 엔드포인트 참조

이 문서는 Docker Registry API v2의 주요 엔드포인트와 구현 시 필요한 상세 정보를 제공합니다.

## API 버전 확인

### GET /v2/
레지스트리가 v2 API를 지원하는지 확인

**요청**
```http
GET /v2/ HTTP/1.1
Host: registry.example.com
```

**응답**
```http
HTTP/1.1 200 OK
Content-Type: application/json
```

빈 JSON 객체 `{}` 반환. 401 응답 시 인증 필요.

## 인증

### Bearer Token 인증

**401 응답 예시**
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:library/ubuntu:pull"
```

**토큰 요청**
```http
GET https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/ubuntu:pull,push
Authorization: Basic base64(username:password)
```

**토큰 응답**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IlBZWU86...",
  "expires_in": 300,
  "issued_at": "2023-01-01T00:00:00Z"
}
```

### Basic 인증
```http
Authorization: Basic base64(username:password)
```

## 블롭(Blob) 작업

### HEAD /v2/{name}/blobs/{digest}
블롭 존재 여부 확인

**요청**
```http
HEAD /v2/myapp/blobs/sha256:abc123... HTTP/1.1
Host: registry.example.com
Authorization: Bearer {token}
```

**응답 (존재하는 경우)**
```http
HTTP/1.1 200 OK
Content-Length: 1234567
Docker-Content-Digest: sha256:abc123...
```

**응답 (존재하지 않는 경우)**
```http
HTTP/1.1 404 Not Found
```

### POST /v2/{name}/blobs/uploads/
블롭 업로드 세션 시작

**요청**
```http
POST /v2/myapp/blobs/uploads/ HTTP/1.1
Host: registry.example.com
Authorization: Bearer {token}
```

**응답**
```http
HTTP/1.1 202 Accepted
Location: /v2/myapp/blobs/uploads/uuid123
Docker-Upload-UUID: uuid123
Range: 0-0
```

### PATCH /v2/{name}/blobs/uploads/{uuid}
청크 업로드

**요청**
```http
PATCH /v2/myapp/blobs/uploads/uuid123 HTTP/1.1
Host: registry.example.com
Content-Type: application/octet-stream
Content-Length: 5242880
Content-Range: 0-5242879
Authorization: Bearer {token}

[binary data]
```

**응답**
```http
HTTP/1.1 202 Accepted
Location: /v2/myapp/blobs/uploads/uuid123
Docker-Upload-UUID: uuid123
Range: 0-5242879
```

### PUT /v2/{name}/blobs/uploads/{uuid}?digest={digest}
블롭 업로드 완료

**요청**
```http
PUT /v2/myapp/blobs/uploads/uuid123?digest=sha256:abc123... HTTP/1.1
Host: registry.example.com
Content-Length: 0
Authorization: Bearer {token}
```

**응답**
```http
HTTP/1.1 201 Created
Location: /v2/myapp/blobs/sha256:abc123...
Docker-Content-Digest: sha256:abc123...
```

### 모놀리식 업로드 (단일 요청)
```http
PUT /v2/myapp/blobs/uploads/?digest=sha256:abc123... HTTP/1.1
Host: registry.example.com
Content-Type: application/octet-stream
Content-Length: 1234567
Authorization: Bearer {token}

[binary data]
```

## 매니페스트 작업

### GET /v2/{name}/manifests/{reference}
매니페스트 조회

**요청**
```http
GET /v2/myapp/manifests/latest HTTP/1.1
Host: registry.example.com
Accept: application/vnd.docker.distribution.manifest.v2+json
Authorization: Bearer {token}
```

**응답**
```http
HTTP/1.1 200 OK
Content-Type: application/vnd.docker.distribution.manifest.v2+json
Docker-Content-Digest: sha256:def456...

{
  "schemaVersion": 2,
  "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
  "config": {
    "mediaType": "application/vnd.docker.container.image.v1+json",
    "size": 7023,
    "digest": "sha256:b5b2b2c50720..."
  },
  "layers": [
    {
      "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
      "size": 32654,
      "digest": "sha256:e692418e4200..."
    },
    {
      "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
      "size": 16724,
      "digest": "sha256:3c3a4604a545..."
    }
  ]
}
```

### PUT /v2/{name}/manifests/{reference}
매니페스트 업로드

**요청**
```http
PUT /v2/myapp/manifests/v1.0.0 HTTP/1.1
Host: registry.example.com
Content-Type: application/vnd.docker.distribution.manifest.v2+json
Content-Length: 1234
Authorization: Bearer {token}

{
  "schemaVersion": 2,
  "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
  "config": {...},
  "layers": [...]
}
```

**응답**
```http
HTTP/1.1 201 Created
Location: /v2/myapp/manifests/sha256:def456...
Docker-Content-Digest: sha256:def456...
```

### DELETE /v2/{name}/manifests/{digest}
매니페스트 삭제

**요청**
```http
DELETE /v2/myapp/manifests/sha256:def456... HTTP/1.1
Host: registry.example.com
Authorization: Bearer {token}
```

**응답**
```http
HTTP/1.1 202 Accepted
```

## 태그 작업

### GET /v2/{name}/tags/list
태그 목록 조회

**요청**
```http
GET /v2/myapp/tags/list HTTP/1.1
Host: registry.example.com
Authorization: Bearer {token}
```

**응답**
```json
{
  "name": "myapp",
  "tags": [
    "latest",
    "v1.0.0",
    "v1.0.1"
  ]
}
```

**페이지네이션**
```http
GET /v2/myapp/tags/list?n=10&last=v1.0.0 HTTP/1.1
```

## 카탈로그

### GET /v2/_catalog
레지스트리의 모든 리포지토리 목록

**요청**
```http
GET /v2/_catalog HTTP/1.1
Host: registry.example.com
Authorization: Bearer {token}
```

**응답**
```json
{
  "repositories": [
    "myapp",
    "another-app",
    "third-app"
  ]
}
```

**페이지네이션**
```http
GET /v2/_catalog?n=10&last=myapp HTTP/1.1
```

## 매니페스트 형식

### Manifest V2 Schema 2
```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
  "config": {
    "mediaType": "application/vnd.docker.container.image.v1+json",
    "size": 7023,
    "digest": "sha256:b5b2b2c50720..."
  },
  "layers": [
    {
      "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
      "size": 32654,
      "digest": "sha256:e692418e4200..."
    }
  ]
}
```

### Manifest List (Multi-Platform)
```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
  "manifests": [
    {
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "size": 7143,
      "digest": "sha256:e692418e4200...",
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      }
    },
    {
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "size": 7682,
      "digest": "sha256:5b0bcabd1ed2...",
      "platform": {
        "architecture": "arm64",
        "os": "linux"
      }
    }
  ]
}
```

## 에러 응답

### 표준 에러 형식
```json
{
  "errors": [
    {
      "code": "UNAUTHORIZED",
      "message": "authentication required",
      "detail": {
        "repository": "myapp"
      }
    }
  ]
}
```

### 주요 에러 코드
- `BLOB_UNKNOWN`: 블롭을 찾을 수 없음
- `BLOB_UPLOAD_INVALID`: 잘못된 블롭 업로드
- `DIGEST_INVALID`: 잘못된 다이제스트 형식
- `MANIFEST_BLOB_UNKNOWN`: 매니페스트에 참조된 블롭이 없음
- `MANIFEST_INVALID`: 잘못된 매니페스트
- `MANIFEST_UNKNOWN`: 매니페스트를 찾을 수 없음
- `NAME_INVALID`: 잘못된 리포지토리 이름
- `SIZE_INVALID`: 잘못된 콘텐츠 크기
- `TAG_INVALID`: 잘못된 태그 형식
- `UNAUTHORIZED`: 인증 필요
- `DENIED`: 권한 부족
- `UNSUPPORTED`: 지원하지 않는 작업

## 다이제스트 계산

### SHA256 다이제스트 형식
```
sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b
```

### 계산 방법
```python
import hashlib

def calculate_digest(data: bytes) -> str:
    """SHA256 다이제스트 계산"""
    digest = hashlib.sha256(data).hexdigest()
    return f"sha256:{digest}"
```

## 콘텐츠 타입

### 이미지 관련
- `application/vnd.docker.distribution.manifest.v2+json`: Manifest V2
- `application/vnd.docker.distribution.manifest.list.v2+json`: Manifest List
- `application/vnd.docker.container.image.v1+json`: 이미지 설정
- `application/vnd.docker.image.rootfs.diff.tar.gzip`: 압축된 레이어
- `application/vnd.docker.image.rootfs.diff.tar`: 비압축 레이어

### OCI 호환
- `application/vnd.oci.image.manifest.v1+json`: OCI 매니페스트
- `application/vnd.oci.image.index.v1+json`: OCI 인덱스
- `application/vnd.oci.image.config.v1+json`: OCI 설정
- `application/vnd.oci.image.layer.v1.tar+gzip`: OCI 레이어

## 구현 팁

### 1. 청크 크기
- 권장: 5MB - 10MB
- 최대: 레지스트리별로 다름 (일반적으로 100MB)

### 2. 재시도 정책
- 5xx 에러: 지수 백오프로 재시도
- 429 Too Many Requests: Retry-After 헤더 확인
- 네트워크 에러: 3-5회 재시도

### 3. 동시성
- 블롭 업로드: 3-5개 동시 업로드 권장
- 매니페스트는 모든 블롭 업로드 완료 후

### 4. 캐싱
- Bearer 토큰: expires_in 시간만큼 캐시
- 블롭 존재 여부: 로컬 캐시 활용

### 5. 호환성
- Accept 헤더로 원하는 매니페스트 형식 지정
- 구형 레지스트리는 Schema 1 지원 필요할 수 있음