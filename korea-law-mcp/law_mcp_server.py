#!/usr/bin/env python3
"""
대한민국 판례 검색 및 법령 정보 조회 MCP 서버

이 스크립트는 MCP(Multi-phase Conversation Provider) 서버로 동작하며,
대한민국 법령정보시스템 API를 활용하여 LLM이 판례 검색, 법령 검색, 법령 조항 조회 등을 수행할 수 있는 도구를 제공합니다.
"""

import json
import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict
from urllib.parse import quote  # URL 인코딩 추가

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# MCP 서버 초기화
mcp = FastMCP("korea-law")

# API 키 설정
API_KEY = os.getenv("LAW_API_KEY")  # 기본값을 테스트에서 작동한 키로 변경

# API 기본 URL
BASE_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
BASE_SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"


# 도우미 함수
async def make_api_request(url: str, params: Dict[str, str]) -> Dict:
    """API 요청을 수행하는 함수"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()

            # 응답 내용 로깅
            content = response.text
            logger.info(f"API 응답 길이: {len(content)} 바이트")
            logger.info(f"응답 시작 부분: {content[:100]}...")

            # 응답이 비어있는지 확인
            if not content.strip():
                logger.error("API 응답이 비어있습니다.")
                return {"error": "빈 응답이 반환되었습니다."}

            # 응답 형식이 JSON인지 XML인지 확인
            content_type = response.headers.get("content-type", "")
            logger.info(f"응답 Content-Type: {content_type}")

            response_type = params.get("type", "JSON").upper()

            # JSON 응답 처리
            if response_type == "JSON":
                try:
                    # JSON이 비어있거나 무효한 경우
                    if content.strip() == "{}" or content.strip() == "":
                        logger.warning("JSON 응답이 비어있습니다. XML로 재시도합니다.")
                        # 같은 요청을 XML 형식으로 다시 시도
                        new_params = params.copy()
                        new_params["type"] = "XML"
                        return await make_api_request(url, new_params)
                    return response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 오류: {str(e)}. XML로 재시도합니다.")
                    # JSON 파싱에 실패하면 XML로 재시도
                    new_params = params.copy()
                    new_params["type"] = "XML"
                    return await make_api_request(url, new_params)

            # XML 응답 처리
            elif response_type == "XML":
                try:
                    # XML을 파싱하여 사전으로 변환
                    root = ET.fromstring(content)

                    # 판례 검색 결과 처리 (PrecSearch)
                    if root.tag == "PrecSearch":
                        total_count_element = root.find("totalCnt")
                        total_count_value = 0
                        if total_count_element is not None and total_count_element.text:
                            total_count_value = int(total_count_element.text)

                        prec_list = []
                        for prec in root.findall("prec"):
                            prec_dict = {}
                            for child in prec:
                                # CDATA 처리를 위한 특별 처리
                                if child.text is not None:
                                    if child.text.startswith(
                                        "<![CDATA["
                                    ) and child.text.endswith("]]>"):
                                        prec_dict[child.tag] = child.text[
                                            9:-3
                                        ]  # CDATA 태그 제거
                                    else:
                                        prec_dict[child.tag] = child.text
                            prec_list.append(prec_dict)

                        return {
                            "PrecSearch": {
                                "totalCnt": str(total_count_value),
                                "prec": prec_list,
                            }
                        }

                    # 판례 상세 정보 처리 (PrecService)
                    elif root.tag == "PrecService":
                        prec_dict = {}
                        # PrecService의 직접 자식 노드를 순회
                        for child in root:
                            if child.text is not None:
                                if child.text.startswith(
                                    "<![CDATA["
                                ) and child.text.endswith("]]>"):
                                    prec_dict[child.tag] = child.text[
                                        9:-3
                                    ]  # CDATA 태그 제거
                                else:
                                    prec_dict[child.tag] = child.text

                        # prec 키 없이 바로 반환
                        return {"PrecService": prec_dict}

                    # 법령 조항 상세 정보 처리 (LawJosubService)
                    elif root.tag == "LawJosubService":
                        result_dict = {}
                        for child in root:
                            # < > 기호는 XML 파싱 시 자동으로 처리되므로 CDATA만 별도 처리
                            if child.text is not None:
                                if child.text.startswith(
                                    "<![CDATA["
                                ) and child.text.endswith("]]>"):
                                    result_dict[child.tag] = child.text[9:-3]
                                else:
                                    result_dict[child.tag] = child.text

                        # 최상위 태그 이름으로 래핑하여 반환
                        return {root.tag: result_dict}

                    # 법령 목록 검색 결과 처리 (LawSearch) - 새로운 구조
                    elif root.tag == "LawSearch":
                        total_count_element = root.find("totalCnt")
                        total_count_value = 0
                        if total_count_element is not None and total_count_element.text:
                            total_count_value = int(total_count_element.text)
                        law_list = []
                        for law in root.findall("law"):  # <law> 태그를 찾음
                            law_dict = {}
                            for child in law:
                                if child.text is not None:
                                    if child.text.startswith(
                                        "<![CDATA["
                                    ) and child.text.endswith("]]>"):
                                        law_dict[child.tag] = child.text[9:-3]
                                    else:
                                        law_dict[child.tag] = child.text
                            law_list.append(law_dict)
                        return {
                            "LawSearch": {
                                "totalCnt": str(total_count_value),
                                "law": law_list,  # 하위 태그 이름은 'law'
                            }
                        }

                    # 기타 XML 구조
                    logger.warning(f"처리되지 않은 XML 루트 태그: {root.tag}")
                    return {"xml_content": content, "root_tag": root.tag}

                except ET.ParseError as e:
                    logger.error(f"XML 파싱 오류: {str(e)}")
                    return {
                        "error": f"XML 파싱 오류: {str(e)}",
                        "raw_content": content[:500],
                    }

            # HTML이나 기타 응답 형식
            else:
                logger.warning(f"지원되지 않는 응답 형식: {response_type}")
                return {
                    "error": f"지원되지 않는 응답 형식: {response_type}",
                    "raw_content": content[:500],
                }

        except Exception as e:
            logger.error(f"API 요청 중 오류 발생: {str(e)}")
            return {"error": str(e)}


@mcp.tool()
async def search_precedents(
    query: str = "",
    court: str = "",
    court_type: str = "",
    sort: str = "ddes",
    date_range: str = "",
    search_type: int = 1,
    case_number: str = "",
    limit: int = 10,
    response_type: str = "XML",  # 기본값을 XML로 변경
) -> str:
    """대한민국 법원 판례를 검색합니다.

    Args:
        query: 판례에서 검색할 키워드
        court: 법원명 (예: 대법원, 서울고등법원)
        court_type: 법원종류 (대법원: 400201, 하위법원: 400202)
        sort: 정렬 옵션 (ddes: 최신순, dasc: 과거순, lasc: 사건명순)
        date_range: 선고일자 검색 (YYYYMMDD~YYYYMMDD 형식)
        search_type: 검색범위 (1: 판례명, 2: 본문검색)
        case_number: 판례 사건번호
        limit: 검색 결과 개수 (최대 100)
        response_type: 응답 형식 (JSON, XML, HTML - 기본값은 XML)
    """
    # API 요청 파라미터 설정 (모든 값은 문자열로 변환)
    params: Dict[str, str] = {"OC": API_KEY, "target": "prec", "type": response_type}

    # 선택적 매개변수 추가 (모두 문자열로 변환)
    if query:
        params["query"] = query
    if court:
        params["curt"] = court
    if court_type:
        params["org"] = court_type
    if sort:
        params["sort"] = sort
    if date_range:
        params["prncYd"] = date_range
    params["search"] = str(search_type)  # 정수를 문자열로 변환
    if case_number:
        params["nb"] = case_number
    params["display"] = str(min(limit, 100))  # 정수를 문자열로 변환

    # API 호출
    response_data = await make_api_request(BASE_SEARCH_URL, params)

    # 오류 처리
    if "error" in response_data:
        error_msg = response_data["error"]
        if "raw_content" in response_data:
            raw_content = response_data.get("raw_content", "")
            logger.error(f"원시 응답 내용 일부: {raw_content}")
            return f"판례 검색 중 오류가 발생했습니다: {error_msg}\n\n서버 응답이 예상 형식(JSON/XML)과 다릅니다. 서비스 상태를 확인해주세요."
        return f"판례 검색 중 오류가 발생했습니다: {error_msg}"

    # 성공 응답이면 그대로 JSON 문자열로 변환
    # make_api_request가 이미 {'PrecSearch': {'totalCnt': '...', 'prec': [...]}} 형태로 반환
    if "PrecSearch" in response_data and response_data["PrecSearch"].get("prec"):
        return json.dumps(response_data, ensure_ascii=False)
    elif "PrecSearch" in response_data:  # 검색 결과는 있지만 prec 리스트가 없는 경우
        return "검색 결과가 없습니다."
    else:  # 예상치 못한 성공 응답 구조
        logger.warning(
            f"make_api_request에서 예상치 못한 성공 응답 구조: {str(response_data)[:2000]}"
        )
        return "서버 응답 처리 중 예상치 못한 오류가 발생했습니다."


@mcp.tool()
async def get_precedent_detail(precedent_id: str, response_type: str = "XML") -> str:
    """판례 상세 정보를 조회합니다.

    Args:
        precedent_id: 판례 일련번호
        response_type: 응답 형식 (JSON, XML, HTML - 기본값은 XML)
    """
    # API 요청 파라미터 설정
    params: Dict[str, str] = {
        "OC": API_KEY,
        "target": "prec",
        "ID": precedent_id,
        "type": response_type,
    }

    # API 호출
    response_data = await make_api_request(BASE_SERVICE_URL, params)

    # 오류 처리
    if "error" in response_data:
        error_msg = response_data["error"]
        if "raw_content" in response_data:
            raw_content = response_data.get("raw_content", "")
            logger.error(f"원시 응답 내용 일부: {raw_content}")
            return f"판례 상세 정보 조회 중 오류가 발생했습니다: {error_msg}\n\n서버 응답이 예상 형식(JSON/XML)과 다릅니다. 서비스 상태를 확인해주세요."
        return f"판례 상세 정보 조회 중 오류가 발생했습니다: {error_msg}"

    # 성공 응답이면 그대로 JSON 문자열로 변환
    # make_api_request가 이미 {'PrecService': {...}} 형태로 반환
    if "PrecService" in response_data:
        # 상세 정보에 '판례정보일련번호'가 있는지 추가 확인 (더 확실한 검증)
        if response_data["PrecService"].get("판례정보일련번호"):
            return json.dumps(response_data, ensure_ascii=False)
        else:
            logger.warning(
                f"PrecService 데이터가 비어있거나 구조가 다릅니다: {str(response_data)[:200]}"
            )
            return f"ID가 {precedent_id}인 판례 정보를 찾을 수 없습니다."
    else:  # 예상치 못한 성공 응답 구조
        logger.warning(
            f"make_api_request에서 예상치 못한 성공 응답 구조: {str(response_data)[:200]}"
        )
        return "서버 응답 처리 중 예상치 못한 오류가 발생했습니다."


@mcp.tool()
async def search_laws(
    query: str = "",
    search_type: int = 1,
    display: int = 10,
    page: int = 1,
    sort: str = "lasc",
    response_type: str = "JSON",  # 기본 JSON
) -> str:
    """법령명 또는 법령 본문 내용으로 법령 목록을 검색합니다.

    법령 ID를 조회하여 다른 도구(get_law_article_detail)에 사용할 수 있습니다.

    Args:
        query: 검색할 법령명 또는 본문 내용 키워드.
        search_type: 검색 범위 (1: 법령명 - 기본값, 2: 본문 검색).
        display: 검색 결과 개수 (기본값 10, 최대 100).
        page: 검색 결과 페이지 번호 (기본값 1).
        sort: 정렬 옵션 (lasc: 법령 오름차순 - 기본값, ldes: 법령 내림차순, dasc: 공포일자 오름차순, ddes: 공포일자 내림차순 등).
        response_type: 응답 형식 (JSON, XML, HTML - 기본값 JSON).
    """
    params: Dict[str, str] = {
        "OC": API_KEY,
        "target": "law",
        "type": response_type,
        "query": query,
        "search": str(search_type),
        "display": str(min(display, 100)),
        "page": str(page),
        "sort": sort,
    }

    # API 호출
    response_data = await make_api_request(BASE_SEARCH_URL, params)

    # 오류 처리
    if "error" in response_data:
        error_msg = response_data["error"]
        if "raw_content" in response_data:
            raw_content = response_data.get("raw_content", "")
            logger.error(f"원시 응답 내용 일부: {raw_content}")
            return (
                f"법령 검색 중 오류: {error_msg}\n\n서버 응답이 예상 형식과 다릅니다."
            )
        return f"법령 검색 중 오류: {error_msg}"

    # 성공 응답 처리 - JSON 응답 키("법령" 가정) 확인
    if (
        "법령" in response_data
        and isinstance(response_data["법령"], list)
        and response_data["법령"]
    ):
        # target=law API의 JSON 응답은 법령 목록을 리스트로 반환할 것으로 가정
        # 실제 API 응답 확인 후 키/구조 조정 필요
        return json.dumps(response_data, ensure_ascii=False)
    elif "법령" in response_data:  # 키는 있지만 리스트가 비어있는 경우
        return "검색된 법령이 없습니다."

    # XML 응답 처리 (XML 파싱 로직은 make_api_request에서 처리)
    elif "LawSearch" in response_data and response_data["LawSearch"].get("law"):
        return json.dumps(response_data, ensure_ascii=False)
    elif "LawSearch" in response_data:  # 검색 결과는 있지만 law 리스트가 없는 경우
        return "검색된 법령이 없습니다."

    else:
        logger.warning(
            f"make_api_request에서 예상치 못한 성공 응답 구조: {str(response_data)[:2000]}"
        )
        return "법령 검색 응답 처리 중 예상치 못한 오류가 발생했습니다."


@mcp.tool()
async def get_law_article_detail(
    law_id: str = "",
    law_mst: str = "",
    article: str = "",
    paragraph: str = "",
    item: str = "",
    sub_item: str = "",
    response_type: str = "JSON",  # 기본 JSON
) -> str:
    """현행 법령의 특정 조항(조, 항, 호, 목)의 본문 내용을 조회합니다.

    법령 ID(`law_id`) 또는 법령 마스터 번호(`law_mst`) 중 하나는 반드시 제공해야 합니다.
    이 값들은 `search_laws` 도구의 결과에서 얻을 수 있습니다.
    조 번호(`article`)는 필수입니다.

    Args:
        law_id: 법령 ID (예: '001823'). `search_laws` 결과의 '법령ID' 필드에 해당. `law_mst`와 함께 제공될 경우 `law_mst` 우선.
        law_mst: 법령 마스터 번호. `search_laws` 결과의 '법령일련번호' 필드에 해당. `law_id` 대신 사용 가능.
        article: 조 번호 (필수, 6자리 문자열). 예: 제2조는 '000200', 제10조의2는 '001002'.
        paragraph: 항 번호 (선택, 6자리 문자열). 예: 제2항은 '000200'.
        item: 호 번호 (선택, 6자리 문자열). 예: 제2호는 '000200', 제10호의2는 '001002'.
        sub_item: 목 번호 (선택, 한글 1글자). 예: '가', '나', '다'. 서버에서 자동으로 URL 인코딩됩니다.
        response_type: 응답 형식 (JSON, XML, HTML - 기본값 JSON). API가 JSON을 제대로 지원하지 않을 수 있어 XML 재시도 로직 포함.
    """

    # 파라미터 준비
    params: Dict[str, str] = {
        "OC": API_KEY,
        "target": "lawjosub",
        "type": response_type,
    }

    # law_id 또는 law_mst 중 하나 선택
    if law_mst:
        params["MST"] = law_mst
    elif law_id:
        params["ID"] = law_id
    else:
        return json.dumps(
            {"error": "법령 ID(law_id) 또는 마스터 번호(law_mst)가 필요합니다."},
            ensure_ascii=False,
        )

    # 조 번호는 필수
    if not article:
        return json.dumps(
            {"error": "조 번호(article)는 필수입니다."}, ensure_ascii=False
        )
    params["JO"] = article

    # 나머지 파라미터 추가
    if paragraph:
        params["HANG"] = paragraph
    if item:
        params["HO"] = item
    if sub_item:
        params["MOK"] = quote(sub_item, encoding="UTF-8")

    # API 호출
    response_data = await make_api_request(BASE_SERVICE_URL, params)

    # 오류 처리
    if "error" in response_data:
        error_msg = response_data["error"]
        if "raw_content" in response_data:
            raw_content = response_data.get("raw_content", "")
            logger.error(f"원시 응답 내용 일부: {raw_content}")
            return f"법령 조항 조회 중 오류: {error_msg}\n\n서버 응답이 예상 형식과 다릅니다."
        return f"법령 조항 조회 중 오류: {error_msg}"

    # 성공 응답 처리 - JSON 응답 키("법령") 확인
    if "법령" in response_data:
        # 조문 정보가 있는지 확인
        law_info = response_data["법령"]
        article_info = law_info.get("조문", {}).get("조문단위", {})

        if not article_info:
            logger.warning(f"JSON 응답에 조문 정보 없음: {str(response_data)[:200]}")
            return "해당 조항의 정보를 찾을 수 없습니다."

        # 조문/항/호/목 내용 중 가장 구체적인 내용을 찾아서 반환 (항/호/목은 아직 API 응답에 없어 보임)
        # 현재 API 응답 구조상 조문 내용만 존재
        content_key = "조문내용"
        content = article_info.get(content_key)

        if content:
            # 찾은 내용을 포함한 전체 응답(원본 JSON 구조)을 JSON으로 반환
            return json.dumps(response_data, ensure_ascii=False)
        else:
            logger.warning(
                f"LawJosubService JSON 응답에서 '{content_key}'를 찾을 수 없음: {str(response_data)[:200]}"
            )
            return "해당 조항의 내용을 찾을 수 없습니다."

    # XML 응답 처리 (XML 파싱 로직은 make_api_request에서 처리)
    elif "LawJosubService" in response_data:
        content_key = (
            "목내용"
            if sub_item
            else "호내용" if item else "항내용" if paragraph else "조문내용"
        )
        content = response_data["LawJosubService"].get(content_key)
        if content:
            return json.dumps(response_data, ensure_ascii=False)
        else:
            logger.warning(
                f"LawJosubService XML 응답에서 '{content_key}'를 찾을 수 없음: {str(response_data)[:200]}"
            )
            return "해당 조항의 내용을 찾을 수 없습니다."

    else:
        logger.warning(
            f"make_api_request에서 예상치 못한 성공 응답 구조: {str(response_data)[:2000]}"
        )
        return "법령 조항 응답 처리 중 예상치 못한 오류가 발생했습니다."


if __name__ == "__main__":
    # 서버 실행
    mcp.run(transport="stdio")
