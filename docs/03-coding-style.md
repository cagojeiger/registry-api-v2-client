# 코딩 스타일 가이드

이 프로젝트는 함수형 프로그래밍 패러다임과 SOLID 원칙을 따르며, 비동기 프로그래밍을 기본으로 합니다.

## 함수형 프로그래밍 원칙

### 1. 순수 함수 (Pure Functions)
모든 함수는 가능한 순수 함수로 작성합니다. 순수 함수는:
- 동일한 입력에 대해 항상 동일한 출력을 반환
- 부작용(side effects)이 없음
- 외부 상태를 변경하지 않음

```python
# 좋은 예 - 순수 함수
def calculate_digest(data: bytes, algorithm: str = "sha256") -> str:
    """데이터의 다이제스트를 계산하는 순수 함수."""
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return f"{algorithm}:{hasher.hexdigest()}"

# 나쁜 예 - 외부 상태에 의존
class DigestCalculator:
    def __init__(self):
        self.last_result = None  # 외부 상태
    
    def calculate(self, data: bytes) -> str:
        result = hashlib.sha256(data).hexdigest()
        self.last_result = result  # 부작용
        return result
```

### 2. 불변성 (Immutability)
데이터는 불변 객체로 다룹니다.

```python
# 좋은 예 - 불변 데이터 구조
from dataclasses import dataclass, replace
from typing import FrozenSet

@dataclass(frozen=True)  # frozen=True로 불변성 보장
class ImageInfo:
    repository: str
    tag: str
    layers: tuple[LayerInfo, ...]  # tuple은 불변

# 데이터 수정이 필요한 경우 새 객체 생성
def update_tag(image: ImageInfo, new_tag: str) -> ImageInfo:
    return replace(image, tag=new_tag)
```

### 3. 함수 합성 (Function Composition)
작은 함수들을 조합하여 복잡한 로직을 구성합니다.

```python
from functools import partial
from typing import Callable, TypeVar

T = TypeVar('T')

# 함수 합성 헬퍼
def compose(*functions: Callable) -> Callable:
    """여러 함수를 합성합니다."""
    def inner(arg):
        result = arg
        for func in reversed(functions):
            result = func(result)
        return result
    return inner

# 사용 예
validate_and_calculate = compose(
    validate_digest,
    calculate_digest
)
```

### 4. 고차 함수 (Higher-Order Functions)
함수를 인자로 받거나 반환하는 함수를 활용합니다.

```python
from typing import AsyncIterator, Callable, Optional

async def with_progress(
    operation: Callable[[], AsyncIterator[bytes]],
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> AsyncIterator[bytes]:
    """진행 상황 추적을 추가하는 고차 함수."""
    total_bytes = 0
    async for chunk in operation():
        total_bytes += len(chunk)
        if progress_callback:
            await progress_callback(total_bytes, 0, "Processing...")
        yield chunk
```

## SOLID 원칙

### 1. 단일 책임 원칙 (Single Responsibility Principle)
각 모듈과 함수는 하나의 책임만 가집니다.

```python
# 좋은 예 - 각 함수가 하나의 책임만 담당
async def read_tar_manifest(tar_path: str) -> dict:
    """tar 파일에서 manifest.json만 읽기"""
    ...

async def parse_image_info(manifest: dict) -> ImageInfo:
    """manifest에서 이미지 정보 파싱"""
    ...

async def calculate_layer_digests(layers: list[LayerInfo]) -> list[str]:
    """레이어 다이제스트 계산"""
    ...
```

### 2. 개방-폐쇄 원칙 (Open/Closed Principle)
확장에는 열려있고 수정에는 닫혀있도록 설계합니다.

```python
from typing import Protocol

# 프로토콜로 인터페이스 정의
class DigestCalculator(Protocol):
    def calculate(self, data: bytes) -> str: ...

# 다양한 구현 가능
def sha256_calculator(data: bytes) -> str:
    return calculate_digest(data, "sha256")

def sha512_calculator(data: bytes) -> str:
    return calculate_digest(data, "sha512")

# 새로운 알고리즘 추가 시 기존 코드 수정 불필요
def create_digest_calculator(algorithm: str) -> Callable[[bytes], str]:
    return partial(calculate_digest, algorithm=algorithm)
```

### 3. 리스코프 치환 원칙 (Liskov Substitution Principle)
타입 힌트와 프로토콜을 사용하여 올바른 치환을 보장합니다.

```python
from typing import AsyncIterator, Protocol

class DataSource(Protocol):
    """데이터 소스 프로토콜"""
    async def read_chunks(self, chunk_size: int) -> AsyncIterator[bytes]: ...

# 모든 구현체는 프로토콜을 준수해야 함
async def read_from_file(path: str, chunk_size: int) -> AsyncIterator[bytes]:
    async with aiofiles.open(path, 'rb') as f:
        while chunk := await f.read(chunk_size):
            yield chunk

async def read_from_tar(tar_file: tarfile.TarFile, member: str, chunk_size: int) -> AsyncIterator[bytes]:
    # tar 파일에서 읽기 구현
    ...
```

### 4. 인터페이스 분리 원칙 (Interface Segregation Principle)
작고 구체적인 인터페이스를 선호합니다.

