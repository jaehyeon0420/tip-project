import os
from dotenv import load_dotenv
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from src.graph.workflow import app
from src.graph.state import GraphState
from src.model.schema import (
    ProtectionTrademarkInfo, 
    CollectedTrademarkInfo, 
    InfringementRisk, 
    Precedent,
    JudgeDecision,
    EvaluationResult
)
from src.main import main
from src.container import Container

load_dotenv()

# -----------------------------------------------------------------------------
# 1. Mock Data Setup
# -----------------------------------------------------------------------------

MOCK_P_TM_DICT = {
    "p_trademark_reg_no": "4019423700000",
    "p_trademark_name": "테스트보호",
    "p_trademark_type": "text",
    "p_trademark_class_code": "30",
    "p_trademark_image": "base64_img_string...",
    "p_trademark_image_vec": [0.1, 0.2, 0.3],
    "p_trademark_user_no": "USER001"
}

# 유사 수집 상표 1 (침해 위험 높음)
MOCK_C_TM_DICT_HIGH = {
    "c_trademark_no": "COL001",
    "c_product_name": "테스트침해상품1",
    "c_product_page_url": "http://example.com/1",
    "c_manufacturer_info": "제조사1",
    "c_brand_info": "브랜드1",
    "c_l_category": "대분류",
    "c_m_category": "중분류",
    "c_s_category": "소분류",
    "c_trademark_type": "text",
    "c_trademark_class_code": "30",
    "c_trademark_name": "테스트침해1",
    "c_trademark_image": "base64_img_string...",
    "c_trademark_image_vec": [0.1, 0.2, 0.3],
    "c_trademark_ent_date": datetime(2026, 2, 11)
}

# 유사 수집 상표 2 (침해 위험 낮음)
MOCK_C_TM_DICT_LOW = {
    "c_trademark_no": "COL002",
    "c_product_name": "테스트침해상품2",
    "c_product_page_url": "http://example.com/2",
    "c_manufacturer_info": "제조사2",
    "c_brand_info": "브랜드2",
    "c_l_category": "대분류",
    "c_m_category": "중분류",
    "c_s_category": "소분류",
    "c_trademark_type": "shape",
    "c_trademark_class_code": "30",
    "c_trademark_name": "테스트침해2",
    "c_trademark_image": "base64_img_string...",
    "c_trademark_image_vec": [0.9, 0.8, 0.7],
    "c_trademark_ent_date": datetime(2026, 2, 12)
}

MOCK_PRECEDENT = Precedent(
    precedent_no="2023다12345",
    file_name="상표권침해금지",
    case_id="2023다12345",
    start_page="1",
    content="본 사건은 상표권 침해에 관한 것으로...",
    is_relevant=False
)


