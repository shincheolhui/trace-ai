# app/agent/subgraphs/workflow_graph.py
"""업무 실행 계획 서브그래프"""
from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState, WorkflowResult
from app.integrations.llm.openrouter_client import get_openrouter_client
from app.services.knowledge_service import get_knowledge_service
from app.schemas.knowledge import StoreType

logger = logging.getLogger(__name__)


WORKFLOW_SYSTEM_PROMPT = """당신은 IT 운영 업무 계획 전문가입니다.
사용자의 요청을 분석하여 구체적인 실행 계획(Action Plan)을 수립합니다.

### 계획 수립 원칙
1. 각 단계는 명확하고 실행 가능해야 합니다
2. 위험도가 높은 작업은 반드시 승인이 필요합니다
3. 롤백 계획이 필요한 경우 명시합니다
4. 예상 소요 시간을 제시합니다

### 위험도 분류 기준
- high: 프로덕션 영향, 데이터 변경, 서비스 중단 가능 → 승인 필수
- medium: 제한적 영향, 복구 가능 → 승인 권장
- low: 읽기 전용, 테스트 환경 → 승인 불필요

### 참고 문서
{system_docs}

### 이전 분석 결과
{analysis_context}

### 출력 형식 (JSON만 출력)
{{
  "action_plan": [
    {{
      "step": 1,
      "title": "단계 제목",
      "description": "상세 설명",
      "risk_level": "high" | "medium" | "low",
      "requires_approval": true | false,
      "estimated_duration": "예상 소요 시간",
      "rollback_plan": "롤백 방법 (필요시, 없으면 null)"
    }}
  ],
  "total_steps": 3,
  "overall_risk": "high" | "medium" | "low",
  "approvals_required": ["승인이 필요한 단계 제목 목록"],
  "summary": "전체 계획 요약 (1-2문장)"
}}
"""


# ===== 노드 함수들 =====

