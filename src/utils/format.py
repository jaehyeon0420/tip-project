import re
from typing import Dict, Any
from src.graph.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

def _type_label(type_code: str) -> str:
    """상표 유형 코드 → 한국어 라벨"""
    return {'text': '문자', 'shape': '도형'}.get(type_code, '도형+문자')

def clean_qwen_response(text: str) -> str:
    """Qwen 모델의 사고 과정(<think>...</think> 등) 제거"""
    try:
        # <think>...</think> 블록 제거
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # 특수 토큰 제거
        text = text.replace('<|im_end|>', '').replace('<|im_start|>', '').replace('assistant', '')
        return text.strip()
    except Exception as e:
        logger.warning(f"Qwen 응답 정제 중 오류: {e}")
        return text

def extract_common_context(state: GraphState) -> Dict[str, Any]:
    """
    모든 프롬프트에서 공통으로 사용하는 컨텍스트를 state에서 추출.
    반환값은 Jinja2 템플릿 변수로 직접 사용 가능한 flat dict.
    """
    try:
        p_tm = state["protection_trademark"]
        c_tm = state["current_collected_trademark"]
        ensemble = state.get("ensemble_result")
        
        # 앙상블 결과가 없는 경우 기본값 처리
        visual_score = f"{ensemble.visual_score:.1f}" if ensemble else "0.0"
        visual_weight = f"{ensemble.visual_weight:.2f}" if ensemble else "0.00"
        phonetic_score = f"{ensemble.phonetic_score:.1f}" if ensemble else "0.0"
        phonetic_weight = f"{ensemble.phonetic_weight:.2f}" if ensemble else "0.00"
        conceptual_score = f"{ensemble.conceptual_score:.1f}" if ensemble else "0.0"
        conceptual_weight = f"{ensemble.conceptual_weight:.2f}" if ensemble else "0.00"
        total_score = f"{ensemble.total_score:.1f}" if ensemble else "0.0"
        risk_level = ensemble.risk_level if ensemble else "N/A"

        return {
            # 상표 기본 정보
            "p_trademark_name": p_tm.p_trademark_name,
            "p_trademark_type_label": _type_label(p_tm.p_trademark_type),
            "c_trademark_name": c_tm.c_trademark_name,
            "c_trademark_type_label": _type_label(c_tm.c_trademark_type),
            # 앙상블 점수 (안전 접근)
            "visual_score": visual_score,
            "visual_weight": visual_weight,
            "phonetic_score": phonetic_score,
            "phonetic_weight": phonetic_weight,
            "conceptual_score": conceptual_score,
            "conceptual_weight": conceptual_weight,
            "total_score": total_score,
            "risk_level": risk_level,
        }
    except Exception as e:
        logger.error(f"공통 컨텍스트 추출 중 오류: {e}")
        return {}


def extract_precedent_context(state: GraphState, use_refined: bool = False) -> Dict[str, Any]:
    """판례 목록을 dict 리스트로 추출"""
    try:
        if use_refined:
            precedents = state.get("refined_precedents") or state.get("retrieved_precedents", [])
        else:
            precedents = state.get("retrieved_precedents", [])
        
        return {
            "precedents": [
                {
                    "case_id": p.case_id or "Unknown",
                    "file_name": p.file_name or "Unknown",
                    "start_page": p.start_page or "0",
                    "content": p.content,
                }
                for p in precedents
            ]
        }
    except Exception as e:
        logger.error(f"판례 컨텍스트 추출 중 오류: {e}")
        return {"precedents": []}

def get_case_description(case_name):
    descriptions = {
        "Case 1": "Microscope (짧은 상표) → 자모(Jamo) 50% + JW 30% + Partial 20%",
        "Case 2": "Telescope (긴 상표) → JW 50% + 자모(Jamo) 30% + Partial 20%",
        "Case 3": "Inclusion (길이 차이 큼) → Partial 70% + 자모(Jamo) 20% + JW 10%",
    }
    return descriptions.get(case_name, case_name)

def clean_hangul(text_list):
    try:
        if not isinstance(text_list, list): text_list = [text_list]
        cleaned = [ ''.join(re.findall(r'[가-힣]+', str(s))) for s in text_list ]
        return [c for c in cleaned if c] if any(cleaned) else [""]
    except Exception:
        return [""]

def apply_korean_phonetics(text_list):
    """
    한국어 발음 변환 로직 (현재는 g2pk 미사용이므로 원본 반환)
    """
    try:
        # if not isinstance(text_list, list):
        #     text_list = [text_list]
        
        # 현재 g2pk 라이브러리가 주석 처리되어 있으므로, 입력값을 그대로 반환하되
        # None을 반환하지 않도록 주의
        # return text_list if text_list else [""]
        
        try:
            from g2pk import G2p
            g2p = G2p()
        except ImportError:
            logger.warning("g2pk 모듈을 찾을 수 없어 발음 변환을 건너뜁니다.")
            return text_list if text_list else [""]
        except Exception as e:
            logger.warning(f"g2pk 초기화 중 오류 발생: {e}")
            return text_list if text_list else [""]

        result = []
        for text in text_list:
            if text and re.match(r'^[가-힣]+$', text):
                try:
                    pronounced = g2p(text).strip()
                    pronounced = ''.join(re.findall(r'[가-힣]+', pronounced))
                    result.append(pronounced if pronounced else text)
                except:
                    result.append(text)
            else:
                result.append(text)
        unique_result = list(dict.fromkeys(result))
        return unique_result if unique_result else [""]
    except Exception as e:
        logger.error(f"발음 변환 중 오류: {e}")
        return text_list if text_list else [""]

def clean_json(text: str) -> str:
    try:
        if text.startswith("```json"):  
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        return text
    except Exception:
        return text

def score_to_hml(scores: Dict[str, float]) -> str:
    """calibrated_scores를 기반으로 타겟 HML 패턴 생성 (C-V-P 순서)"""
    try:
        def to_l(v): return 'H' if v >= 0.8 else ('M' if v >= 0.4 else 'L')
        # conceptual 또는 semantic 키 중 존재하는 것을 유연하게 사용
        c_score = scores.get('conceptual') if scores.get('conceptual') is not None else scores.get('semantic', 0)
        return f"{to_l(c_score)}{to_l(scores.get('visual', 0))}{to_l(scores.get('phonetic', 0))}"
    except Exception as e:
        logger.error(f"HML 패턴 생성 오류: {e}")
        return "LLL" # 기본값
