from typing import Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
from src.utils.llm import generate_text
from src.model.schema import ProtectionTrademarkInfo, CollectedTrademarkInfo
from src.configs import get_system_prompt, get_user_prompt, get_detail_prompt
from src.container import Container
from src.utils.logger import get_logger
import numpy as np

logger = get_logger(__name__)

def calculate_conceptual_similarity(protection_trademark: ProtectionTrademarkInfo, 
                                    current_collected_trademark: CollectedTrademarkInfo) -> Dict[str, Any]:
    """Model C: 관념 유사도"""
    try:
        text_embedding_model = Container.get_text_embedding_model()
        model = Container.get_gpt51_chat()
        
        # 이미지 -> GPT-5.1-chat -> 관념 묘사문
        system_prompt = get_system_prompt("conceptual_similarity")
        
        logger.info("[관념 유사도] 1. 보호 상표 이미지 캡셔닝 시작")
        p_description = generate_text(model, system_prompt, 
                                                                get_user_prompt("conceptual_similarity"),
                                                                get_detail_prompt("conceptual_similarity"),
                                                                protection_trademark.p_trademark_image)
                                                                
        logger.info("[관념 유사도] 2. 수집 상표 이미지 캡셔닝 시작")
        c_description = generate_text(model, system_prompt, 
                                                                get_user_prompt("conceptual_similarity"),
                                                                get_detail_prompt("conceptual_similarity"),
                                                                current_collected_trademark.c_trademark_image)
        
        logger.debug(f"[관념 유사도] 캡션 결과: - 보호: {p_description[:50]}...\n- 수집: {c_description[:50]}...")
        
        # 관념 묘사문 -> text-embedding-3-large 임베딩
        logger.info("[관념 유사도] 3. 텍스트 임베딩 생성")
        p_embedding = text_embedding_model.embed_query(p_description)
        c_embedding = text_embedding_model.embed_query(c_description)
        
        # 코사인 유사도 계산
        target_vec = np.array(p_embedding).reshape(1, -1)        
        can_vec = np.array(c_embedding).reshape(1, -1)
        
        score = cosine_similarity(target_vec, can_vec)[0][0]
        final_score = round(score, 2)
        
        logger.info(f"[관념 유사도] 4. 유사도 점수 산출: {final_score}")

        return { "score" : final_score, "p_description" : p_description }
    except Exception as e:
        logger.error(f"[관념 유사도] 계산 중 오류 발생: {e}", exc_info=True)
        return {"score": 0.0, "p_description": ""}
