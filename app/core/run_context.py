# app/core/run_context.py
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Optional

_run_id_ctx: ContextVar[Optional[str]] = ContextVar("run_id", default=None)

def generate_run_id() -> str:
    return str(uuid.uuid4())

def set_run_id(run_id: str) -> None:
    _run_id_ctx.set(run_id)

def get_run_id() -> Optional[str]:
    return _run_id_ctx.get()
