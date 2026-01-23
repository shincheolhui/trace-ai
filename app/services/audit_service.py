# app/services/audit_service.py
"""감사 요약 생성 서비스 - W3-3"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal
from uuid import uuid4

from app.schemas.agent import ApprovalRecord, AuditSummary
from app.services.approval_store import get_pending_approval

logger = logging.getLogger(__name__)

# 감사 저장 디렉터리 (MVP용)
AUDIT_DIR = Path("audit")
AUDIT_DIR.mkdir(exist_ok=True)


def generate_audit_id() -> str:
    """감사 ID 생성"""
    return f"audit_{uuid4().hex[:8]}"


def create_audit_summary(
    run_id: str,
    state: Dict[str, Any],
    started_at: datetime,
    finished_at: datetime,
) -> AuditSummary:
    """감사 요약 생성"""
    
    # Intent
    intent = state.get("intent", "unknown")
    
    # 요약 생성
    summary_parts = []
    
    # Compliance 결과
    if state.get("compliance_result"):
        compliance = state.get("compliance_result", {})
        if isinstance(compliance, dict):
            summary_parts.append(f"[규정검사] {compliance.get('summary', '')}")
        else:
            summary_parts.append(f"[규정검사] {compliance.summary if hasattr(compliance, 'summary') else ''}")
    
    # RCA 결과
    if state.get("rca_result"):
        rca = state.get("rca_result", {})
        if isinstance(rca, dict):
            summary_parts.append(f"[원인분석] {rca.get('summary', '')}")
        else:
            summary_parts.append(f"[원인분석] {rca.summary if hasattr(rca, 'summary') else ''}")
    
    # Workflow 결과
    if state.get("workflow_result"):
        workflow = state.get("workflow_result", {})
        if isinstance(workflow, dict):
            summary_parts.append(f"[실행계획] {workflow.get('summary', '')}")
        else:
            summary_parts.append(f"[실행계획] {workflow.summary if hasattr(workflow, 'summary') else ''}")
    
    # Mixed intent인 경우 integrated_summary 사용
    if intent == "mixed" and state.get("analysis_results", {}).get("integrated_summary"):
        summary = state["analysis_results"]["integrated_summary"]
    elif summary_parts:
        summary = " | ".join(summary_parts)
    else:
        summary = f"{intent} 요청 처리 완료"
    
    # Evidence 수집
    evidence_refs = []
    
    # Compliance evidence
    if state.get("compliance_result"):
        compliance = state.get("compliance_result", {})
        if isinstance(compliance, dict):
            evidence_refs.extend(compliance.get("evidence", []))
        elif hasattr(compliance, "evidence"):
            evidence_refs.extend(compliance.evidence)
    
    # RCA evidence
    if state.get("rca_result"):
        rca = state.get("rca_result", {})
        if isinstance(rca, dict):
            evidence_refs.extend(rca.get("evidence", []))
        elif hasattr(rca, "evidence"):
            evidence_refs.extend(rca.evidence)
    
    # Global evidence
    evidence_refs.extend(state.get("evidence", []))
    
    # 중복 제거 (간단한 방법)
    seen = set()
    unique_evidence = []
    for ev in evidence_refs:
        ev_id = ev.get("id") or ev.get("chunk_id") or str(ev)
        if ev_id not in seen:
            seen.add(ev_id)
            unique_evidence.append(ev)
    evidence_refs = unique_evidence[:10]  # 최대 10개
    
    # 승인 내역 수집
    approvals = []
    approval_status = state.get("approval_status", "not_required")
    
    if approval_status in ["pending", "approved", "rejected"]:
        pending = get_pending_approval(run_id)
        if pending:
            approvals.append(ApprovalRecord(
                run_id=run_id,
                status=pending.status,
                approved_by=pending.resolved_by,
                note=pending.resolution_note,
                created_at=pending.created_at.isoformat() if pending.created_at else None,
                resolved_at=pending.resolved_at.isoformat() if pending.resolved_at else None,
            ))
    
    # 실행된 액션 수집
    actions_executed = []
    
    # Action plan에서 실행된 항목
    action_plan = state.get("action_plan", [])
    for step in action_plan:
        actions_executed.append({
            "step": step.get("step", 0),
            "title": step.get("title", ""),
            "status": "planned",  # MVP에서는 planned로 표시
            "risk_level": step.get("risk_level", "unknown"),
        })
    
    # Execution results
    execution_results = state.get("execution_results", [])
    for exec_result in execution_results:
        actions_executed.append({
            "step": exec_result.get("step", "unknown"),
            "title": exec_result.get("message", ""),
            "status": exec_result.get("status", "unknown"),
        })
    
    # 결과 상태 결정
    errors = state.get("errors", [])
    has_results = bool(state.get("analysis_results") or state.get("compliance_result") or state.get("rca_result") or state.get("workflow_result"))
    
    if errors and not has_results:
        result_status = "FAILED"
    elif errors:
        result_status = "PARTIAL"
    else:
        result_status = "SUCCESS"
    
    # Trace 요약 (주요 노드만)
    trace = state.get("trace", {})
    trace_summary = {
        "intent_classified": trace.get("classify_intent", {}).get("status") == "success",
        "subgraphs_executed": [],
        "approval_checked": trace.get("check_approval", {}).get("status") == "success",
        "finalized": trace.get("finalize", {}).get("status") == "success",
    }
    
    if trace.get("compliance_subgraph"):
        trace_summary["subgraphs_executed"].append("compliance")
    if trace.get("rca_subgraph"):
        trace_summary["subgraphs_executed"].append("rca")
    if trace.get("workflow_subgraph"):
        trace_summary["subgraphs_executed"].append("workflow")
    if trace.get("mixed_summary"):
        trace_summary["subgraphs_executed"].append("mixed")
    
    # AuditSummary 생성
    audit = AuditSummary(
        audit_id=generate_audit_id(),
        run_id=run_id,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        intent=intent,
        summary=summary,
        evidence_refs=evidence_refs,
        approvals=approvals,
        actions_executed=actions_executed,
        result_status=result_status,
        analysis_results=state.get("analysis_results", {}),
        errors=errors,
        trace_summary=trace_summary,
    )
    
    logger.info(f"[audit_service] Generated audit summary: audit_id={audit.audit_id}, run_id={run_id}")
    return audit


def save_audit_summary(audit: AuditSummary) -> str:
    """감사 요약 저장 (JSON 파일)"""
    # 파일명: audit_{run_id}.json
    filepath = AUDIT_DIR / f"audit_{audit.run_id}.json"
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(audit.model_dump(), f, ensure_ascii=False, indent=2)
    
    logger.info(f"[audit_service] Saved audit summary: {filepath}")
    return str(filepath)


def get_audit_summary(run_id: str) -> AuditSummary | None:
    """감사 요약 조회"""
    filepath = AUDIT_DIR / f"audit_{run_id}.json"
    
    if not filepath.exists():
        logger.warning(f"[audit_service] Audit not found: {filepath}")
        return None
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return AuditSummary(**data)
