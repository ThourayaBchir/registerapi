from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

from app.api.main import api_router
from app.core.database import close_pool, init_pool
from app.core.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    await init_redis()
    try:
        yield
    finally:
        await close_redis()
        await close_pool()


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(title="User Activation API", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.include_router(api_router)

    scalar_ui = get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="User Activation API",
    )

    @app.get("/docs", include_in_schema=False)
    async def scalar_docs() -> str:
        return scalar_ui

    return app


app = create_app()
