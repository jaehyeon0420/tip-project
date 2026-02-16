import os
from functools import lru_cache
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from openai import AsyncOpenAI
from src.tools.vector_store import VectorStore
from src.configs import model_config

# 환경 변수 로드
load_dotenv()

class Container:
    """싱글톤 패턴 적용 의존성 주입 컨테이너"""
    
    @staticmethod
    @lru_cache(maxsize=1)
    def get_vector_store() -> VectorStore:
        return VectorStore()

    @staticmethod
    @lru_cache(maxsize=1)
    def get_gpt51_chat() -> AzureChatOpenAI:
        
        return AzureChatOpenAI(
            azure_deployment="gpt-5.1-chat",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2025-04-01-preview",
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def get_gpt4o() -> AzureChatOpenAI:
        
        return AzureChatOpenAI(
            azure_deployment="gpt-4o",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-12-01-preview"
        )
        
    @staticmethod
    @lru_cache(maxsize=1)
    def get_gpt4o_mini() -> AzureChatOpenAI:
        return AzureChatOpenAI(
            azure_deployment="gpt-4o-mini",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-12-01-preview"
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def get_vllm_client() -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=os.getenv("VLLM_API_KEY"), 
            base_url=os.getenv("VLLM_API_URL")
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def get_text_embedding_model() -> AzureOpenAIEmbeddings:
        return AzureOpenAIEmbeddings(
            azure_deployment="text-embedding-3-large",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        )