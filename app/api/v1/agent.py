# app/api/v1/agent.py
from __future__ import annotations

import logging
from fastapi import APIRouter
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.agent_service import run_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
def agent_run(req: AgentRunRequest):
    logger.info(f"[agent_run] req: {req}")
    result = run_agent(req.query, req.context)

    run_id = result.get("run_id", "UNKNOWN_RUN_ID")
    approval_status = result.get("approval_status", "not_required")
    
    # 승인 대기 상태인 경우
    if approval_status == "pending":
        approval_info = result.get("_approval_info", {})
        return AgentRunResponse(
            run_id=run_id,
            status="PENDING_APPROVAL",
            result=result,
            approval_required=True,
            approval_reasons=approval_info.get("reasons", []),
            action_plan_preview=result.get("action_plan", [])[:3],  # 최대 3개 미리보기
        )
    
    # 거부된 경우
    if approval_status == "rejected":
        return AgentRunResponse(
            run_id=run_id,
            status="REJECTED",
            result=result,
        )
    
    # 오류가 있는 경우
    if result.get("errors"):
        return AgentRunResponse(
            run_id=run_id,
            status="ERROR" if not result.get("analysis_results") else "COMPLETED",
            result=result,
        )
    
    # 정상 완료
    return AgentRunResponse(
        run_id=run_id,
        status="COMPLETED",
        result=result,
    )