@pytest.mark.asyncio
async def test_main_e2e_happy_path(mocker):
    """
    [E2E] main() 함수 전체 실행 테스트 (Happy Path)
    
    시나리오:
    1. search_similar_trademarks -> 보호상표 1개, 수집상표 2개(High, Low) 반환
    2. ScoringService -> High: 85점(Risk H), Low: 40점(Risk L)
    3. save_infringe_risk -> High만 저장됨
    4. retrieve_precedents -> 판례 2건 반환
    5. grade_precedents -> LLM Judge: 'approve'
    6. generate_report -> vLLM: 보고서 생성
    7. evaluate_report -> LLM Judge: 'approved' (85점)
    8. send_report_mail -> 메일 발송 (High 1건에 대한 보고서)
    """

    # -------------------------------------------------------------------------
    # 2. Mocking External Dependencies
    # -------------------------------------------------------------------------

    # (1) Database Connection
    # main.py에서 Database.get_pool(), Database.close() 호출
    mocker.patch("src.main.Database.get_pool", new_callable=AsyncMock)
    mocker.patch("src.main.Database.close", new_callable=AsyncMock)
    
    # (2) VectorStore (Container.get_vector_store)
    mock_vector_store = AsyncMock()
    
    # search_similar_trademarks: 보호상표 1개 + 수집상표 2개 반환
    mock_vector_store.search_similar_trademarks.return_value = [
        {
            "protection_trademark": MOCK_P_TM_DICT,
            "collected_trademarks": [MOCK_C_TM_DICT_HIGH, MOCK_C_TM_DICT_LOW]
        }
    ]
    
    # save_infringe_risk: 리턴값 없음
    mock_vector_store.save_infringe_risk.return_value = None
    
    # search_precedents: 판례 2건 반환
    mock_vector_store.search_precedents.return_value = [MOCK_PRECEDENT, MOCK_PRECEDENT]
    
    mocker.patch("src.container.Container.get_vector_store", return_value=mock_vector_store)


    # (3) ScoringService (Logic)
    # calculate_risk가 호출될 때, 수집상표 이름에 따라 다른 점수 반환하도록 side_effect 설정
    
    def mock_calculate_risk(p_tm, c_tm, v_score, p_score, c_score):
        # c_tm은 Pydantic 모델(CollectedTrademarkInfo)로 변환된 상태임
        if c_tm.c_trademark_name == "테스트침해1":  # High Risk
            return InfringementRisk(
                visual_score=85.0, visual_weight=0.3,
                phonetic_score=85.0, phonetic_weight=0.3,
                conceptual_score=85.0, conceptual_weight=0.4,
                total_score=85.0, risk_level="H"
            )
        else:  # Low Risk
            return InfringementRisk(
                visual_score=40.0, visual_weight=0.3,
                phonetic_score=40.0, phonetic_weight=0.3,
                conceptual_score=40.0, conceptual_weight=0.4,
                total_score=40.0, risk_level="L"
            )

    mocker.patch("src.services.scoring.ScoringService.calculate_visual_similarity", return_value=85.0)
    mocker.patch("src.services.scoring.ScoringService.calculate_phonetic_similarity", return_value=85.0)
    mocker.patch("src.services.scoring.ScoringService.calculate_conceptual_similarity", return_value=85.0)
    mocker.patch("src.services.scoring.ScoringService.calculate_risk", side_effect=mock_calculate_risk)


    # (4) LLM Judge (Container.get_llm_judge)
    # grade_precedents_node -> JudgeDecision
    # evaluate_report_node -> EvaluationResult
    
    mock_llm_judge = MagicMock()
    
    def mock_with_structured_output(schema):
        mock_structured = MagicMock()
        
        if schema == JudgeDecision:
            # 판례 검증: 승인
            mock_structured.ainvoke = AsyncMock(return_value=JudgeDecision(
                decision="approve",
                relevant_indices=[0, 1],
                feedback_or_query=None
            ))
        elif schema == EvaluationResult:
            # 보고서 평가: 승인 (85점)
            mock_structured.ainvoke = AsyncMock(return_value=EvaluationResult(
                score=85.0,
                feedback="훌륭한 보고서입니다.",
                decision="approved"
            ))
        return mock_structured

    mock_llm_judge.with_structured_output = MagicMock(side_effect=mock_with_structured_output)
    mocker.patch("src.container.Container.get_gpt51_chat        ", return_value=mock_llm_judge)


    # (5) vLLM Client (Container.get_vllm_client)
    # generate_report_node -> Report Content
    
    mock_vllm_client = AsyncMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "# 상표권 침해 분석 보고서\n\n본 상표는 침해 가능성이 높습니다..."
    
    mock_vllm_client.chat.completions.create.return_value = mock_completion
    mocker.patch("src.container.Container.get_vllm_client", return_value=mock_vllm_client)


    # (6) Mail Service (send_report_mail)
    # main.py에서 직접 import해서 사용하므로 해당 경로 patch
    mock_send_mail = mocker.patch("src.main.send_report_mail", new_callable=AsyncMock, return_value=True)


    # -------------------------------------------------------------------------
    # 3. Execution & Verification
    # -------------------------------------------------------------------------
    
    # Container 캐시 초기화 (필수)
    Container.get_vector_store.cache_clear()
    Container.get_llm_judge.cache_clear()
    Container.get_llm_query_gen.cache_clear()
    Container.get_vllm_client.cache_clear()

    # main 실행
    await main()

    # (1) 유사 상표 검색 호출 확인
    assert mock_vector_store.search_similar_trademarks.call_count == 1
    
    # (2) 침해 위험 저장: High Risk인 '테스트침해1'만 저장되어야 함 (Low Risk는 Skip)
    assert mock_vector_store.save_infringe_risk.call_count == 1
    saved_risk_args = mock_vector_store.save_infringe_risk.call_args[0][0] # 첫번째 호출의 첫번째 인자(risk_data)
    assert saved_risk_args["c_tm"].c_trademark_name == "테스트침해1"
    assert saved_risk_args["ensemble_result"].risk_level == "H"

    # (3) 판례 검색: High Risk인 건에 대해서만 수행됨
    # Low Risk 건은 check_infringement에서 'end'로 빠지므로 판례 검색 안 함
    assert mock_vector_store.search_precedents.call_count == 1

    # (4) 메일 발송: 보호상표 1개에 대해 1번 호출됨
    assert mock_send_mail.call_count == 1
    
    # 메일 발송 인자 검증
    call_kwargs = mock_send_mail.call_args.kwargs
    assert call_kwargs["p_trademark_name"] == "테스트보호"
    assert call_kwargs["p_trademark_reg_no"] == "4019423700000"
    
    # approved_reports 리스트에는 High Risk인 1건만 들어있어야 함
    approved_reports = call_kwargs["approved_reports"]
    assert len(approved_reports) == 1
    assert approved_reports[0].c_trademark_name == "테스트침해1"
    assert approved_reports[0].risk_level == "H"



