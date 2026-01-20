# app/agent/nodes/classify_intent.py
"""Intent 분류 노드"""
from __future__ import annotations

import json
import logging
from typing import Literal

from app.agent.state import AgentState
from app.integrations.llm.openrouter_client import get_openrouter_client

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """당신은 사용자 요청을 분류하는 전문가입니다.

사용자의 요청을 다음 카테고리 중 하나로 분류하세요:

1. **compliance**: 규정/정책 준수 여부 확인, 승인 요청, 규정 검토
   - 예: "이 문서가 보안 정책에 맞나요?", "출장 승인 요청합니다"

2. **rca**: 장애/문제 분석, 근본 원인 분석, 트러블슈팅
   - 예: "서버 오류 분석해주세요", "왜 이런 에러가 발생했나요?"

3. **workflow**: 업무 실행, 작업 자동화, 프로세스 수행
   - 예: "배포 진행해주세요", "테스트 환경 구성해주세요"

4. **mixed**: 위 카테고리 중 2개 이상에 해당하는 복합 요청

5. **unknown**: 위 카테고리에 해당하지 않거나 판단 불가

반드시 다음 JSON 형식으로만 응답하세요:
{"intent": "compliance" | "rca" | "workflow" | "mixed" | "unknown", "reason": "분류 이유 (1문장)"}
"""


def classify_intent_node(state: AgentState) -> dict:
    """사용자 입력의 Intent를 분류하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] classify_intent_node: input='{user_input[:50]}...'")
    
    if not user_input.strip():
        logger.warning(f"[{run_id}] Empty user input, setting intent to 'unknown'")
        return {
            "intent": "unknown",
            "trace": {
                **state.trace,
                "classify_intent": {"status": "skipped", "reason": "empty input"}
            }
        }
    
    client = get_openrouter_client()
    
    try:
        response = client.chat_with_system(
            system_prompt=INTENT_SYSTEM_PROMPT,
            user_message=user_input,
        )
        
        # JSON 파싱
        result = json.loads(response)
        intent = result.get("intent", "unknown")
        reason = result.get("reason", "")
        
        # 유효성 검증
        valid_intents = {"compliance", "rca", "workflow", "mixed", "unknown"}
        if intent not in valid_intents:
            intent = "unknown"
        
        logger.info(f"[{run_id}] Intent classified: {intent} - {reason}")
        
        return {
            "intent": intent,
            "trace": {
                **state.trace,
                "classify_intent": {
                    "status": "success",
                    "intent": intent,
                    "reason": reason,
                }
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[{run_id}] Failed to parse intent response: {e}")
        return {
            "intent": "unknown",
            "errors": state.errors + [f"Intent 분류 실패: JSON 파싱 오류"],
            "trace": {
                **state.trace,
                "classify_intent": {"status": "error", "error": str(e)}
            }
        }
    except Exception as e:
        logger.error(f"[{run_id}] Intent classification failed: {e}")
        return {
            "intent": "unknown",
            "errors": state.errors + [f"Intent 분류 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "classify_intent": {"status": "error", "error": str(e)}
            }
        }
