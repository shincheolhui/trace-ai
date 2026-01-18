# app/agent/orchestrator.py
from __future__ import annotations

import logging
from functools import lru_cache
from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.agent.nodes.dummy import dummy_node

logger = logging.getLogger(__name__)

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("DUMMY", dummy_node)
    graph.add_edge(START, "DUMMY")
    graph.add_edge("DUMMY", END)

    return graph.compile()

@lru_cache(maxsize=1)
def get_graph():
    logger.info("[orchestrator] build_graph() called")
    return build_graph()
