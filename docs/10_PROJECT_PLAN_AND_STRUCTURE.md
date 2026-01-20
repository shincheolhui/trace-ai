# TRACE-AI

## Part 1. Project Plan (4 Weeks)

- 프로젝트명: TRACE-AI
- 기간: 4주 (28일)
- 목표: **해커톤 시연 가능한 엔터프라이즈 AI Agent MVP 완성**
- 핵심 원칙: **범위 고정 / 고도화 금지 / 흐름 우선 / run_id 기반 추적**

---

## 1. 운영 원칙 (변경 금지)

### 1.1 Definition of Done (완료 기준)

다음 조건을 모두 만족하면 **완료**로 간주한다.

- 기능이 "존재"한다 (mock 포함)
- LangGraph 기준 END 상태까지 도달한다
- run_id 기준으로 판단·승인·실행·로그·감사를 설명할 수 있다

---

### 1.2 범위 통제 규칙

- ❌ 새로운 기능 추가 금지
- ❌ 성능 최적화 / 고급 패턴 / Agent 실험 금지
- ⭕ 주차 목표 미달 시 **이월 금지**, 대신 **범위 축소**
- ⭕ "잘 만든 일부"보다 "끝까지 이어지는 전체"

---

## 2. Git Workflow (전역 규칙)

### 2.1 브랜치 네이밍 규칙

```
w{주차}-{작업번호}-{요약}
```

예:

- `w1-2-run-id-plumbing`
- `w2-3-rca-subgraph`

---

### 2.2 커밋 메시지 규칙

```
[W{주차}-{작업번호}] <행동 + 결과>
```

예:

- `[W1-2] generate and propagate run_id`
- `[W3-3] generate audit summary per run`

---

### 2.3 작업–Git 매핑 원칙

- WBS 작업 1개 = 브랜치 1개
- 체크리스트 100% 충족 후 main 병합
- 체크리스트 미완료 상태에서 merge 금지

---

## 3. 4주 WBS + 상세 작업내용 + 실행 체크리스트

---

# WEEK 1 — 뼈대 고정 (Architecture First)

> 주 목표
>
> "기능 품질과 무관하게, 시스템이 끝까지 흐를 수 있는 구조 확보"

---

### W1-1 프로젝트 초기 구조 구성

**작업 목적**

TRACE-AI의 전체 개발을 수용할 수 있는 최소한의 서버·디렉터리·설정 구조를 만든다.

이 단계에서는 기능 구현이 아니라 **'자리 잡기'**가 목적이다.

**작업 내용**

- FastAPI 프로젝트 생성
- `app/`, `api/`, `agent/`, `core/`, `logs/` 디렉터리 생성
- 환경변수 로딩 구조 (`.env`, `.env.example`)
- `/api/v1/health` 엔드포인트 추가
- README에 실행 방법 최소 문구 추가

**브랜치**

- `w1-1-project-skeleton`

**체크리스트**

- [x] FastAPI 서버 기동
- [x] `/api/v1/health` 200 OK
- [x] 디렉터리 구조 확정
- [x] README 실행 방법 작성

---

### W1-2 run_id 기반 실행 골격

**작업 목적**

TRACE-AI의 모든 판단·실행·로그·감사를 하나의 실행 단위(run)로 묶기 위한 **핵심 기반**을 만든다.

**작업 내용**

- 요청 진입 시 UUID 기반 run_id 생성
- FastAPI request context에 run_id 저장
- LangGraph State에 run_id 포함
- 응답 JSON에 run_id 포함
- 기본 로그 출력 시 run_id 포함

**브랜치**

- `w1-2-run-id-plumbing`

**체크리스트**

- [x] 요청마다 run_id 생성
- [x] LangGraph State에 run_id 존재
- [x] API 응답에 run_id 포함
- [x] 로그에서 run_id 확인 가능
- [x] 단일 run 추적 가능

---

### W1-3 LangGraph Orchestrator 기본 흐름

**작업 목적**

TRACE-AI의 모든 기능이 얹힐 **LangGraph 실행 뼈대**를 만든다.

**작업 내용**

- Orchestrator Graph 생성
- Dummy Node 생성
- START → Dummy Node → END 구성
- Node 실행 전/후 로그 출력
- State 전달 구조 확인

**브랜치**

- `w1-3-langgraph-orchestrator`

**체크리스트**

- [x] Graph 실행 성공
- [x] 최소 3개 Node 존재
- [x] Node start/end 로그 출력

---

### W1-4 UI ↔ API 연결

**작업 목적**

사용자 입력이 실제 서버 실행으로 이어지고 결과가 다시 UI로 돌아오는 **최소 왕복 흐름 확보**.

**작업 내용**

