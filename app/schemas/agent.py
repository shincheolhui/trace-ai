# app/schemas/agent.py
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class AgentRunRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class AgentRunResponse(BaseModel):
    run_id: str
    status: str
    result: Dict[str, Any]
