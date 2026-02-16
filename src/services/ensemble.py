from src.model.schema import InfringementRisk, ProtectionTrademarkInfo, CollectedTrademarkInfo
from langchain_openai import AzureChatOpenAI
from src.configs import get_system_prompt, get_user_prompt, get_detail_prompt, render_user_prompt, model_config
from src.container import Container
from src.utils.llm import generate_text
from src.utils.format import clean_json
from src.utils.logger import get_logger
from typing import List, Tuple, Dict
import json
import math

logger = get_logger(__name__)

async def calculate_risk(protection_trademark: ProtectionTrademarkInfo,
                    current_collected_trademark: CollectedTrademarkInfo,
                    visual_similarity_score: float, 
                    phonetic_similarity_score: float, 
                    conceptual_similarity_score: float,
                    conceptual_description: str,
                    ) -> InfringementRisk:
    """앙상블 모델"""
    try:
        model = Container.get_gpt51_chat()
            
        # 유사도 범위
        visual_anchors = model_config.get("risk").get("anchors").get("visual")
        phonetic_anchors = model_config.get("risk").get("anchors").get("phonetic")
        conceptual_anchors = model_config.get("risk").get("anchors").get("conceptual")
        
        # 보간법 적용 (Logic)
        cal_vis = _score_calibrator(visual_similarity_score, visual_anchors)
        cal_pho = _score_calibrator(phonetic_similarity_score, phonetic_anchors)
        cal_sem = _score_calibrator(conceptual_similarity_score, conceptual_anchors)
        
        logger.info(f"[앙상블] 점수 보정 완료: 시각({cal_vis:.2f}), 호칭({cal_pho:.2f}), 관념({cal_sem:.2f})")
        
        # 보호 상표 이미지 -> GPT-5.1-chat -> 관념 묘사문
        logger.info("[앙상블] 보호 상표 시각적 묘사 생성 시작")
        visual_description = generate_text(model, get_system_prompt("risk_visual_description"), 
                                                                    get_user_prompt("risk_visual_description"), 
                                                                    get_detail_prompt("risk_visual_description"),
                                                                    protection_trademark.p_trademark_image)
        logger.info("[앙상블] 보호 상표 시각적 묘사 생성 완료")
    
        # 검색 쿼리 생성
        queries = []
        
        try:        
            # JSON 형식 정제
            search_query = _generate_search_query(model, protection_trademark.p_trademark_name, protection_trademark.p_product_kinds, visual_description, conceptual_description)
            parsed_json = json.loads(search_query)
            queries = parsed_json.get("queries", [])
            logger.info(f"[앙상블] 거절 사유 검색 쿼리 생성: {len(queries)}개")
            
        except Exception as e:
            logger.warning(f"[앙상블] 검색 쿼리 생성 실패 (기본값 사용): {e}")
            fallback_queries = [
                protection_trademark.p_trademark_name,
                f"{protection_trademark.p_trademark_name} {protection_trademark.p_product_kinds}",
                f"{protection_trademark.p_product_kinds} 상표 거절 사례"
            ]
            # 빈 문자열 제거 및 유효성 검사
            fallback_queries = [q for q in fallback_queries if q.strip()]
            queries = fallback_queries
        
        # 거절 사유 조회
        logger.info("[앙상블] 거절 사유 DB 조회 시작")
        formatted_contexts_str = await _search_reason_trademark(queries) 
        logger.info(f"[앙상블] 거절 사유 DB 조회 완료 (길이: {len(formatted_contexts_str)})")
        
        # 식별력 평가
        logger.info("[앙상블] 식별력 평가 시작")
        risk_identification_evaluation_json = _evaluate_identification(model, cal_vis, cal_pho, cal_sem, protection_trademark.p_trademark_name, protection_trademark.p_product_kinds, visual_description, conceptual_description, formatted_contexts_str)
        logger.info("[앙상블] 식별력 평가 완료")
        
        # 동적 가중치 저장
        dynamic_weights: Dict[str, float] = {}
        default_weight = model_config.get("risk").get("default_weight") # 기본 가중치
        
        # 필수 키 검증
        required_keys = ["visual", "phonetic", "semantic"]
        if not all(key in risk_identification_evaluation_json for key in required_keys):
            logger.warning("[앙상블] 식별력 평가 결과 키 누락. 기본 가중치 적용")
            dynamic_weights = {
                "visual": default_weight,
                "phonetic": default_weight,
                "semantic": default_weight
            }
        
        for key in required_keys:
            # 각 요소의 분석 결과
            analysis_item = risk_identification_evaluation_json.get(key, {})
            
            # grade_score 추출 (기본값: 3)
            # LLM이 3.0(float)이나 "3"(str)을 줄 수도 있으므로 안전하게 int 변환 시도
            raw_grade = analysis_item.get("grade_score", 3)
            
            try:
                grade_int = int(raw_grade)
            except (ValueError, TypeError):
                grade_int = 3 # 변환 실패 시 중간값
                
            # 가중치 매핑 테이블 조회 (1~5 범위를 벗어나면 기본값 처리)
            grade_weight = model_config.get("risk").get("grade_weight")
            weight = grade_weight.get(grade_int, default_weight)
            
            dynamic_weights[key] = weight   
        
        logger.info(f"[앙상블] 동적 가중치 산출: {dynamic_weights}")

        # 임계값 설정
        threshold_weight = model_config.get("risk").get("threshold_weight")
        threshold_score = model_config.get("risk").get("threshold_score")
        
        
        # 식별력이 강하고, 유사도가 높은 요소 추출
        dominant_factors_scores = []
        if dynamic_weights["visual"] >= threshold_weight and cal_vis >= threshold_score:
            dominant_factors_scores.append(cal_vis)
        if dynamic_weights["phonetic"] >= threshold_weight and cal_pho >= threshold_score:
            dominant_factors_scores.append(cal_pho)
        if dynamic_weights["semantic"] >= threshold_weight and cal_sem >= threshold_score:
            dominant_factors_scores.append(cal_sem)
        
        final_score = 0.0
        
        score_dict = {
            "visual": cal_vis,
            "phonetic": cal_pho,
            "semantic": cal_sem
        }
        
        # 
        if dominant_factors_scores:
            # [Case A] Dominant Part Rule (요부 관찰)
            # "하나만 걸려도 아웃이다"
            logger.info("[앙상블] 요부 관찰(Dominant Part Rule) 적용")
            
            # 요부 조건을 만족하는 항목들 중 가장 높은 유사도 점수를 채택
            final_score = max(dominant_factors_scores)
        else:
            # [Case B] Overall Observation Rule (전체 관찰)
            # "전체적인 인상을 종합적으로 본다"
            logger.info("[앙상블] 전체 관찰(Overall Observation Rule) 적용")
            
            final_score = _calculate_weighted_rms(score_dict, dynamic_weights)
        
        final_score = round(final_score, 4)
        risk_level = _determine_risk_level(final_score)

        return InfringementRisk(
            visual_score=cal_vis,
            visual_weight=dynamic_weights["visual"],
            phonetic_score=cal_pho,
            phonetic_weight=dynamic_weights["phonetic"],
            conceptual_score=cal_sem,
            conceptual_weight=dynamic_weights["semantic"],
            total_score=final_score,
            risk_level=risk_level,
            visual_description=visual_description
        )

    except Exception as e:
        logger.error(f"[앙상블] 치명적 오류 발생: {e}", exc_info=True)
        # Fail-safe 반환
        return InfringementRisk(
            visual_score=0.0, visual_weight=0.0,
            phonetic_score=0.0, phonetic_weight=0.0,
            conceptual_score=0.0, conceptual_weight=0.0,
            total_score=0.0, risk_level="S", visual_description=""
        )
    

