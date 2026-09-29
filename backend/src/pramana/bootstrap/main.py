"""
bootstrap.main — FastAPI application factory (Phase 1 walking skeleton).

Creates the app, wires adapters, registers all routers.
This is the composition root — the only module that imports adapters.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pramana.ingest.router import router as ingest_router
from pramana.pipeline.router import router as pipeline_router


def create_application() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="PRAMANA",
        description=(
            "Offline, air-gapped, multi-vendor network-configuration compliance auditor. "
            "SIH26155 · NTRO · Team Vernils"
        ),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── CORS (localhost-only; nginx handles in production) ────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["internal"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    # ── API routers ───────────────────────────────────────────────────────────
    app.include_router(ingest_router, prefix="/api/v1")
    app.include_router(pipeline_router, prefix="/api/v1")

    return app


# Module-level app instance (for uvicorn / gunicorn)
app = create_application()
