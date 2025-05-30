# Registry API v2 Client 라이브러리 사양서

## 개요

`registry-api-v2-client`는 Docker Registry API v2 스펙을 직접 구현하는 Python 라이브러리입니다. 이 라이브러리의 핵심 목적은 `docker save` 명령으로 저장된 tar 파일을 인증이 없는 registry:2 컨테이너에 직접 푸시할 수 있게 하는 것입니다.

### 주요 특징
- Docker Registry API v2 스펙 준수
- `aiohttp` 라이브러리를 사용한 비동기 Python 구현
- Docker 데몬 없이 독립적으로 작동
- tar 파일에서 직접 이미지 푸시 지원
- 인증 없는 registry:2 컨테이너 전용
- 완전한 비동기(async/await) 지원으로 높은 성능

### 지원 대상
- **지원**: 인증 없이 실행되는 registry:2 컨테이너
  ```bash
  docker run -d -p 5000:5000 --name registry registry:2
  ```
- **미지원**: 인증이 필요한 레지스트리 (Docker Hub, Harbor, ECR, GCR 등)

### 사용 사례
- 로컬 개발 환경에서 이미지 관리
- Air-gapped 환경에서 프라이빗 레지스트리 운영
- CI/CD 파이프라인에서 Docker 데몬 없이 이미지 푸시
- 테스트 환경에서 이미지 백업 및 복원

## 아키텍처

### 핵심 구성 요소

```
registry_api_v2_client/
├── core/
│   ├── registry_client.py    # 메인 클라이언트 클래스
│   ├── manifest.py          # 매니페스트 처리
│   └── blob.py             # 블롭 업로드/다운로드
├── tar/
│   ├── reader.py            # tar 파일 읽기
│   ├── parser.py            # Docker 이미지 구조 파싱
│   └── layer.py             # 레이어 처리
├── utils/
│   ├── digest.py            # SHA256 다이제스트 계산
│   ├── chunked.py           # 청크 업로드 헬퍼
│   └── retry.py             # 재시도 로직
└── exceptions.py            # 커스텀 예외
```

## API 설계

### 1. RegistryClient 클래스

```python
import aiohttp
from typing import Optional, List, Union, Callable, AsyncIterator

class RegistryClient:
    """Docker Registry API v2 비동기 클라이언트 (인증 없는 registry:2 전용)"""
    
    def __init__(
        self,
        registry_url: str,
        timeout: int = 30,
        connector: Optional[aiohttp.TCPConnector] = None
    ):
        """
        Args:
            registry_url: 레지스트리 URL (예: http://localhost:5000)
            timeout: 요청 타임아웃 (초)
            connector: aiohttp 커넥터 (연결 풀링 설정)
        """
        self.registry_url = registry_url.rstrip('/')
        self.timeout = timeout
        self.connector = connector
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def push_tar(
        self,
        tar_path: str,
        repository: str,
        tag: str = "latest",
        progress_callback: Optional[Callable] = None,
        concurrent_uploads: int = 3
    ) -> str:
        """
        Docker save로 생성된 tar 파일을 레지스트리에 푸시
        
        Args:
            tar_path: tar 파일 경로
            repository: 저장소 이름 (예: myapp)
            tag: 태그 이름
            progress_callback: 진행 상황 콜백 함수 (async 함수 가능)
            concurrent_uploads: 동시 업로드 수
            
        Returns:
            매니페스트 다이제스트
        """
        pass
    
    async def check_blob_exists(self, repository: str, digest: str) -> bool:
        """블롭 존재 여부 확인"""
        pass
    
    async def upload_blob(
        self,
        repository: str,
        data: Union[bytes, AsyncIterator[bytes]],
        digest: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """블롭 업로드"""
        pass
    
    async def upload_manifest(
        self,
        repository: str,
        reference: str,
        manifest: dict,
        media_type: str = "application/vnd.docker.distribution.manifest.v2+json"
    ) -> str:
        """매니페스트 업로드"""
        pass
    
    async def get_manifest(
        self,
        repository: str,
        reference: str,
        accept: str = "application/vnd.docker.distribution.manifest.v2+json"
    ) -> dict:
        """매니페스트 조회"""
        pass
    
    async def delete_manifest(self, repository: str, digest: str) -> None:
        """매니페스트 삭제"""
        pass
    
    async def list_tags(self, repository: str) -> List[str]:
        """태그 목록 조회"""
        pass
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()
    
    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
```

