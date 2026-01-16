아주 적절한 요구입니다.
이제 이 문서는 **“구조 헌법” + “신규 참여자 온보딩 문서” + “미래의 나를 위한 설명서”** 역할까지 해야 합니다.
따라서 **파일 하나하나의 책임과 금지 범위까지 명확히 적는 것이 맞습니다.**

아래는 요청하신 대로 **각 파일/디렉터리의 역할 설명을 충분히 보강한**
👉 **붙여넣기 전용 최종본 `12_PROJECT_STRUCTURE.md` (확장 설명 버전)** 입니다.

Notion / GitHub에 **그대로 복사·붙여넣기·커밋**하셔도 됩니다.

---

# 12_PROJECT_STRUCTURE.md
TRACE-AI 프로젝트 구조 정의서 (상세 설명 포함)

---

## 1. 목적 및 적용 범위

본 문서는 TRACE-AI 프로젝트의 **디렉터리 구조, 파일 책임, 역할 분리 기준**을 정의한다.

- 대상 독자: 프로젝트 개발자, 리뷰어, 미래의 나
- 목적:
  - 코드 위치에 대한 판단 비용 제거
  - “이 파일에서 무엇을 해야 하고, 무엇을 하면 안 되는지” 명확화
- 본 문서에 정의된 구조는 **임의 변경을 금지**한다.

---

## 2. 프로젝트 루트 구조

```

trace-ai/
├─ README.md
├─ pyproject.toml
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
├─ 01_PRD.md
├─ 02_FEATURE_SPEC.md
├─ 03_REQUIREMENTS.md
├─ 04_UI_SPEC.md
├─ 05_USE_CASES.md
├─ 06_ARCHITECTURE.md
├─ 07_LANGGRAPH_WORKFLOW.md
├─ 08_API_SPEC.md
├─ 09_LOGGING_AUDIT.md
├─ 10_TEST_PLAN.md
├─ 11_PROJECT_PLAN_TRACE_AI.md
├─ 12_PROJECT_STRUCTURE.md

```

### 문서 관리 원칙

- 문서 번호는 **의미적 순서**이며 변경하지 않는다
- `11_PROJECT_PLAN_TRACE_AI.md`
  - 실행/운영용 문서
  - 구조 정의 포함 금지
- `12_PROJECT_STRUCTURE.md`
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

#### 공통 원칙
- API는 **얇아야 한다**
- 검증 → 서비스 호출 → 응답 변환만 담당

#### agent.py
- Agent 실행/재개/승인 API
- LangGraph 실행은 service를 통해 간접 호출

#### admin_knowledge.py
- 지식 저장소 업로드/관리 API
- 관리자 전용 성격 (MVP에서는 단순화)

#### runs.py
- run_id 기준 로그/감사 조회 API
- 실행 결과를 “설명”하기 위한 조회 전용

#### health.py
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

#### config.py
- 환경변수 로딩
- 설정 객체 정의
- 실행 환경 판단 로직 포함 가능

#### logging.py
- JSON 구조화 로그 포맷 정의
- run_id 자동 포함
- 로그 출력 방식의 단일 기준

#### run_context.py
- run_id 생성 및 요청 스코프 전파
- FastAPI 미들웨어와 연동

#### errors.py
- 표준 예외 클래스
- 에러 코드/메시지 정의

#### constants.py
- 문자열/상수 정의
- 매직 스트링 금지 목적

---

### 4.4 app/schemas/ (Pydantic Models)

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

#### agent_service.py
- run 실행/재개/결과 병합
- LangGraph 호출의 유일한 진입점

#### knowledge_service.py
- 문서 파싱/임베딩/저장/검색
- Vector DB 추상화 사용

#### audit_service.py
- run 단위 감사 정보 생성
- 승인/판단/근거 통합

#### log_service.py
- 실행 로그 저장/조회
- 구조화 로그 파일 관리

---

### 4.6 app/agent/ (LangGraph 영역)

```

agent/
├─ state.py
├─ orchestrator.py
├─ nodes/
├─ subgraphs/
└─ prompts/

```

#### state.py
- LangGraph State 정의
- 모든 노드가 공유하는 데이터 구조

#### orchestrator.py
- 메인 LangGraph 정의
- 서브그래프 연결 및 실행 순서 관리

#### nodes/
- 공통 노드 모음
- intent 분류, 승인 게이트, 결과 병합 등

#### subgraphs/
- Compliance / RCA / Workflow 서브그래프
- 독립 실행 가능해야 함

#### prompts/
- 프롬프트 템플릿 관리
- 코드와 분리하여 수정 용이성 확보

---

### 4.7 app/integrations/ (외부 연동)

```

integrations/
├─ llm/
├─ vectorstore/
├─ parsers/
├─ tools/
└─ storage/

```

#### llm/
- OpenRouter 호출 래퍼
- 재시도/타임아웃 처리 포함

#### vectorstore/
- Vector DB 인터페이스
- FAISS / Milvus 구현 분리

#### parsers/
- 문서/로그 파싱 전용
- 비즈니스 로직 금지

#### tools/
- 외부 도구(Jira/Slack) 연동
- mock/real 구현 분리

#### storage/
- 로컬 파일 저장
- 로그/감사/업로드 파일 관리

---

### 4.8 app/data/ (런타임 데이터)

- 업로드 파일, 인덱스, 로그, 감사 결과 저장
- **Git 관리 대상 아님**

---

### 4.9 app/tests/

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

본 문서는 TRACE-AI 프로젝트의  
**구조적 단일 기준 문서**이며,  
모든 코드 배치는 본 문서를 따른다.

---

### 다음 단계 (자연스러운 흐름)

이제 정말 **코드를 치기만 하면 되는 상태**입니다.

다음 중 바로 진행할 수 있습니다.

1️⃣ **PowerShell 기준 전체 디렉터리/빈 파일 생성 명령**
2️⃣ `app/main.py` + `run_id 미들웨어` 최소 구현
3️⃣ `ui/app.py` Chainlit 최소 실행 코드

원하시는 것을 바로 말씀해 주세요.
