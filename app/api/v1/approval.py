# app/api/v1/approval.py
"""승인 API 엔드포인트 - W3-2"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from app.schemas.agent import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatusResponse,
    PendingApprovalListResponse,
)
from app.services.approval_store import (
    get_pending_approval,
    approve_run,
    reject_run,
    list_pending_approvals,
)
from app.services.agent_service import resume_after_approval

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/approval", tags=["approval"])


@router.post("/approve", response_model=ApprovalResponse)
def approve_execution(req: ApprovalRequest):
    """실행 계획 승인"""
    logger.info(f"[approval] Approve request: run_id={req.run_id}")
    
    # 승인 처리
    pending = approve_run(req.run_id, req.approved_by, req.note)
    
    if not pending:
        return ApprovalResponse(
            run_id=req.run_id,
            status="not_found",
            message="승인 대기 중인 실행을 찾을 수 없습니다.",
        )
    
    if pending.status != "approved":
        return ApprovalResponse(
            run_id=req.run_id,
            status="already_resolved",
            message=f"이미 처리된 요청입니다. 상태: {pending.status}",
        )
    
    # 승인 후 실행 재개
    try:
        execution_result = resume_after_approval(req.run_id, pending.state_snapshot)
        return ApprovalResponse(
            run_id=req.run_id,
            status="approved",
            message="승인 완료. 실행이 재개되었습니다.",
            execution_result=execution_result,
        )
    except Exception as e:
        logger.error(f"[approval] Resume failed: {e}")
        return ApprovalResponse(
            run_id=req.run_id,
            status="approved",
            message=f"승인 완료. 실행 재개 중 오류 발생: {str(e)}",
        )


@router.post("/reject", response_model=ApprovalResponse)
def reject_execution(req: ApprovalRequest):
    """실행 계획 거부"""
    logger.info(f"[approval] Reject request: run_id={req.run_id}")
    
    # 거부 처리
    pending = reject_run(req.run_id, req.approved_by, req.note)
    
    if not pending:
        return ApprovalResponse(
            run_id=req.run_id,
            status="not_found",
            message="승인 대기 중인 실행을 찾을 수 없습니다.",
        )
    
    if pending.status != "rejected":
        return ApprovalResponse(
            run_id=req.run_id,
            status="already_resolved",
            message=f"이미 처리된 요청입니다. 상태: {pending.status}",
        )
    
    return ApprovalResponse(
        run_id=req.run_id,
        status="rejected",
        message="실행이 거부되었습니다.",
    )


@router.get("/status/{run_id}", response_model=ApprovalStatusResponse)
def get_approval_status(run_id: str):
    """승인 상태 조회"""
    pending = get_pending_approval(run_id)
    
    if not pending:
        return ApprovalStatusResponse(
            run_id=run_id,
            status="not_found",
        )
    
    return ApprovalStatusResponse(
        run_id=run_id,
        status=pending.status,
        action_plan=pending.action_plan,
        approval_reasons=pending.approval_reasons,
        created_at=pending.created_at.isoformat() if pending.created_at else None,
        resolved_at=pending.resolved_at.isoformat() if pending.resolved_at else None,
        resolved_by=pending.resolved_by,
    )


@router.get("/pending", response_model=PendingApprovalListResponse)
def get_pending_list():
    """대기 중인 승인 목록 조회"""
    pending_list = list_pending_approvals()
    
    approvals = [
        ApprovalStatusResponse(
            run_id=p.run_id,
            status=p.status,
            action_plan=p.action_plan,
            approval_reasons=p.approval_reasons,
            created_at=p.created_at.isoformat() if p.created_at else None,
        )
        for p in pending_list
    ]
    
    return PendingApprovalListResponse(
        count=len(approvals),
        pending_approvals=approvals,
    )