- Chainlit 기본 UI 구성
- 사용자 입력 → FastAPI 호출
- API 응답 → UI 출력
- run_id 화면 표시

**브랜치**

- `w1-4-ui-api-bridge`

**체크리스트**

- [x] UI에서 입력 가능
- [x] API 호출 성공
- [x] 응답 UI 출력
- [x] run_id 표시

---

### W1-5 Week 1 종료 점검

**작업 목적**

Week 1의 모든 구성 요소가 하나의 흐름으로 연결되는지 최종 확인.

**작업 내용**

- 전체 실행 1회
- 오류 발생 시에도 END 도달 확인
- 로그 파일 생성 여부 확인

**브랜치**

- `w1-5-week1-smoke`

**체크리스트**

- [x] END 상태 도달
- [x] 오류 발생해도 흐름 유지
- [x] 로그 존재

---

# Week 1 공식 완료 선언

> Week 1 완료(W1-1~W1-5).
> 
> FastAPI 서버 기동, run_id 생성/전파, LangGraph 오케스트레이터(START→DUMMY→END) 실행, Chainlit UI 연동을 완료했으며, UI→API→LangGraph 왕복 스모크 테스트 2회(서로 다른 run_id) 성공으로 전체 실행 흐름과 추적 가능성을 검증함.

---

# WEEK 2 — 핵심 기능 연결 (TOP3)

> 주 목표
>
> 규정 감지 + 장애 RCA + 업무 실행 계획이 하나의 run 안에서 동작

---

### W2-1 지식 저장소 업로드 파이프라인

**작업 목적**

AI 판단의 근거가 되는 문서를 시스템이 "기억"할 수 있게 만든다.

**작업 내용**

- 문서 업로드 API 구현
- 텍스트 파싱
- 청크 분할
- 임베딩 생성
- Vector DB 저장
- 단순 검색 API 구현

**브랜치**

- `w2-1-knowledge-ingest`

**체크리스트**

- [ ] 문서 업로드 가능
- [ ] 임베딩 생성 성공
- [ ] 검색 결과 반환

---

### W2-2 규정 위반 감지 서브그래프

**작업 목적**

입력 내용이 내부 규정을 위반하는지 **근거 기반으로 판단**.

**작업 내용**

- 입력 분석
- 정책 지식 저장소 검색
- 위반/비위반/잠재적 위반 판단
- Evidence 구성

**브랜치**

- `w2-2-compliance-subgraph`

**체크리스트**

- [ ] 정책 검색
- [ ] 위반 판단
- [ ] Evidence 출력

---

### W2-3 장애 RCA 서브그래프

**작업 목적**

로그/장애 설명을 기반으로 **원인 가설 + 근거**를 제시.

**작업 내용**

- 로그 입력 처리
- 장애 지식 저장소 검색
- 복수 가설 생성
- 우선순위 정렬

**브랜치**

- `w2-3-rca-subgraph`

**체크리스트**

- [ ] 로그 입력 처리
- [ ] 유사 사례 검색
- [ ] Top-N 가설 반환

---

### W2-4 업무 실행 계획 서브그래프

**작업 목적**

판단 결과를 실제 "조치 계획" 형태로 변환.

**작업 내용**

- Action Plan 생성
- 단계별 설명
- 위험도 분류
- 승인 필요 여부 설정

**브랜치**

- `w2-4-workflow-subgraph`

**체크리스트**

- [ ] Action Plan 생성
- [ ] 위험도 부여
- [ ] 승인 필요 단계 표시

---

### W2-5 서브그래프 통합

**작업 목적**

여러 판단 결과를 하나의 실행 컨텍스트로 통합.

**작업 내용**

- intent 분기
- 다중 서브그래프 실행
- 결과 병합

**브랜치**

- `w2-5-merge-subgraphs`

**체크리스트**

- [ ] intent 분기 동작
- [ ] mixed 요청 처리
- [ ] 결과 병합 성공

---

# WEEK 3 — 로그·감사 & 안정화

> 주 목표
>
> "왜 이런 판단과 실행이 나왔는지 설명 가능"

---

### W3-1 구조화 로그 시스템

**작업 내용**

- JSON 로그 포맷
- Node start/end
- 판단/실행 로그

---

### W3-2 승인(Human-in-the-loop)

**작업 내용**

- 승인 대기 상태
- 승인 API
- 승인 후 재개

---

### W3-3 감사(Audit) 요약 생성

**작업 내용**

- run 단위 감사 JSON
- 판단·근거·승인·실행 포함

---

### W3-4 오류 처리 안정화

**작업 내용**

- LLM 실패 처리
- 검색 실패 처리
- 실패해도 감사 생성

---

