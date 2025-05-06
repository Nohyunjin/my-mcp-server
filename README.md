# My MCP Server

다양한 API들을 하나의 Multi-Channel Platform(MCP)으로 통합하는 프로젝트입니다.

## 개요

이 프로젝트는 다양한 출처의 API를 하나의 통일된 인터페이스로 묶어 제공합니다. 공공 API, Google API 등 다양한 서비스를 통합하여 사용자에게 일관된 경험을 제공하는 것이 목표입니다.

## 현재 지원하는 API

- 대한민국 법령 정보 API
- 기타 API는 계속 추가 예정

## 프로젝트 구조

```
my-mcp-server/
├── korea-law-mcp/     # 대한민국 법령 정보 API 관련 코드
└── ... (추가 예정)    # 기타 API 통합 모듈
```

## 시작하기

### 필수 요구사항

- Python 3.8 이상

### 설치

```bash
git clone https://github.com/Nohyunjin/my-mcp-server.git
cd my-mcp-server
# 각 API 모듈에 필요한 의존성 설치
```

### 환경 설정

각 API 모듈별로 필요한 환경 변수나 설정 파일을 구성해야 합니다.

## 라이센스

이 프로젝트는 [라이센스 정보]에 따라 배포됩니다.
