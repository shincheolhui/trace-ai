# app/agent/orchestrator.py
"""LangGraph 메인 오케스트레이터 - 서브그래프 라우팅"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.agent.nodes.classify_intent import classify_intent_node
from app.agent.subgraphs.compliance_graph import get_compliance_graph
from app.agent.subgraphs.rca_graph import get_rca_graph
from app.agent.subgraphs.workflow_graph import get_workflow_graph

logger = logging.getLogger(__name__)


# ===== 라우터 함수 =====

def route_by_intent(state: AgentState) -> Literal["COMPLIANCE", "RCA", "WORKFLOW", "MIXED", "END"]:
    """Intent에 따라 적절한 서브그래프로 라우팅"""
    intent = state.intent
    run_id = state.run_id
    
    logger.info(f"[{run_id}] Routing by intent: {intent}")
    
    if intent == "compliance":
        return "COMPLIANCE"
    elif intent == "rca":
        return "RCA"
    elif intent == "workflow":
        return "WORKFLOW"
    elif intent == "mixed":
        logger.info(f"[{run_id}] Mixed intent, executing multiple subgraphs")
        return "MIXED"
    else:
        # unknown
        logger.info(f"[{run_id}] Unknown intent, ending")
        return "END"


def compliance_subgraph_node(state: AgentState) -> dict:
    """규정 위반 감지 서브그래프 실행 노드"""
    run_id = state.run_id
    logger.info(f"[{run_id}] Executing compliance subgraph")
    
    try:
        compliance_graph = get_compliance_graph()
        
        # 서브그래프 실행
        result = compliance_graph.invoke(state.model_dump())
        
        # 결과에서 필요한 필드만 추출하여 반환
        return {
            "compliance_result": result.get("compliance_result"),
            "evidence": result.get("evidence", state.evidence),
            "errors": result.get("errors", state.errors),
            "trace": result.get("trace", state.trace),
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Compliance subgraph failed: {e}")
        return {
            "errors": state.errors + [f"Compliance 서브그래프 실행 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "compliance_subgraph": {"status": "error", "error": str(e)}
            }
        }


def rca_subgraph_node(state: AgentState) -> dict:
    """장애 RCA 서브그래프 실행 노드"""
    run_id = state.run_id
    logger.info(f"[{run_id}] Executing RCA subgraph")
    
    try:
        rca_graph = get_rca_graph()
        
        # 서브그래프 실행
        result = rca_graph.invoke(state.model_dump())
        
        # 결과에서 필요한 필드만 추출하여 반환
        return {
            "rca_result": result.get("rca_result"),
            "context": result.get("context", state.context),
            "evidence": result.get("evidence", state.evidence),
            "errors": result.get("errors", state.errors),
            "trace": result.get("trace", state.trace),
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] RCA subgraph failed: {e}")
        return {
            "errors": state.errors + [f"RCA 서브그래프 실행 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "rca_subgraph": {"status": "error", "error": str(e)}
            }
        }


def workflow_subgraph_node(state: AgentState) -> dict:
    """업무 실행 계획 서브그래프 실행 노드"""
    run_id = state.run_id
    logger.info(f"[{run_id}] Executing Workflow subgraph")
    
    try:
        workflow_graph = get_workflow_graph()
        
        # 서브그래프 실행
        result = workflow_graph.invoke(state.model_dump())
        
        # 결과에서 필요한 필드만 추출하여 반환
        return {
            "workflow_result": result.get("workflow_result"),
            "action_plan": result.get("action_plan", state.action_plan),
            "approval_required": result.get("approval_required", state.approval_required),
            "approval_status": result.get("approval_status", state.approval_status),
            "context": result.get("context", state.context),
            "evidence": result.get("evidence", state.evidence),
            "errors": result.get("errors", state.errors),
            "trace": result.get("trace", state.trace),
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Workflow subgraph failed: {e}")
        return {
            "errors": state.errors + [f"Workflow 서브그래프 실행 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "workflow_subgraph": {"status": "error", "error": str(e)}
            }
        }


def mixed_subgraph_node(state: AgentState) -> dict:
    """복합 요청 처리 - 다중 서브그래프 순차 실행 노드"""
    run_id = state.run_id
    logger.info(f"[{run_id}] Executing MIXED subgraphs (compliance → rca → workflow)")
    
    # 결과를 누적할 변수들
    compliance_result = None
    rca_result = None
    workflow_result = None
    context = dict(state.context)
    evidence = list(state.evidence)
    errors = list(state.errors)
    trace = dict(state.trace)
    action_plan = state.action_plan
    approval_required = state.approval_required
    approval_status = state.approval_status
    
    # 1. Compliance 서브그래프 실행
    try:
        logger.info(f"[{run_id}] MIXED: Running compliance subgraph")
        compliance_graph = get_compliance_graph()
        compliance_state = state.model_dump()
        compliance_state["context"] = context
        compliance_state["evidence"] = evidence
        
        result = compliance_graph.invoke(compliance_state)
        
        compliance_result = result.get("compliance_result")
        evidence = result.get("evidence", evidence)
        trace["mixed_compliance"] = {"status": "success"}
        
        logger.info(f"[{run_id}] MIXED: Compliance completed")
        
    except Exception as e:
        logger.error(f"[{run_id}] MIXED: Compliance failed: {e}")
        errors.append(f"Mixed-Compliance 실패: {str(e)}")
        trace["mixed_compliance"] = {"status": "error", "error": str(e)}
    
    # 2. RCA 서브그래프 실행
    try:
        logger.info(f"[{run_id}] MIXED: Running RCA subgraph")
        rca_graph = get_rca_graph()
        rca_state = state.model_dump()
        rca_state["context"] = context
        rca_state["evidence"] = evidence
        
        result = rca_graph.invoke(rca_state)
        
        rca_result = result.get("rca_result")
        context = result.get("context", context)
        evidence = result.get("evidence", evidence)
        trace["mixed_rca"] = {"status": "success"}
        
        logger.info(f"[{run_id}] MIXED: RCA completed")
        
    except Exception as e:
        logger.error(f"[{run_id}] MIXED: RCA failed: {e}")
        errors.append(f"Mixed-RCA 실패: {str(e)}")
        trace["mixed_rca"] = {"status": "error", "error": str(e)}
    
    # 3. Workflow 서브그래프 실행 (이전 분석 결과를 컨텍스트로 전달)
    try:
        logger.info(f"[{run_id}] MIXED: Running Workflow subgraph")
        workflow_graph = get_workflow_graph()
        workflow_state = state.model_dump()
        workflow_state["context"] = context
        workflow_state["evidence"] = evidence
        
        # 이전 분석 결과를 Workflow에 전달
        if compliance_result:
            workflow_state["compliance_result"] = compliance_result
        if rca_result:
            workflow_state["rca_result"] = rca_result
        
        result = workflow_graph.invoke(workflow_state)
        
        workflow_result = result.get("workflow_result")
        action_plan = result.get("action_plan", action_plan)
        approval_required = result.get("approval_required", approval_required)
        approval_status = result.get("approval_status", approval_status)
        context = result.get("context", context)
        evidence = result.get("evidence", evidence)
        trace["mixed_workflow"] = {"status": "success"}
        
        logger.info(f"[{run_id}] MIXED: Workflow completed")
        
    except Exception as e:
        logger.error(f"[{run_id}] MIXED: Workflow failed: {e}")
        errors.append(f"Mixed-Workflow 실패: {str(e)}")
        trace["mixed_workflow"] = {"status": "error", "error": str(e)}
    
    # 실행된 서브그래프 수 계산
    executed_count = sum([
        1 if compliance_result else 0,
        1 if rca_result else 0,
        1 if workflow_result else 0,
    ])
    
    trace["mixed_summary"] = {
        "status": "success" if executed_count > 0 else "partial",
        "executed_subgraphs": executed_count,
        "total_subgraphs": 3,
    }
    
    logger.info(f"[{run_id}] MIXED: Completed {executed_count}/3 subgraphs")
    
    return {
        "compliance_result": compliance_result,
        "rca_result": rca_result,
        "workflow_result": workflow_result,
        "context": context,
        "evidence": evidence,
        "action_plan": action_plan,
        "approval_required": approval_required,
        "approval_status": approval_status,
        "errors": errors,
        "trace": trace,
    }


def finalize_node(state: AgentState) -> dict:
    """최종 결과 정리 노드"""
    run_id = state.run_id
    logger.info(f"[{run_id}] Finalizing agent execution")
    
    # 분석 결과 통합
    analysis_results = dict(state.analysis_results)
    
    if state.compliance_result:
        analysis_results["compliance"] = {
            "status": state.compliance_result.status,
            "violations": state.compliance_result.violations,
            "recommendations": state.compliance_result.recommendations,
            "summary": state.compliance_result.summary,
        }
    
    if state.rca_result:
        analysis_results["rca"] = {
            "hypotheses": state.rca_result.hypotheses,
            "summary": state.rca_result.summary,
        }
    
    if state.workflow_result:
        analysis_results["workflow"] = {
            "action_plan": state.workflow_result.action_plan,
            "approvals_required": state.workflow_result.approvals_required,
            "summary": state.workflow_result.summary,
        }
    
    # 통합 요약 생성 (mixed intent인 경우)
    if state.intent == "mixed":
        summaries = []
        if state.compliance_result and state.compliance_result.summary:
            summaries.append(f"[규정검사] {state.compliance_result.summary}")
        if state.rca_result and state.rca_result.summary:
            summaries.append(f"[원인분석] {state.rca_result.summary}")
        if state.workflow_result and state.workflow_result.summary:
            summaries.append(f"[실행계획] {state.workflow_result.summary}")
        
        if summaries:
            analysis_results["integrated_summary"] = " | ".join(summaries)
    
    return {
        "analysis_results": analysis_results,
        "trace": {
            **state.trace,
            "finalize": {"status": "success"}
        }
    }


# ===== 메인 그래프 빌드 =====

def build_graph():
    """메인 오케스트레이터 그래프 생성"""
    graph = StateGraph(AgentState)
    
    # 노드 추가
    graph.add_node("CLASSIFY_INTENT", classify_intent_node)
    graph.add_node("COMPLIANCE", compliance_subgraph_node)
    graph.add_node("RCA", rca_subgraph_node)
    graph.add_node("WORKFLOW", workflow_subgraph_node)
    graph.add_node("MIXED", mixed_subgraph_node)
    graph.add_node("FINALIZE", finalize_node)
    
    # 엣지 연결
    graph.add_edge(START, "CLASSIFY_INTENT")
    
    # 조건부 라우팅
    graph.add_conditional_edges(
        "CLASSIFY_INTENT",
        route_by_intent,
        {
            "COMPLIANCE": "COMPLIANCE",
            "RCA": "RCA",
            "WORKFLOW": "WORKFLOW",
            "MIXED": "MIXED",
            "END": "FINALIZE",
        }
    )
    
    # 서브그래프 완료 후 FINALIZE로
    graph.add_edge("COMPLIANCE", "FINALIZE")
    graph.add_edge("RCA", "FINALIZE")
    graph.add_edge("WORKFLOW", "FINALIZE")
    graph.add_edge("MIXED", "FINALIZE")
    graph.add_edge("FINALIZE", END)
    
    return graph.compile()


@lru_cache(maxsize=1)
def get_graph():
    """컴파일된 그래프 싱글톤"""
    logger.info("[orchestrator] Building main graph")
    return build_graph()
