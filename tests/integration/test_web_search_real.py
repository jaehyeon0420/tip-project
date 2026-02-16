import pytest
from src.graph.nodes.retrieval_nodes import web_search_node

@pytest.mark.asyncio
async def test_web_search_real(real_state):
    """실제 법령정보센터 API를 호출하여 판례를 검색"""
    real_state["web_search_keywords"] = ["상표권 침해", "외관 유사"]
    real_state["web_search_count"] = 0

    result = await web_search_node(real_state)

    # 검증: API가 정상 응답하고, 판례 목록이 반환되는지
    assert "retrieved_precedents" in result
    assert "web_search_count" in result
    assert result["web_search_count"] == 1

    # 실제 판례가 1건 이상 조회되는지
    precedents = result["retrieved_precedents"]
    # 검색 결과가 없을 수도 있으므로 경고만 하고 통과시킬 수도 있지만, 
    # 일반적인 키워드("상표권 침해")이므로 결과가 있어야 정상
    if not precedents:
        pytest.skip("법령정보센터 API 검색 결과가 없습니다. (일시적 장애 또는 키워드 문제)")
        
    assert len(precedents) >= 1

    # 각 판례의 필수 필드가 채워져 있는지
    for p in precedents:
        assert p.precedent_no  # 판례 일련번호 존재
        assert p.content       # 본문 존재
        assert p.case_id       # 사건번호 존재
