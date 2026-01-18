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
    return AgentRunResponse(
        run_id=run_id,
        status="COMPLETED",
        result=result,
    )