### 2. TarImageReader 클래스

```python
import aiofiles
import asyncio
import tarfile
from typing import AsyncIterator

class TarImageReader:
    """Docker save tar 파일 비동기 리더"""
    
    def __init__(self, tar_path: str):
        """
        Args:
            tar_path: tar 파일 경로
        """
        self.tar_path = tar_path
        self._tar_file = None
    
    async def get_manifest(self) -> dict:
        """tar 파일의 manifest.json 반환"""
        pass
    
    async def get_config(self, config_digest: str) -> bytes:
        """이미지 설정 JSON 반환"""
        pass
    
    async def get_layer_stream(self, layer_path: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """레이어 tar 파일 스트림 반환 (비동기 이터레이터)"""
        pass
    
    async def get_repositories(self) -> dict:
        """repositories 정보 반환"""
        pass
    
    async def extract_image_info(self) -> ImageInfo:
        """이미지 정보 추출"""
        pass
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()
    
    async def close(self):
        """리소스 정리"""
        if self._tar_file:
            await asyncio.get_event_loop().run_in_executor(
                None, self._tar_file.close
            )
```

### 3. 데이터 모델

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class ImageInfo:
    """Docker 이미지 정보"""
    repository: str
    tag: str
    config_digest: str
    layers: List[LayerInfo]
    architecture: str
    os: str
    created: datetime
    size: int

@dataclass
class LayerInfo:
    """레이어 정보"""
    digest: str
    size: int
    media_type: str
    tar_path: str  # tar 파일 내 경로

@dataclass
class ManifestV2:
    """Docker Manifest V2"""
    schema_version: int = 2
    media_type: str = "application/vnd.docker.distribution.manifest.v2+json"
    config: BlobDescriptor
    layers: List[BlobDescriptor]

@dataclass
class BlobDescriptor:
    """블롭 디스크립터"""
    media_type: str
    size: int
    digest: str
```

## 구현 상세

### 1. push_tar 메서드 플로우

```python
async def push_tar(
    self,
    tar_path: str,
    repository: str,
    tag: str = "latest",
    concurrent_uploads: int = 3
) -> str:
    """
    1. tar 파일 읽기 및 파싱
    2. 각 레이어 비동기 동시 업로드
       - 블롭 존재 확인 (HEAD /v2/{repo}/blobs/{digest})
       - 존재하지 않으면 업로드
    3. 설정 블롭 업로드
    4. 매니페스트 생성 및 업로드
    5. 태그 설정
    """
    # 1. tar 파일 읽기
    async with TarImageReader(tar_path) as reader:
        image_info = await reader.extract_image_info()
        
        # 2. 레이어 동시 업로드 (세마포어로 동시성 제한)
        semaphore = asyncio.Semaphore(concurrent_uploads)
        
        async def upload_layer(layer: LayerInfo) -> dict:
            async with semaphore:
                # 블롭 존재 확인
                if not await self.check_blob_exists(repository, layer.digest):
                    # 레이어 스트림 가져오기
                    layer_stream = reader.get_layer_stream(layer.tar_path)
                    await self.upload_blob(
                        repository, 
                        layer_stream, 
                        layer.digest,
                        progress_callback
                    )
                
                return {
                    "mediaType": layer.media_type,
                    "size": layer.size,
                    "digest": layer.digest
                }
        
        # 모든 레이어 동시 업로드
        upload_tasks = [upload_layer(layer) for layer in image_info.layers]
        uploaded_layers = await asyncio.gather(*upload_tasks)
        
        # 3. 설정 업로드
        config_data = await reader.get_config(image_info.config_digest)
        if not await self.check_blob_exists(repository, image_info.config_digest):
            await self.upload_blob(
                repository, 
                config_data, 
                image_info.config_digest,
                progress_callback
            )
        
        # 4. 매니페스트 생성
        manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "size": len(config_data),
                "digest": image_info.config_digest
            },
            "layers": uploaded_layers
        }
        
        # 5. 매니페스트 업로드
        return await self.upload_manifest(repository, tag, manifest)
