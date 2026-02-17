from src.container import Container
from src.graph.state import GraphState
from src.configs import get_system_prompt, render_system_prompt, render_user_prompt, model_config
from src.utils.format import extract_common_context, extract_precedent_context
from src.model.schema import Precedent, JudgeDecision
from src.utils.llm import generate_text
from src.utils.format import clean_json, score_to_hml
from src.utils.logger import get_logger
from langchain_core.messages import SystemMessage, HumanMessage

from typing import List, Dict, Any
import json

logger = get_logger(__name__)

def generate_query(p_trademark_name: str, p_product_kinds: str, visual_description: str, weights: Dict[str, float], scores: Dict[str, float]) -> str:
    try:
        gpt_model = Container.get_gpt4o()
        
        context = {**{
            "forbidden_word": p_trademark_name,        # 보호상표명
        }} 
        
        # system 프롬프트 렌더링
        system_prompt = render_system_prompt("query_generation", **context)
        
        context = {**{
            "forbidden_word": p_trademark_name,        # 보호상표명
            "goods" : p_product_kinds,
            "visual_description" : visual_description,
            "dynamic_weights" : weights,
            "calibrated_scores" : scores
        }} 
        
        # user 프롬프트 렌더링
        user_prompt = render_user_prompt("query_generation", **context)
        
        # 쿼리 생성
        querys_json = generate_text(gpt_model, system_prompt, user_prompt, "")
        
        querys_json = clean_json(querys_json)  
        
        return json.loads(querys_json)
    except Exception as e:
        logger.error(f"[판례 검색] 쿼리 생성 중 오류: {e}", exc_info=True)
        return {"queries": [p_trademark_name]}

async def retrieve_precedents(search_querys: List[str], scores: Dict[str, float]) -> List[Precedent]:
    try:
        embedding_model = Container.get_text_embedding_model()
        vector_store = Container.get_vector_store()
        target_hml = score_to_hml(scores)
        
        logger.info(f"[판례 검색] 타겟 HML 패턴: {target_hml}")
        
        legal_ratio = model_config.get("precedent").get("legal_ratio")
        
        # 법리, 본문 비율 계산
        l_limit, f_limit = int(20 * legal_ratio), 20 - int(20 * legal_ratio)
        
        precedents = []
        
        for query in search_querys:
            # 쿼리 임베딩
            # (주의: embed_query는 동기 함수이므로 블로킹 가능성 있음. 향후 aembed_query로 교체 권장)
            q_vec = await embedding_model.aembed_query(query)
            
            # 판례 검색 (단수형 메서드 호출로 수정)
            search_precedents = await vector_store.search_precedent(q_vec, target_hml, l_limit, f_limit)
            
            # 리스트 확장 (append -> extend 수정)
            precedents.extend(search_precedents)
        
        logger.info(f"[판례 검색] 초기 검색 결과: {len(precedents)}건")

        # 중복 제거
        unique_results = {res["unique_key"]: res for res in precedents}.values()
        
        # 정렬 후 Precedent 객체 생성
        sorted_res = sorted(unique_results, key=lambda x: x['score'], reverse=True)
        
        precedents_obj = [Precedent(
            precedent_no = str(row["precedent_no"]), # 판례 번호
            file_name  = row["file_name"],           # 판례 파일명
            case_id    = row["case_id"],             # 판례 사건번호
            start_page = row["start_page"],          # 판례 시작 페이지
            content    = row["content"],             # 판례 내용,
            # hml_pattern = row["hml_pattern"],       # 판례 HML 패턴 (Schema에 필드 추가 필요, 현재는 생략)
            is_relevant= False                       # 적합성 여부 (초기값 False)
        ) for row in sorted_res]
        
        top_k = model_config.get('precedent').get('top_k')
        
        final_results = precedents_obj[:top_k]
        logger.info(f"[판례 검색] 최종 반환: {len(final_results)}건 (Top-K 적용)")
        
        return final_results
        
    except Exception as e:
        logger.error(f"[판례 검색] DB 조회 중 오류: {e}", exc_info=True)
        return []

