# app/integrations/llm/openrouter_client.py
"""OpenRouter API 클라이언트 - 임베딩 생성"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """OpenRouter를 통한 임베딩 생성 클라이언트"""
    
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def create_embedding(self, text: str) -> List[float]:
        """단일 텍스트 임베딩 생성"""
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """배치 임베딩 생성"""
        if not texts:
            return []
        
        # OpenAI API는 배치 처리 지원
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        
        # 인덱스 순서대로 정렬하여 반환
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding
        
        return embeddings


@lru_cache(maxsize=1)
def get_openrouter_client() -> OpenRouterClient:
    """OpenRouter 클라이언트 싱글톤"""
    logger.info("[openrouter] Creating OpenRouter client")
    return OpenRouterClient()
