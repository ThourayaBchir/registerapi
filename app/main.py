from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    app = FastAPI(title="User Activation API", lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
