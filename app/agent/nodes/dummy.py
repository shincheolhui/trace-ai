# app/agent/nodes/dummy.py
from __future__ import annotations

import logging
from typing import Any, Dict

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

def dummy_node(state: AgentState) -> Dict[str, Any]:
    logger.info(f"[orchestrator][node_start] dummy_node run_id={state.run_id}")

    # state 갱신(전달/변경 증명)
    state.trace["dummy"] = {
        "ok": True,
        "message": "passed dummy node",
    }

    logger.info(f"[orchestrator][node_end] dummy_node run_id={state.run_id} trace={state.trace}")
    return state.model_dump()