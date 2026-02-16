import pytest
from src.graph.workflow import check_infringement, route_after_grading, route_after_evaluation
from src.model.schema import InfringementRisk

# 1. check_infringement 테스트

def test_check_infringement_high_risk(mock_state):
    # High Risk, High Score
    mock_state["ensemble_result"] = InfringementRisk(
        visual_score=0, visual_weight=0, phonetic_score=0, phonetic_weight=0, conceptual_score=0, conceptual_weight=0,
        total_score=80.0, risk_level="H"
    )
    assert check_infringement(mock_state) == "save_risk"

def test_check_infringement_medium_risk(mock_state):
    # Medium Risk, High Score
    mock_state["ensemble_result"] = InfringementRisk(
        visual_score=0, visual_weight=0, phonetic_score=0, phonetic_weight=0, conceptual_score=0, conceptual_weight=0,
        total_score=75.0, risk_level="M"
    )
    assert check_infringement(mock_state) == "save_risk"

def test_check_infringement_low_score(mock_state):
    # High Risk but Low Score (가정: 점수가 낮으면 위험도도 낮겠지만, 로직상 점수 체크 확인)
    mock_state["ensemble_result"] = InfringementRisk(
        visual_score=0, visual_weight=0, phonetic_score=0, phonetic_weight=0, conceptual_score=0, conceptual_weight=0,
        total_score=60.0, risk_level="H"
    )
    assert check_infringement(mock_state) == "end"

def test_check_infringement_low_risk_level(mock_state):
    # High Score but Low Risk Level
    mock_state["ensemble_result"] = InfringementRisk(
        visual_score=0, visual_weight=0, phonetic_score=0, phonetic_weight=0, conceptual_score=0, conceptual_weight=0,
        total_score=80.0, risk_level="L"
    )
    assert check_infringement(mock_state) == "end"


# 2. route_after_grading 테스트

def test_route_after_grading_approved(mock_state):
    mock_state["grading_decision"] = "approved"
    assert route_after_grading(mock_state) == "generate_report"

def test_route_after_grading_rewrite(mock_state):
    mock_state["grading_decision"] = "rewrite"
    assert route_after_grading(mock_state) == "generate_query"

def test_route_after_grading_web_search(mock_state):
    mock_state["grading_decision"] = "web_search"
    assert route_after_grading(mock_state) == "web_search"

def test_route_after_grading_default(mock_state):
    # 이상한 값이 들어오면 기본값 approved -> generate_report
    mock_state["grading_decision"] = "unknown"
    assert route_after_grading(mock_state) == "generate_report"


# 3. route_after_evaluation 테스트

def test_route_after_evaluation_approved(mock_state):
    mock_state["evaluation_decision"] = "approved"
    mock_state["evaluation_score"] = 90.0
    assert route_after_evaluation(mock_state) == "end"

def test_route_after_evaluation_high_score_force_end(mock_state):
    # 점수가 임계값(80) 이상이면 decision이 regenerate여도 종료
    mock_state["evaluation_decision"] = "regenerate"
    mock_state["evaluation_score"] = 85.0
    assert route_after_evaluation(mock_state) == "end"

def test_route_after_evaluation_regenerate_report(mock_state):
    mock_state["evaluation_decision"] = "regenerate"
    mock_state["evaluation_score"] = 50.0
    mock_state["regeneration_count"] = 0 # Max 3
    assert route_after_evaluation(mock_state) == "generate_report"

def test_route_after_evaluation_regenerate_query(mock_state):
    # 보고서 재생성 횟수 초과 -> 쿼리 재생성 시도
    mock_state["evaluation_decision"] = "regenerate"
    mock_state["evaluation_score"] = 50.0
    mock_state["regeneration_count"] = 3 # Max Reached
    mock_state["rewrite_count"] = 0 # Query Rewrite Available
    assert route_after_evaluation(mock_state) == "generate_query"

def test_route_after_evaluation_all_exhausted(mock_state):
    # 모든 횟수 초과
    mock_state["evaluation_decision"] = "regenerate"
    mock_state["evaluation_score"] = 50.0
    mock_state["regeneration_count"] = 3
    mock_state["rewrite_count"] = 3
    assert route_after_evaluation(mock_state) == "end"
