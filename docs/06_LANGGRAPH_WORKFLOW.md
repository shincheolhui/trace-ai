아래는 **PRD 최종본 + 기능 정의서 + 요구사항 명세서 + 화면 설계서 + 유스케이스 + 아키텍처 설계서**를 기준으로 정리한
**TRACE-AI 프로젝트 – 7. LangGraph 워크플로우 상세 설계서 (LangGraph Workflow Design)** 입니다.

요청하신 대로 **Notion 및 프로젝트 루트(`docs/07_LANGGRAPH_WORKFLOW.md`)에 그대로 붙여넣어 사용 가능한 Markdown 형식**이며,
**제품 관점의 워크플로우 정의에 집중**하고 개발자 개인 환경 전제는 포함하지 않습니다.

---

# TRACE-AI

## 06. LangGraph 워크플로우 상세 설계서

---

## 1. 문서 개요

| 항목    | 내용                                                |
| ----- | ------------------------------------------------- |
| 프로젝트명 | TRACE-AI                                          |
| 문서 목적 | TRACE-AI의 LangGraph 기반 상태 흐름(State Machine) 상세 정의 |
| 대상 독자 | 백엔드 개발자, 아키텍트, QA                                 |
| 문서 형식 | Markdown (Notion / GitHub 호환)                     |
| 기준 문서 | PRD 최종본, 아키텍처 설계서                                 |
| 범위    | 해커톤 MVP 기준 LangGraph 워크플로우                        |

---

## 2. 설계 목표 및 원칙

### 2.1 설계 목표

1. **명시적 상태 관리**

   * 모든 처리 단계는 상태(Node)로 정의
2. **중단·재개 가능성**

   * 승인 대기 시 워크플로우 중단 후 재개
3. **의도 기반 분기**

   * 하나의 요청에서 다수 서브그래프 실행 가능
4. **통제 우선**

   * 실행 전 승인 단계 필수
5. **추적 가능성**

   * 모든 상태 전이는 run_id로 기록

---

### 2.2 공통 설계 원칙

* 모든 Node는 **입력(State) → 출력(State)** 을 명확히 정의
* Node 내부에서 외부 실행 금지 (Tool은 별도 계층)
* 실패는 “중단 사유”로 기록하고 감사 대상이 됨

---

## 3. 전체 워크플로우 개요

### 3.1 상위 Orchestrator Graph

```
[START]
   ↓
[O1] Initialize Run
   ↓
[O2] Intent Classification
   ↓
[O3] Route Planner
   ↓
 ┌───────────────┬───────────────┬───────────────┐
 ↓               ↓               ↓
[RCA Graph]   [Compliance]   [Workflow Graph]
 ↓               ↓               ↓
 └───────────────┴───────────────┘
                 ↓
            [O10] Merge Results
                 ↓
            [O11] Approval Gate
                 ↓
        ┌───────────────┐
        ↓               ↓
   [WAIT]          [EXECUTE]
        ↓               ↓
   [END]         [O12] Finalize & Audit
```

---

## 4. 공통 State 정의

### 4.1 Global State Schema

```python
State = {
  "run_id": str,
  "user_input": str,
  "files": list,
  "intent": list,
  "context": dict,

  "evidence": list,
  "analysis_results": dict,
  "action_plan": list,

  "approval_required": bool,
  "approval_status": str,  # WAITING / APPROVED / REJECTED

  "execution_results": list,
  "logs": list,
  "errors": list
}
```

---

## 5. Orchestrator Node 상세

---

### O1. Initialize Run

**역할**

* run_id 생성
* 초기 상태 구성

**입력**

* 사용자 요청
* 업로드 파일

**출력**

* 초기 State

---

### O2. Intent Classification

**역할**

* 사용자 요청 의도 분류

**의도 유형**

* `compliance`
* `rca`
* `workflow`
* `mixed`

**출력**

* intent 리스트

---

### O3. Route Planner

**역할**

* 실행할 서브그래프 결정
* 실행 순서 정의

**출력**

```json
{
  "routes": ["rca", "compliance", "workflow"]
}
```

---

## 6. 서브그래프 상세 설계

---

## 6.1 Compliance Subgraph (규정 위반 감지)

### 노드 구성

```
[C1] Analyze Input
   ↓
[C2] Search Policy Knowledge Store
   ↓
[C3] Evaluate Compliance
   ↓
[C4] Generate Recommendations
```

---

### C1. Analyze Input

* 입력 문서/텍스트 구조화

### C2. Search Policy Knowledge Store

* 정책 지식 저장소 검색
* Evidence 수집

### C3. Evaluate Compliance

* 위반 / 비위반 / 잠재적 위반 판단

### C4. Generate Recommendations

* 수정 권고 생성

---

## 6.2 RCA Subgraph (장애 RCA)

### 노드 구성

```
[R1] Parse Incident Data
   ↓
[R2] Search Incident Knowledge Store
   ↓
[R3] Hypothesis Generation
   ↓
[R4] Rank & Evidence Mapping
```

---

### R3. Hypothesis Generation

* 복수 원인 가설 생성

### R4. Rank & Evidence Mapping

* 신뢰도 기반 정렬
* 근거 연결

---

## 6.3 Workflow Subgraph (업무 실행 계획)

### 노드 구성

```
[W1] Generate Action Plan
   ↓
[W2] Risk Assessment
   ↓
[W3] Approval Requirement Check
```

---

### W3. Approval Requirement Check

* 위험도 기준 승인 필요 여부 설정

---

## 7. 결과 병합 및 승인 흐름

---

### O10. Merge Results

**역할**

* RCA / Compliance / Workflow 결과 통합

---

### O11. Approval Gate

**분기 조건**

* `approval_required == True`

#### 승인 필요

* 상태: `WAITING_APPROVAL`
* 워크플로우 중단

#### 승인 불필요

* EXECUTE로 이동

---

## 8. 승인 후 재개(Resume) 흐름

### Resume Entry Node

* 승인 결과를 State에 반영
* 승인된 단계만 실행 대상으로 전달

---

## 9. 실행 및 종료

---

### EXECUTE Node

* 승인된 Action Step 실행 요청
* Tool Execution Layer 호출

---

### O12. Finalize & Audit

**역할**

* 최종 결과 정리
* 감사 기록 생성
* END 상태 전환

---

## 10. 오류 처리 설계

### 오류 발생 시 공통 규칙

* 오류 Node에서 처리
* 오류 내용은 State.errors에 저장
* 가능한 경우 다른 서브그래프는 계속 수행
* 감사 기록에 오류 포함

---

## 11. LangGraph 설계 요약 (One-liner)

> **TRACE-AI의 LangGraph 워크플로우는
> 의도 기반 분기 → 서브그래프 처리 → 승인 → 실행 → 감사로 이어지는
> 명시적 상태 머신이다.**

---

### 다음 단계

다음 문서는 이 워크플로우를 **외부 인터페이스 관점에서 정의하는**

👉 **07. API 명세서 (FastAPI)** 입니다.
