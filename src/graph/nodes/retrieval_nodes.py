import asyncio
import aiohttp
import re
import os
from typing import List, Dict, Any, Optional
from src.model.schema import Precedent
from src.graph.state import GraphState
from src.configs import model_config
from src.container import Container
from src.utils.logger import get_logger

logger = get_logger(__name__)

# API 설정
API_USER_ID = os.getenv("OPEN_API_USER_ID")
SEARCH_URL = os.getenv("OPEN_API_SEARCH_URL")
SERVICE_URL = os.getenv("OPEN_API_SERVICE_URL")

async def save_infringe_risk_node(state: GraphState) -> Dict[str, Any]:
    """위험군 저장 노드"""
    try:
        vector_store = Container.get_vector_store()
        
        # 앙상블 모델 결과
        ensemble_result = state.get("ensemble_result")
        total_score = ensemble_result.total_score
        risk_level = ensemble_result.risk_level
        
        # 보호 상표 번호
        p_trademark_reg_no = state["protection_trademark"].p_trademark_reg_no
        
        logger.info(f"[위험군 저장] 조건 확인: 총점={total_score}, 위험도={risk_level}")
        
        # 결과 재검증
        if risk_level in ["H", "M", "L"]:
            # 수집 상표 정보, 앙상블 모델 결과, 보호 상표 번호
            risk_data = {
                "c_tm": state["current_collected_trademark"],
                "ensemble_result": state["ensemble_result"],
                "p_trademark_reg_no": p_trademark_reg_no
            }
            
            # INSERT tbl_infringe_risk 
            logger.info("[위험군 저장] DB 저장 시작")
            await vector_store.save_infringe_risk(risk_data)
            logger.info("[위험군 저장] 완료")
        else:
            logger.info("[위험군 저장] 조건 미달로 저장하지 않음")
        
        return {}
    except Exception as e:
        logger.error(f"[위험군 저장] 오류 발생: {e}", exc_info=True)
        return {}


def _clean_html(raw_html: str) -> str:
    """HTML 태그 및 불필요한 공백 제거"""
    try:
        if not raw_html:
            return ""
        # <br/> 태그를 개행 문자로 변환
        text = raw_html.replace("<br/>", "\n").replace("<br>", "\n")
        # HTML 태그 제거 (정규식)
        text = re.sub(r'<[^>]+>', '', text)
        # &nbsp; 등 엔티티 처리
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        logger.warning(f"HTML 정제 중 오류 (무시됨): {e}")
        return raw_html or ""


async def fetch_precedent_list(session: aiohttp.ClientSession, keywords: List[str]) -> List[str]:
    """판례 목록 조회하여 일련번호 리스트 반환"""
    try:
        # 쿼리 스트링 파라미터 구성 (MultiDict 지원을 위해 list of tuples 사용)
        params = [
            ("OC", API_USER_ID),
            ("target", "prec"),
            ("type", "JSON"),
            ("search", "2"),                                    # 본문 검색
            ("display", str(model_config.get('web_search').get('display'))),  # 검색 결과 출력 건수
            ("page", "1")
        ]
        # 키워드 추가
        for k in keywords:
            params.append(("query", k))
            
        async with session.get(SEARCH_URL, params=params) as response:
            
            if response.status != 200:
                logger.error(f"[웹 검색 API] HTTP 상태 오류: {response.status}")
                return []
            
            try:
                data = await response.json()
            except Exception:
                logger.error("[웹 검색 API] 응답 JSON 파싱 실패")
                return []

            # API 응답 구조: {'PrecSearch': {'prec': [...]}}
            search_result = data.get("PrecSearch", {})
            
            # 검색 결과가 없거나 에러인 경우
            if not search_result or "prec" not in search_result:
                logger.info(f"[웹 검색 API] 검색 결과 없음 (키워드: {keywords})")
                return []
                
            prec_list = search_result["prec"]
            
            # 검색 결과가 1개일 경우 dict, 여러 개일 경우 list
            if isinstance(prec_list, dict):
                prec_list = [prec_list]
            
            ids = [item["판례일련번호"] for item in prec_list if "판례일련번호" in item]
            logger.debug(f"[웹 검색 API] 판례 ID 목록 확보: {len(ids)}건")
            return ids
            
    except Exception as e:
        logger.error(f"[웹 검색 API] 목록 조회 중 오류: {e}", exc_info=True)
        return []

