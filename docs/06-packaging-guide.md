# PyPI 패키징 및 업로드 가이드

이 문서는 Python 패키지를 PyPI(Python Package Index)에 업로드하는 전체 프로세스를 설명합니다.

## 사전 준비

### 1. PyPI 계정 설정
1. [PyPI](https://pypi.org) 계정 생성
2. [Test PyPI](https://test.pypi.org) 계정 생성 (테스트용)
3. 2FA(Two-Factor Authentication) 활성화 (권장)

### 2. API 토큰 생성
1. PyPI 계정 설정에서 API 토큰 생성
2. 토큰을 안전한 곳에 저장
3. `.pypirc` 파일 설정 (선택사항):

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # 실제 토큰으로 교체

[testpypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Test PyPI 토큰
repository = https://test.pypi.org/legacy/
```

### 3. 필수 도구 설치
```bash
# 빌드 도구
pip install --upgrade build

# 업로드 도구
pip install --upgrade twine

# 또는 한 번에 설치
pip install --upgrade build twine
```

## 패키지 빌드

### 1. 프로젝트 정리
```bash
# 이전 빌드 제거
rm -rf dist/ build/ *.egg-info/

# 테스트 실행
pytest

# 코드 품질 검사
ruff check .
mypy src/
```

### 2. 버전 확인 및 업데이트
```python
# src/registry_api_v2_client/__init__.py
__version__ = "0.1.0"  # 새 버전으로 업데이트
```

```toml
# pyproject.toml
[project]
version = "0.1.0"  # 동일한 버전
```

### 3. 패키지 빌드
```bash
# 소스 배포판과 휠 생성
python -m build

# 결과 확인
ls dist/
# registry-api-v2-client-0.1.0.tar.gz
# registry_api_v2_client-0.1.0-py3-none-any.whl
```

## 패키지 검증

### 1. 빌드된 패키지 검사
```bash
# 메타데이터 검증
python -m twine check dist/*

# 내용 확인
tar -tzf dist/registry-api-v2-client-0.1.0.tar.gz
unzip -l dist/registry_api_v2_client-0.1.0-py3-none-any.whl
```

### 2. 로컬 설치 테스트
```bash
# 가상환경 생성
python -m venv test-env
source test-env/bin/activate  # Windows: test-env\Scripts\activate

# 빌드된 패키지 설치
pip install dist/registry_api_v2_client-0.1.0-py3-none-any.whl

# 임포트 테스트
python -c "import registry_api_v2_client; print(registry_api_v2_client.__version__)"

# CLI 테스트 (있는 경우)
registry-api --help
```

## Test PyPI 업로드

### 1. Test PyPI에 업로드
```bash
# Test PyPI에 업로드
python -m twine upload --repository testpypi dist/*

# 또는 직접 URL 지정
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

### 2. Test PyPI에서 설치 테스트
```bash
# 새 가상환경에서 테스트
python -m venv test-install
source test-install/bin/activate

# Test PyPI에서 설치
pip install --index-url https://test.pypi.org/simple/ --no-deps registry-api-v2-client

# 의존성 포함 설치
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ registry-api-v2-client
```

## 실제 PyPI 업로드

### 1. 최종 확인사항
- [ ] 버전 번호가 올바른가?
- [ ] README.md가 최신 상태인가?
- [ ] 모든 테스트가 통과하는가?
- [ ] CHANGELOG가 업데이트되었는가?
- [ ] 라이선스 파일이 포함되어 있는가?

### 2. PyPI 업로드
```bash
# 실제 PyPI에 업로드
python -m twine upload dist/*

# 업로드 확인
# https://pypi.org/project/registry-api-v2-client/
```

### 3. 설치 확인
```bash
# 새 환경에서 설치
pip install registry-api-v2-client

# 버전 확인
pip show registry-api-v2-client
```

## 자동화된 릴리즈 프로세스

### GitHub Actions를 사용한 자동 배포
```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        twine upload dist/*
```

### 시맨틱 릴리즈 사용
```toml
# pyproject.toml에 추가
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/registry_api_v2_client/__init__.py:__version__"]
branch = "main"
upload_to_pypi = true
build_command = "python -m build"
```

## 버전 관리 모범 사례

### Semantic Versioning (SemVer)
- **MAJOR.MINOR.PATCH** (예: 1.2.3)
  - MAJOR: 하위 호환성이 깨지는 변경
  - MINOR: 하위 호환성을 유지하는 기능 추가
  - PATCH: 하위 호환성을 유지하는 버그 수정

### 프리릴리즈 버전
```
0.1.0a1  # 알파
0.1.0b1  # 베타
0.1.0rc1  # 릴리즈 후보
```

## 일반적인 문제 해결

### 1. 패키지 이름 충돌
- PyPI에서 이미 사용 중인 이름인지 확인
- 고유한 프리픽스 사용 고려

### 2. 업로드 실패
```bash
# 인증 문제
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEI...

# 네트워크 문제
python -m twine upload --verbose dist/*
```

### 3. 메타데이터 오류
- `twine check` 실행하여 검증
- README 파일 인코딩 확인 (UTF-8)
- 긴 설명 렌더링 테스트

### 4. 의존성 문제
- 모든 의존성이 PyPI에 있는지 확인
- 버전 범위가 너무 제한적이지 않은지 확인

## 체크리스트

### 첫 릴리즈
- [ ] 프로젝트 구조 설정
- [ ] pyproject.toml 작성
- [ ] README.md 작성
- [ ] 라이선스 선택
- [ ] 테스트 작성
- [ ] 문서화
- [ ] PyPI 계정 생성
- [ ] Test PyPI에서 테스트
- [ ] 실제 PyPI에 업로드

### 후속 릴리즈
- [ ] 버전 번호 업데이트
- [ ] CHANGELOG 업데이트
- [ ] 테스트 실행
- [ ] 문서 업데이트
- [ ] 빌드 및 업로드
- [ ] Git 태그 생성
- [ ] GitHub 릴리즈 생성

## 유용한 명령어 모음

```bash
# 개발 환경 설정
pip install -e ".[dev]"

# 테스트 실행
pytest --cov

# 코드 품질 검사
ruff check .
black --check .
mypy src/

# 문서 빌드
mkdocs build

# 패키지 빌드
python -m build

# 업로드 전 검사
twine check dist/*

# Test PyPI 업로드
twine upload -r testpypi dist/*

# 실제 PyPI 업로드
twine upload dist/*

# 설치된 패키지 정보
pip show registry-api-v2-client
```