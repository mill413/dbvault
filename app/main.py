from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import AppError, app_error_handler
from app.core.logging import configure_logging
from app.drivers.bootstrap import register_builtin_drivers
from app.scheduler.service import shutdown_scheduler, start_scheduler
from app.services.auth_service import ensure_initial_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    register_builtin_drivers()
    db = SessionLocal()
    try:
        ensure_initial_admin(db)
    finally:
        db.close()
    if get_settings().scheduler_enabled:
        start_scheduler()
    yield
    shutdown_scheduler()


settings = get_settings()
app = FastAPI(
    title="DBVault API",
    version="0.1.0",
    openapi_url="/openapi.json" if settings.openapi_enabled else None,
    docs_url="/docs" if settings.openapi_enabled else None,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex}"
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    return response


app.add_exception_handler(AppError, app_error_handler)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
