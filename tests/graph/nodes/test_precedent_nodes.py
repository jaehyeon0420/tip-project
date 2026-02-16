import pytest
from unittest.mock import AsyncMock, MagicMock
from src.graph.nodes.precedent_nodes import grade_precedents_node
from src.model.schema import Precedent, JudgeDecision

@pytest.mark.asyncio
async def test_retry_limit_exceeded_force_approve(mock_state):
    # 모든 재시도 횟수 초과
    mock_state["rewrite_count"] = 3
    mock_state["web_search_count"] = 3
    mock_state["retrieved_precedents"] = [Precedent(precedent_no="1", content="내용", is_relevant=False)]
    
    result = await grade_precedents_node(mock_state)
    
    assert result["grading_decision"] == "approved"
    assert result["is_precedent_exists"] is True
    assert result["refined_precedents"][0].is_relevant is True

@pytest.mark.asyncio
async def test_no_precedents_rewrite(mock_state):
    # 판례 0건, Rewrite 기회 남음
    mock_state["retrieved_precedents"] = []
    mock_state["rewrite_count"] = 0
    
    result = await grade_precedents_node(mock_state)
    
    assert result["grading_decision"] == "rewrite"
    assert result["rewrite_count"] == 1

@pytest.mark.asyncio
async def test_no_precedents_web_search(mock_state):
    # 판례 0건, Rewrite 소진, Web Search 기회 남음
    mock_state["retrieved_precedents"] = []
    mock_state["rewrite_count"] = 3
    mock_state["web_search_count"] = 0
    mock_state["search_querys"] = ["기존쿼리"]
    
    result = await grade_precedents_node(mock_state)
    
    assert result["grading_decision"] == "web_search"
    assert result["web_search_keywords"] == ["기존쿼리"]

@pytest.mark.asyncio
async def test_llm_approve_decision(mock_state, mocker):
    # 판례 존재
    mock_state["retrieved_precedents"] = [
        Precedent(precedent_no="1", content="내용1", is_relevant=False),
        Precedent(precedent_no="2", content="내용2", is_relevant=False)
    ]
    
    # Mock LLM Judge
    # ChatOpenAI 객체는 동기 객체이고, 메서드 중 일부가 비동기임.
    # with_structured_output은 동기 메서드임.
    mock_llm = MagicMock() 
    mock_structured_llm = MagicMock()
    
    # ainvoke는 비동기 메서드이므로 AsyncMock
    mock_structured_llm.ainvoke = AsyncMock()
    
    # LLM이 0번 인덱스를 승인한다고 가정
    decision = JudgeDecision(decision="approve", relevant_indices=[0])
    mock_structured_llm.ainvoke.return_value = decision
    
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mocker.patch('src.container.Container.get_gpt51_chat', return_value=mock_llm)
    
    result = await grade_precedents_node(mock_state)
    
    assert result["grading_decision"] == "approved"
    assert len(result["refined_precedents"]) == 1
    assert result["refined_precedents"][0].precedent_no == "1"
    assert result["refined_precedents"][0].is_relevant is True

@pytest.mark.asyncio
async def test_llm_rewrite_decision(mock_state, mocker):
    mock_state["retrieved_precedents"] = [Precedent(precedent_no="1", content="내용", is_relevant=False)]
    
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.ainvoke = AsyncMock()
    
    decision = JudgeDecision(decision="rewrite", feedback_or_query="쿼리 수정 제안")
    mock_structured_llm.ainvoke.return_value = decision
    
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mocker.patch('src.container.Container.get_gpt51_chat', return_value=mock_llm)
    
    result = await grade_precedents_node(mock_state)
    
    assert result["grading_decision"] == "rewrite"
    assert result["query_feedback"] == "쿼리 수정 제안"
    assert result["rewrite_count"] == 1

@pytest.mark.asyncio
async def test_llm_web_search_decision(mock_state, mocker):
    mock_state["retrieved_precedents"] = [Precedent(precedent_no="1", content="내용", is_relevant=False)]
    
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.ainvoke = AsyncMock()
    
    decision = JudgeDecision(decision="web_search", feedback_or_query="키워드1")
    mock_structured_llm.ainvoke.return_value = decision
    
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mocker.patch('src.container.Container.get_gpt51_chat', return_value=mock_llm)
    
    result = await grade_precedents_node(mock_state)
    
    assert result["grading_decision"] == "web_search"
    assert result["web_search_keywords"] == ["키워드1"]
