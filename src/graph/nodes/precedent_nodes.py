from typing import Dict, Any
from src.graph.state import GraphState
from src.utils.logger import get_logger
from src.services.precedent import generate_query, retrieve_precedents, grade_precedents

logger = get_logger(__name__)

def generate_query_node(state: GraphState) -> Dict[str, Any]:
    """모델 결과를 바탕으로 판례 검색 쿼리 생성"""
    try:
        logger.info("[판례 검색 쿼리] 생성 시작")
        
        weights = {
            "visual" : state["visual_weight"],
            "phonetic" : state["phonetic_weight"],
            "conceptual" : state["conceptual_weight"],
        }
        scores = {
            "visual" :state["visual_similarity_score"],
            "phonetic" :state["phonetic_similarity_score"],
            "conceptual" :state["conceptual_similarity_score"],
        }
        
        query_json = generate_query(state["protection_trademark"].p_trademark_name,
                       state["protection_trademark"].p_product_kinds,
                       state["ensemble_result"].visual_description,
                       weights,
                       scores)
        
        queries = query_json.get("queries", [])
        logger.info(f"[판례 검색 쿼리] 생성 완료: {len(queries)}개 ({', '.join(queries[:3])}...)")
        
        return {
            "search_querys": queries,
            "regeneration_count": 0  # 쿼리 재생성 시 보고서 재생성 카운트 초기화
        }
    except Exception as e:
        logger.error(f"[판례 검색 쿼리] 오류 발생: {e}", exc_info=True)
        return {"search_querys": []}

async def retrieve_precedents_node(state: GraphState) -> Dict[str, Any]:
    """판례 검색 노드"""
    try:
        logger.info("[판례 검색] DB 조회 시작")
        
        scores = {
            "visual" :state["visual_similarity_score"],
            "phonetic" :state["phonetic_similarity_score"],
            "conceptual" :state["conceptual_similarity_score"],
        }
        
        precedents = await retrieve_precedents(state["search_querys"], scores)
        
        logger.info(f"[판례 검색] DB 조회 완료: {len(precedents)}건 발견")
        
        return {"retrieved_precedents": precedents}
    except Exception as e:
        logger.error(f"[판례 검색] 오류 발생: {e}", exc_info=True)
        return {"retrieved_precedents": []}

def grade_precedents_node(state: GraphState) -> Dict[str, Any]:
    """판례 검증 노드 (Agentic 하지 않은 구조화된 검증)"""
    try:
        logger.info("[판례 검증] 적합성 평가 시작")
        
        rewrite_count = state.get("rewrite_count", 0)
        web_search_count = state.get("web_search_count", 0)
        
        grade_precedents_result = grade_precedents(state)
        
        # 검증 결과
        refined = grade_precedents_result.get("refined_precedents", [])
        grading_decision = grade_precedents_result.get("grading_decision", "")
        is_precedent_exists = grade_precedents_result.get("is_precedent_exists", False)
        web_search_keywords = grade_precedents_result.get("web_search_keywords", [])
        
        logger.info(f"[판례 검증] 평가 완료: 결정={grading_decision}, 채택된 판례={len(refined)}건")
        
        return_dict = {}
        
        return_dict["refined_precedents"] = refined
        return_dict["grading_decision"] = grading_decision
        
        # 검증 결과에 따른 상태 업데이트
        if grading_decision == "approved":
            return_dict["is_precedent_exists"] = is_precedent_exists
        elif grading_decision == "rewrite":
            return_dict["rewrite_count"] = rewrite_count + 1
            logger.info(f"   ↪ 쿼리 재생성 카운트 증가 ({rewrite_count} -> {return_dict['rewrite_count']})")
        elif grading_decision == "web_search":
            # web_search_node에서 증가시키므로 여기서는 키워드만 전달하거나,
            # 정책에 따라 여기서 증가시킬 수도 있음. 
            # (기존 코드 유지하되 로그만 추가)
            return_dict["web_search_count"] = web_search_count + 1
            return_dict["web_search_keywords"] = web_search_keywords
            logger.info(f"   ↪ 웹 검색 카운트 증가 ({web_search_count} -> {return_dict['web_search_count']})")
            
        return return_dict
    except Exception as e:
        logger.error(f"[판례 검증] 오류 발생: {e}", exc_info=True)
        return {"grading_decision": "approved", "refined_precedents": []} # Fail-safe
