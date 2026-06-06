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
from datetime import datetime, timezone

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        from app.api.schemas import HealthResponse

        return HealthResponse(
            status="ok",
            app=settings.app_name,
            time=datetime.now(timezone.utc),
        ).model_dump(mode="json")

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
