# TRACE-AI

## Quickstart (Backend)

### 1) Install

```bash
pip install -r requirements.txt
```

### 2) Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3) Health Check

```bash
curl -s http://localhost:8000/api/v1/health
```

Expected:

```json
{ "status": "ok" }
```