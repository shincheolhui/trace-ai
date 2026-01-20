# app/api/v1/admin_knowledge.py
"""지식 저장소 관리 API (Admin)"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.knowledge import (
    StoreType,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    DocumentListResponse,
    DeleteResponse,
    StoreStatsResponse,
)
from app.services.knowledge_service import get_knowledge_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/knowledge-store", tags=["Knowledge Store (Admin)"])


def verify_admin_token(x_admin_token: Optional[str] = Header(None)) -> None:
    """Admin 토큰 검증"""
    settings = get_settings()
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(
    store_type: StoreType = Form(..., description="저장소 유형"),
    tags: Optional[str] = Form(None, description="태그 (쉼표 구분)"),
    version: Optional[str] = Form(None, description="문서 버전"),
    files: List[UploadFile] = File(..., description="업로드할 문서 파일"),
    x_admin_token: Optional[str] = Header(None),
):
    """문서 적재 (업로드 → 파싱 → 임베딩 → 저장)
    
    지원 파일 형식:
    - PDF (.pdf)
    - 텍스트 (.txt, .md)
    """
    verify_admin_token(x_admin_token)
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    # 태그 파싱
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    
    # 파일 읽기
    file_data = []
    for file in files:
        content = await file.read()
        file_data.append((file.filename, content))
        logger.info(f"[api] Received file: {file.filename} ({len(content)} bytes)")
    
    # 적재 실행
    service = get_knowledge_service()
    result = await service.ingest_documents(
        files=file_data,
        store_type=store_type,
        tags=tag_list,
        version=version,
    )
    
    return result


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
    x_admin_token: Optional[str] = Header(None),
):
    """지식 저장소 검색
    
    쿼리를 임베딩하여 유사한 문서 청크를 검색합니다.
    """
    verify_admin_token(x_admin_token)
    
    service = get_knowledge_service()
    result = await service.search(
        query=request.query,
        store_type=request.store_type,
        top_k=request.top_k,
        filter_tags=request.filter_tags,
    )
    
    return result


@router.get("/docs", response_model=DocumentListResponse)
async def list_documents(
    store_type: StoreType,
    x_admin_token: Optional[str] = Header(None),
):
    """문서 목록 조회"""
    verify_admin_token(x_admin_token)
    
    service = get_knowledge_service()
    documents = service.list_documents(store_type)
    
    return DocumentListResponse(
        store_type=store_type,
        documents=documents,
        total_count=len(documents),
    )


@router.delete("/docs/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    store_type: StoreType,
    x_admin_token: Optional[str] = Header(None),
):
    """문서 삭제"""
    verify_admin_token(x_admin_token)
    
    service = get_knowledge_service()
    deleted = service.delete_document(doc_id, store_type)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {doc_id}"
        )
    
    return DeleteResponse(
        doc_id=doc_id,
        store_type=store_type,
        deleted=True,
        message="Document deleted successfully",
    )


@router.get("/stats", response_model=StoreStatsResponse)
async def get_store_stats(
    store_type: StoreType,
    x_admin_token: Optional[str] = Header(None),
):
    """저장소 통계 조회"""
    verify_admin_token(x_admin_token)
    
    service = get_knowledge_service()
    stats = service.get_store_stats(store_type)
    
    return StoreStatsResponse(**stats)
