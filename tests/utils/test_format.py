import pytest
from datetime import datetime
from src.utils.format import _type_label, clean_qwen_response, extract_common_context
from src.graph.state import GraphState
from src.model.schema import ProtectionTrademarkInfo, CollectedTrademarkInfo, InfringementRisk

def test_type_label():
    assert _type_label('text') == '문자'
    assert _type_label('shape') == '도형'
    assert _type_label('unknown') == '도형+문자'

def test_clean_qwen_response():
    raw_text = "<|im_start|>assistant\n<think>\nThinking process...\n</think>\nActual response<|im_end|>"
    cleaned = clean_qwen_response(raw_text)
    assert cleaned == "Actual response"

def test_extract_common_context():
    # Mock Data Setup
    p_tm = ProtectionTrademarkInfo(
        p_trademark_name="TestPTM",
        p_trademark_type="text",
        p_trademark_reg_no="12345",
        p_applicant_name="Tester",
        p_application_date="2023-01-01",
        p_registration_date="2023-06-01",
        p_designated_goods="Goods",
        p_trademark_class_code="30",
        p_trademark_image="img",
        p_trademark_user_no="user"
    )
    c_tm = CollectedTrademarkInfo(
        c_trademark_name="TestCTM",
        c_trademark_type="shape",
        c_trademark_no="67890",
        c_applicant_name="Collector",
        c_application_date="2023-02-01",
        c_status="Live",
        c_designated_goods="Goods",
        c_product_name="Product",
        c_product_page_url="url",
        c_manufacturer_info="maker",
        c_brand_info="brand",
        c_l_category="L",
        c_m_category="M",
        c_s_category="S",
        c_trademark_class_code="25",
        c_trademark_image="img",
        c_trademark_ent_date=datetime(2023, 2, 1)
    )
    ensemble = InfringementRisk(
        visual_score=80.5,
        visual_weight=0.3,
        phonetic_score=70.0,
        phonetic_weight=0.3,
        conceptual_score=90.0, conceptual_weight=0.4,
        total_score=81.15,
        risk_level="High"
    )
    
    # State Setup
    state: GraphState = {
        "protection_trademark": p_tm,
        "current_collected_trademark": c_tm,
        "ensemble_result": ensemble,
        # Other fields can be empty/None for this test
        "retrieved_precedents": [],
        "refined_precedents": [],
        "grading_decision": "",
        "evaluation_decision": "",
        "web_search_keywords": [],
        "rewrite_count": 0,
        "web_search_count": 0,
        "regeneration_count": 0,
        "final_report": ""
    }

    # Execution
    context = extract_common_context(state)

    # Assertion
    assert context["p_trademark_name"] == "TestPTM"
    assert context["p_trademark_type_label"] == "문자"
    assert context["c_trademark_name"] == "TestCTM"
    assert context["visual_score"] == "80.5"
    assert context["risk_level"] == "High"
