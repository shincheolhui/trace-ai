# app/agent/state.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class AgentState(BaseModel):
    run_id: str
    user_input: Optional[str] = None
    context: Dict[str, Any] = {}
    evidence: List[Dict[str, Any]] = []
    analysis_results: Dict[str, Any] = {}
    action_plan: List[Dict[str, Any]] = []