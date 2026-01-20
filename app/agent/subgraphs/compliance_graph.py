# app/agent/subgraphs/compliance_graph.py
"""규정 위반 감지 서브그래프"""
from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState, ComplianceResult
from app.integrations.llm.openrouter_client import get_openrouter_client
from app.services.knowledge_service import get_knowledge_service
from app.schemas.knowledge import StoreType

logger = logging.getLogger(__name__)

# 프롬프트 로드
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """마크다운 프롬프트 파일 로드"""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return ""


COMPLIANCE_SYSTEM_PROMPT = """당신은 기업 내부 규정 및 정책 준수 여부를 분석하는 전문가입니다.

### 분석 원칙
1. 모든 판단에는 반드시 근거(Evidence)가 필요합니다
2. 불확실한 경우 "potential_violation"으로 분류합니다
3. 위반 시 구체적인 수정 권고사항을 제시합니다
4. 판단 근거가 없으면 "근거 부족"으로 명시합니다

### 관련 규정
{policies}

### 출력 형식 (JSON만 출력)
{{
  "status": "violation" | "no_violation" | "potential_violation",
  "violations": [
    {{
      "rule_name": "위반된 규정명",
      "rule_content": "규정 원문 (간략히)",
      "violation_detail": "위반 내용 설명",
      "severity": "high" | "medium" | "low"
    }}
  ],
  "recommendations": ["수정 권고사항"],
  "summary": "분석 요약 (1-2문장)"
}}

규정이 없으면:
{{
  "status": "no_violation",
  "violations": [],
  "recommendations": ["관련 규정을 찾지 못했습니다. 담당자에게 문의하세요."],
  "summary": "관련 규정이 없어 위반 여부를 판단할 수 없습니다."
}}
"""


# ===== 노드 함수들 =====

