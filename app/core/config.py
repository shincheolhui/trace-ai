# app/core/config.py
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # ===== OpenRouter =====
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # 임베딩 모델 (OpenRouter에서 지원하는 임베딩 모델)
    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    
    # LLM 모델 (채팅/추론용)
    LLM_MODEL: str = "openai/gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2000
    
    # ===== 지식 저장소 =====
    DATA_DIR: Path = Path("app/data")
    KNOWLEDGE_STORE_DIR: Path = Path("app/data/knowledge")
    FAISS_INDEX_DIR: Path = Path("app/data/faiss_index")
    
    # 청킹 설정
    CHUNK_SIZE: int = 500  # 문자 기준
    CHUNK_OVERLAP: int = 50
    
    # ===== Admin =====
    ADMIN_TOKEN: str = "dev-admin-token"  # MVP용 간단 토큰


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """설정 싱글톤"""
    return Settings()
