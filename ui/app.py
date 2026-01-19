# ui/app.py
from __future__ import annotations

import os
import json
import chainlit as cl
import httpx

API_BASE_URL = os.getenv("TRACE_AI_API_BASE_URL", "http://127.0.0.1:8000")
AGENT_RUN_URL = f"{API_BASE_URL}/api/v1/agent/run"

@cl.on_chat_start
async def on_chat_start():
    msg = (
        "TRACE-AI UI가 준비되었습니다.\n"
        f"- Backend: {API_BASE_URL}\n"
        "- 입력한 메시지는 /api/v1/agent/run 으로 전달됩니다."
    )
    await cl.Message(content=msg).send()

@cl.on_message
async def on_message(message: cl.Message):
    user_text = (message.content or "").strip()
    if not user_text:
        await cl.Message(content="빈 입력입니다. 내용을 입력해 주세요.").send()
        return

    payload = {"query": user_text, "context": {}}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(AGENT_RUN_URL, json=payload)

        # 응답 파싱
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}

        # run_id는 body 기준을 우선 (W1-2/W1-3에서 이미 포함)
        body_run_id = None
        if isinstance(data, dict):
            body_run_id = data.get("run_id") or (data.get("result") or {}).get("run_id")

        header_run_id = resp.headers.get("x-run-id")  # W1-2 미들웨어에서 주입

        # UI 출력(요약 + 원문 JSON)
        lines = []
        lines.append(f"HTTP {resp.status_code}")
        if body_run_id:
            lines.append(f"run_id(body): {body_run_id}")
        if header_run_id:
            lines.append(f"run_id(header): {header_run_id}")

        # 핵심 결과만 간단히 표시 (trace 중심)
        trace = None
        if isinstance(data, dict):
            trace = (data.get("result") or {}).get("trace") or data.get("trace")

        if trace is not None:
            lines.append("\ntrace:")
            lines.append(json.dumps(trace, ensure_ascii=False, indent=2))

        # 전체 응답도 함께 제공(디버깅/데모 용)
        lines.append("\nfull_response:")
        lines.append(json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, dict) else str(data))

        await cl.Message(content="\n".join(lines)).send()

    except httpx.RequestError as e:
        await cl.Message(content=f"Backend 호출 실패: {type(e).__name__}: {e}").send()
    except Exception as e:
        await cl.Message(content=f"예외 발생: {type(e).__name__}: {e}").send()