@pytest.mark.asyncio
async def test_real_workflow_execution():
    """
    [Real Data Test] Mock 없이 실제 LLM과 로직을 타는 통합 테스트
    - .env 환경변수를 로드합니다.
    - 실제 LangGraph 워크플로우(app)를 호출합니다.
    """
    # 1. 환경 변수 로드 (API Key, DB 접속 정보 등)
    load_dotenv()
    
    # 2. Container 초기화 (실제 구현체 주입)
    # 주의: 실제 DB 커넥션 풀과 VectorStore가 생성됩니다.
    container = Container()
    
    # 3. 테스트용 실제 데이터 구성 (예: '스타벅스' vs '스타박스')
    # 보호 상표 (원본)
    p_tm = ProtectionTrademarkInfo(
        p_trademark_reg_no="4020230000000",
        p_trademark_name="스타벅스",
        p_trademark_type="text",
        p_trademark_class_code="30",
        p_trademark_image="", # 필요 시 이미지 URL 또는 Base64
        p_trademark_image_vec=[0.1, 0.2, 0.3],
        p_trademark_user_no="TEST_USER_001"
    )
    
    # 수집 상표 (침해 의심)
    c_tm = CollectedTrademarkInfo(
        c_trademark_no="COL_TEST_001",
        c_product_name="스타박스 커피",
        c_product_page_url="http://test-shop.com/starbox",
        c_manufacturer_info="가짜커피주식회사",
        c_brand_info="스타박스",
        c_l_category="식품",
        c_m_category="커피",
        c_s_category="원두",
        c_trademark_type="text",
        c_trademark_class_code="30",
        c_trademark_name="스타박스",
        c_trademark_image="",
        c_trademark_image_vec=[0.1, 0.2, 0.3],
        c_trademark_ent_date=datetime.now()
    )

    # 4. 초기 GraphState 설정
    initial_state = GraphState(
        protection_trademark=p_tm,
        collected_trademarks=[c_tm],
        current_collected_trademark=c_tm, # 현재 처리할 상표 지정
        
        # 카운터 초기화
        rewrite_count=0,
        web_search_count=0,
        regeneration_count=0,
        is_infringement_found=False,
        
        # 나머지 필드는 None 또는 빈 값으로 시작해도 됨
        visual_similarity_score=0.0,
        visual_weight=0.0,
        phonetic_similarity_score=0.0,
        phonetic_weight=0.0,
        conceptual_similarity_score=0.0,
        conceptual_weight=0.0,
        ensemble_result=None,
        search_querys=[],
        retrieved_precedents=[],
        refined_precedents=[],
        grading_decision="",
        query_feedback="",
        web_search_keywords=[],
        is_precedent_exists=False,
        report_content="",
        evaluation_score=0.0,
        evaluation_feedback="",
        evaluation_decision=""
    )

    print("\n>>> [Start] Real Workflow Execution")
    
    # 5. 워크플로우 실행
    # ainvoke를 통해 비동기로 그래프 실행
    final_state = await app.ainvoke(initial_state)
    
    # 6. 결과 확인 및 출력
    print("\n>>> [Result] Workflow Finished")
    
    # (1) 앙상블 점수 확인
    if final_state.get("ensemble_result"):
        risk = final_state["ensemble_result"]
        print(f"--- Risk Analysis ---")
        print(f"Total Score: {risk.total_score}")
        print(f"Risk Level: {risk.risk_level}")
        print(f"Visual: {risk.visual_score}, Phonetic: {risk.phonetic_score}, Conceptual: {risk.conceptual_score}")
    
    # (2) 판례 검색 결과 확인
    precedents = final_state.get("retrieved_precedents", [])
    print(f"\n--- Precedents Found: {len(precedents)} ---")
    
    # (3) 보고서 생성 결과 확인
    report = final_state.get("report_content")
    if report:
        print("\n--- Generated Report ---")
        print(report[:500] + "..." if len(report) > 500 else report)
        
    # (4) 보고서 평가 점수 확인
    print(f"\n--- Report Evaluation ---")
    print(f"Score: {final_state.get('evaluation_score')}")
    print(f"Decision: {final_state.get('evaluation_decision')}")

    # 간단한 검증
    assert final_state is not None