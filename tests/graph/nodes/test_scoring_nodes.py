import pytest
from unittest.mock import MagicMock
from src.graph.nodes.scoring_nodes import visual_similarity, phonetic_similarity, conceptual_similarity, ensemble_model
from src.model.schema import InfringementRisk

def test_visual_similarity_returns_score(mock_state, mocker):
    # Mock Service
    mocker.patch(
        'src.services.scoring.ScoringService.calculate_visual_similarity',
        return_value=85.0
    )
    
    result = visual_similarity(mock_state)
    
    assert "visual_similarity_score" in result
    assert result["visual_similarity_score"] == 85.0

def test_phonetic_similarity_returns_score(mock_state, mocker):
    mocker.patch(
        'src.services.scoring.ScoringService.calculate_phonetic_similarity',
        return_value=75.0
    )
    
    result = phonetic_similarity(mock_state)
    
    assert "phonetic_similarity_score" in result
    assert result["phonetic_similarity_score"] == 75.0

def test_conceptual_similarity_returns_score(mock_state, mocker):
    mocker.patch(
        'src.services.scoring.ScoringService.calculate_conceptual_similarity',
        return_value=90.0
    )
    
    result = conceptual_similarity(mock_state)
    
    assert "conceptual_similarity_score" in result
    assert result["conceptual_similarity_score"] == 90.0

def test_ensemble_model_high_risk(mock_state, mocker):
    # Mock Ensemble Result (High Risk)
    mock_risk = InfringementRisk(
        visual_score=80, visual_weight=0.3,
        phonetic_score=80, phonetic_weight=0.3,
        conceptual_score=80, conceptual_weight=0.4,
        total_score=80.0, risk_level="H"
    )
    
    mocker.patch(
        'src.services.scoring.ScoringService.calculate_risk',
        return_value=mock_risk
    )
    
    result = ensemble_model(mock_state)
    
    assert "ensemble_result" in result
    assert result["ensemble_result"] == mock_risk
    assert result["is_infringement_found"] is True

def test_ensemble_model_low_risk(mock_state, mocker):
    # Mock Ensemble Result (Low Risk)
    mock_risk = InfringementRisk(
        visual_score=30, visual_weight=0.3,
        phonetic_score=30, phonetic_weight=0.3,
        conceptual_score=30, conceptual_weight=0.4,
        total_score=30.0, risk_level="L"
    )
    
    mocker.patch(
        'src.services.scoring.ScoringService.calculate_risk',
        return_value=mock_risk
    )
    
    result = ensemble_model(mock_state)
    
    assert result["is_infringement_found"] is False
