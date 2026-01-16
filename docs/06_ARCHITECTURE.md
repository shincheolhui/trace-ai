아래는 **PRD 최종본 + 기능 정의서 + 요구사항 명세서 + 화면 설계서 + 유스케이스**를 기준으로 정리한
**TRACE-AI 프로젝트 – 6. 아키텍처 설계서 (Architecture Design)** 입니다.

요청하신 대로 **Notion 및 프로젝트 루트(`docs/06_ARCHITECTURE.md`)에 그대로 붙여넣어 사용 가능한 Markdown 형식**이며,
**제품 아키텍처 관점만 기술**하고 개발자 개인 환경 전제는 포함하지 않습니다.

---

# TRACE-AI

## 6. 아키텍처 설계서 (Architecture Design)

---

## 1. 문서 개요

| 항목    | 내용                                 |
| ----- | ---------------------------------- |
| 프로젝트명 | TRACE-AI                           |
| 문서 목적 | TRACE-AI의 전체 시스템 아키텍처 및 컴포넌트 역할 정의 |
| 대상 독자 | 개발자, 아키텍트, 기술 리드, 해커톤 심사위원         |
| 문서 형식 | Markdown (Notion / GitHub 호환)      |
| 기준 문서 | PRD 최종본, 기능 정의서, 요구사항 명세서, 유스케이스   |
| 범위    | 해커톤 MVP 기준 아키텍처                    |

---

## 2. 아키텍처 설계 목표

TRACE-AI 아키텍처는 다음 목표를 가진다.

1. **신뢰성**

   * 판단·승인·실행·감사가 분리되면서도 일관된 흐름 유지
2. **통제 가능성**

   * 실행 단계는 항상 승인 게이트를 통과
3. **추적 가능성**

   * 모든 요청은 run_id로 전 컴포넌트에서 추적
4. **확장성**

   * 에이전트, 지식 저장소, Tool을 독립적으로 확장 가능
5. **엔터프라이즈 적합성**

   * 감사·책임·권한 구조 명확

---

## 3. 전체 아키텍처 개요

### 3.1 논리적 아키텍처 개요

```
[ UI (Chainlit) ]
        |
        v
[ API Gateway (FastAPI) ]
        |
        v
[ Agent Orchestrator (LangGraph) ]
   |        |        |
   v        v        v
[규정 감지] [장애 RCA] [업무 실행]
   |        |        |
   +--------+--------+
            |
            v
     [Approval / Control Layer]
            |
            v
     [Tool Execution Layer]
            |
            v
        [Logs / Audit]
```

---

## 4. 계층별 아키텍처 설계

---

## 4.1 Presentation Layer (UI)

### 구성 요소

* **Chainlit Web UI**

### 역할

* 사용자 요청 입력
* 파일 업로드 (로그/문서)
* 판단 결과, 실행 계획 표시
* 승인/거부 인터랙션
* 로그 및 감사 결과 조회

### 설계 특징

* 비IT 직군도 이해 가능한 단순 UI
* 실행 환경 상태는 **표시만 제공**
* UI는 판단·실행 로직을 직접 포함하지 않음

---

## 4.2 API Layer (FastAPI)

### 구성 요소

* REST API Endpoints
* Request/Response Validation
* 인증/권한 검사 (MVP 수준)

### 역할

* UI 요청 수신
* run_id 생성
* Agent Orchestrator 호출
* 승인 요청 및 결과 전달
* 로그/감사 조회 제공

### 설계 특징

* Stateless API
* run_id를 모든 하위 계층으로 전달

---

## 4.3 Agent Orchestration Layer (LangGraph)

### 구성 요소

* Orchestrator Graph
* Sub Graph:

  * 규정 위반 감지 그래프
  * 장애 RCA 그래프
  * 업무 실행 그래프

### 역할

* 사용자 요청 의도(Intent) 분류
* 서브 그래프 실행 순서 결정
* 상태 관리 및 분기 처리
* 승인 대기 상태 관리

### 설계 특징

* **상태 기반(Stateful) 워크플로우**
* 승인 시점에서 실행 중단 및 재개 가능
* 그래프 단위 테스트 용이

---

## 4.4 Knowledge Layer (지식 저장소)

### 구성 요소

* Vector DB (FAISS / Milvus)
* 문서 메타데이터 저장소

### 역할

* 내부 문서 임베딩 저장
* 유사도 기반 검색
* 근거(Evidence) 제공

### 지식 저장소 유형

* 정책 지식 저장소
* 장애 지식 저장소
* 시스템/업무 지식 저장소

### 설계 특징

* 판단 로직과 분리
* 문서 유형별 분리 가능

---

## 4.5 Approval & Control Layer

### 구성 요소

* 승인 상태 관리자
* 승인 요청 큐
* 승인 결과 저장소

### 역할

* 실행 단계 위험도 평가
* 승인 필요 여부 판단
* 승인/거부 처리
* 승인 이력 기록

### 설계 특징

* 모든 실행은 반드시 이 계층을 통과
* 승인 정책은 중앙 집중 관리

---

## 4.6 Tool Execution Layer

### 구성 요소

* Tool Adapter
* External Tool Interface

### 역할

* 승인된 실행 단계 수행
* 실행 결과 반환

### 설계 특징

* Tool 구현과 Agent 분리
* 새로운 Tool 추가 시 Agent 수정 최소화
* 실행 실패도 정상 결과로 처리 가능

---

## 4.7 Logging & Audit Layer

### 구성 요소

* 구조화 로그(JSON)
* 감사 기록 저장소

### 역할

* 판단/실행 단계 로그 기록
* run 단위 감사 요약 생성
* 감사 이력 조회 제공

### 설계 특징

* 모든 이벤트는 run_id 기준
* 감사 기록은 변경 불가(append-only)

---

## 5. 데이터 흐름 (End-to-End)

### 5.1 표준 요청 흐름

```
User
 ↓
UI (Chainlit)
 ↓
FastAPI (run_id 생성)
 ↓
LangGraph Orchestrator
 ↓
지식 저장소 검색
 ↓
판단 결과 생성
 ↓
실행 계획 생성
 ↓
승인 대기
 ↓
승인 후 실행
 ↓
로그 기록
 ↓
감사 요약 생성
```

---

## 6. 주요 아키텍처 결정 사항 (ADR 요약)

| 결정 항목         | 선택                |
| ------------- | ----------------- |
| Orchestration | LangGraph         |
| API           | FastAPI           |
| UI            | Chainlit          |
| 지식 저장소        | Vector DB 기반      |
| 실행 통제         | Human-in-the-loop |
| 감사            | run_id 기반         |

---

## 7. 확장 아키텍처 고려 사항 (Beyond MVP)

* RBAC / SSO 연동
* 중앙 로그 수집 시스템 연계
* 멀티 지식 저장소 클러스터
* 워크플로우 시각적 편집기

---

## 8. 아키텍처 설계 요약 (One-liner)

> **TRACE-AI 아키텍처는
> 판단·승인·실행·감사를 분리하면서
> 하나의 run_id로 통합하는 엔터프라이즈 구조이다.**

---

### 다음 단계

다음 문서는 이 아키텍처를 **에이전트 상태 흐름 관점에서 구체화하는**

👉 **7. LangGraph 워크플로우 상세 설계서** 입니다.

계속 진행하시겠습니까?
