# app/services/knowledge_service.py
"""지식 저장소 서비스 - 문서 적재/검색 파이프라인"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.integrations.llm.openrouter_client import get_openrouter_client
from app.integrations.parsers.pdf_parser import parse_pdf_bytes, extract_pdf_metadata_bytes
from app.integrations.parsers.text_parser import parse_text_bytes, chunk_text
from app.integrations.vectorstore.faiss_store import get_faiss_store
from app.schemas.knowledge import (
    StoreType,
    DocumentStatus,
    DocumentInfo,
    IngestResponse,
    SearchResult,
    SearchResponse,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """지식 저장소 관리 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.metadata_dir = self.settings.KNOWLEDGE_STORE_DIR / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_metadata_path(self, store_type: str) -> Path:
        """메타데이터 파일 경로"""
        return self.metadata_dir / f"{store_type}_docs.json"
    
    def _load_doc_metadata(self, store_type: str) -> Dict[str, Dict[str, Any]]:
        """문서 메타데이터 로드"""
        path = self._get_metadata_path(store_type)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}
    
    def _save_doc_metadata(self, store_type: str, metadata: Dict[str, Dict[str, Any]]) -> None:
        """문서 메타데이터 저장"""
        path = self._get_metadata_path(store_type)
        path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8"
        )
    
    def _detect_file_type(self, filename: str) -> str:
        """파일 유형 감지"""
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return "pdf"
        elif ext in [".txt", ".md", ".markdown"]:
            return "text"
        else:
            return "unknown"
    
    async def ingest_document(
        self,
        filename: str,
        content: bytes,
        store_type: StoreType,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None,
    ) -> IngestResponse:
        """단일 문서 적재
        
        파이프라인: 파싱 → 청킹 → 임베딩 → 저장
        """
        ingest_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        
        logger.info(f"[knowledge] Starting ingest: {filename} -> {store_type.value} (ingest_id={ingest_id})")
        
        try:
            # 1. 파싱
            file_type = self._detect_file_type(filename)
            if file_type == "pdf":
                text = parse_pdf_bytes(content, filename)
                file_metadata = extract_pdf_metadata_bytes(content)
            elif file_type == "text":
                text = parse_text_bytes(content, filename)
                file_metadata = {}
            else:
                raise ValueError(f"Unsupported file type: {filename}")
            
            if not text or not text.strip():
                raise ValueError(f"No text extracted from {filename}")
            
            logger.info(f"[knowledge] Parsed {filename}: {len(text)} chars")
            
            # 2. 청킹
            chunks = chunk_text(text)
            if not chunks:
                raise ValueError(f"No chunks created from {filename}")
            
            logger.info(f"[knowledge] Created {len(chunks)} chunks from {filename}")
            
            # 3. 임베딩 생성
            client = get_openrouter_client()
            embeddings = client.create_embeddings(chunks)
            
            logger.info(f"[knowledge] Generated {len(embeddings)} embeddings")
            
            # 4. 벡터 저장소에 저장
            store = get_faiss_store(store_type.value)
            
            chunk_ids = []
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_{i}"
                chunk_ids.append(chunk_id)
                chunk_metadatas.append({
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "filename": filename,
                    "store_type": store_type.value,
                    "tags": tags or [],
                    "version": version,
                    "text": chunk,  # 검색 결과에서 텍스트 반환용
                })
            
            store.add(embeddings, chunk_metadatas, chunk_ids)
            store.save()
            
            # 5. 문서 메타데이터 저장
            doc_metadata = self._load_doc_metadata(store_type.value)
            doc_metadata[doc_id] = {
                "doc_id": doc_id,
                "filename": filename,
                "store_type": store_type.value,
                "status": DocumentStatus.COMPLETED.value,
                "chunk_count": len(chunks),
                "tags": tags or [],
                "version": version,
                "created_at": datetime.now().isoformat(),
                "metadata": file_metadata,
            }
            self._save_doc_metadata(store_type.value, doc_metadata)
            
            logger.info(f"[knowledge] Ingest completed: {filename} (doc_id={doc_id}, chunks={len(chunks)})")
            
            return IngestResponse(
                ingest_id=ingest_id,
                status=DocumentStatus.COMPLETED,
                store_type=store_type,
                doc_ids=[doc_id],
                chunk_count=len(chunks),
            )
            
        except Exception as e:
            logger.error(f"[knowledge] Ingest failed: {filename} - {e}")
            return IngestResponse(
                ingest_id=ingest_id,
                status=DocumentStatus.FAILED,
                store_type=store_type,
                doc_ids=[],
                chunk_count=0,
                error=str(e),
            )
    
    async def ingest_documents(
        self,
        files: List[tuple[str, bytes]],  # (filename, content) 튜플
        store_type: StoreType,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None,
    ) -> IngestResponse:
        """다중 문서 적재"""
        ingest_id = str(uuid.uuid4())
        all_doc_ids = []
        total_chunks = 0
        errors = []
        
        for filename, content in files:
            result = await self.ingest_document(
                filename=filename,
                content=content,
                store_type=store_type,
                tags=tags,
                version=version,
            )
            
            if result.status == DocumentStatus.COMPLETED:
                all_doc_ids.extend(result.doc_ids)
                total_chunks += result.chunk_count
            else:
                errors.append(f"{filename}: {result.error}")
        
        status = DocumentStatus.COMPLETED if not errors else DocumentStatus.FAILED
        error_msg = "; ".join(errors) if errors else None
        
        return IngestResponse(
            ingest_id=ingest_id,
            status=status,
            store_type=store_type,
            doc_ids=all_doc_ids,
            chunk_count=total_chunks,
            error=error_msg,
        )
    
    async def search(
        self,
        query: str,
        store_type: StoreType,
        top_k: int = 5,
        filter_tags: Optional[List[str]] = None,
    ) -> SearchResponse:
        """지식 저장소 검색"""
        logger.info(f"[knowledge] Search: '{query}' in {store_type.value} (top_k={top_k})")
        
        # 쿼리 임베딩 생성
        client = get_openrouter_client()
        query_embedding = client.create_embedding(query)
        
        # 벡터 검색
        store = get_faiss_store(store_type.value)
        
        # 태그 필터 처리 (FAISS는 직접 필터링 불가, 후처리로 해결)
        search_results = store.search(query_embedding, top_k=top_k * 2 if filter_tags else top_k)
        
        results = []
        for chunk_id, score, metadata in search_results:
            # 태그 필터링
            if filter_tags:
                chunk_tags = metadata.get("tags", [])
                if not any(tag in chunk_tags for tag in filter_tags):
                    continue
            
            results.append(SearchResult(
                chunk_id=chunk_id,
                doc_id=metadata.get("doc_id", ""),
                score=score,
                text=metadata.get("text", ""),
                metadata={
                    "filename": metadata.get("filename", ""),
                    "tags": metadata.get("tags", []),
                    "version": metadata.get("version"),
                    "chunk_index": metadata.get("chunk_index", 0),
                },
            ))
            
            if len(results) >= top_k:
                break
        
        logger.info(f"[knowledge] Found {len(results)} results for '{query}'")
        
        return SearchResponse(
            query=query,
            store_type=store_type,
            results=results,
            total_count=len(results),
        )
    
    def list_documents(self, store_type: StoreType) -> List[DocumentInfo]:
        """문서 목록 조회"""
        doc_metadata = self._load_doc_metadata(store_type.value)
        
        documents = []
        for doc_id, meta in doc_metadata.items():
            documents.append(DocumentInfo(
                doc_id=doc_id,
                filename=meta.get("filename", ""),
                store_type=StoreType(meta.get("store_type", store_type.value)),
                status=DocumentStatus(meta.get("status", "completed")),
                chunk_count=meta.get("chunk_count", 0),
                tags=meta.get("tags", []),
                version=meta.get("version"),
                created_at=datetime.fromisoformat(meta.get("created_at", datetime.now().isoformat())),
                metadata=meta.get("metadata", {}),
            ))
        
        return documents
    
    def delete_document(self, doc_id: str, store_type: StoreType) -> bool:
        """문서 삭제"""
        logger.info(f"[knowledge] Deleting document: {doc_id} from {store_type.value}")
        
        # 메타데이터에서 문서 정보 조회
        doc_metadata = self._load_doc_metadata(store_type.value)
        
        if doc_id not in doc_metadata:
            logger.warning(f"[knowledge] Document not found: {doc_id}")
            return False
        
        doc_info = doc_metadata[doc_id]
        chunk_count = doc_info.get("chunk_count", 0)
        
        # 청크 ID 목록 생성
        chunk_ids = [f"{doc_id}_{i}" for i in range(chunk_count)]
        
        # 벡터 저장소에서 삭제
        store = get_faiss_store(store_type.value)
        store.delete(chunk_ids)
        store.save()
        
        # 메타데이터에서 삭제
        del doc_metadata[doc_id]
        self._save_doc_metadata(store_type.value, doc_metadata)
        
        logger.info(f"[knowledge] Deleted document: {doc_id} ({chunk_count} chunks)")
        return True
    
    def get_store_stats(self, store_type: StoreType) -> dict:
        """저장소 통계"""
        doc_metadata = self._load_doc_metadata(store_type.value)
        store = get_faiss_store(store_type.value)
        
        return {
            "store_type": store_type.value,
            "document_count": len(doc_metadata),
            "chunk_count": store.count(),
        }


# 서비스 싱글톤
_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """KnowledgeService 싱글톤"""
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service
