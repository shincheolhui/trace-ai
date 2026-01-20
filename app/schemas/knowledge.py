# app/schemas/knowledge.py
"""지식 저장소 관련 Pydantic 모델"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StoreType(str, Enum):
    """지식 저장소 유형"""
    POLICY = "policy"       # 정책/규정 문서
    INCIDENT = "incident"   # 장애 사례
    SYSTEM = "system"       # 시스템/업무 문서


class DocumentStatus(str, Enum):
    """문서 상태"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ===== Request Models =====

class IngestRequest(BaseModel):
    """문서 적재 요청 (JSON 부분)"""
    store_type: StoreType = Field(..., description="저장소 유형")
    tags: Optional[List[str]] = Field(default=None, description="태그 목록")
    version: Optional[str] = Field(default=None, description="문서 버전")


class SearchRequest(BaseModel):
    """검색 요청"""
    query: str = Field(..., min_length=1, description="검색 쿼리")
    store_type: StoreType = Field(..., description="검색 대상 저장소")
    top_k: int = Field(default=5, ge=1, le=20, description="반환 결과 수")
    filter_tags: Optional[List[str]] = Field(default=None, description="태그 필터")


# ===== Response Models =====

class ChunkInfo(BaseModel):
    """청크 정보"""
    chunk_id: str
    text_preview: str = Field(..., description="텍스트 미리보기 (앞 200자)")
    char_count: int


class DocumentInfo(BaseModel):
    """문서 정보"""
    doc_id: str
    filename: str
    store_type: StoreType
    status: DocumentStatus
    chunk_count: int = 0
    tags: List[str] = []
    version: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = {}


class IngestResponse(BaseModel):
    """문서 적재 응답"""
    ingest_id: str = Field(..., description="적재 작업 ID")
    status: DocumentStatus
    store_type: StoreType
    doc_ids: List[str] = Field(default_factory=list, description="저장된 문서 ID")
    chunk_count: int = Field(default=0, description="총 청크 수")
    error: Optional[str] = Field(default=None, description="실패 시 에러 메시지")


class SearchResult(BaseModel):
    """검색 결과 항목"""
    chunk_id: str
    doc_id: str
    score: float = Field(..., description="유사도 점수")
    text: str = Field(..., description="청크 텍스트")
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """검색 응답"""
    query: str
    store_type: StoreType
    results: List[SearchResult]
    total_count: int


class DocumentListResponse(BaseModel):
    """문서 목록 응답"""
    store_type: StoreType
    documents: List[DocumentInfo]
    total_count: int


class DeleteResponse(BaseModel):
    """문서 삭제 응답"""
    doc_id: str
    store_type: StoreType
    deleted: bool
    message: str


class StoreStatsResponse(BaseModel):
    """저장소 통계 응답"""
    store_type: StoreType
    document_count: int
    chunk_count: int
