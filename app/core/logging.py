# app/core/logging.py
"""구조화 로그 시스템 - W3-1"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, ParamSpec

from app.core.run_context import get_run_id

# ===== 로그 이벤트 타입 =====
class LogEventType:
    """로그 이벤트 타입 상수"""
    NODE_START = "node_start"
    NODE_END = "node_end"
    DECISION = "decision"
    ACTION = "action"
    ERROR = "error"
    LLM_CALL = "llm_call"
    RETRIEVAL = "retrieval"
    APPROVAL = "approval"


# ===== JSON Formatter =====
class JsonFormatter(logging.Formatter):
    """JSON 구조화 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": get_run_id(),
        }
        
        # 추가 필드가 있으면 포함
        if hasattr(record, "event_type"):
            payload["event_type"] = record.event_type
        if hasattr(record, "node_name"):
            payload["node_name"] = record.node_name
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms
        if hasattr(record, "extra_data"):
            payload["data"] = record.extra_data
            
        return json.dumps(payload, ensure_ascii=False)


# ===== 로깅 유틸리티 함수 =====

def get_structured_logger(name: str) -> logging.Logger:
    """구조화 로거 반환"""
    return logging.getLogger(name)


def log_node_start(logger: logging.Logger, run_id: str, node_name: str, extra: Optional[Dict] = None) -> None:
    """노드 시작 로그"""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"[{run_id}] Node START: {node_name}",
        (), None
    )
    record.event_type = LogEventType.NODE_START
    record.node_name = node_name
    if extra:
        record.extra_data = extra
    logger.handle(record)


def log_node_end(logger: logging.Logger, run_id: str, node_name: str, duration_ms: float, status: str = "success", extra: Optional[Dict] = None) -> None:
    """노드 종료 로그"""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"[{run_id}] Node END: {node_name} ({status}, {duration_ms:.2f}ms)",
        (), None
    )
    record.event_type = LogEventType.NODE_END
    record.node_name = node_name
    record.duration_ms = duration_ms
    if extra:
        record.extra_data = {"status": status, **extra}
    else:
        record.extra_data = {"status": status}
    logger.handle(record)


def log_decision(logger: logging.Logger, run_id: str, decision_type: str, result: Any, reason: Optional[str] = None) -> None:
    """판단 로그 (예: intent 분류, 규정 위반 여부 등)"""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"[{run_id}] DECISION: {decision_type} = {result}",
        (), None
    )
    record.event_type = LogEventType.DECISION
    record.extra_data = {
        "decision_type": decision_type,
        "result": result,
    }
    if reason:
        record.extra_data["reason"] = reason
    logger.handle(record)


def log_action(logger: logging.Logger, run_id: str, action_type: str, description: str, extra: Optional[Dict] = None) -> None:
    """실행 로그 (예: 서브그래프 실행, API 호출 등)"""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"[{run_id}] ACTION: {action_type} - {description}",
        (), None
    )
    record.event_type = LogEventType.ACTION
    record.extra_data = {
        "action_type": action_type,
        "description": description,
    }
    if extra:
        record.extra_data.update(extra)
    logger.handle(record)


def log_llm_call(logger: logging.Logger, run_id: str, model: str, purpose: str, duration_ms: float, tokens: Optional[Dict] = None) -> None:
    """LLM 호출 로그"""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"[{run_id}] LLM_CALL: {model} for {purpose} ({duration_ms:.2f}ms)",
        (), None
    )
    record.event_type = LogEventType.LLM_CALL
    record.duration_ms = duration_ms
    record.extra_data = {
        "model": model,
        "purpose": purpose,
    }
    if tokens:
        record.extra_data["tokens"] = tokens
    logger.handle(record)


def log_retrieval(logger: logging.Logger, run_id: str, store_type: str, query_preview: str, result_count: int, duration_ms: float) -> None:
    """검색 로그 (Knowledge Store 검색)"""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"[{run_id}] RETRIEVAL: {store_type} found {result_count} results ({duration_ms:.2f}ms)",
        (), None
    )
    record.event_type = LogEventType.RETRIEVAL
    record.duration_ms = duration_ms
    record.extra_data = {
        "store_type": store_type,
        "query_preview": query_preview[:50] + "..." if len(query_preview) > 50 else query_preview,
        "result_count": result_count,
    }
    logger.handle(record)


def log_error(logger: logging.Logger, run_id: str, error_type: str, error_message: str, node_name: Optional[str] = None) -> None:
    """에러 로그"""
    record = logger.makeRecord(
        logger.name, logging.ERROR, "", 0,
        f"[{run_id}] ERROR: {error_type} - {error_message}",
        (), None
    )
    record.event_type = LogEventType.ERROR
    record.extra_data = {
        "error_type": error_type,
        "error_message": error_message,
    }
    if node_name:
        record.node_name = node_name
    logger.handle(record)


def log_approval(logger: logging.Logger, run_id: str, action: str, status: str, extra: Optional[Dict] = None) -> None:
    """승인 관련 로그"""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0,
        f"[{run_id}] APPROVAL: {action} - {status}",
        (), None
    )
    record.event_type = LogEventType.APPROVAL
    record.extra_data = {
        "action": action,
        "status": status,
    }
    if extra:
        record.extra_data.update(extra)
    logger.handle(record)


# ===== 노드 데코레이터 =====
P = ParamSpec("P")
T = TypeVar("T")


def trace_node(node_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """노드 실행을 트레이스하는 데코레이터
    
    Usage:
        @trace_node("CLASSIFY_INTENT")
        def classify_intent_node(state: AgentState) -> dict:
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger = get_structured_logger(func.__module__)
            run_id = get_run_id() or "unknown"
            
            # 노드 시작 로그
            log_node_start(logger, run_id, node_name)
            
            start_time = time.perf_counter()
            status = "success"
            error_msg = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                error_msg = str(e)
                log_error(logger, run_id, type(e).__name__, str(e), node_name)
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                extra = {"error": error_msg} if error_msg else None
                log_node_end(logger, run_id, node_name, duration_ms, status, extra)
        
        return wrapper
    return decorator


# ===== 셋업 =====
def setup_logging() -> None:
    """로깅 시스템 초기화"""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    # 중복 핸들러 방지
    root.handlers = [handler]
