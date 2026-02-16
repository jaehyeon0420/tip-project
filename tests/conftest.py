import sys
import os
from pathlib import Path
from datetime import datetime
import pytest

# 프로젝트 루트 디렉토리를 sys.path에 추가하여 src 모듈을 import 할 수 있게 함
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.model.schema import ProtectionTrademarkInfo, CollectedTrademarkInfo, InfringementRisk, Precedent

@pytest.fixture
def mock_protection_trademark():
    return ProtectionTrademarkInfo(
        p_trademark_reg_no="4019425640000",
        p_trademark_name="한제원 고은",
        p_trademark_type="text",
        p_trademark_class_code="35",
        p_trademark_image="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",
        p_trademark_image_vec=[-0.06968858,0.03230422,-0.018603882,0.04342757,-0.0023708798,-0.123452656,-0.0021535142,-0.07486537,0.088634074,0.10396755,-0.0031705326,0.097691,0.015030993,0.0019450396,-0.09984204,-0.037858654,-0.03646889,0.058958713,-0.090120785,0.08594688,0.048570078,-0.12366359,0.051392533,0.16086689,0.03910946,0.11727619,0.07704165,-0.050940234,-0.14321922,-0.12523833,0.024382439,0.018911403,-0.010235041,-0.057912175,-0.12302401,-0.041815087,-0.044605415,0.023455972,0.04991314,-0.02423022,-0.041733146,-0.0037571278,-0.08606289,-0.182516,0.108231485,-0.040656365,0.1473519,-0.11376156,-0.01389464,0.14173004,0.076191895,0.056164127,-0.09358002,-0.091492385,-0.05629774,-0.023789972,0.1615143,0.19771187,0.05023142,0.04681303,-0.00059163297,-0.035318755,-0.06654717,-0.06290096,0.018154256,-0.06503878,0.0022827147,0.053715724,-0.09188533,0.10074337,-0.063319534,0.16535427,-0.15145345,0.057106905,-0.06312774,0.12096162,0.029267747,-0.050053343,-0.014693931,-0.038972937,0.10458229,0.044177853,-0.0019352934,-0.108371966,0.04830097,-0.11523005,-0.09143865,-0.025693333,0.0119714,0.14440884,-0.013700169,-0.10642063,0.1666081,0.082657896,-0.007599909,0.029698718,-0.09793837,-0.015567642,-0.13238293,0.0385935,-0.030375417,0.061019707,0.16005611,0.001972143,0.09315053,0.16546805,-0.13604252,0.058139846,-0.028060865,-0.06034795,-0.014576052,-0.033752315,-0.15682483,-0.051310442,0.09351308,0.12470337,0.22538733,0.13819443,-0.11585573,-0.13664107,-0.02150197,-0.043801315,0.14266448,0.04124236,-0.002459649,-0.15802729,0.01869548,0.08303432],
        p_trademark_user_no="qowo0420",
        p_product_kinds="식이보충기능성음료 판매알선업,건강기능식품 도매업,건강기능식품 소매업,건강기능식품 판매대행업,건강기능식품 판매알선업,식이보충음료 판매대행업,건강기능식품 통신 판매대행업,건강기능식품 통신 판매알선업,음료형태의 건강기능식품 판매알선업,숙취해소용 기능성음료 판매알선업,비알코올성 음료 판매대행업,홍삼을 주원료로 하고 당귀/천궁/작약/감초/계피/숙지황/황기의 한약재를 포함하는 건강보조식품 판매중개업,홍삼을 주원료로 하고  당귀/천궁/작약/감초/계피/숙지황/황기의 한약재를 포함하는  건강보조식품 도매업,홍삼을 주원료로 하고  당귀/천궁/작약/감초/계피/숙지황/황기의 한약재를 포함하는  건강보조식품 판매대행업,홍삼을 주원료로 하고  당귀/천궁/작약/감초/계피/숙지황/황기의 한약재를 포함하는  건강보조식품 판매알선업,온라인 주문을 통한 건강기능식품 판매대행업,온라인 주문을 통한 비알코올성 음료 판매대행업,인터넷 종합 쇼핑몰업,인삼을 주 원료로한 건강기능식품 소매업,인삼을 주 원료로한  건강기능식품 도매업,상품 주문 대행업"
    )

@pytest.fixture
def mock_collected_trademark():
    return CollectedTrademarkInfo(
        c_trademark_no="COL001",
        c_product_name="테스트상품",
        c_product_page_url="http://example.com/product",
        c_manufacturer_info="테스트제조사",
        c_brand_info="테스트브랜드",
        c_l_category="의류",
        c_m_category="셔츠",
        c_s_category="티셔츠",
        c_trademark_type="text",
        c_trademark_class_code="25",
        c_trademark_name="테스트수집",
        c_trademark_image="http://example.com/c_img.jpg",
        c_trademark_image_vec=[],
        c_trademark_ent_date=datetime(2026, 2, 11, 4, 24, 27, 103000)
    )

@pytest.fixture
def mock_ensemble_result():
    return InfringementRisk(
        visual_score=80.0, visual_weight=0.3,
        phonetic_score=75.0, phonetic_weight=0.3,
        conceptual_score=90.0, conceptual_weight=0.4,
        total_score=82.5, risk_level="H"
    )

@pytest.fixture
def mock_state(mock_protection_trademark, mock_collected_trademark, mock_ensemble_result):
    """기본 GraphState 구성"""
    return {
        "protection_trademark": mock_protection_trademark,
        "collected_trademarks": [mock_collected_trademark],
        "current_collected_trademark": mock_collected_trademark,
        "visual_similarity_score": 80.0,
        "visual_weight": 0.3,
        "phonetic_similarity_score": 75.0,
        "phonetic_weight": 0.3,
        "conceptual_similarity_score": 90.0,
        "conceptual_weight": 0.4,
        "ensemble_result": mock_ensemble_result,
        "search_query": "테스트 쿼리",
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
