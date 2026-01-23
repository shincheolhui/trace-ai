# app/api/v1/runs.py
"""실행 관련 API 엔드포인트 - W3-3"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from app.schemas.agent import AuditSummary
from app.services.audit_service import get_audit_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}/audit", response_model=AuditSummary)
def get_run_audit(run_id: str):
    """실행 감사 요약 조회"""
    logger.info(f"[runs] Get audit request: run_id={run_id}")
    
    audit = get_audit_summary(run_id)
    
    if not audit:
        raise HTTPException(status_code=404, detail=f"감사 요약을 찾을 수 없습니다: run_id={run_id}")
    
    return audit