async def fetch_precedent_detail(session: aiohttp.ClientSession, prec_no: str) -> Optional[Precedent]:
    """개별 판례 본문 상세 조회"""
    try:
        params = {
            "OC": API_USER_ID,
            "target": "prec",
            "ID": prec_no,
            "type": "JSON"
        }
        
        async with session.get(SERVICE_URL, params=params) as response:
            if response.status != 200:
                return None
            
            try:
                data = await response.json()
            except Exception:
                return None

            info = data.get("PrecService", {})
            
            if not info:
                return None
                
            # 본문 추출 우선순위: 판결요지 > 판시사항 > 판결내용 > 본문없음
            content = info.get("판결요지", "")
            if not content:
                content = info.get("판시사항", "")
            if not content:
                content = info.get("판결내용", "") 
            
            if not content:
                return None
            
            cleaned_content = _clean_html(content)
            
            return Precedent(
                precedent_no=prec_no,
                case_id=info.get("사건번호", "Unknown"),
                file_name=info.get("사건명", "Unknown"),     # 파일명 대신 사건명 매핑
                start_page="0",                             # API 결과에는 페이지 정보 없음
                content=cleaned_content,
                is_relevant=False # 초기값
            )
            
    except Exception as e:
        logger.error(f"[웹 검색 API] 상세 조회 중 오류 ({prec_no}): {e}", exc_info=True)
        return None

async def web_search_node(state: GraphState) -> Dict[str, Any]:
    """
    웹 검색 노드 (법령정보센터 API 연동)
    grade_precedents_node에서 결정된 검색어에서 추출된 web_search_keywords를 사용
    """
    try:
        keywords = state.get("web_search_keywords", [])
        web_search_count = state.get("web_search_count", 0)
        
        # 키워드가 없으면 기존 쿼리를 fallback으로 사용하거나 빈 리스트 처리
        if not keywords:
            logger.warning("[웹 검색] 검색 키워드가 없어 검색을 건너뜁니다.")
            return {
                "retrieved_precedents": [],
                "web_search_count": web_search_count + 1
            }
        
        logger.info(f"[웹 검색] 시작: 키워드={keywords} (시도 {web_search_count + 1}회)")
        
        async with aiohttp.ClientSession() as session:
            # 판례 목록 조회
            prec_ids = await fetch_precedent_list(session, keywords)
            
            if not prec_ids:
                logger.info("[웹 검색] 외부 API에서 판례를 찾지 못했습니다.")
                return {
                    "retrieved_precedents": [],
                    "web_search_count": web_search_count + 1
                }
                
            # 판례 본문 조회 (병렬 처리)
            logger.info(f"[웹 검색] 상세 본문 조회 시작 ({len(prec_ids)}건)")
            tasks = [fetch_precedent_detail(session, pid) for pid in prec_ids]
            results = await asyncio.gather(*tasks)
                    
            # None 제외 및 유효한 결과만 필터링
            precedents = [r for r in results if r is not None]
            
        logger.info(f"[웹 검색] 완료: 유효한 판례 {len(precedents)}건 확보")
        
        # 검색 결과 반환하여, 다시 판례 검증 노드로 라우팅
        return {
            "retrieved_precedents": precedents,
            "web_search_count": web_search_count + 1,
        }
    except Exception as e:
        logger.error(f"[웹 검색] 노드 실행 중 오류: {e}", exc_info=True)
        return {"retrieved_precedents": [], "web_search_count": 0}
