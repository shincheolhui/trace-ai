# app/agent/state.py
"""LangGraph 상태 정의"""
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ComplianceResult(BaseModel):
    """규정 위반 감지 결과"""
    status: Literal["violation", "no_violation", "potential_violation"] = "no_violation"
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class RCAResult(BaseModel):
    """장애 RCA 결과"""
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class WorkflowResult(BaseModel):
    """업무 실행 계획 결과"""
    action_plan: List[Dict[str, Any]] = Field(default_factory=list)
    approvals_required: List[str] = Field(default_factory=list)
    summary: str = ""


class AgentState(BaseModel):
    """LangGraph 전역 상태"""
    # 기본 정보
    run_id: str
    user_input: Optional[str] = None
    files: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Intent 분류
    intent: Literal["compliance", "rca", "workflow", "mixed", "unknown"] = "unknown"
    
    # 서브그래프 결과
    compliance_result: Optional[ComplianceResult] = None
    rca_result: Optional[RCAResult] = None
    workflow_result: Optional[WorkflowResult] = None
    
    # 공통 필드
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_results: Dict[str, Any] = Field(default_factory=dict)
    action_plan: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 승인 관련
    approval_required: bool = False
    approval_status: Literal["pending", "approved", "rejected", "not_required"] = "not_required"
    
    # 실행 및 로그
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    # 추적용
    trace: Dict[str, Any] = Field(default_factory=dict)
