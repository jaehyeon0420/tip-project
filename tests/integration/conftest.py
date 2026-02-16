import pytest
from datetime import datetime
from dotenv import load_dotenv
from src.container import Container
from src.model.schema import (
    ProtectionTrademarkInfo, CollectedTrademarkInfo, 
    InfringementRisk, Precedent
)

# 환경 변수 로드
load_dotenv()

@pytest.fixture
def real_state():
    """실제 데이터에 가까운 State"""
    p_tm = ProtectionTrademarkInfo(
        p_trademark_reg_no="4019423700000",
        p_trademark_name="스타벅스",
        p_trademark_type="text",
        p_trademark_class_code="30",
        p_trademark_image="",
        p_trademark_user_no="USER001"
    )
    c_tm = CollectedTrademarkInfo(
        c_trademark_no="COL001",
        c_product_name="스타벅",
        c_product_page_url="http://example.com",
        c_manufacturer_info="테스트",
        c_brand_info="스타벅",
        c_l_category="식품",
        c_m_category="음료",
        c_s_category="커피",
        c_trademark_type="text",
        c_trademark_class_code="30",
        c_trademark_name="스타벅",
        c_trademark_image="",
        c_trademark_ent_date=datetime(2026, 2, 11, 4, 24, 27, 103000)
    )
    ensemble = InfringementRisk(
        visual_score=85.0, visual_weight=0.3,
        phonetic_score=90.0, phonetic_weight=0.3,
        conceptual_score=80.0, conceptual_weight=0.4,
        total_score=84.5, risk_level="H"
    )
    return {
        "protection_trademark": p_tm,
        "collected_trademarks": [c_tm],
        "current_collected_trademark": c_tm,
        "visual_similarity_score": 85.0,
        "visual_weight": 0.3,
        "phonetic_similarity_score": 90.0,
        "phonetic_weight": 0.3,
        "conceptual_similarity_score": 80.0,
        "conceptual_weight": 0.4,
        "ensemble_result": ensemble,
        "search_querys": [],
        "retrieved_precedents": [],
        "refined_precedents": [],
        "grading_decision": "",
        "query_feedback": "",
        "web_search_keywords": [],
        "is_precedent_exists": False,
        "report_content": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "evaluation_decision": "",
        "rewrite_count": 0,
        "web_search_count": 0,
        "regeneration_count": 0,
        "is_infringement_found": False
    }
