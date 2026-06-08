"""
FastAPI application factory.

Usage::

    uvicorn app.main:app --reload

The factory pattern keeps tests easy: ``create_app()`` builds an
isolated app instance that can be wrapped with ``TestClient``.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.utils.config import settings
from app.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("INFO" if not settings.app_debug else "DEBUG")
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "REST API for the Murim Knowledge Base. "
            "Catalogs characters, organizations and locations extracted "
            "from Murim / Wuxia / Xianxia web-novels."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS: when allow_origins is ["*"] we must NOT set allow_credentials=True
    # (W3C CORS spec disallows it). For dev we allow all origins without credentials;
    # set APP_CORS_ORIGINS env var for production.
    import os

    cors_origins_raw = os.getenv("APP_CORS_ORIGINS", "")
    if cors_origins_raw:
        cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
        allow_creds = True
    else:
        cors_origins = ["*"]
        allow_creds = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        from app.api.schemas import HealthResponse

        return HealthResponse(
            status="ok",
            app=settings.app_name,
            time=datetime.now(UTC),
        ).model_dump(mode="json")

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
