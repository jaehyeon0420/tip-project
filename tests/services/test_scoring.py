import pytest
from datetime import datetime
from src.model.schema import InfringementRisk, ProtectionTrademarkInfo, CollectedTrademarkInfo
from src.services.visual_scoring import calculate_visual_similarity
from src.services.phonetic_scoring import calculate_phonetic_similarity
from src.services.conceptual_scoring import calculate_conceptual_similarity
from src.services.ensemble import calculate_risk


def test_calculate_visual_similarity():
    
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    
    score = calculate_visual_similarity(v1, v2)
    print(f"score: {score}")
    
    #assert isinstance(score, float)
    #assert score == 0.0

def test_calculate_phonetic_similarity(mock_protection_trademark, mock_collected_trademark):
    #score = calculate_phonetic_similarity(mock_protection_trademark, mock_collected_trademark)
    #assert isinstance(score, float)
    #assert score == 0.0
    pass

class TestConceptualSimilarityReal:
    """Model C: 관념 유사도 - LLM + Embedding 필요 (실제 API 호출)"""

    @pytest.fixture
    def p_trademark(self):
        return ProtectionTrademarkInfo(
            p_trademark_reg_no="4019423700000",
            p_trademark_name="스타벅스",
            p_trademark_type="text",
            p_trademark_class_code="30",
            p_trademark_image=b"",  # 실 테스트 시 실제 이미지 바이트 필요
            p_trademark_image_vec=[0.1] * 512,
            p_trademark_user_no="USER001",
            p_product_kinds="커피, 음료"
        )

    @pytest.fixture
    def c_trademark(self):
        return CollectedTrademarkInfo(
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
            c_trademark_image=b"",
            c_trademark_image_vec=[0.1] * 512,
            c_trademark_ent_date=datetime(2026, 2, 11)
        )

    async def test_conceptual_returns_dict(self, p_trademark, c_trademark):
        result = await calculate_conceptual_similarity(p_trademark, c_trademark)
        print(f"result: {result}")
        assert isinstance(result, dict)
        assert "score" in result
        assert "p_description" in result

async def test_calculate_risk(mock_protection_trademark, mock_collected_trademark):
    # 입력 점수
    v_score = 80.0
    p_score = 70.0
    c_score = 90.0
    
    result = await calculate_risk(
        mock_protection_trademark,
        mock_collected_trademark,
        v_score, p_score, c_score,
        "본 상표는 원형 테두리 내부에 한글 “내집안전”이 결합된 구성으로 파악된다. 사전적 정의(Literal Meaning): “내집”은 ‘자신이 소유하거나 거주하는 집’을 의미하며, 동의어로는 자가(自家), 자택, 주거공간 등이 있다. “안전”은 위험이 없는 상태, 보호, 방호, 보안을 뜻한다. 결합 시 ‘가정의 보호·보안’이라는 의미를 형성한다. 요부는 의미 전달력이 강한 “안전” 및 결합어 “내집안전” 전체로 볼 수 있으며, 실사용 과정에서 “내집”, “집안전”, “내집안” 등으로 약칭·변형되어 호칭될 가능성이 있다. 시각적 뉘앙스(Visual Nuance): 흑백 대비의 단색 구성과 원형 프레임은 단정하고 안정적이며, 균형 잡힌 배열은 신뢰감·공공성·제도적 이미지를 환기한다. 종합적 관념(Total Conception): 일반 수요자에게 가정의 보호와 생활 안전을 상징하는 보안·안전관리 관련 표지로 인식될 개념적 인상을 형성한다."
    )
    
    assert isinstance(result, InfringementRisk)
    assert result.visual_score == v_score
    assert result.phonetic_score == p_score
    assert result.conceptual_score == c_score
    # 현재 구현은 total_score=0.0, risk_level="L" 고정
    assert result.total_score == 0.0
    assert result.risk_level == "L"
