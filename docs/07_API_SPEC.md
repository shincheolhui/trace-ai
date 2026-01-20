아래는 **PRD 최종본 + 기능 정의서 + 요구사항 명세서 + 아키텍처 + LangGraph 워크플로우**를 기준으로 정리한
**TRACE-AI 프로젝트 – 8. API 명세서 (FastAPI)** 입니다.

요청하신 대로 **Notion 및 프로젝트 루트(`docs/08_API_SPEC.md`)에 그대로 붙여넣어 사용 가능한 Markdown 형식**이며,
**제품 API 관점에서 필수 엔드포인트·스키마·상태·에러 규격**을 구현 가능한 수준으로 명세합니다.

---

# TRACE-AI

## 07. API 명세서 (FastAPI)

---

## 1. 문서 개요

| 항목    | 내용                                      |
| ----- | --------------------------------------- |
| 프로젝트명 | TRACE-AI                                |
| 문서 목적 | TRACE-AI의 REST API 인터페이스를 명세            |
| 대상 독자 | 백엔드 개발자, 프론트(UI) 개발자, QA                |
| 문서 형식 | Markdown (Notion / GitHub 호환)           |
| 기준 문서 | 요구사항 명세서, 아키텍처 설계서, LangGraph 워크플로우 설계서 |
| 범위    | 해커톤 MVP 기준 API                          |

---

## 2. 공통 규약

### 2.1 Base URL / Versioning

* Base Path: `/api/v1`

### 2.2 Content Types

* JSON 요청/응답: `application/json`
* 파일 업로드: `multipart/form-data`

### 2.3 공통 식별자

* **run_id**: 모든 실행(분석/승인/실행/감사) 단위 식별자(UUID 권장)
* **doc_id**: 지식 저장소 문서 식별자

### 2.4 권한(해커톤 MVP)

* User API: 인증 옵션(비활성 가능)
* Admin API: `X-ADMIN-TOKEN` 헤더 기반 보호

---

## 3. 공통 응답 모델

### 3.1 ErrorResponse

| 필드         | 타입     | 필수 | 설명        |
| ---------- | ------ | -: | --------- |
| error_code | string |  Y | 표준 에러 코드  |
| message    | string |  Y | 사용자 메시지   |
| detail     | object |  N | 상세 정보     |
| run_id     | string |  N | 관련 run_id |

---

### 3.2 EvidenceItem

| 필드            | 타입     | 필수 | 설명      |          |         |
| ------------- | ------ | -: | ------- | -------- | ------- |
| store_type    | string |  Y | `policy | incident | system` |
| doc_id        | string |  Y | 문서 ID   |          |         |
| chunk_id      | string |  N | 청크 ID   |          |         |
| score         | number |  N | 유사도     |          |         |
| source_name   | string |  N | 문서명     |          |         |
| quote_preview | string |  N | 근거 발췌   |          |         |

---

### 3.3 ActionStep

| 필드             | 타입      | 필수 | 설명              |        |       |
| -------------- | ------- | -: | --------------- | ------ | ----- |
| step_id        | string  |  Y | 실행 단계 ID        |        |       |
| title          | string  |  Y | 단계명             |        |       |
| description    | string  |  Y | 설명              |        |       |
| risk_level     | string  |  Y | `low            | medium | high` |
| needs_approval | boolean |  Y | 승인 필요 여부        |        |       |
| tool_name      | string  |  N | 실행 Tool 이름      |        |       |
| tool_input     | object  |  N | Tool 입력(요약/마스킹) |        |       |

---

## 4. Agent API

---

## 4.1 Agent Run (분석/계획 실행 시작)

### Endpoint

* `POST /api/v1/agent/run`

### 목적

* 사용자 요청을 LangGraph Orchestrator에 전달하여 분석/계획을 수행한다.
* 승인 필요 시 `WAITING_APPROVAL` 상태로 반환한다.

### Request (multipart/form-data)

| 필드      | 타입           | 필수 | 설명        |
| ------- | ------------ | -: | --------- |
| query   | string       |  Y | 사용자 요청    |
| context | string(JSON) |  N | 추가 컨텍스트   |
| files   | file[]       |  N | 로그/문서 업로드 |

### Response 200