def analyze_request_node(state: AgentState) -> dict:
    """요청을 분석하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] analyze_request_node: analyzing request")
    
    # 요청 분석 정보 추출
    request_info = {
        "raw_input": user_input,
        "has_action_keywords": any(kw in user_input.lower() for kw in 
            ["배포", "deploy", "실행", "execute", "설정", "configure", 
             "생성", "create", "삭제", "delete", "변경", "update", "수정"]),
        "has_risk_keywords": any(kw in user_input.lower() for kw in 
            ["프로덕션", "production", "운영", "live", "데이터베이스", "database"]),
    }
    
    # 이전 분석 결과가 있으면 컨텍스트에 추가
    analysis_context = {}
    if state.compliance_result:
        analysis_context["compliance"] = {
            "status": state.compliance_result.status,
            "summary": state.compliance_result.summary,
        }
    if state.rca_result:
        analysis_context["rca"] = {
            "hypotheses_count": len(state.rca_result.hypotheses),
            "summary": state.rca_result.summary,
        }
    
    context = dict(state.context)
    context["request_info"] = request_info
    context["analysis_context"] = analysis_context
    
    logger.info(f"[{run_id}] Request analysis: action={request_info['has_action_keywords']}, risk={request_info['has_risk_keywords']}")
    
    return {
        "context": context,
        "trace": {
            **state.trace,
            "analyze_request": {
                "status": "success",
                "has_action_keywords": request_info["has_action_keywords"],
                "has_risk_keywords": request_info["has_risk_keywords"],
            }
        }
    }


def retrieve_system_docs_node(state: AgentState) -> dict:
    """시스템/업무 문서를 검색하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] retrieve_system_docs_node: searching system docs")
    
    try:
        service = get_knowledge_service()
        
        # system 스토어에서 검색 (async 함수 동기 호출)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        search_response = loop.run_until_complete(
            service.search(
                query=user_input,
                store_type=StoreType.SYSTEM,
                top_k=5,
            )
        )
        
        evidence = []
        for result in search_response.results:
            evidence.append({
                "type": "system_doc",
                "doc_id": result.doc_id,
                "content": result.text,
                "score": result.score,
                "metadata": result.metadata,
            })
        
        logger.info(f"[{run_id}] Found {len(evidence)} system doc chunks")
        
        return {
            "evidence": state.evidence + evidence,
            "trace": {
                **state.trace,
                "retrieve_system_docs": {
                    "status": "success",
                    "count": len(evidence),
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] System docs retrieval failed: {e}")
        return {
            "errors": state.errors + [f"시스템 문서 검색 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "retrieve_system_docs": {"status": "error", "error": str(e)}
            }
        }


def generate_action_plan_node(state: AgentState) -> dict:
    """실행 계획을 생성하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] generate_action_plan_node: generating action plan")
    
    # 시스템 문서 증거 수집
    system_evidence = [e for e in state.evidence if e.get("type") == "system_doc"]
    
    if not system_evidence:
        system_docs_text = "참고할 시스템 문서가 없습니다."
    else:
        system_docs_text = "\n\n---\n\n".join([
            f"[문서: {e.get('doc_id', 'unknown')}]\n{e.get('content', '')}"
            for e in system_evidence
        ])
    
    # 이전 분석 컨텍스트
    analysis_context = state.context.get("analysis_context", {})
    if analysis_context:
        analysis_text = json.dumps(analysis_context, ensure_ascii=False, indent=2)
    else:
        analysis_text = "이전 분석 결과가 없습니다."
    
    # 프롬프트 구성
    system_prompt = WORKFLOW_SYSTEM_PROMPT.format(
        system_docs=system_docs_text,
        analysis_context=analysis_text,
    )
    
    # 사용자 메시지 구성
    user_message = f"다음 요청에 대한 실행 계획을 수립해주세요:\n\n{user_input}"
    
    client = get_openrouter_client()
    
    try:
        response = client.chat_with_system(
            system_prompt=system_prompt,
            user_message=user_message,
        )
        
        # JSON 파싱
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        
        result = json.loads(response)
        
        # Action Plan 추출
        action_plan = result.get("action_plan", [])
        approvals_required = result.get("approvals_required", [])
        overall_risk = result.get("overall_risk", "low")
        
        # 승인 필요 여부 결정
        approval_required = len(approvals_required) > 0 or overall_risk == "high"
        
        workflow_result = WorkflowResult(
            action_plan=action_plan,
            approvals_required=approvals_required,
            summary=result.get("summary", ""),
        )
        
        logger.info(f"[{run_id}] Generated {len(action_plan)} action steps, approval_required={approval_required}")
        
        return {
            "workflow_result": workflow_result,
            "action_plan": action_plan,
            "approval_required": approval_required,
            "approval_status": "pending" if approval_required else "not_required",
            "trace": {
                **state.trace,
                "generate_action_plan": {
                    "status": "success",
                    "step_count": len(action_plan),
                    "overall_risk": overall_risk,
                    "approval_required": approval_required,
                }
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[{run_id}] Failed to parse workflow response: {e}")
        
        workflow_result = WorkflowResult(
            action_plan=[{
                "step": 1,
                "title": "수동 검토 필요",
                "description": "자동 계획 수립에 실패했습니다. 담당자가 직접 검토해주세요.",
                "risk_level": "medium",
                "requires_approval": True,
                "estimated_duration": "미정",
                "rollback_plan": None,
            }],
            approvals_required=["수동 검토 필요"],
            summary="자동 계획 수립 실패, 수동 검토 필요",
        )
        
        return {
            "workflow_result": workflow_result,
            "approval_required": True,
            "approval_status": "pending",
            "errors": state.errors + [f"실행 계획 파싱 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "generate_action_plan": {"status": "parse_error", "error": str(e)}
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Action plan generation failed: {e}")
        
        workflow_result = WorkflowResult(
            action_plan=[],
            approvals_required=[],
            summary=f"실행 계획 생성 실패: {str(e)}",
        )
        
        return {
            "workflow_result": workflow_result,
            "errors": state.errors + [f"실행 계획 생성 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "generate_action_plan": {"status": "error", "error": str(e)}
            }
        }


def assess_risk_node(state: AgentState) -> dict:
    """위험도를 평가하는 노드"""
    run_id = state.run_id
    workflow_result = state.workflow_result
    
    if not workflow_result:
        logger.warning(f"[{run_id}] No workflow result to assess")
        return {}
    
    logger.info(f"[{run_id}] assess_risk_node: assessing risk")
    
    action_plan = workflow_result.action_plan
    
    # 위험도 점수 계산
    risk_scores = {"high": 3, "medium": 2, "low": 1}
    total_risk_score = 0
    high_risk_steps = []
    
    for step in action_plan:
        risk_level = step.get("risk_level", "low")
        total_risk_score += risk_scores.get(risk_level, 1)
        
        if risk_level == "high":
            high_risk_steps.append(step.get("title", f"Step {step.get('step', '?')}"))
    
    # 평균 위험도 계산
    avg_risk = total_risk_score / len(action_plan) if action_plan else 0
    
    if avg_risk >= 2.5 or len(high_risk_steps) >= 2:
        overall_risk = "high"
    elif avg_risk >= 1.5 or len(high_risk_steps) >= 1:
        overall_risk = "medium"
    else:
        overall_risk = "low"
    
    # 승인 필요 여부 업데이트
    approval_required = overall_risk in ["high", "medium"] or len(high_risk_steps) > 0
    
    logger.info(f"[{run_id}] Risk assessment: overall={overall_risk}, high_risk_steps={len(high_risk_steps)}")
    
    # context에 위험도 정보 추가
    context = dict(state.context)
    context["risk_assessment"] = {
        "overall_risk": overall_risk,
        "high_risk_steps": high_risk_steps,
        "avg_risk_score": avg_risk,
    }
    
    return {
        "context": context,
        "approval_required": approval_required,
        "approval_status": "pending" if approval_required else "not_required",
        "trace": {
            **state.trace,
            "assess_risk": {
                "status": "success",
                "overall_risk": overall_risk,
                "high_risk_count": len(high_risk_steps),
                "approval_required": approval_required,
            }
        }
    }


def finalize_plan_node(state: AgentState) -> dict:
    """최종 계획을 정리하는 노드"""
    run_id = state.run_id
    workflow_result = state.workflow_result
    
    logger.info(f"[{run_id}] finalize_plan_node: finalizing plan")
    
    if not workflow_result:
        return {
            "trace": {
                **state.trace,
                "finalize_plan": {"status": "skipped", "reason": "no_workflow_result"}
            }
        }
    
    # 최종 action_plan 업데이트
    action_plan = workflow_result.action_plan
    
    # 승인 필요 단계 표시 강화
    for step in action_plan:
        if step.get("requires_approval") and step.get("risk_level") == "high":
            step["approval_note"] = "⚠️ 고위험 작업 - 반드시 승인 필요"
    
    # 업데이트된 WorkflowResult
    updated_result = WorkflowResult(
        action_plan=action_plan,
        approvals_required=workflow_result.approvals_required,
        summary=workflow_result.summary,
    )
    
    return {
        "workflow_result": updated_result,
        "action_plan": action_plan,
        "trace": {
            **state.trace,
            "finalize_plan": {
                "status": "success",
                "final_step_count": len(action_plan),
            }
        }
    }


# ===== 서브그래프 빌드 =====

def build_workflow_graph():
    """업무 실행 계획 서브그래프 생성"""
    graph = StateGraph(AgentState)
    
    # 노드 추가
    graph.add_node("ANALYZE_REQUEST", analyze_request_node)
    graph.add_node("RETRIEVE_SYSTEM_DOCS", retrieve_system_docs_node)
    graph.add_node("GENERATE_ACTION_PLAN", generate_action_plan_node)
    graph.add_node("ASSESS_RISK", assess_risk_node)
    graph.add_node("FINALIZE_PLAN", finalize_plan_node)
    
    # 엣지 연결
    graph.add_edge(START, "ANALYZE_REQUEST")
    graph.add_edge("ANALYZE_REQUEST", "RETRIEVE_SYSTEM_DOCS")
    graph.add_edge("RETRIEVE_SYSTEM_DOCS", "GENERATE_ACTION_PLAN")
    graph.add_edge("GENERATE_ACTION_PLAN", "ASSESS_RISK")
    graph.add_edge("ASSESS_RISK", "FINALIZE_PLAN")
    graph.add_edge("FINALIZE_PLAN", END)
    
    return graph.compile()


@lru_cache(maxsize=1)
def get_workflow_graph():
    """컴파일된 업무 실행 계획 서브그래프 싱글톤"""
    logger.info("[workflow_graph] Building workflow subgraph")
    return build_workflow_graph()