### W3-5 데모 리허설 1차

**작업 내용**

- 전체 시나리오 1회 실행
- 설명 흐름 점검

---

# WEEK 4 — 데모 완성 & 정리

> 주 목표
>
> "보여줄 수 있는 상태로 고정하고 멈춘다"

---

### W4-1 데모 시나리오 고정

### W4-2 UI 가독성 개선

### W4-3 문서 최종 점검

### W4-4 최종 리허설

### W4-5 종료 선언 (Code Freeze)

---

## 4. 최종 한 문장 요약

> 이 문서는 무엇을 더 만들지 결정하는 문서가 아니라 무엇을 안 만들어도 되는지를 결정하는 문서다.

---

---

## Part 2. 프로젝트 구조 정의서 (Project Structure)

---

## 1. 목적 및 적용 범위

본 문서는 TRACE-AI 프로젝트의 **디렉터리 구조, 파일 책임, 역할 분리 기준**을 정의한다.

- 대상 독자: 프로젝트 개발자, 리뷰어, 미래의 나
- 목적:
  - 코드 위치에 대한 판단 비용 제거
  - "이 파일에서 무엇을 해야 하고, 무엇을 하면 안 되는지" 명확화
- 본 문서에 정의된 구조는 **임의 변경을 금지**한다.

---

## 2. 프로젝트 루트 구조

```
trace-ai/
├─ README.md
├─ pyproject.toml # 또는 requirements.txt
├─ .env.example
├─ .gitignore
├─ docs/
├─ app/
├─ ui/
├─ scripts/
```

### 루트 파일 설명

- **README.md**
  - 프로젝트 개요, 실행 방법, 최소 사용법
  - 상세 설계 내용은 포함하지 않는다 (docs로 위임)

- **pyproject.toml / requirements.txt**
  - Python 의존성 정의
  - 개발/실행에 필요한 최소 패키지만 포함

- **.env.example**
  - 필수 환경변수 목록 정의
  - 실제 값 포함 금지

- **.gitignore**
  - `app/data/`, 로그, 로컬 인덱스 파일 포함

---

## 3. docs/ 디렉터리 구조

```
docs/
├─ 01_PRD_AND_FUNCTIONAL_SPEC.md
├─ 02_REQUIREMENTS.md
├─ 03_UI_SPEC.md
├─ 04_USE_CASES.md
├─ 05_ARCHITECTURE.md
├─ 06_LANGGRAPH_WORKFLOW.md
├─ 07_API_SPEC.md
├─ 08_LOGGING_AUDIT.md
├─ 09_TEST_PLAN.md
├─ 10_PROJECT_PLAN_AND_STRUCTURE.md
```

### 문서 관리 원칙

- 문서 번호는 **의미적 순서**이며 변경하지 않는다
- `10_PROJECT_PLAN_AND_STRUCTURE.md`
  - 실행/운영용 문서 + 구조 정의 통합
  - 구조 단일 기준 문서 (Single Source of Truth)
  - 구조 변경 시 반드시 본 문서 수정 선행

---

## 4. app/ 디렉터리 (Backend: FastAPI)

```
app/
├─ main.py
├─ api/
├─ core/
├─ schemas/
├─ services/
├─ agent/
├─ integrations/
├─ data/
└─ tests/
```

---

### 4.1 app/main.py

- FastAPI 애플리케이션 엔트리포인트
- 역할:
  - FastAPI 인스턴스 생성
  - 미들웨어 등록 (run_id, logging)
  - 라우터 등록
- 금지:
  - 비즈니스 로직 작성
  - LangGraph 직접 호출

---

### 4.2 app/api/ (API Layer)

```
api/
└─ v1/
   ├─ agent.py
   ├─ admin_knowledge.py
   ├─ runs.py
   └─ health.py
```

### 공통 원칙
- API는 **얇아야 한다**
- 검증 → 서비스 호출 → 응답 변환만 담당

### agent.py
- Agent 실행/재개/승인 API
- LangGraph 실행은 service를 통해 간접 호출

### admin_knowledge.py
- 지식 저장소 업로드/관리 API
- 관리자 전용 성격 (MVP에서는 단순화)

### runs.py
- run_id 기준 로그/감사 조회 API
- 실행 결과를 "설명"하기 위한 조회 전용

### health.py
- 헬스체크 API
- 외부 의존성 호출 금지

---

### 4.3 app/core/ (공통 인프라)

```
core/
├─ config.py
├─ logging.py
├─ errors.py
├─ run_context.py
└─ constants.py
```

### config.py
- 환경변수 로딩
- 설정 객체 정의
- 실행 환경 판단 로직 포함 가능

