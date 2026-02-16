from typing import Dict, Any
from src.graph.state import GraphState
from src.services.visual_scoring import calculate_visual_similarity
from src.services.phonetic_scoring import calculate_phonetic_similarity
from src.services.conceptual_scoring import calculate_conceptual_similarity
from src.services.ensemble import calculate_risk
from src.utils.logger import get_logger

logger = get_logger(__name__)

def visual_similarity(state: GraphState) -> Dict[str, Any]:
    """시각적 유사도 분석"""
    try:
        p_tm = state["protection_trademark"]
        c_tm = state["current_collected_trademark"]
        
        logger.info(f"[시각적 유사도] 분석 시작: {p_tm.p_trademark_name} vs {c_tm.c_trademark_name}")
        
        score = calculate_visual_similarity(
            p_tm.p_trademark_image_vec, 
            c_tm.c_trademark_image_vec
        )
        logger.info(f"[시각적 유사도] 분석 완료: 점수={score:.4f}")
        return {"visual_similarity_score": score}
    except Exception as e:
        logger.error(f"[시각적 유사도] 오류 발생: {e}", exc_info=True)
        return {"visual_similarity_score": 0.0}

def phonetic_similarity(state: GraphState) -> Dict[str, Any]:
    """발음적 유사도 분석"""
    try:
        p_tm = state["protection_trademark"]
        c_tm = state["current_collected_trademark"]
        
        logger.info(f"[발음적 유사도] 분석 시작: {p_tm.p_trademark_name} vs {c_tm.c_trademark_name}")
        
        score = calculate_phonetic_similarity(
            p_tm.p_trademark_name, 
            c_tm.c_trademark_name
        )
        logger.info(f"[발음적 유사도] 분석 완료: 점수={score:.4f}")
        
        return {"phonetic_similarity_score": score}
    except Exception as e:
        logger.error(f"[발음적 유사도] 오류 발생: {e}", exc_info=True)
        return {"phonetic_similarity_score": 0.0}

def conceptual_similarity(state: GraphState) -> Dict[str, Any]:
    """관념적 유사도 분석"""
    try:
        p_tm = state["protection_trademark"]
        c_tm = state["current_collected_trademark"]
        
        logger.info(f"[관념적 유사도] 분석 시작: {p_tm.p_trademark_name} vs {c_tm.c_trademark_name}")
        
        dict_result = calculate_conceptual_similarity(p_tm, c_tm)
        
        score = dict_result.get("score", 0.0)
        logger.info(f"[관념적 유사도] 분석 완료: 점수={score:.4f}")
        
        return {
            "conceptual_similarity_score": score, 
            "conceptual_description": dict_result.get("p_description", "")
        }
    except Exception as e:
        logger.error(f"[관념적 유사도] 오류 발생: {e}", exc_info=True)
        return {"conceptual_similarity_score": 0.0, "conceptual_description": ""}

async def ensemble_model(state: GraphState) -> Dict[str, Any]:
    """앙상블 모델"""
    try:
        logger.info("[앙상블 모델] 위험도 평가 시작")
        
        ensemble_result = await calculate_risk(
            state["protection_trademark"],
            state["current_collected_trademark"],
            state["visual_similarity_score"],
            state["phonetic_similarity_score"],
            state["conceptual_similarity_score"],
            state["conceptual_description"]
        )
        
        # 위험도가 일정 수준 이상이면 침해 발견 플래그 설정
        is_infringement = ensemble_result.risk_level in ["H", "M"]
        
        logger.info(f"[앙상블 모델] 평가 완료: 위험등급={ensemble_result.risk_level}, 총점={ensemble_result.total_score:.2f}, 침해여부={is_infringement}")
        
        return {
            "visual_similarity_score": ensemble_result.visual_score,
            "visual_weight": ensemble_result.visual_weight,
            "phonetic_similarity_score": ensemble_result.phonetic_score,
            "phonetic_weight": ensemble_result.phonetic_weight,
            "conceptual_similarity_score": ensemble_result.conceptual_score,
            "conceptual_weight": ensemble_result.conceptual_weight,
            "ensemble_result": ensemble_result,
            "is_infringement_found": is_infringement
        }
    except Exception as e:
        logger.error(f"[앙상블 모델] 오류 발생: {e}", exc_info=True)
        return {"is_infringement_found": False, "ensemble_result": None}
