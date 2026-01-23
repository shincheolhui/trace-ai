# app/schemas/agent.py
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    run_id: str
    status: Literal["COMPLETED", "PENDING_APPROVAL", "REJECTED", "ERROR"]
    result: Dict[str, Any]
    
    # 승인 대기 시 추가 정보
    approval_required: bool = False
    approval_reasons: List[str] = Field(default_factory=list)
    action_plan_preview: List[Dict[str, Any]] = Field(default_factory=list)


# ===== 승인 관련 스키마 =====

class ApprovalRequest(BaseModel):
    """승인/거부 요청"""
    run_id: str
    approved_by: str = "user"
    note: str = ""


class ApprovalResponse(BaseModel):
    """승인/거부 응답"""
    run_id: str
    status: Literal["approved", "rejected", "not_found", "already_resolved"]
    message: str
    
    # 승인 후 재개 결과 (승인 시에만)
    execution_result: Optional[Dict[str, Any]] = None


class ApprovalStatusResponse(BaseModel):
    """승인 상태 조회 응답"""
    run_id: str
    status: Literal["pending", "approved", "rejected", "expired", "not_found"]
    action_plan: List[Dict[str, Any]] = Field(default_factory=list)
    approval_reasons: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None


class PendingApprovalListResponse(BaseModel):
    """대기 중인 승인 목록 응답"""
    count: int
    pending_approvals: List[ApprovalStatusResponse] = Field(default_factory=list)


# ===== 감사 관련 스키마 =====

class ApprovalRecord(BaseModel):
    """승인 내역"""
    run_id: str
    status: Literal["pending", "approved", "rejected"]
    approved_by: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


class AuditSummary(BaseModel):
    """감사 요약"""
    audit_id: str
    run_id: str
    user: str = "system"  # MVP에서는 기본값 사용
    started_at: str
    finished_at: str
    intent: Literal["compliance", "rca", "workflow", "mixed", "unknown"]
    summary: str
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)
    approvals: List[ApprovalRecord] = Field(default_factory=list)
    actions_executed: List[Dict[str, Any]] = Field(default_factory=list)
    result_status: Literal["SUCCESS", "PARTIAL", "FAILED"]
    
    # 추가 정보
    analysis_results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    trace_summary: Dict[str, Any] = Field(default_factory=dict)