### logging.py
- JSON 구조화 로그 포맷 정의
- run_id 자동 포함
- 로그 출력 방식의 단일 기준

### run_context.py
- run_id 생성 및 요청 스코프 전파
- FastAPI 미들웨어와 연동

### errors.py
- 표준 예외 클래스
- 에러 코드/메시지 정의

### constants.py
- 문자열/상수 정의
- 매직 스트링 금지 목적

---

### 4.4 app/schemas/ (Pydantic Models)

```
schemas/
├─ common.py
├─ agent.py
├─ knowledge.py
└─ runs.py
```

- API Request / Response 모델 정의
- LangGraph State와는 분리
- Validation 목적에 한정

---

### 4.5 app/services/ (Use Case Layer)

```
services/
├─ agent_service.py
├─ knowledge_service.py
├─ audit_service.py
└─ log_service.py
```

### agent_service.py
- run 실행/재개/결과 병합
- LangGraph 호출의 유일한 진입점

### knowledge_service.py
- 문서 파싱/임베딩/저장/검색
- Vector DB 추상화 사용

### audit_service.py
- run 단위 감사 정보 생성
- 승인/판단/근거 통합

### log_service.py
- 실행 로그 저장/조회
- 구조화 로그 파일 관리

---

### 4.6 app/agent/ (LangGraph 영역)

```
agent/
├─ state.py
├─ orchestrator.py
├─ nodes/
│  ├─ init_run.py
│  ├─ classify_intent.py
│  ├─ route_plan.py
│  ├─ merge_results.py
│  ├─ approval_gate.py
│  └─ finalize_audit.py
├─ subgraphs/
│  ├─ compliance_graph.py
│  ├─ rca_graph.py
│  └─ workflow_graph.py
└─ prompts/
   ├─ compliance.md
   ├─ rca.md
   └─ workflow.md
```

### state.py
- LangGraph State 정의
- 모든 노드가 공유하는 데이터 구조

### orchestrator.py
- 메인 LangGraph 정의
- 서브그래프 연결 및 실행 순서 관리

### nodes/
- 공통 노드 모음
- intent 분류, 승인 게이트, 결과 병합 등

### subgraphs/
- Compliance / RCA / Workflow 서브그래프
- 독립 실행 가능해야 함

### prompts/
- 프롬프트 템플릿 관리
- 코드와 분리하여 수정 용이성 확보

---

### 4.7 app/integrations/ (외부 연동)

```
integrations/
├─ llm/
│  └─ openrouter_client.py
├─ vectorstore/
│  ├─ base.py
│  ├─ faiss_store.py
│  └─ milvus_store.py
├─ parsers/
│  ├─ pdf_parser.py
│  ├─ text_parser.py
│  └─ log_parser.py
├─ tools/
│  ├─ tool_registry.py
│  ├─ mock_tools.py
│  ├─ jira_tool.py
│  └─ slack_tool.py
└─ storage/
   └─ local_fs.py
```

### llm/
- OpenRouter 호출 래퍼
- 재시도/타임아웃 처리 포함

### vectorstore/
- Vector DB 인터페이스
- FAISS / Milvus 구현 분리

### parsers/
- 문서/로그 파싱 전용
- 비즈니스 로직 금지

### tools/
- 외부 도구(Jira/Slack) 연동
- mock/real 구현 분리

### storage/
- 로컬 파일 저장
- 로그/감사/업로드 파일 관리

---

### 4.8 app/data/ (런타임 데이터)

- 업로드 파일, 인덱스, 로그, 감사 결과 저장
- **Git 관리 대상 아님**

---

### 4.9 app/tests/

```
tests/
├─ test_health.py
├─ test_run_id.py
└─ test_agent_smoke.py
```

- 최소 스모크 테스트
- 구조 변경 시 깨짐 방지 목적

---

## 5. ui/ 디렉터리 (Chainlit)

```
ui/
├─ app.py
├─ chainlit.md
├─ components/
└─ assets/
```

- app.py: Chainlit 엔트리포인트
- Backend API만 의존
- LangGraph 직접 접근 금지

---

## 6. scripts/ 디렉터리

```
scripts/
├─ seed_mock_docs.py
├─ run_smoke.sh
```

- 개발 편의용 스크립트
- 프로덕션 코드와 분리

---

## 7. 구조 변경 금지 원칙

- 본 구조는 **Code Freeze까지 유지**
- 디렉터리/파일 추가 시:
  1. 본 문서 수정
  2. 변경 사유 명시
  3. 커밋 메시지에 구조 변경 명시

---

## 8. 최종 선언

본 문서는 TRACE-AI 프로젝트의 **구조적 단일 기준 문서**이며, 모든 코드 배치는 본 문서를 따른다.
