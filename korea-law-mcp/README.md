# 대한민국 판례 검색 및 법령 정보 조회 MCP 서버

대한민국 법원 판례 및 법령 정보를 검색하는 MCP(Multi-phase Conversation Provider) 서버입니다. 이 서버는 LLM이 대한민국 법령정보시스템의 API를 활용할 수 있도록 도구(Tool)를 제공합니다.

## 기능

- **판례 검색 도구 (`search_precedents`)**: 키워드, 법원, 날짜 등으로 판례 목록 검색
- **판례 상세 정보 조회 도구 (`get_precedent_detail`)**: 판례 일련번호로 상세 정보 조회
- **법령 목록 검색 도구 (`search_laws`)**: 법령명 또는 내용으로 법령 목록 및 ID 검색
- **법령 조항 상세 조회 도구 (`get_law_article_detail`)**: 법령 ID와 조/항/호/목 번호로 특정 조항 내용 조회

## 설치 방법

1. 저장소 클론:

```bash
git clone https://github.com/Nohyunjin/my-mcp-server.git
cd my-mcp-server/korea-law-mcp
```

2. 가상 환경 생성 및 활성화:

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. 의존성 설치:

```bash
uv pip install -r requirements.txt
```

4. 환경 변수 설정:
   `.env` 파일을 프로젝트 루트 디렉토리에 생성하고 다음 내용을 추가합니다:

```
# API 키 설정 (실제 구현시에는 본인의 이메일의 ID로 변경)
LAW_API_KEY={YOUR_API_KEY}

# API 키 발급
[국가법령정보 공동활용 API 신청](https://open.law.go.kr/LSO/login.do?ReURI=/LSO/openApi/cuAskList.do)
```

## 서버 실행

```bash
python law_mcp_server.py
```

실행에 오류가 없는지를 확인하는 것이지, 반드시 실행할 필요는 없습니다.

## MCP 서버를 Claude for Desktop과 연결하기

1. Claude for Desktop 앱 설정 파일을 열기:

**MacOS/Linux**:

```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows**:

```powershell
$env:AppData\Claude\claude_desktop_config.json
```

2. 다음과 같이 MCP 서버 설정 추가 (가상 환경 사용을 위해 `uv run` 사용 권장):

**MacOS/Linux**:

```json
{
    "mcpServers": {
        "korea-law": {
            "command": "uv",  // uv 실행 파일의 전체 경로가 필요할 수 있습니다. (which uv)
            "args": [
                "--directory",
                "/ABSOLUTE/PATH/TO/PARENT/FOLDER/korea-law-mcp", // 프로젝트 디렉토리
                "run",
                "law_mcp_server.py"
            ]
        }
    }
}
```

**Windows**:

```json
{
    "mcpServers": {
        "korea-law": {
            "command": "uv",
            "args": [
                "--directory",
                "C:\\ABSOLUTE\\PATH\\TO\\PARENT\\FOLDER\\korea-law-mcp", // 프로젝트 디렉토리
                "run",
                "law_mcp_server.py"
            ]
        }
    }
}
```

**참고:**

- `command`에 `uv` 대신 `uv` 실행 파일의 전체 경로를 입력해야 할 수 있습니다. (`which uv` 또는 `where uv` 명령어로 확인)
- `/ABSOLUTE/PATH/TO/PARENT/FOLDER/korea-law-mcp` 부분은 실제 프로젝트 경로로 변경해야 합니다.

3. Claude for Desktop 앱 재시작

## MCP 도구 사용 예시

서버가 제공하는 네 가지 도구를 사용하여 LLM은 사용자의 자연어 질의를 처리하고 판례 및 법령 정보를 검색/조회할 수 있습니다:

1.  **판례 검색 (`search_precedents`)**: 다양한 조건으로 판례 목록 조회.
2.  **판례 상세 조회 (`get_precedent_detail`)**: 판례 일련번호로 상세 정보 조회.
3.  **법령 검색 (`search_laws`)**: 법령명으로 검색하여 법령 ID 또는 법령일련번호(MST) 획득.
4.  **법령 조항 상세 조회 (`get_law_article_detail`)**: `search_laws`에서 얻은 ID/MST와 조/항/호/목 번호로 특정 조항 내용 조회.

## 자연어 쿼리 예시

LLM은 다음과 같은 자연어 쿼리를 이해하고 적절한 MCP 도구 호출(또는 조합)로 변환할 수 있습니다:

- "최근 음주 운전과 관련된 대법원 판례를 찾아줘"
- "2021년 1월부터 2022년 6월까지의 상속 관련 판례"
- "서울고등법원의 최근 지식재산권 판례"
- "대법원의 과거 5년간 이혼 관련 판례"
- "형법 ID 알려줘"
- "형법 제1조 제2항 내용 보여줘"
- "판례 599717의 참조조문인 치료감호법 제4조 제7항 내용 알려줘"

## 참고 정보

이 프로젝트는 대한민국 법령정보시스템의 API를 활용합니다:

- 판례 목록 조회 API: http://www.law.go.kr/DRF/lawSearch.do?target=prec
- 판례 본문 조회 API: http://www.law.go.kr/DRF/lawService.do?target=prec
- 법령 목록 조회 API: http://www.law.go.kr/DRF/lawSearch.do?target=law
- 법령 조항 상세 조회 API: http://www.law.go.kr/DRF/lawService.do?target=lawjosub
