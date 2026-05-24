"""persona-hub persistence API entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.db import get_engine
from app.models import Base
from app.rate_limit import get_limiter
from app.routers import personas, signals


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create tables for sqlite-based dev runs; production uses Alembic."""
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(
    title="persona-hub API",
    description="Persistence and aggregation API for persona-hub.",
    version="0.1.0",
    lifespan=lifespan,
)

limiter = get_limiter()
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    detail: Any = getattr(exc, "detail", "rate limit exceeded")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded: {detail}"},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


app.include_router(personas.router)
app.include_router(signals.router)