```python
# 좋은 예 - 작은 인터페이스들
class BlobChecker(Protocol):
    async def check_exists(self, repository: str, digest: str) -> bool: ...

class BlobUploader(Protocol):
    async def upload(self, repository: str, data: AsyncIterator[bytes], digest: str) -> str: ...

class ManifestHandler(Protocol):
    async def get(self, repository: str, reference: str) -> dict: ...
    async def put(self, repository: str, reference: str, manifest: dict) -> str: ...

# 나쁜 예 - 큰 인터페이스
class RegistryAPI(Protocol):
    async def check_blob(self, ...): ...
    async def upload_blob(self, ...): ...
    async def get_manifest(self, ...): ...
    async def put_manifest(self, ...): ...
    async def delete_manifest(self, ...): ...
    # 너무 많은 메서드...
```

### 5. 의존성 역전 원칙 (Dependency Inversion Principle)
구체적인 구현이 아닌 추상화에 의존합니다.

```python
from typing import Protocol

# 추상화 정의
class HTTPClient(Protocol):
    async def get(self, url: str, **kwargs) -> Response: ...
    async def post(self, url: str, **kwargs) -> Response: ...
    async def put(self, url: str, **kwargs) -> Response: ...

# 고수준 모듈은 추상화에 의존
async def upload_blob_with_client(
    client: HTTPClient,  # 구체적인 aiohttp가 아닌 프로토콜에 의존
    url: str,
    data: bytes
) -> str:
    response = await client.put(url, data=data)
    return response.headers.get("Docker-Content-Digest", "")
```

## 비동기 프로그래밍 패턴

### 1. 동시성 제어
```python
import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')

async def bounded_gather(
    *coros: Callable[[], Awaitable[T]], 
    limit: int = 3
) -> list[T]:
    """동시 실행 수를 제한하는 gather."""
    semaphore = asyncio.Semaphore(limit)
    
    async def bounded(coro: Callable[[], Awaitable[T]]) -> T:
        async with semaphore:
            return await coro()
    
    return await asyncio.gather(*[bounded(coro) for coro in coros])
```

### 2. 리소스 관리
```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def managed_session(url: str) -> AsyncIterator[aiohttp.ClientSession]:
    """세션 생명주기를 관리하는 컨텍스트 매니저."""
    session = aiohttp.ClientSession()
    try:
        yield session
    finally:
        await session.close()
```

### 3. 에러 처리
```python
from typing import TypeVar, Callable, Awaitable, Union

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

async def safe_execute(
    operation: Callable[[], Awaitable[T]],
    fallback: T,
    exceptions: tuple[type[E], ...] = (Exception,)
) -> Union[T, E]:
    """안전한 비동기 실행 with fallback."""
    try:
        return await operation()
    except exceptions:
        return fallback
```

## 테스트 가능한 코드

### 의존성 주입
```python
# 의존성을 매개변수로 전달
async def push_image(
    tar_reader: Callable[[str], Awaitable[ImageInfo]],
    blob_uploader: Callable[[str, AsyncIterator[bytes], str], Awaitable[str]],
    manifest_uploader: Callable[[str, str, dict], Awaitable[str]],
    tar_path: str,
    repository: str,
    tag: str
) -> str:
    """의존성이 주입된 이미지 푸시 함수."""
    image_info = await tar_reader(tar_path)
    # ... 구현
```

### 테스트 헬퍼
```python
from unittest.mock import AsyncMock

def create_mock_blob_uploader() -> AsyncMock:
    """테스트용 mock blob uploader 생성."""
    mock = AsyncMock()
    mock.return_value = "sha256:abc123..."
    return mock
```

## 타입 안정성

### 제네릭 활용
```python
from typing import TypeVar, Generic, AsyncIterator

T = TypeVar('T')

class AsyncBuffer(Generic[T]):
    """타입 안전한 비동기 버퍼."""
    def __init__(self) -> None:
        self._items: list[T] = []
    
    async def push(self, item: T) -> None:
        self._items.append(item)
    
    async def pop(self) -> T | None:
        return self._items.pop() if self._items else None
```

### NewType 활용
```python
from typing import NewType

Digest = NewType('Digest', str)
Repository = NewType('Repository', str)
Tag = NewType('Tag', str)

# 타입 안정성 향상
async def check_blob_exists(repo: Repository, digest: Digest) -> bool:
    ...
```

## 코드 구조화

### 모듈 구성
```
src/registry_api_v2_client/
├── api/              # HTTP API 관련 순수 함수들
│   ├── blob.py      # blob 관련 API 함수
│   ├── manifest.py  # manifest 관련 API 함수
│   └── common.py    # 공통 헬퍼 함수
├── tar/             # tar 파일 처리 함수들
├── utils/           # 유틸리티 순수 함수들
└── types.py         # 타입 정의
```

### 네이밍 규칙
- 함수: 동사로 시작하는 snake_case (`calculate_digest`, `upload_blob`)
- 상수: 대문자 SNAKE_CASE (`CHUNK_SIZE`, `DEFAULT_TIMEOUT`)
- 타입: PascalCase (`ImageInfo`, `LayerInfo`)
- 비동기 함수: `async_` 접두사는 사용하지 않음 (타입 시스템으로 구분)