def retrieve_policies_node(state: AgentState) -> dict:
    """관련 규정을 검색하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] retrieve_policies_node: searching policies")
    
    try:
        service = get_knowledge_service()
        
        # 규정(policy) 스토어에서 검색 (async 함수 동기 호출)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        search_response = loop.run_until_complete(
            service.search(
                query=user_input,
                store_type=StoreType.POLICY,
                top_k=5,
            )
        )
        
        evidence = []
        for result in search_response.results:
            evidence.append({
                "type": "policy",
                "doc_id": result.doc_id,
                "content": result.text,
                "score": result.score,
                "metadata": result.metadata,
            })
        
        logger.info(f"[{run_id}] Found {len(evidence)} policy chunks")
        
        return {
            "evidence": state.evidence + evidence,
            "trace": {
                **state.trace,
                "retrieve_policies": {
                    "status": "success",
                    "count": len(evidence),
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Policy retrieval failed: {e}")
        return {
            "errors": state.errors + [f"규정 검색 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "retrieve_policies": {"status": "error", "error": str(e)}
            }
        }


def analyze_compliance_node(state: AgentState) -> dict:
    """규정 위반 여부를 분석하는 노드"""
    run_id = state.run_id
    user_input = state.user_input or ""
    
    logger.info(f"[{run_id}] analyze_compliance_node: analyzing")
    
    # 규정 증거 수집
    policy_evidence = [e for e in state.evidence if e.get("type") == "policy"]
    
    if not policy_evidence:
        policies_text = "관련 규정이 없습니다."
    else:
        policies_text = "\n\n---\n\n".join([
            f"[규정: {e.get('doc_id', 'unknown')}]\n{e.get('content', '')}"
            for e in policy_evidence
        ])
    
    # 프롬프트 구성
    system_prompt = COMPLIANCE_SYSTEM_PROMPT.format(policies=policies_text)
    
    # 첨부 파일이 있으면 사용자 메시지에 추가
    user_message = user_input
    if state.files:
        file_contents = "\n\n".join([
            f"[첨부파일: {f.get('name', 'unknown')}]\n{f.get('content', '')[:2000]}"
            for f in state.files
        ])
        user_message = f"{user_input}\n\n### 첨부 파일\n{file_contents}"
    
    client = get_openrouter_client()
    
    try:
        response = client.chat_with_system(
            system_prompt=system_prompt,
            user_message=user_message,
        )
        
        # JSON 파싱
        # 마크다운 코드 블록 제거
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        
        result = json.loads(response)
        
        compliance_result = ComplianceResult(
            status=result.get("status", "no_violation"),
            violations=result.get("violations", []),
            recommendations=result.get("recommendations", []),
            evidence=policy_evidence,
            summary=result.get("summary", ""),
        )
        
        logger.info(f"[{run_id}] Compliance analysis: {compliance_result.status}")
        
        return {
            "compliance_result": compliance_result,
            "trace": {
                **state.trace,
                "analyze_compliance": {
                    "status": "success",
                    "result_status": compliance_result.status,
                    "violation_count": len(compliance_result.violations),
                }
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[{run_id}] Failed to parse compliance response: {e}")
        
        # 파싱 실패 시 기본 결과
        compliance_result = ComplianceResult(
            status="potential_violation",
            violations=[],
            recommendations=["분석 결과를 파싱할 수 없습니다. 담당자에게 문의하세요."],
            summary="분석 결과 파싱 실패",
        )
        
        return {
            "compliance_result": compliance_result,
            "errors": state.errors + [f"규정 분석 파싱 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "analyze_compliance": {"status": "parse_error", "error": str(e)}
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Compliance analysis failed: {e}")
        
        compliance_result = ComplianceResult(
            status="potential_violation",
            violations=[],
            recommendations=["분석 중 오류가 발생했습니다. 담당자에게 문의하세요."],
            summary=f"분석 실패: {str(e)}",
        )
        
        return {
            "compliance_result": compliance_result,
            "errors": state.errors + [f"규정 분석 실패: {str(e)}"],
            "trace": {
                **state.trace,
                "analyze_compliance": {"status": "error", "error": str(e)}
            }
        }


def generate_recommendation_node(state: AgentState) -> dict:
    """위반 시 권고사항을 생성하는 노드"""
    run_id = state.run_id
    compliance_result = state.compliance_result
    
    if not compliance_result:
        logger.warning(f"[{run_id}] No compliance result, skipping recommendation")
        return {}
    
    # 위반이 아니면 스킵
    if compliance_result.status == "no_violation":
        logger.info(f"[{run_id}] No violation, skipping recommendation generation")
        return {
            "trace": {
                **state.trace,
                "generate_recommendation": {"status": "skipped", "reason": "no_violation"}
            }
        }
    
    # 이미 권고사항이 있으면 스킵
    if compliance_result.recommendations:
        logger.info(f"[{run_id}] Recommendations already exist")
        return {
            "trace": {
                **state.trace,
                "generate_recommendation": {"status": "already_exists"}
            }
        }
    
    logger.info(f"[{run_id}] generate_recommendation_node: generating")
    
    # 권고사항 생성을 위한 프롬프트
    violations_text = json.dumps(compliance_result.violations, ensure_ascii=False, indent=2)
    
    client = get_openrouter_client()
    
    try:
        response = client.chat_with_system(
            system_prompt="당신은 규정 준수 전문가입니다. 위반 사항에 대한 구체적인 수정 권고사항을 제시하세요.",
            user_message=f"다음 위반 사항에 대한 수정 권고사항을 JSON 배열로 제시하세요:\n\n{violations_text}\n\n형식: [\"권고사항1\", \"권고사항2\", ...]",
        )
        
        recommendations = json.loads(response)
        
        # ComplianceResult 업데이트
        updated_result = ComplianceResult(
            status=compliance_result.status,
            violations=compliance_result.violations,
            recommendations=recommendations,
            evidence=compliance_result.evidence,
            summary=compliance_result.summary,
        )
        
        return {
            "compliance_result": updated_result,
            "trace": {
                **state.trace,
                "generate_recommendation": {
                    "status": "success",
                    "count": len(recommendations),
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[{run_id}] Recommendation generation failed: {e}")
        return {
            "trace": {
                **state.trace,
                "generate_recommendation": {"status": "error", "error": str(e)}
            }
        }


# ===== 서브그래프 빌드 =====

def build_compliance_graph():
    """규정 위반 감지 서브그래프 생성"""
    graph = StateGraph(AgentState)
    
    # 노드 추가
    graph.add_node("RETRIEVE_POLICIES", retrieve_policies_node)
    graph.add_node("ANALYZE_COMPLIANCE", analyze_compliance_node)
    graph.add_node("GENERATE_RECOMMENDATION", generate_recommendation_node)
    
    # 엣지 연결
    graph.add_edge(START, "RETRIEVE_POLICIES")
    graph.add_edge("RETRIEVE_POLICIES", "ANALYZE_COMPLIANCE")
    graph.add_edge("ANALYZE_COMPLIANCE", "GENERATE_RECOMMENDATION")
    graph.add_edge("GENERATE_RECOMMENDATION", END)
    
    return graph.compile()


@lru_cache(maxsize=1)
def get_compliance_graph():
    """컴파일된 규정 위반 감지 서브그래프 싱글톤"""
    logger.info("[compliance_graph] Building compliance subgraph")
    return build_compliance_graph()