```

### 2. 블롭 업로드 구현

```python
async def upload_blob(
    self,
    repository: str,
    data: Union[bytes, AsyncIterator[bytes]],
    digest: str,
    progress_callback: Optional[Callable] = None
) -> str:
    """
    비동기 청크 업로드:
    1. POST /v2/{repo}/blobs/uploads/ - 업로드 세션 시작
    2. PATCH /v2/{repo}/blobs/uploads/{uuid} - 청크 업로드 (반복)
    3. PUT /v2/{repo}/blobs/uploads/{uuid}?digest={digest} - 업로드 완료
    """
    # 1. 업로드 세션 시작
    async with self.session.post(
        f"{self.registry_url}/v2/{repository}/blobs/uploads/"
    ) as resp:
        resp.raise_for_status()
        upload_url = resp.headers["Location"]
        if not upload_url.startswith("http"):
            upload_url = f"{self.registry_url}{upload_url}"
    
    # 2. 비동기 청크 업로드
    chunk_size = 5 * 1024 * 1024  # 5MB
    uploaded_bytes = 0
    total_size = 0  # 총 크기 (알려진 경우)
    
    # 데이터가 AsyncIterator인 경우
    if hasattr(data, '__aiter__'):
        async for chunk in data:
            # 청크 업로드
            async with self.session.patch(
                upload_url,
                data=chunk,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(len(chunk))
                }
            ) as resp:
                resp.raise_for_status()
                upload_url = resp.headers["Location"]
                if not upload_url.startswith("http"):
                    upload_url = f"{self.registry_url}{upload_url}"
            
            uploaded_bytes += len(chunk)
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(uploaded_bytes, total_size, f"Uploading {digest[:12]}...")
                else:
                    progress_callback(uploaded_bytes, total_size, f"Uploading {digest[:12]}...")
    
    # 데이터가 bytes인 경우
    else:
        total_size = len(data)
        # bytes를 청크로 분할
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            async with self.session.patch(
                upload_url,
                data=chunk,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(len(chunk))
                }
            ) as resp:
                resp.raise_for_status()
                upload_url = resp.headers["Location"]
                if not upload_url.startswith("http"):
                    upload_url = f"{self.registry_url}{upload_url}"
            
            uploaded_bytes += len(chunk)
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(uploaded_bytes, total_size, f"Uploading {digest[:12]}...")
                else:
                    progress_callback(uploaded_bytes, total_size, f"Uploading {digest[:12]}...")
    
    # 3. 업로드 완료
    final_url = f"{upload_url}&digest={digest}" if "?" in upload_url else f"{upload_url}?digest={digest}"
    async with self.session.put(
        final_url,
        headers={"Content-Length": "0"}
    ) as resp:
        resp.raise_for_status()
    
    return digest
```

### 3. HTTP 요청 처리

```python
async def _request(
    self,
    method: str,
    path: str,
    **kwargs
) -> aiohttp.ClientResponse:
    """기본 HTTP 요청 (인증 없음)"""
    url = f"{self.registry_url}{path}"
    
    async with self.session.request(
        method, url, **kwargs
    ) as resp:
        resp.raise_for_status()
        return resp

async def check_blob_exists(self, repository: str, digest: str) -> bool:
    """블롭 존재 여부 확인"""
    try:
        async with self.session.head(
            f"{self.registry_url}/v2/{repository}/blobs/{digest}"
        ) as resp:
            return resp.status == 200
    except aiohttp.ClientError:
        return False

async def get_manifest(
    self,
    repository: str,
    reference: str,
    accept: str = "application/vnd.docker.distribution.manifest.v2+json"
) -> dict:
    """매니페스트 조회"""
    async with self.session.get(
        f"{self.registry_url}/v2/{repository}/manifests/{reference}",
        headers={"Accept": accept}
    ) as resp:
        resp.raise_for_status()
        return await resp.json()
```

## 사용 예제

### 기본 사용법

```python
import asyncio
from registry_api_v2_client import RegistryClient

