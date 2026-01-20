# app/integrations/vectorstore/base.py
"""VectorStore 추상 인터페이스"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class VectorStoreBase(ABC):
    """벡터 저장소 추상 클래스"""
    
    @abstractmethod
    def add(
        self,
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """벡터 및 메타데이터 추가
        
        Args:
            embeddings: 임베딩 벡터 리스트
            metadatas: 메타데이터 리스트
            ids: 문서/청크 ID 리스트
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """유사도 검색
        
        Args:
            query_embedding: 쿼리 임베딩 벡터
            top_k: 반환할 결과 수
            filter_metadata: 메타데이터 필터 (선택)
            
        Returns:
            (id, score, metadata) 튜플 리스트
        """
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """ID로 벡터 삭제
        
        Args:
            ids: 삭제할 ID 리스트
        """
        pass
    
    @abstractmethod
    def save(self) -> None:
        """인덱스 영속화"""
        pass
    
    @abstractmethod
    def load(self) -> bool:
        """인덱스 로드
        
        Returns:
            로드 성공 여부
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """저장된 벡터 수 반환"""
        pass
