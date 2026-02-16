from typing import TypedDict, List, Optional
from src.model.schema import ProtectionTrademarkInfo, CollectedTrademarkInfo, InfringementRisk, Precedent

class GraphState(TypedDict):
    
    # 상표 정보
    protection_trademark: ProtectionTrademarkInfo       # 보호 상표
    collected_trademarks: List[CollectedTrademarkInfo]  # 수집 상표 리스트
    current_collected_trademark: CollectedTrademarkInfo # 처리중인 수집 상표 정보
    
    # 모델 점수 및 가중치
    visual_similarity_score : float                     # 시각
    visual_weight: float                                # 시각 가중치
    
    phonetic_similarity_score: float                    # 발음
    phonetic_weight: float                              # 발음 가중치
    conceptual_similarity_score: float                  # 관념
    conceptual_weight: float                            # 관념 가중치
    conceptual_description: str                         # 관념 묘사문
    ensemble_result: Optional[InfringementRisk]         # 앙상블
    
    # RAG 관련
    search_querys: List[str]                            # 판례 정보 조회 질문 쿼리
    retrieved_precedents: List[Precedent]               # 판례 정보 조회 결과
    refined_precedents: List[Precedent]                 # 판례 정보 조회 결과 정제
    grading_decision: str                               # 판례 검증 결과    
    query_feedback: str                                 # 판례 정보 조회 질문 쿼리 재생성 피드백
    web_search_keywords: List[str]                      # 웹 검색용 키워드 리스트
    is_precedent_exists: bool                           # 판례 존재 여부
    
    # 보고서 관련
    report_content: str                                 # 보고서 내용
    evaluation_score: float                             # 보고서 평가 점수
    evaluation_feedback: str                            # 보고서 평가 피드백
    evaluation_decision: str                            # 보고서 평가 결정 (approved, regenerate, rewrite_all)
    
    # 제어 플래그 및 카운터
    rewrite_count: int                                  # 판례 정보 조회 질문 쿼리 재생성 카운터
    web_search_count: int                               # 웹 검색 시도 횟수
    regeneration_count: int                             # 보고서 생성 재생성 카운터 
    is_infringement_found: bool                         # 위험군으로 식별되었는지 여부
