# app/services/agent_service.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.agent.orchestrator import get_graph
from app.agent.state import AgentState
from app.core.run_context import get_run_id

logger = logging.getLogger(__name__)

def run_agent(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    run_id = get_run_id()  # W1-2에서 contextvar로 전파됨
    if not run_id:
        # W1-2 전제상 발생하면 안되지만, 안전망
        run_id = "UNKNOWN"

    state = AgentState(
        run_id=run_id,
        user_input=query,
        context=context or {},
    )

    logger.info(f"[agent_service] invoke graph run_id={run_id}")
    graph = get_graph()
    result = graph.invoke(state)

    return result
