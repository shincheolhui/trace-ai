# TRACE-AI

TRACE-AI는 해커톤용 **엔터프라이즈 AI Agent 플랫폼 PoC**입니다.  
FastAPI 기반 Backend, LangGraph 오케스트레이터, Chainlit UI를 사용하여  
**run_id 기반 추적 가능한 AI Agent 실행 흐름**을 제공합니다.

---

## 1. 프로젝트 개요

### 핵심 목표
- run_id 기반 **요청 단위 추적(Observability)**
- LangGraph 기반 **Agent Orchestration**
- UI → API → Agent → UI **왕복 실행 흐름 검증**
- 엔터프라이즈 확장 전제의 디렉터리 구조 확립

### 기술 스택
- **Python 3.13.11**
- FastAPI / Uvicorn
- LangGraph
- Chainlit (UI)
- httpx
- contextvars 기반 run_id 전파

---

## 2. 현재 구현 범위 (Week 1 완료)

Week 1(W1-1 ~ W1-5)에서 아래 항목을 완료했습니다.

- FastAPI 서버 기동 및 Health Check
- run_id 생성 및 Header/Log/Response 전파
- LangGraph 오케스트레이터 기본 그래프  
  (`START → DUMMY → END`)
- Agent 실행 API (`POST /api/v1/agent/run`)
- Chainlit UI ↔ Backend 연동
- UI → API → LangGraph **스모크 테스트 2회 성공**
- run_id 기반 실행 로그 추적 검증

---

## 3. 디렉터리 구조 (요약)

```
trace-ai/
├─ app/                    # Backend (FastAPI)
│  ├─ api/
│  ├─ agent/
│  ├─ services/
│  ├─ core/
│  └─ main.py
├─ ui/                     # Chainlit UI
│  └─ app.py
├─ docs/                   # 설계 문서 (PRD, 구조, WBS 등)
├─ requirements.lock.txt
├─ README.md
└─ .venv/                  # Python 가상환경
```

> 상세 구조는 `docs/12_PROJECT_STRUCTURE.md`를 참고하세요.

---

## 4. Python 3.13.11 설치

### 4.1 Windows

1. 공식 사이트 접속  
   https://www.python.org/downloads/release/python-31311/

2. **Windows installer (64-bit)** 다운로드

3. 설치 시 반드시 체크
   - ✅ *Add Python to PATH*
   - ✅ *Install for all users* (권장)

4. 설치 확인
```powershell
python --version
# Python 3.13.11
```

---

### 4.2 macOS

#### 방법 A: python.org 공식 설치 (권장)

1. [https://www.python.org/downloads/release/python-31311/](https://www.python.org/downloads/release/python-31311/)
2. **macOS installer (.pkg)** 다운로드
3. 설치 후 확인

```bash
python3 --version
# Python 3.13.11
```

#### 방법 B: Homebrew (선택)

```bash
brew install python@3.13
python3.13 --version
```

---

## 5. 가상환경 생성 및 활성화 (Python 3.13.11 명시)

### 5.1 가상환경 생성

> ⚠️ 반드시 **Python 3.13.11 바이너리**로 가상환경을 생성해야 합니다.

---

### Windows

Python 3.13.11 설치 시 생성되는 `python3.13` 또는 `py -3.13`을 사용합니다.

#### 방법 A (권장: py launcher 사용)

```powershell
py -3.13 -m venv .venv
```

#### 방법 B (직접 python 실행 경로 사용)

```powershell
python3.13 -m venv .venv
```

버전 확인:

```powershell
.\.venv\Scripts\python.exe --version
# Python 3.13.11
```

---

### macOS

macOS에서는 `python3.13`을 명시적으로 사용합니다.

```bash
python3.13 -m venv .venv
```

버전 확인:

```bash
./.venv/bin/python --version
# Python 3.13.11
```

---

### 5.2 가상환경 활성화

#### Windows (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
source .venv/bin/activate
```

활성화 후 프롬프트에 `(.venv)`가 표시되며,
아래 명령으로 버전을 다시 확인하는 것을 권장합니다.

```bash
python --version
# Python 3.13.11
```

---

## 6. 의존성 설치 (`requirements.lock.txt`)

가상환경 활성화 상태에서:

```bash
pip install -r requirements.lock.txt
```

> `requirements.lock.txt`는 해커톤 환경 재현을 위해 버전이 고정되어 있습니다.

---

## 7. Backend 실행 (FastAPI)

### 7.1 실행

```bash
uvicorn app.main:app --reload
```

정상 로그 예시:

```
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

### 7.2 Health Check

```bash
curl http://127.0.0.1:8000/api/v1/health
```

---

## 8. UI 실행 (Chainlit)

> Backend와 **다른 터미널/가상환경**에서 실행해야 합니다.

### 8.1 UI 실행

```bash
chainlit run ui/app.py -w --port 8001
```

정상 로그 예시:

```
Your app is available at http://localhost:8001
```

### 8.2 브라우저 접속

* [http://localhost:8001](http://localhost:8001)

---

## 9. 실행 테스트 (Smoke Test)

Chainlit UI에서 아래 메시지를 입력하세요.

1. `hello`
2. `smoke test`

정상 결과:

* HTTP 200
* run_id(body) 표시
* run_id(header) 표시
* trace.dummy.ok = true

Backend 로그에서 run_id 기준 실행 흐름이 확인됩니다.

---

## 10. 주요 API

### Agent 실행

```
POST /api/v1/agent/run
```

Request:

```json
{
  "query": "hello",
  "context": {}
}
```

Response:

```json
{
  "run_id": "...",
  "status": "COMPLETED",
  "result": {
    "trace": {
      "dummy": {
        "ok": true,
        "message": "passed dummy node"
      }
    }
  }
}
```

---

## 11. Week 1 완료 선언

Week 1(W1-1 ~ W1-5)을 통해 TRACE-AI는 다음 상태에 도달했습니다.

* 실행 가능한 Backend + UI
* run_id 기반 추적 가능성 확보
* LangGraph 기반 Agent Orchestration 검증
* 해커톤 데모 가능한 최소 플랫폼 완성

---

## 12. 다음 단계 (Week 2)

Week 2에서는 다음 중 하나를 진행할 예정입니다.

* Intent 분류 노드 추가
* 실제 Agent 판단 로직 확장
* run/audit 조회 API 추가
* Vector DB 기반 지식 연결

---

## License / Notes

본 프로젝트는 해커톤 및 PoC 목적의 내부 프로젝트입니다.

---
