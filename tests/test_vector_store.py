import pytest
import asyncio
from src.container import Container
from src.utils.db import Database
from typing import List, Dict, Any

# 비동기 테스트를 위한 설정
# cd c:\ms-third-workspace\tip-project
# python -m tests.test_vector_store
@pytest.mark.asyncio
async def test_search_similar_trademarks():
    """
    VectorStore.search_similar_trademarks 메서드 통합 테스트
    실제 DB에 연결하여 데이터를 조회하고 구조를 검증합니다.
    """
    
    # 1. DB 연결 초기화
    try:
        pool = await Database.get_pool()
        assert pool is not None
    except Exception as e:
        pytest.fail(f"DB Connection Failed: {e}")

    vector_store = Container.get_vector_store()
    
    # 2. 메서드 실행 (Threshold는 테스트 데이터에 맞춰 조정 가능)
    # 실제 데이터가 없을 수 있으므로 에러가 나지 않는지 우선 확인
    try:
        results = await vector_store.search_similar_trademarks() # 테스트를 위해 낮은 임계값 사용
        
        # 3. 결과 구조 검증
        assert isinstance(results, list)
        
        for group in results:
            assert isinstance(group, dict)
            assert "protection_trademark" in group
            assert "collected_trademarks" in group
            
            p_tm = group["protection_trademark"]
            c_tm_list = group["collected_trademarks"]
            
            assert isinstance(p_tm, dict)
            assert isinstance(c_tm_list, list)
            
            # 필수 필드 존재 여부 확인 (Protection Trademark)
            assert "trademark_id" in p_tm
            assert "trademark_name" in p_tm
            
            # 수집 상표 리스트가 있는 경우 내부 검증
            if c_tm_list:
                c_tm = c_tm_list[0]
                assert isinstance(c_tm, dict)
                assert "c_trademark_no" in c_tm
                assert "product_trademark_name" in c_tm
                
    except Exception as e:
        pytest.fail(f"Method Execution Failed: {e}")
        
    finally:
        # 리소스 정리
        await Database.close()

if __name__ == "__main__":
    # 스크립트로 직접 실행 시
    asyncio.run(test_search_similar_trademarks())