def _generate_search_query(model : AzureChatOpenAI, p_trademark_name: str, p_product_kinds: str, visual_description: str, conceptual_description: str) -> str:
    model_gpt4o_mini = Container.get_gpt4o_mini()
        
    # User Prompt 생성
    context = {**{
        "target_text": p_trademark_name,        # 보호상표명
        "target_product": p_product_kinds,      # 지정상품명 리스트
        "vis_desc": visual_description,         # 시각 묘사문
        "sem_desc": conceptual_description      # 관념 묘사문(모델 4 결과)
    }} 
    
    user_prompt = render_user_prompt("risk_query_generation", **context)
    
    # 검색 쿼리 생성
    try:
        search_query = generate_text(model_gpt4o_mini, get_system_prompt("risk_query_generation"), 
                                                                user_prompt, 
                                                                "")
        
        # JSON 형식 정제
        search_query = clean_json(search_query)        
        return search_query
    
    except Exception as e:
        logger.error(f"[앙상블] 검색 쿼리 생성 실패: {e}", exc_info=True)
        return ""

async def _search_reason_trademark(queries: List[str]) -> List[str]:
    text_embedding_model = Container.get_text_embedding_model()
    vector_store = Container.get_vector_store()
    
    reason_trademarks_list = []
    unique_patent_ids = set()
    
    for query in queries:
        try:
            # 쿼리 임베딩
            query_vec = text_embedding_model.embed_query(query)
            reason_trademark_threshold = model_config.get("risk").get("reason_trademark_threshold")
            
            # 거절 사유 조회
            reason_trademarks = await vector_store.search_reason_trademark(query_vec, reason_trademark_threshold)
            
            # 중복 제거
            for row in reason_trademarks:
                if row.patent_id not in unique_patent_ids:
                    unique_patent_ids.add(row.patent_id)
                    reason_trademarks_list.append(row)
        except Exception as e:
            logger.warning(f"[앙상블] 거절 사유 검색 중 오류 (쿼리: {query}): {e}")
            continue
                
    # 코사인 유사도 기준 내림차순
    reason_trademarks_list.sort(key=lambda x: x.similarity_score, reverse=True)
    
    # 상위 10개 선택
    reason_trademarks_list = reason_trademarks_list[:10]
    
    # 결과 포맷팅
    formatted_contexts = []
    
    for row in reason_trademarks_list:
        # LLM이 참고하기 좋은 포맷으로 변환
        context_str = (
            f"[Case ID: {row.patent_id}]\n"
            f"- Similarity: {row.similarity_score:.4f}\n"
            f"- Tags: {row.reason_tags} (Product: {row.product_tags})\n"
            f"- Content: {row.cleaned_content}\n"
        )
        formatted_contexts.append(context_str)
        
    return "\n\n".join(formatted_contexts)


