# app/services/approval_store.py
"""승인 대기 상태 저장소 (인메모리, MVP용)"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PendingApproval(BaseModel):
    """승인 대기 상태"""
    run_id: str
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    
    # 승인 대기 중인 상태 스냅샷
    state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    
    # 승인 요청 정보
    action_plan: list = Field(default_factory=list)
    approval_reasons: list = Field(default_factory=list)
    
    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    # 승인/거부 정보
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None


# 인메모리 저장소 (해커톤 MVP용)
_pending_approvals: Dict[str, PendingApproval] = {}


def save_pending_approval(
    run_id: str,
    state_snapshot: Dict[str, Any],
    action_plan: list,
    approval_reasons: list,
) -> PendingApproval:
    """승인 대기 상태 저장"""
    pending = PendingApproval(
        run_id=run_id,
        state_snapshot=state_snapshot,
        action_plan=action_plan,
        approval_reasons=approval_reasons,
    )
    _pending_approvals[run_id] = pending
    logger.info(f"[approval_store] Saved pending approval: run_id={run_id}")
    return pending


def get_pending_approval(run_id: str) -> Optional[PendingApproval]:
    """승인 대기 상태 조회"""
    return _pending_approvals.get(run_id)


def approve_run(run_id: str, approved_by: str = "user", note: str = "") -> Optional[PendingApproval]:
    """실행 승인"""
    pending = _pending_approvals.get(run_id)
    if not pending:
        logger.warning(f"[approval_store] Approval not found: run_id={run_id}")
        return None
    
    if pending.status != "pending":
        logger.warning(f"[approval_store] Already resolved: run_id={run_id}, status={pending.status}")
        return pending
    
    pending.status = "approved"
    pending.resolved_at = datetime.utcnow()
    pending.resolved_by = approved_by
    pending.resolution_note = note
    
    logger.info(f"[approval_store] Approved: run_id={run_id}, by={approved_by}")
    return pending


def reject_run(run_id: str, rejected_by: str = "user", note: str = "") -> Optional[PendingApproval]:
    """실행 거부"""
    pending = _pending_approvals.get(run_id)
    if not pending:
        logger.warning(f"[approval_store] Approval not found: run_id={run_id}")
        return None
    
    if pending.status != "pending":
        logger.warning(f"[approval_store] Already resolved: run_id={run_id}, status={pending.status}")
        return pending
    
    pending.status = "rejected"
    pending.resolved_at = datetime.utcnow()
    pending.resolved_by = rejected_by
    pending.resolution_note = note
    
    logger.info(f"[approval_store] Rejected: run_id={run_id}, by={rejected_by}")
    return pending


def list_pending_approvals() -> list[PendingApproval]:
    """대기 중인 승인 목록 조회"""
    return [p for p in _pending_approvals.values() if p.status == "pending"]


def get_approval_status(run_id: str) -> Optional[str]:
    """승인 상태만 조회"""
    pending = _pending_approvals.get(run_id)
    return pending.status if pending else None
