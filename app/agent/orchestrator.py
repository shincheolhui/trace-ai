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

logger = logging.getLogger(__name__)


# ===== 라우터 함수 =====

def route_by_intent(state: AgentState) -> Literal["COMPLIANCE", "RCA", "WORKFLOW", "END"]:
    """Intent에 따라 적절한 서브그래프로 라우팅"""
    intent = state.intent
    run_id = state.run_id
    
    logger.info(f"[{run_id}] Routing by intent: {intent}")
    
    if intent == "compliance":
        return "COMPLIANCE"
    elif intent == "rca":
        return "RCA"
    elif intent == "workflow":
        # W3-1에서 구현 예정
        logger.warning(f"[{run_id}] Workflow subgraph not implemented yet")
        return "END"
    elif intent == "mixed":
        # 복합 요청은 일단 compliance 우선 처리
        logger.info(f"[{run_id}] Mixed intent, routing to COMPLIANCE first")
        return "COMPLIANCE"
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
            "WORKFLOW": "FINALIZE",  # W3-1에서 WORKFLOW 노드로 변경 예정
            "END": "FINALIZE",
        }
    )
    
    # 서브그래프 완료 후 FINALIZE로
    graph.add_edge("COMPLIANCE", "FINALIZE")
    graph.add_edge("RCA", "FINALIZE")
    graph.add_edge("FINALIZE", END)
    
    return graph.compile()


@lru_cache(maxsize=1)
def get_graph():
    """컴파일된 그래프 싱글톤"""
    logger.info("[orchestrator] Building main graph")
    return build_graph()
