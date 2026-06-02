from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from fastapi.responses import PlainTextResponse

from app.api.v1 import auth, orgs, repos, developers, insights, agent_runs, actions, webhooks
from app.core.telemetry import instrument_app
from app.config import settings

app = FastAPI(title="Axon", version="0.1.0", docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.middleware.base import BaseHTTPMiddleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if hasattr(request.state, "rate_limit_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
            response.headers["Retry-After"] = str(request.state.rate_limit_reset)
        return response

app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(orgs.router, prefix="/api/v1")
app.include_router(repos.router, prefix="/api/v1")
app.include_router(developers.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(agent_runs.router, prefix="/api/v1")
app.include_router(actions.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment, "version": app.version}

@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest())

@app.on_event("startup")
async def startup_event():
    instrument_app(app)
