# app/integrations/llm/openrouter_client.py
"""OpenRouter API 클라이언트 - 임베딩 생성 및 LLM 호출"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """OpenRouter를 통한 임베딩 생성 및 LLM 호출 클라이언트"""
    
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
        # 임베딩 설정
        self.embedding_model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        # LLM 설정
        self.llm_model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        
        # 하위 호환성
        self.model = self.embedding_model
    
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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """LLM 채팅 완성
        
        Args:
            messages: OpenAI 형식의 메시지 리스트
                [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            model: 모델 이름 (기본값: 설정 파일)
            temperature: 온도 (기본값: 설정 파일)
            max_tokens: 최대 토큰 (기본값: 설정 파일)
            
        Returns:
            LLM 응답 텍스트
        """
        response = self.client.chat.completions.create(
            model=model or self.llm_model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        return response.choices[0].message.content
    
    def chat_with_system(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
    ) -> str:
        """시스템 프롬프트와 사용자 메시지로 간편 호출"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        return self.chat(messages, model=model)


@lru_cache(maxsize=1)
def get_openrouter_client() -> OpenRouterClient:
    """OpenRouter 클라이언트 싱글톤"""
    logger.info("[openrouter] Creating OpenRouter client")
    return OpenRouterClient()
