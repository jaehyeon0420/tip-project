import pytest
from unittest.mock import AsyncMock, MagicMock
from src.graph.nodes.report_nodes import generate_report_node, evaluate_report_node
from src.model.schema import EvaluationResult

@pytest.mark.asyncio
async def test_generate_report_success(mock_state, mocker):
    # Mock vLLM Client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "생성된 보고서 내용"
    
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch('src.container.Container.get_vllm_client', return_value=mock_client)
    
    result = await generate_report_node(mock_state)
    
    assert "report_content" in result
    assert result["report_content"] == "생성된 보고서 내용"

@pytest.mark.asyncio
async def test_generate_report_error_handling(mock_state, mocker):
    # Mock vLLM Client Error
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    mocker.patch('src.container.Container.get_vllm_client', return_value=mock_client)
    
    result = await generate_report_node(mock_state)
    
    assert "report_content" in result
    assert "보고서 생성 실패" in result["report_content"]

@pytest.mark.asyncio
async def test_evaluate_report_approved(mock_state, mocker):
    mock_state["report_content"] = "보고서"
    
    # Mock LLM Judge
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.ainvoke = AsyncMock()
    
    decision = EvaluationResult(score=90.0, feedback="Good", decision="approved")
    mock_structured_llm.ainvoke.return_value = decision
    
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mocker.patch('src.container.Container.get_gpt51_chat', return_value=mock_llm)
    
    result = await evaluate_report_node(mock_state)
    
    assert result["evaluation_decision"] == "approved"
    assert result["evaluation_score"] == 90.0

@pytest.mark.asyncio
async def test_evaluate_report_regenerate(mock_state, mocker):
    mock_state["report_content"] = "보고서"
    mock_state["regeneration_count"] = 0
    
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.ainvoke = AsyncMock()
    
    decision = EvaluationResult(score=50.0, feedback="Bad", decision="regenerate")
    mock_structured_llm.ainvoke.return_value = decision
    
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mocker.patch('src.container.Container.get_gpt51_chat', return_value=mock_llm)
    
    result = await evaluate_report_node(mock_state)
    
    assert result["evaluation_decision"] == "regenerate"
    assert result["regeneration_count"] == 1