def _evaluate_identification(model : AzureChatOpenAI, cal_vis: float, cal_pho: float, cal_sem: float, p_trademark_name: str, p_product_kinds: str, visual_description: str, conceptual_description: str, formatted_contexts_str: str) : 
    try:
        score_summary = (
            f"- Visual Similarity Score: {cal_vis:.2f}\n"
            f"- Phonetic Similarity Score: {cal_pho:.2f}\n"
            f"- Semantic Similarity Score: {cal_sem:.2f}"
        )
        
        context = {**{
            "target_text": p_trademark_name,   # 보호상표명
            "target_product": p_product_kinds, # 지정상품명 리스트
            "vis_desc": visual_description,                         # 시각 묘사문
            "sem_desc": conceptual_description,                     # 관념 묘사문(모델 4 결과)
            "score_summary" : score_summary,                        # 유사도 분석 결과
            "rag_text" : formatted_contexts_str                     # 거절 사유 정보
        }} 
        
        user_prompt = render_user_prompt("risk_Identification_evaluation", **context)
        
        risk_identification_evaluation = generate_text(model, get_system_prompt("risk_Identification_evaluation"), 
                                                                    user_prompt, 
                                                                    "",
                                                                    )
        # JSON 형식 정제
        risk_identification_evaluation = clean_json(risk_identification_evaluation)    
        
        return json.loads(risk_identification_evaluation)
    except Exception as e:
        logger.error(f"[앙상블] 식별력 평가 생성 실패: {e}", exc_info=True)
        return {}

def _score_calibrator(score: float, anchors: List[Tuple[float, float]]) -> float:
    """
    score가 anchors의 어느 구간에 속하는지 찾아서 선형 보간
    """
    try:
        # anchors 형변환
        anchors = [(float(x[0]), float(x[1])) for x in anchors]
        
        # 범위 밖 처리
        if score <= anchors[0][0]:
            return anchors[0][1]
        if score >= anchors[-1][0]:
            return anchors[-1][1]
            
        # 구간 탐색 및 선형 보간
        for i in range(len(anchors) - 1):
            x1, y1 = anchors[i]
            x2, y2 = anchors[i + 1]
            
            if x1 <= score <= x2:
                # Linear Interpolation Formula: y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
                # 분모가 0인 경우 방지 (x1 == x2 인 경우)
                if x2 == x1:
                    return y1 
                
                ratio = (score - x1) / (x2 - x1)
                interpolated_y = y1 + ratio * (y2 - y1)
                return round(interpolated_y, 4) # 소수점 4자리까지 반올림
        return 0.0
    except Exception as e:
        logger.error(f"[앙상블] 점수 보정 중 오류: {e}")
        return score

def _calculate_weighted_rms(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    가중 평방 평균 (Weighted RMS) 계산
    Formula: sqrt( sum(w * s^2) / sum(w) )
    """
    try:
        numerator = 0.0
        denominator = 0.0
        
        for key in scores:
            s = scores.get(key, 0.0)
            w = weights.get(key, 0.0)
            
            numerator += w * (s ** 2)
            denominator += w
            
        if denominator == 0:
            return 0.0
            
        return math.sqrt(numerator / denominator)
    except Exception as e:
        logger.error(f"[앙상블] 가중 RMS 계산 오류: {e}")
        return 0.0

def _determine_risk_level(score: float) -> str:
    """
    최종 점수에 따른 위험 등급 결정 (Revised Logic)
    - 0.85 이상: High (고위험)
    - 0.70 ~ 0.85: Medium (중위험)
    - 0.55 ~ 0.70: Low (저위험 - 관찰 필요)
    - 0.55 미만: Safe (비유사 - 보고서 제외)
    """
    try:
        risk_thresholds = model_config.get("risk").get("risk_threshold")
        if score >= risk_thresholds["H"]:
            return "H"
        elif score >= risk_thresholds["M"]:
            return "M"
        elif score >= risk_thresholds["L"]:
            return "L"
        else:
            return "S"  # Safe 등급 (반환값 누락 수정)
    except Exception as e:
        logger.error(f"[앙상블] 위험 등급 결정 오류: {e}")
        return "S"
