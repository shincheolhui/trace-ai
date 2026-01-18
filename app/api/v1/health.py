# app/api/v1/health.py
from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])

@router.get("/health")
def health(request: Request):
    return {"status": "ok", "run_id": getattr(request.state, "run_id", None)}