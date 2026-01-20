아래는 **PRD 최종본 + 기능 정의서 + 요구사항 명세서 + 아키텍처 + LangGraph 워크플로우 + API 명세**를 기준으로 정리한
**TRACE-AI 프로젝트 – 9. 로그/감사 설계서 (Logging & Audit Design)** 입니다.

요청하신 대로 **Notion 및 프로젝트 루트(`docs/09_LOGGING_AUDIT.md`)에 그대로 붙여넣어 사용 가능한 Markdown 형식**이며,
**제품 관점의 로그·감사 설계만 포함**하고 개발자 개인 환경 전제는 포함하지 않습니다.

---

# TRACE-AI

## 08. 로그 / 감사 설계서 (Logging & Audit Design)

---

## 1. 문서 개요

| 항목    | 내용                                      |
| ----- | --------------------------------------- |
| 프로젝트명 | TRACE-AI                                |
| 문서 목적 | TRACE-AI의 로그 및 감사(Audit) 체계를 설계·정의      |
| 대상 독자 | 개발자, 아키텍트, QA, 해커톤 심사위원                 |
| 문서 형식 | Markdown (Notion / GitHub 호환)           |
| 기준 문서 | 요구사항 명세서, 아키텍처 설계서, LangGraph 워크플로우 설계서 |
| 범위    | 해커톤 MVP 기준 로그·감사 설계                     |

---

## 2. 설계 목표

TRACE-AI의 로그·감사 시스템은 다음 목표를 가진다.

1. **완전한 추적성(Traceability)**

   * 하나의 요청을 run_id로 끝까지 추적 가능
2. **책임성(Accountability)**

   * 누가, 언제, 무엇을 승인·실행했는지 명확
3. **판단 근거 보존**

   * 판단 결과와 사용된 근거(Evidence) 연결
4. **엔터프라이즈 감사 적합성**

   * 사후 감사 및 리뷰에 바로 활용 가능
5. **불변성**

   * 감사 기록은 변경 불가(append-only)

---

## 3. 로그(Log)와 감사(Audit)의 구분

| 구분     | 로그(Log)        | 감사(Audit)       |
| ------ | -------------- | --------------- |
| 목적     | 디버깅·운영         | 책임·감사·보고        |
| 단위     | 이벤트/노드         | run 단위          |
| 변경 가능성 | 가능(보존 정책 적용)   | 불가(append-only) |
| 주요 사용자 | 개발자/운영자        | 관리자/감사자         |
| 예시     | “RCA 서브그래프 시작” | “승인 후 실행 완료”    |

---

## 4. 공통 식별자 설계

### 4.1 run_id

* 모든 요청은 고유한 **run_id**를 가진다.
* run_id는 다음에 공통 사용된다.

  * 판단 결과
  * 승인 기록
  * 실행 결과
  * 로그
  * 감사 요약

---

## 5. 로그 설계

---

## 5.1 로그 이벤트 구조

모든 로그는 **구조화 JSON 형식**으로 기록한다.

### 공통 로그 필드

| 필드        | 타입     | 설명                                   |
| --------- | ------ | ------------------------------------ |
| timestamp | string | ISO-8601                             |
| level     | string | INFO / WARN / ERROR                  |
| run_id    | string | 요청 식별자                               |
| component | string | api / orchestrator / subgraph / tool |
| graph     | string | rca / compliance / workflow          |
| node      | string | LangGraph 노드명                        |
| event     | string | start / end / decision / error       |
| message   | string | 요약 메시지                               |
| meta      | object | 추가 정보                                |

---

### 5.2 주요 로그 이벤트 유형

#### (1) Node Start / End

```json
{
  "event": "start",
  "node": "R3_HypothesisGeneration"
}
```

#### (2) 지식 저장소 검색

```json
{
  "event": "knowledge_search",
  "meta": {
    "store_type": "policy",
    "top_k": 5
  }
}
```

#### (3) 승인 이벤트

```json
{
  "event": "approval",
  "meta": {
    "action": "approved",
    "step_ids": ["step-1"]
  }
}
```

#### (4) 실행 이벤트

```json
{
  "event": "execution",
  "meta": {
    "tool": "issue_create",
    "status": "success"
  }
}
```

#### (5) 오류 이벤트

```json
{
  "event": "error",
  "meta": {
    "error_type": "ToolExecutionError"
  }
}
```

---

## 6. 민감 정보 보호 정책

### 6.1 로그에 기록 금지

* API Key, 토큰
* 개인 식별 정보
* 문서 원문 전체
* Tool 입력의 원문

### 6.2 대체 기록 방식

* 요약(summary)
* 마스킹(`[REDACTED]`)
* 해시(hash)

---

## 7. 감사(Audit) 설계

---

## 7.1 감사 레코드 구조

감사 기록은 **run 단위로 1건 이상 생성**된다.

| 필드               | 타입     | 설명                                  |
| ---------------- | ------ | ----------------------------------- |
| audit_id         | string | 감사 ID                               |
| run_id           | string | 연결된 실행                              |
| user             | string | 요청 사용자                              |
| started_at       | string | 실행 시작                               |
| finished_at      | string | 실행 종료                               |
| intent           | string | rca / compliance / workflow / mixed |
| summary          | string | 판단·실행 요약                            |
| evidence_refs    | array  | 사용된 근거                              |
| approvals        | array  | 승인 내역                               |
| actions_executed | array  | 실행된 단계                              |
| result_status    | string | SUCCESS / PARTIAL / FAILED          |

---

## 7.2 감사 생성 시점

* LangGraph 최종 노드에서 생성
* 실행 종료 시점 기준

---

## 8. 로그·감사 저장 전략 (MVP)

### 8.1 저장 방식

| 구분 | 방식                |
| -- | ----------------- |
| 로그 | JSONL 파일 또는 단순 DB |
| 감사 | JSON 파일 또는 DB     |

### 8.2 디렉터리 구조 예시

```
logs/
 └─ runs/
    └─ {run_id}.jsonl

audit/
 └─ audit_{date}.json
```

---

## 9. 로그·감사 조회 기능 연계

| 기능       | 연계 API                   |
| -------- | ------------------------ |
| 실행 로그 조회 | GET /runs/{run_id}/logs  |
| 감사 요약 조회 | GET /runs/{run_id}/audit |

---

## 10. 오류 및 예외 처리 정책

* 오류 발생 시:

  * ERROR 로그 기록
  * 감사 기록에 오류 요약 포함
* 일부 실패는 **PARTIAL SUCCESS**로 기록 가능

---

## 11. 확장 고려 사항 (Beyond MVP)

* 중앙 로그 수집 시스템 연계
* OpenTelemetry 연동
* 감사 리포트 자동 생성(PDF/CSV)

---

## 12. 로그/감사 설계 요약 (One-liner)

> **TRACE-AI의 로그·감사 체계는
> 하나의 run_id로 판단·승인·실행·근거를 끝까지 증명한다.**

---

### 다음 단계

다음 문서는 품질 검증 관점의

👉 **09. 테스트 계획서 (Test Plan)** 입니다.
