import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.graph.nodes.retrieval_nodes import save_infringe_risk_node,  web_search_node, _clean_html
from src.model.schema import Precedent

@pytest.mark.asyncio
async def test_save_infringe_risk_calls_vector_store(mock_state, mocker):
    # Mock VectorStore
    mock_store = AsyncMock()
    mocker.patch('src.container.Container.get_vector_store', return_value=mock_store)
    
    # High Risk State
    mock_state["ensemble_result"].total_score = 80.0
    mock_state["ensemble_result"].risk_level = "H"
    print(f'mock_state : {mock_state}')
    await save_infringe_risk_node(mock_state)
    
    mock_store.save_infringe_risk.assert_called_once()


def test_clean_html():
    raw = "<div>Hello&nbsp;World<br/></div>"
    cleaned = _clean_html(raw)
    assert cleaned == "Hello World"

@pytest.mark.asyncio
async def test_web_search_keywords(mock_state):
    # 키워드 리스트
    mock_state["web_search_keywords"] = ["상표권", "외관 유사"]
    mock_state["web_search_count"] = 0
    
    result = await web_search_node(mock_state)
    
    # 검색 결과 존재 여부 체크
    assert len(result["retrieved_precedents"]) > 0
    assert result["web_search_count"] == 1

