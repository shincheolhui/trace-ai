# W3-5 데모 리허설 가이드

## 전체 시나리오 실행 방법

W3-5 데모 리허설을 위한 전체 시나리오 실행 가이드입니다.

---

## 사전 준비

### 1. Backend 서버 기동

프로젝트 루트에서 Backend 서버를 실행합니다:

```powershell
# 가상환경 활성화 (Windows)
.\.venv\Scripts\Activate.ps1

# Backend 서버 실행
uvicorn app.main:app --reload
```

서버가 정상적으로 기동되면 `http://localhost:8000`에서 접근 가능합니다.

---

## 실행 방법

### 방법 1: 자동 실행 스크립트 (권장)

프로젝트 루트에서 다음 명령을 실행합니다:

```powershell
.\scripts\run_full_demo_scenario.ps1
```

이 스크립트는 다음을 자동으로 수행합니다:
1. Backend 서버 상태 확인
2. 데모 문서 시드 (지식 저장소에 업로드)
3. Agent Run 실행 (Mixed Intent 시나리오)

---

### 방법 2: 수동 실행

#### Step 1: 데모 문서 시드

프로젝트 루트에서 실행:

```powershell
.\scripts\seed_demo_docs.ps1
```

이 스크립트는 다음 문서들을 지식 저장소에 업로드합니다:
- `demo_docs/policy_security_password.txt` → Policy Store
- `demo_docs/incident_redis_connection.txt` → Incident Store
- `demo_docs/system_deployment_procedure.txt` → System Store

#### Step 2: Agent Run 실행

Mixed Intent 시나리오를 실행합니다 (Compliance + RCA + Workflow 모두 포함):

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/agent/run" `
    -H "Content-Type: application/json" `
    -d "@demo_request_mixed.json"
```

또는 직접 JSON을 작성하여 실행:

```powershell
$requestBody = @{
    query = "서버에서 Redis 연결 오류가 발생했습니다. 이 문제가 보안 정책에 위반되는지 확인하고, 원인을 분석한 후 해결 계획을 수립해주세요."
} | ConvertTo-Json

curl.exe -X POST "http://localhost:8000/api/v1/agent/run" `
    -H "Content-Type: application/json" `
    -d $requestBody
```

---

## 예상 실행 흐름

### 1. Intent 분류
- 요청이 `mixed` intent로 분류됩니다 (Compliance + RCA + Workflow 모두 포함)

### 2. 서브그래프 순차 실행
1. **Compliance 서브그래프**
   - Policy Store에서 보안 정책 검색
   - Redis 연결 오류가 정책 위반인지 분석
   - 위반 여부 및 근거 제공

2. **RCA 서브그래프**
   - Incident Store에서 유사 장애 사례 검색
   - 로그 파싱 및 원인 가설 생성
   - 우선순위 정렬된 가설 목록 제공

3. **Workflow 서브그래프**
   - System Store에서 배포 절차 검색
   - Action Plan 생성 (단계별 실행 계획)
   - 위험도 평가 및 승인 필요 여부 결정

### 3. 결과 통합
- 세 서브그래프 결과를 통합하여 최종 요약 생성
- `integrated_summary` 필드에 통합 결과 포함

---

## 실행 결과 확인

### Agent Run 응답 확인

응답에서 다음 정보를 확인할 수 있습니다:
- `run_id`: 실행 식별자
- `status`: 실행 상태 (`COMPLETED`, `PENDING_APPROVAL`, `FAILED`)
- `intent`: 분류된 Intent (`mixed`)
- `analysis_results`: 각 서브그래프 결과
  - `compliance`: 규정 위반 감지 결과
  - `rca`: 원인 분석 결과
  - `workflow`: 실행 계획 결과
- `integrated_summary`: 통합 요약

### 감사 요약 조회

Agent Run 응답에서 받은 `run_id`로 감사 요약을 조회할 수 있습니다:

```powershell
curl.exe -X GET "http://localhost:8000/api/v1/runs/{run_id}/audit"
```

---

## 데모 시나리오 설명 흐름

### 1. 문제 상황 제시
"서버에서 Redis 연결 오류가 발생했습니다."

### 2. 요청 내용
- 보안 정책 위반 여부 확인 (Compliance)
- 원인 분석 (RCA)
- 해결 계획 수립 (Workflow)

### 3. 시스템 동작 설명
- Intent 분류 → `mixed`로 분류
- 세 가지 서브그래프 순차 실행
- 각 서브그래프가 해당 지식 저장소에서 정보 검색
- 결과 통합 및 최종 요약 생성

### 4. 결과 해석
- Compliance: 정책 위반 여부 및 근거
- RCA: 원인 가설 및 우선순위
- Workflow: 실행 계획 및 승인 필요 여부

---

## 트러블슈팅

### Backend 서버가 응답하지 않는 경우
- 서버가 실행 중인지 확인: `curl.exe http://localhost:8000/health`
- 포트 8000이 사용 중인지 확인
- 로그에서 오류 메시지 확인

### 문서 시드 실패
- `demo_docs/` 디렉터리가 프로젝트 루트에 있는지 확인
- 세 파일이 모두 존재하는지 확인:
  - `policy_security_password.txt`
  - `incident_redis_connection.txt`
  - `system_deployment_procedure.txt`
- Backend 서버가 실행 중인지 확인

### Agent Run 실패
- 지식 저장소에 문서가 업로드되었는지 확인:
  ```powershell
  curl.exe -X GET "http://localhost:8000/api/v1/admin/knowledge-store/stats?store_type=policy" `
      -H "X-Admin-Token: dev-admin-token"
  ```
- LLM API 키가 설정되어 있는지 확인 (`.env` 파일)
- 응답의 `errors` 필드 확인

### intent가 `unknown`으로 나오는 경우
- 한글 query가 깨져 전달되었을 수 있음. `run_full_demo_scenario.ps1`은 `demo_request_mixed.json`을 직접 사용하도록 되어 있어 인코딩 이슈를 피함. 수동 실행 시에도 `-d "@demo_request_mixed.json"` 형태로 JSON 파일 직접 전달을 권장.

---

## 참고 파일

- `scripts/seed_demo_docs.ps1`: 데모 문서 시드 스크립트
- `scripts/run_full_demo_scenario.ps1`: 전체 시나리오 자동 실행 스크립트
- `demo_request_mixed.json`: Mixed Intent 요청 예시
- `demo_docs/`: 데모 문서 디렉터리
  - `policy_security_password.txt`
  - `incident_redis_connection.txt`
  - `system_deployment_procedure.txt`
