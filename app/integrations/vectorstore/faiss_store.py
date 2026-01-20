# app/integrations/vectorstore/faiss_store.py
"""FAISS 기반 벡터 저장소 구현"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

from app.core.config import get_settings
from app.integrations.vectorstore.base import VectorStoreBase

logger = logging.getLogger(__name__)


class FAISSVectorStore(VectorStoreBase):
    """FAISS 벡터 저장소
    
    - FAISS 인덱스: 벡터 검색
    - JSON 파일: 메타데이터 저장 (FAISS는 메타데이터 미지원)
    """
    
    def __init__(self, store_type: str, dimension: int = None):
        """
        Args:
            store_type: 저장소 유형 (policy, incident, system)
            dimension: 임베딩 차원
        """
        settings = get_settings()
        self.store_type = store_type
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        
        # 저장 경로
        self.base_dir = settings.FAISS_INDEX_DIR / store_type
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.base_dir / "index.faiss"
        self.metadata_path = self.base_dir / "metadata.json"
        
        # 인덱스 및 메타데이터
        self.index: Optional[faiss.IndexFlatIP] = None  # Inner Product (코사인 유사도용)
        self.id_to_idx: Dict[str, int] = {}  # id -> faiss index
        self.idx_to_id: Dict[int, str] = {}  # faiss index -> id
        self.metadatas: Dict[str, Dict[str, Any]] = {}  # id -> metadata
        
        # 기존 인덱스 로드 시도
        self.load()
    
    def _init_index(self) -> None:
        """새 인덱스 초기화"""
        # Inner Product 인덱스 (정규화된 벡터에서는 코사인 유사도와 동일)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_to_idx = {}
        self.idx_to_id = {}
        self.metadatas = {}
        logger.info(f"[faiss] Initialized new index for '{self.store_type}' (dim={self.dimension})")
    
    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2 정규화 (코사인 유사도 계산용)"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # 0벡터 방지
        return vectors / norms
    
    def add(
        self,
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        """벡터 및 메타데이터 추가"""
        if not embeddings:
            return
        
        if self.index is None:
            self._init_index()
        
        # numpy 배열로 변환 및 정규화
        vectors = np.array(embeddings, dtype=np.float32)
        vectors = self._normalize(vectors)
        
        # 현재 인덱스 크기
        start_idx = self.index.ntotal
        
        # FAISS에 추가
        self.index.add(vectors)
        
        # 매핑 및 메타데이터 저장
        for i, (doc_id, metadata) in enumerate(zip(ids, metadatas)):
            idx = start_idx + i
            self.id_to_idx[doc_id] = idx
            self.idx_to_id[idx] = doc_id
            self.metadatas[doc_id] = metadata
        
        logger.info(f"[faiss] Added {len(ids)} vectors to '{self.store_type}' (total: {self.index.ntotal})")
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """유사도 검색"""
        if self.index is None or self.index.ntotal == 0:
            logger.warning(f"[faiss] Empty index for '{self.store_type}'")
            return []
        
        # 쿼리 벡터 정규화
        query_vec = np.array([query_embedding], dtype=np.float32)
        query_vec = self._normalize(query_vec)
        
        # 검색 (필터링 고려하여 더 많이 가져옴)
        search_k = min(top_k * 3, self.index.ntotal) if filter_metadata else top_k
        scores, indices = self.index.search(query_vec, search_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS에서 결과 없음 표시
                continue
            
            doc_id = self.idx_to_id.get(int(idx))
            if doc_id is None:
                continue
            
            metadata = self.metadatas.get(doc_id, {})
            
            # 메타데이터 필터링
            if filter_metadata:
                match = all(
                    metadata.get(k) == v 
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue
            
            results.append((doc_id, float(score), metadata))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def delete(self, ids: List[str]) -> None:
        """ID로 벡터 삭제
        
        Note: FAISS IndexFlatIP는 직접 삭제를 지원하지 않음
        재구축 방식으로 처리 (비효율적이지만 MVP 기준)
        """
        if self.index is None:
            return
        
        # 삭제할 ID 제외하고 재구축
        remaining_ids = [doc_id for doc_id in self.id_to_idx.keys() if doc_id not in ids]
        
        if not remaining_ids:
            self._init_index()
            logger.info(f"[faiss] Deleted all vectors from '{self.store_type}'")
            return
        
        # 기존 벡터/메타데이터 백업
        old_metadatas = self.metadatas.copy()
        
        # 기존 벡터 추출
        old_indices = [self.id_to_idx[doc_id] for doc_id in remaining_ids]
        vectors = np.zeros((len(old_indices), self.dimension), dtype=np.float32)
        for i, idx in enumerate(old_indices):
            vectors[i] = self.index.reconstruct(idx)
        
        # 재초기화 및 재추가
        self._init_index()
        self.index.add(vectors)
        
        for i, doc_id in enumerate(remaining_ids):
            self.id_to_idx[doc_id] = i
            self.idx_to_id[i] = doc_id
            self.metadatas[doc_id] = old_metadatas[doc_id]
        
        logger.info(f"[faiss] Deleted {len(ids)} vectors from '{self.store_type}' (remaining: {self.index.ntotal})")
    
    def save(self) -> None:
        """인덱스 영속화"""
        if self.index is None:
            return
        
        # FAISS 인덱스 저장
        faiss.write_index(self.index, str(self.index_path))
        
        # 메타데이터 저장
        metadata_dump = {
            "id_to_idx": self.id_to_idx,
            "idx_to_id": {str(k): v for k, v in self.idx_to_id.items()},
            "metadatas": self.metadatas,
        }
        self.metadata_path.write_text(
            json.dumps(metadata_dump, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.info(f"[faiss] Saved index for '{self.store_type}' ({self.index.ntotal} vectors)")
    
    def load(self) -> bool:
        """인덱스 로드"""
        if not self.index_path.exists() or not self.metadata_path.exists():
            logger.info(f"[faiss] No existing index for '{self.store_type}'")
            return False
        
        try:
            # FAISS 인덱스 로드
            self.index = faiss.read_index(str(self.index_path))
            
            # 메타데이터 로드
            metadata_dump = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            self.id_to_idx = metadata_dump["id_to_idx"]
            self.idx_to_id = {int(k): v for k, v in metadata_dump["idx_to_id"].items()}
            self.metadatas = metadata_dump["metadatas"]
            
            logger.info(f"[faiss] Loaded index for '{self.store_type}' ({self.index.ntotal} vectors)")
            return True
        except Exception as e:
            logger.error(f"[faiss] Failed to load index for '{self.store_type}': {e}")
            self._init_index()
            return False
    
    def count(self) -> int:
        """저장된 벡터 수 반환"""
        if self.index is None:
            return 0
        return self.index.ntotal


# 저장소 유형별 싱글톤 캐시
_stores: Dict[str, FAISSVectorStore] = {}


def get_faiss_store(store_type: str) -> FAISSVectorStore:
    """저장소 유형별 FAISS 인스턴스 반환
    
    Args:
        store_type: policy, incident, system
        
    Returns:
        FAISSVectorStore 인스턴스
    """
    if store_type not in _stores:
        _stores[store_type] = FAISSVectorStore(store_type)
    return _stores[store_type]
