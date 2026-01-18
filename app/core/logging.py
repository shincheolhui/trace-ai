# app/core/logging.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.run_context import get_run_id

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": get_run_id(),
        }
        return json.dumps(payload, ensure_ascii=False)

def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    # 중복 핸들러 방지
    root.handlers = [handler]