| 필드                 | 타입             | 설명         |                  |          |        |
| ------------------ | -------------- | ---------- | ---------------- | -------- | ------ |
| run_id             | string         | 실행 식별자     |                  |          |        |
| status             | string         | `COMPLETED | WAITING_APPROVAL | FAILED`  |        |
| intent             | string         | `rca       | compliance       | workflow | mixed` |
| evidence           | EvidenceItem[] | 근거 목록      |                  |          |        |
| analysis_results   | object         | 분석 결과      |                  |          |        |
| action_plan        | ActionStep[]   | 실행 계획      |                  |          |        |
| approvals_required | ActionStep[]   | 승인 필요 단계   |                  |          |        |
| error              | ErrorResponse  | 실패 시       |                  |          |        |

---

## 4.2 Agent Approve (승인 처리 및 재개)

### Endpoint

* `POST /api/v1/agent/approve`

### Request (application/json)

| 필드                | 타입       | 필수 | 설명     |
| ----------------- | -------- | -: | ------ |
| run_id            | string   |  Y | 실행 식별자 |
| approved_step_ids | string[] |  Y | 승인 단계  |
| rejected_step_ids | string[] |  N | 거부 단계  |
| comment           | string   |  N | 코멘트    |

### Response 200

| 필드                | 타입            | 설명         |         |
| ----------------- | ------------- | ---------- | ------- |
| run_id            | string        | run_id     |         |
| status            | string        | `COMPLETED | FAILED` |
| execution_results | object[]      | 실행 결과      |         |
| audit             | object        | 감사 요약      |         |
| error             | ErrorResponse | 실패 시       |         |

---

## 5. 지식 저장소(Admin) API

---

## 5.1 문서 적재 (Ingest)

### Endpoint

* `POST /api/v1/admin/knowledge-store/ingest`

### Auth

* `X-ADMIN-TOKEN: <token>`

### Request (multipart/form-data)

| 필드         | 타입     | 필수 | 설명              |          |         |
| ---------- | ------ | -: | --------------- | -------- | ------- |
| store_type | string |  Y | `policy         | incident | system` |
| tags       | string |  N | comma-separated |          |         |
| version    | string |  N | 문서 버전           |          |         |
| files      | file[] |  Y | 문서 파일           |          |         |

### Response 200

| 필드          | 타입            | 설명           |         |
| ----------- | ------------- | ------------ | ------- |
| ingest_id   | string        | ingest 작업 ID |         |
| status      | string        | `COMPLETED   | FAILED` |
| store_type  | string        | 적재 대상        |         |
| doc_ids     | string[]      | 저장 문서 ID     |         |
| chunk_count | integer       | 청크 수         |         |
| error       | ErrorResponse | 실패 시         |         |

---

## 5.2 문서 목록 조회

* `GET /api/v1/admin/knowledge-store/docs?store_type=policy&limit=50&offset=0`

---

## 5.3 문서 삭제(또는 비활성화)

* `DELETE /api/v1/admin/knowledge-store/docs/{doc_id}?store_type=policy`

---

## 6. Observability API (Logs / Audit)

---

## 6.1 실행 로그 조회

* `GET /api/v1/runs/{run_id}/logs`

### Response 200

* `logs`: 구조화 로그 리스트

---

## 6.2 감사 요약 조회

* `GET /api/v1/runs/{run_id}/audit`

### Response 200

* 감사 요약 JSON 반환

---

## 6.3 실행 목록 조회(선택)

* `GET /api/v1/runs?from=...&to=...&status=...`

---

## 7. 상태 코드 및 표준 에러 코드

### 7.1 HTTP Status

* 200 OK
* 400 Bad Request
* 401 Unauthorized
* 403 Forbidden
* 404 Not Found
* 409 Conflict
* 500 Internal Server Error

### 7.2 표준 에러 코드

| 코드                 | 설명         |
| ------------------ | ---------- |
| E400_INVALID_INPUT | 입력 오류      |
| E401_UNAUTHORIZED  | 인증 실패      |
| E403_FORBIDDEN     | 권한 없음      |
| E404_NOT_FOUND     | 리소스 없음     |
| E409_INVALID_STATE | 상태 충돌      |
| E500_LLM_ERROR     | LLM 호출 실패  |
| E500_STORE_ERROR   | 지식 저장소 오류  |
| E500_TOOL_ERROR    | Tool 실행 오류 |
| E500_PARSE_ERROR   | 문서 파싱 오류   |

---

## 8. API 명세 요약 (One-liner)

> **TRACE-AI API는
> run_id 중심으로 분석(run) → 승인(approve) → 로그/감사 조회를 제공하며,
> 관리자는 지식 저장소를 적재·관리할 수 있다.**

---

### 다음 단계

다음 문서는 관측/감사 관점의 세부 설계인

👉 **08. 로그/감사 설계서 (Logging & Audit Design)** 입니다.
