"""
FastAPI application factory.
Creates and configures the FastAPI app with middleware, routes, etc.
"""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.core.telemetry import init_telemetry


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="DevPulse API",
        description="AI-powered developer productivity intelligence platform",
        version="0.1.0",
        debug=settings.debug,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Middleware
    # ─────────────────────────────────────────────────────────────────────────

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Initialize services
    # ─────────────────────────────────────────────────────────────────────────

    init_telemetry()

    # ─────────────────────────────────────────────────────────────────────────
    # Health check endpoint
    # ─────────────────────────────────────────────────────────────────────────

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "ok",
            "environment": settings.environment,
            "version": "0.1.0",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # API Routes
    # ─────────────────────────────────────────────────────────────────────────

    from app.api.v1.agent_runs import router as agent_runs_router

    app.include_router(agent_runs_router)

    # ─────────────────────────────────────────────────────────────────────────
    # Error handling (can be expanded)
    # ─────────────────────────────────────────────────────────────────────────

    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return Response(
            {"detail": "Not found"},
            status_code=404
        )

    return app


# Create app instance
app = create_app()
