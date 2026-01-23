# app/services/agent_service.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.agent.orchestrator import get_graph
from app.agent.state import AgentState
from app.core.run_context import get_run_id
from app.services.approval_store import save_pending_approval

logger = logging.getLogger(__name__)


def run_agent(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Agent 실행 - 승인 대기 상태 처리 포함"""
    run_id = get_run_id()  # W1-2에서 contextvar로 전파됨
    if not run_id:
        # W1-2 전제상 발생하면 안되지만, 안전망
        run_id = "UNKNOWN"
    
    # 시작 시간 기록
    started_at = datetime.now(timezone.utc)
    
    # context에 시작 시간 추가
    if context is None:
        context = {}
    context["_started_at"] = started_at.isoformat()

    state = AgentState(
        run_id=run_id,
        user_input=query,
        context=context,
    )

    logger.info(f"[agent_service] invoke graph run_id={run_id}")
    graph = get_graph()
    result = graph.invoke(state)
    
    # 결과에 시작 시간 추가 (감사 생성용)
    result["_started_at"] = started_at.isoformat()
    
    # 승인 대기 상태인 경우 상태 저장
    if result.get("approval_status") == "pending":
        # 승인 사유 수집
        approval_reasons = []
        workflow_result = result.get("workflow_result")
        if workflow_result and hasattr(workflow_result, "approvals_required"):
            approval_reasons = workflow_result.approvals_required
        elif isinstance(workflow_result, dict):
            approval_reasons = workflow_result.get("approvals_required", [])
        
        # trace에서도 승인 사유 확인
        trace = result.get("trace", {})
        check_approval_trace = trace.get("check_approval", {})
        if check_approval_trace.get("approval_reasons"):
            for reason in check_approval_trace.get("approval_reasons", []):
                if reason not in approval_reasons:
                    approval_reasons.append(reason)
        
        # 상태 스냅샷 저장
        save_pending_approval(
            run_id=run_id,
            state_snapshot=result,
            action_plan=result.get("action_plan", []),
            approval_reasons=approval_reasons,
        )
        
        logger.info(f"[agent_service] Pending approval saved: run_id={run_id}")
        
        # 응답에 승인 정보 추가
        result["_approval_info"] = {
            "status": "pending",
            "reasons": approval_reasons,
            "action_plan_count": len(result.get("action_plan", [])),
        }

    return result


def resume_after_approval(run_id: str, state_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """승인 후 실행 재개"""
    logger.info(f"[agent_service] Resuming after approval: run_id={run_id}")
    
    # 상태 복원
    state_snapshot["approval_status"] = "approved"
    
    # 간단한 finalize만 수행 (이미 분석은 완료된 상태)
    # 실제로는 실행(execution) 단계가 추가될 수 있음
    result = {
        **state_snapshot,
        "execution_results": [
            {
                "step": "approval_granted",
                "message": "실행 계획이 승인되었습니다.",
                "status": "ready_for_execution",
            }
        ],
        "trace": {
            **state_snapshot.get("trace", {}),
            "resume_after_approval": {"status": "success"}
        }
    }
    
    logger.info(f"[agent_service] Resume completed: run_id={run_id}")
    return result
