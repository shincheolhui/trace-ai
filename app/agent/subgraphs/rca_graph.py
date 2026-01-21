# app/agent/subgraphs/rca_graph.py
"""장애 RCA (Root Cause Analysis) 서브그래프"""
from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState, RCAResult
from app.integrations.llm.openrouter_client import get_openrouter_client
from app.services.knowledge_service import get_knowledge_service
from app.schemas.knowledge import StoreType

logger = logging.getLogger(__name__)


RCA_SYSTEM_PROMPT = """당신은 IT 시스템 장애 분석 전문가입니다.
로그, 에러 메시지, 장애 설명을 기반으로 근본 원인을 분석하고 가설을 제시합니다.

### 분석 원칙
1. 복수의 가설을 생성하고 우선순위를 매깁니다
2. 각 가설에는 반드시 근거(로그, 증거)가 필요합니다
3. 가설은 검증 가능해야 합니다
4. 불확실한 경우 "추가 정보 필요"로 명시합니다

### 유사 장애 사례
{incidents}

### 시스템 정보
{system_info}

### 출력 형식 (JSON만 출력)
{{
  "hypotheses": [
    {{
      "rank": 1,
      "title": "가설 제목",
      "description": "가설 상세 설명",
      "evidence": ["근거1", "근거2"],
      "confidence": "high" | "medium" | "low",
      "verification_steps": ["검증 방법1", "검증 방법2"]
    }}
  ],
  "additional_info_needed": ["추가로 필요한 정보"],
  "summary": "전체 분석 요약 (1-2문장)"
}}

유사 사례가 없으면:
{{
  "hypotheses": [
    {{
      "rank": 1,
      "title": "일반적인 분석",
      "description": "제공된 정보 기반 분석",
      "evidence": ["입력된 로그/에러 정보"],
      "confidence": "low",
      "verification_steps": ["추가 로그 확인", "시스템 상태 점검"]
    }}
  ],
  "additional_info_needed": ["상세 로그", "시스템 구성 정보"],
  "summary": "유사 사례가 없어 일반적인 분석을 수행했습니다."
}}
"""


# ===== 노드 함수들 =====

