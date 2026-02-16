from typing import List
from src.utils.logger import get_logger
import numpy as np

logger = get_logger(__name__)

def calculate_visual_similarity(p_trademark_image_vec: List[float], c_trademark_image_vec: List[float]) -> float:
    """Model A: 외관 유사도 (코사인 유사도)"""
    try:
        if not p_trademark_image_vec or not c_trademark_image_vec:
            logger.warning("[외관 유사도] 이미지 벡터가 없어 유사도 0점 처리")
            return 0.0
        
        # 파이썬 리스트를 NumPy 배열로 변환
        v1 = np.array(p_trademark_image_vec)
        v2 = np.array(c_trademark_image_vec)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            logger.warning("[외관 유사도] 벡터 노름(Norm)이 0이어서 유사도 0점 처리")
            return 0.0
        
        score = float(np.dot(v1, v2) / (norm1 * norm2))
        logger.debug(f"[외관 유사도] 코사인 유사도 계산: {score:.4f}")
        
        return score
    except Exception as e:
        logger.error(f"[외관 유사도] 계산 중 오류 발생: {e}", exc_info=True)
        return 0.0