async def main():
    # 로컬 registry:2 컨테이너에 연결
    async with RegistryClient("http://localhost:5000") as client:
        # tar 파일 푸시
        digest = await client.push_tar(
            tar_path="/path/to/image.tar",
            repository="myapp",
            tag="v1.0.0"
        )
        print(f"Pushed image with digest: {digest}")

# 실행
asyncio.run(main())
```

### 진행 상황 추적

```python
async def progress_callback(current: int, total: int, message: str):
    percent = (current / total) * 100 if total > 0 else 0
    print(f"{message}: {percent:.1f}%")

async def main():
    async with RegistryClient("http://localhost:5000") as client:
        digest = await client.push_tar(
            tar_path="/path/to/image.tar",
            repository="myapp",
            tag="v1.0.0",
            progress_callback=progress_callback,
            concurrent_uploads=5  # 동시 업로드 수 증가
        )

asyncio.run(main())
```

### 여러 이미지 동시 푸시

```python
async def push_multiple_images():
    async with RegistryClient("http://localhost:5000") as client:
        # 여러 이미지 동시 푸시
        tasks = [
            client.push_tar("/path/to/app1.tar", "app1", "latest"),
            client.push_tar("/path/to/app2.tar", "app2", "latest"),
            client.push_tar("/path/to/app3.tar", "app3", "latest"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Failed to push image {i+1}: {result}")
            else:
                print(f"Successfully pushed image {i+1}: {result}")

asyncio.run(push_multiple_images())
```

### 커넥션 풀 최적화

```python
import aiohttp

async def optimized_push():
    # 커넥션 풀 설정
    connector = aiohttp.TCPConnector(
        limit=100,  # 전체 연결 수 제한
        limit_per_host=30,  # 호스트당 연결 수 제한
        keepalive_timeout=30
    )
    
    async with RegistryClient(
        "http://localhost:5000",
        connector=connector
    ) as client:
        # 대량의 이미지 푸시
        for i in range(100):
            await client.push_tar(
                f"/path/to/image{i}.tar",
                f"image{i}",
                "latest"
            )
    
    # 커넥터 정리
    await connector.close()
```

## 에러 처리

### 커스텀 예외

```python
class RegistryError(Exception):
    """레지스트리 기본 예외"""
    pass

class BlobUploadError(RegistryError):
    """블롭 업로드 실패"""
    pass

class ManifestError(RegistryError):
    """매니페스트 관련 오류"""
    pass

class TarReadError(RegistryError):
    """tar 파일 읽기 오류"""
    pass

class RegistryConnectionError(RegistryError):
    """레지스트리 연결 오류"""
    pass
```

### 에러 처리 예제

```python
async def safe_push():
    try:
        async with RegistryClient("http://localhost:5000") as client:
            await client.push_tar("/path/to/image.tar", "myapp")
    except RegistryConnectionError:
        print("레지스트리에 연결할 수 없습니다. registry:2 컨테이너가 실행 중인지 확인하세요.")
    except TarReadError as e:
        print(f"tar 파일을 읽을 수 없습니다: {e}")
    except BlobUploadError as e:
        print(f"블롭 업로드 실패: {e}")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
```

## 성능 고려사항

1. **비동기 스트리밍**: 대용량 레이어를 위한 비동기 스트림 처리
2. **동시 업로드**: 여러 레이어를 동시에 업로드 (기본 3개, 설정 가능)
3. **재시도 로직**: 네트워크 오류 시 exponential backoff로 자동 재시도
4. **연결 풀링**: aiohttp.TCPConnector를 통한 효율적인 연결 관리
5. **메모리 효율성**: AsyncIterator를 통한 스트리밍으로 메모리 사용량 최소화
6. **청크 크기 최적화**: 5MB 청크로 네트워크 효율성과 메모리 사용량 균형

## 제한사항

1. **인증 미지원**: 인증이 필요한 레지스트리는 사용 불가
2. **registry:2 전용**: 다른 레지스트리 구현체는 테스트되지 않음
3. **HTTP/HTTPS만 지원**: Unix 소켓 등 다른 프로토콜 미지원
4. **Manifest V2만 지원**: OCI 이미지 스펙은 지원하지 않음