def parse_logs_node(state: AgentState) -> dict:
    """로그 입력을 파싱하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] parse_logs_node: parsing input")
    
    # 로그 정보 추출 (간단한 구현)
    # 실제로는 더 정교한 로그 파싱이 필요할 수 있음
    log_info = {
        "raw_input": user_input,
        "has_error_keywords": any(kw in user_input.lower() for kw in 
            ["error", "exception", "fail", "오류", "에러", "실패", "장애"]),
        "has_log_format": any(kw in user_input for kw in 
            ["INFO", "WARN", "ERROR", "DEBUG", "FATAL"]),
    }
    
    # 첨부 파일에서 로그 추출
    file_logs = []
    for f in state.files:
        if f.get("name", "").endswith((".log", ".txt")):
            file_logs.append({
                "filename": f.get("name", "unknown"),
                "content": f.get("content", "")[:5000],  # 최대 5000자
            })
    
    context = dict(state.context)
    context["log_info"] = log_info
    context["file_logs"] = file_logs
    
    logger.info(f"[{run_id}] Parsed logs: has_error={log_info['has_error_keywords']}, files={len(file_logs)}")
    
    return {
        "context": context,
        "trace": {
            **state.trace,
            "parse_logs": {
                "status": "success",
                "has_error_keywords": log_info["has_error_keywords"],
                "file_count": len(file_logs),
            }
        }
    }


def retrieve_incidents_node(state: AgentState) -> dict:
    """유사 장애 사례를 검색하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] retrieve_incidents_node: searching incidents")
    
    try:
        service = get_knowledge_service()
        
        # incident 스토어에서 검색 (async 함수 동기 호출)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        search_response = loop.run_until_complete(
            service.search(
                query=user_input,
                store_type=StoreType.INCIDENT,
                top_k=5,
            )
        )
        
        evidence = []
        for result in search_response.results:
            evidence.append({
                "type": "incident",
                "doc_id": result.doc_id,
                "content": result.text,
                "score": result.score,
                "metadata": result.metadata,
            })
        
        logger.info(f"[{run_id}] Found {len(evidence)} incident cases")
        
        return {
            "evidence": state.evidence + evidence,
            "trace": {
                **state.trace,
                "retrieve_incidents": {
                    "status": "success",
                    "count": len(evidence),
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Incident retrieval failed: {e}")
        return {
            "errors": state.errors + [f"장애 사례 검색 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "retrieve_incidents": {"status": "error", "error": str(e)}
            }
        }


def retrieve_system_info_node(state: AgentState) -> dict:
    """시스템 정보를 검색하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] retrieve_system_info_node: searching system info")
    
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
                top_k=3,
            )
        )
        
        evidence = []
        for result in search_response.results:
            evidence.append({
                "type": "system",
                "doc_id": result.doc_id,
                "content": result.text,
                "score": result.score,
                "metadata": result.metadata,
            })
        
        logger.info(f"[{run_id}] Found {len(evidence)} system info chunks")
        
        return {
            "evidence": state.evidence + evidence,
            "trace": {
                **state.trace,
                "retrieve_system_info": {
                    "status": "success",
                    "count": len(evidence),
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] System info retrieval failed: {e}")
        return {
            "errors": state.errors + [f"시스템 정보 검색 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "retrieve_system_info": {"status": "error", "error": str(e)}
            }
        }


def generate_hypotheses_node(state: AgentState) -> dict:
    """가설을 생성하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] generate_hypotheses_node: generating hypotheses")
    
    # 증거 수집
    incident_evidence = [e for e in state.evidence if e.get("type") == "incident"]
    system_evidence = [e for e in state.evidence if e.get("type") == "system"]
    
    # 프롬프트 구성
    if not incident_evidence:
        incidents_text = "유사 장애 사례가 없습니다."
    else:
        incidents_text = "\n\n---\n\n".join([
            f"[사례: {e.get('doc_id', 'unknown')}]\n{e.get('content', '')}"
            for e in incident_evidence
        ])
    
    if not system_evidence:
        system_text = "시스템 정보가 없습니다."
    else:
        system_text = "\n\n---\n\n".join([
            f"[시스템: {e.get('doc_id', 'unknown')}]\n{e.get('content', '')}"
            for e in system_evidence
        ])
    
    system_prompt = RCA_SYSTEM_PROMPT.format(
        incidents=incidents_text,
        system_info=system_text,
    )
    
    # 사용자 메시지 구성
    user_message = f"다음 장애/로그를 분석하고 원인 가설을 제시해주세요:\n\n{user_input}"
    
    # 첨부 파일 로그 추가
    file_logs = state.context.get("file_logs", [])
    if file_logs:
        file_content = "\n\n".join([
            f"[파일: {f.get('filename', 'unknown')}]\n{f.get('content', '')[:2000]}"
            for f in file_logs
        ])
        user_message += f"\n\n### 첨부 로그 파일\n{file_content}"
    
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
        
        # 가설 정렬 (rank 기준)
        hypotheses = result.get("hypotheses", [])
        hypotheses.sort(key=lambda x: x.get("rank", 999))
        
        rca_result = RCAResult(
            hypotheses=hypotheses,
            evidence=incident_evidence + system_evidence,
            summary=result.get("summary", ""),
        )
        
        logger.info(f"[{run_id}] Generated {len(hypotheses)} hypotheses")
        
        return {
            "rca_result": rca_result,
            "trace": {
                **state.trace,
                "generate_hypotheses": {
                    "status": "success",
                    "hypothesis_count": len(hypotheses),
                }
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[{run_id}] Failed to parse RCA response: {e}")
        
        rca_result = RCAResult(
            hypotheses=[{
                "rank": 1,
                "title": "분석 결과 파싱 실패",
                "description": "LLM 응답을 파싱할 수 없습니다.",
                "evidence": [],
                "confidence": "low",
                "verification_steps": ["수동 분석 필요"],
            }],
            evidence=[],
            summary="분석 결과 파싱 실패",
        )
        
        return {
            "rca_result": rca_result,
            "errors": state.errors + [f"RCA 결과 파싱 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "generate_hypotheses": {"status": "parse_error", "error": str(e)}
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Hypothesis generation failed: {e}")
        
        rca_result = RCAResult(
            hypotheses=[{
                "rank": 1,
                "title": "분석 실패",
                "description": f"분석 중 오류 발생: {str(e)}",
                "evidence": [],
                "confidence": "low",
                "verification_steps": ["시스템 상태 확인", "수동 분석 필요"],
            }],
            evidence=[],
            summary=f"분석 실패: {str(e)}",
        )
        
        return {
            "rca_result": rca_result,
            "errors": state.errors + [f"RCA 분석 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "generate_hypotheses": {"status": "error", "error": str(e)}
            }
        }


def prioritize_hypotheses_node(state: AgentState) -> dict:
    """가설 우선순위를 정렬하는 노드"""
    run_id = state.run_id
    rca_result = state.rca_result
    
    if not rca_result:
        logger.warning(f"[{run_id}] No RCA result to prioritize")
        return {}
    
    logger.info(f"[{run_id}] prioritize_hypotheses_node: sorting hypotheses")
    
    # 가설 정렬 (이미 rank로 정렬되어 있지만, confidence도 고려)
    hypotheses = list(rca_result.hypotheses)
    
    # confidence 점수 매핑
    confidence_score = {"high": 3, "medium": 2, "low": 1}
    
    # rank 우선, 동일 rank면 confidence 우선
    hypotheses.sort(key=lambda x: (
        x.get("rank", 999),
        -confidence_score.get(x.get("confidence", "low"), 0)
    ))
    
    # Top-N만 유지 (최대 5개)
    top_hypotheses = hypotheses[:5]
    
    # 업데이트된 RCAResult 생성
    updated_result = RCAResult(
        hypotheses=top_hypotheses,
        evidence=rca_result.evidence,
        summary=rca_result.summary,
    )
    
    logger.info(f"[{run_id}] Prioritized to top {len(top_hypotheses)} hypotheses")
    
    return {
        "rca_result": updated_result,
        "trace": {
            **state.trace,
            "prioritize_hypotheses": {
                "status": "success",
                "top_count": len(top_hypotheses),
            }
        }
    }


# ===== 서브그래프 빌드 =====

def build_rca_graph():
    """장애 RCA 서브그래프 생성"""
    graph = StateGraph(AgentState)
    
    # 노드 추가
    graph.add_node("PARSE_LOGS", parse_logs_node)
    graph.add_node("RETRIEVE_INCIDENTS", retrieve_incidents_node)
    graph.add_node("RETRIEVE_SYSTEM_INFO", retrieve_system_info_node)
    graph.add_node("GENERATE_HYPOTHESES", generate_hypotheses_node)
    graph.add_node("PRIORITIZE_HYPOTHESES", prioritize_hypotheses_node)
    
    # 엣지 연결
    graph.add_edge(START, "PARSE_LOGS")
    graph.add_edge("PARSE_LOGS", "RETRIEVE_INCIDENTS")
    graph.add_edge("RETRIEVE_INCIDENTS", "RETRIEVE_SYSTEM_INFO")
    graph.add_edge("RETRIEVE_SYSTEM_INFO", "GENERATE_HYPOTHESES")
    graph.add_edge("GENERATE_HYPOTHESES", "PRIORITIZE_HYPOTHESES")
    graph.add_edge("PRIORITIZE_HYPOTHESES", END)
    
    return graph.compile()


@lru_cache(maxsize=1)
def get_rca_graph():
    """컴파일된 RCA 서브그래프 싱글톤"""
    logger.info("[rca_graph] Building RCA subgraph")
    return build_rca_graph()