def grade_precedents(state: GraphState) -> Dict[str, Any]:
    try:
        precedents = state.get("retrieved_precedents", [])                          # 검색 판례 목록
        rewrite_count = state.get("rewrite_count", 0)                               # 쿼리 재생성 시도 횟수
        web_search_count = state.get("web_search_count", 0)                         # 웹 검색 시도 횟수
        
        precedent_config = model_config.get('precedent', {})                        # 판례 관련 설정
        MAX_REWRITE_COUNT = precedent_config.get("max_rewrite_count", 3)            # 쿼리 재생성 최대 시도 횟수
        MAX_WEB_SEARCH_COUNT = precedent_config.get("max_web_search_count", 3)      # 웹 검색 최대 시도 횟수

        # 쿼리 재생성, 웹 검색 시도 한도 초과 시 기존에 조회된 판례로 보고서 생성
        if rewrite_count >= MAX_REWRITE_COUNT and web_search_count >= MAX_WEB_SEARCH_COUNT:
            logger.warning("[판례 검증] 모든 재시도 한도 초과. 강제 승인 처리.")
            is_exists = len(precedents) > 0
            refined = [p.model_copy(update={"is_relevant": True}) for p in precedents]
            return {
                "grading_decision": "approved",
                "refined_precedents": refined,
                "is_precedent_exists": is_exists
            }

        # 검색 판례 0건
        if not precedents:
            logger.warning("[판례 검증] 검색된 판례가 0건입니다.")
            
            # 쿼리 재생성 -> 판례 검색
            if rewrite_count < MAX_REWRITE_COUNT:
                return {
                    "grading_decision": "rewrite",
                    "query_feedback": "검색 결과가 0건입니다.",
                }
            # 웹 검색  -> 판례 검증
            elif web_search_count < MAX_WEB_SEARCH_COUNT:
                # 검색어가 없으면 기존 검색어 사용
                current_queries = state.get("search_querys", [])
                current_query = current_queries[0] if current_queries else ""
                
                return {
                    "grading_decision": "web_search",
                    "web_search_keywords": [current_query] if current_query else [],
                }
            # 검색 판례 0건, 쿼리 재생성 및 웹 검색 시도 한도 초과
            else:
                return {
                    "grading_decision": "approved",
                    "is_precedent_exists": False,
                    "refined_precedents": []
                }
        
        llm_judge = Container.get_gpt51_chat()
        structured_llm = llm_judge.with_structured_output(JudgeDecision)
        
        # 컨텍스트 추출
        context = {**extract_common_context(state), **extract_precedent_context(state)}
        
        messages = [
            SystemMessage(content=get_system_prompt("precedent_grading")),
            HumanMessage(content=render_user_prompt("precedent_grading", **context)),
        ]

        logger.info("[판례 검증] LLM 평가 요청")
        result: JudgeDecision = structured_llm.invoke(messages)

        # 결과 로깅
        logger.info(f"[판례 검증] LLM 결정: {result.decision} | 선택된 인덱스: {result.relevant_indices}")
        
        if result.decision == "approve":
            # 적합한 판례 인덱스 목록
            indices = result.relevant_indices
            
            valid_indices = [i for i in indices if 0 <= i < len(precedents)]
            
            # 적합한 판례 인덱스가 없으면 쿼리 재생성으로 처리
            if not valid_indices:
                logger.warning("[판례 검증] 승인되었으나 유효한 인덱스가 없음 -> 재검색 유도")
                return {
                    "grading_decision": "rewrite",
                    "query_feedback": "검색 쿼리에 적합한 판례가 존재하지 않습니다.",
                }

            refined = []
            for i in valid_indices:
                p = precedents[i].model_copy()
                p.is_relevant = True
                refined.append(p)
            
            return {"grading_decision": "approved", "refined_precedents": refined, "is_precedent_exists": len(refined) > 0}

        elif result.decision == "rewrite":
            return {
                "grading_decision": "rewrite",
                "query_feedback": result.feedback_or_query,
            }

        elif result.decision == "web_search":
            
            # JudgeDecision의 feedback_or_query가 키워드 리스트(List[str])라고 가정하지만,
            # 모델 출력에 따라 문자열일 수도 있으므로 리스트로 변환
            keywords = result.feedback_or_query
            if isinstance(keywords, str):
                 keywords = [keywords]
            elif keywords is None:
                 keywords = []

            return {
                "grading_decision": "web_search",
                "web_search_keywords": keywords,
            }
            
        # Fallback (도달하지 않음)
        return {
            "grading_decision": "approved", 
            "refined_precedents": [], 
            "is_precedent_exists": False
        }
            
    except Exception as e:
        logger.error(f"[판례 검증] 오류 발생: {e}", exc_info=True)
        # 에러 시 강제 진행 (또는 중단 정책에 따름)
        return {
            "grading_decision": "approved",
            "refined_precedents": [],
            "is_precedent_exists": False
        }
