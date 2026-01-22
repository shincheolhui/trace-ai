# app/main.py
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.agent import router as agent_router
from app.api.v1.admin_knowledge import router as admin_knowledge_router
from app.api.v1.approval import router as approval_router
from app.core.logging import setup_logging
from app.core.run_context import generate_run_id, set_run_id

class RunIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        run_id = generate_run_id()
        request.state.run_id = run_id
        set_run_id(run_id)

        response = await call_next(request)
        response.headers["X-Run-Id"] = run_id
        return response

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="TRACE-AI", version="0.1.0")

    app.add_middleware(RunIdMiddleware)

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")
    app.include_router(admin_knowledge_router, prefix="/api/v1")
    app.include_router(approval_router, prefix="/api/v1")
    return app

app = create_app()
