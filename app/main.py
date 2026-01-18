# app/main.py
from fastapi import FastAPI

from app.api.v1.health import router as health_router

def create_app() -> FastAPI:
    app = FastAPI(title="TRACE-AI", version="0.1.0")

    # v1 routers
    app.include_router(health_router, prefix="/api/v1")

    return app

app = create_app()