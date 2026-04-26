"""
API endpoints for agent run management.

Allows users to:
- Trigger manual analysis
- View agent run status
- Stream agent run progress
- Access agent run results and actions
"""

from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_async_session
from app.models.agent_run import AgentRun
from app.models.tenant import Tenant
from app.models.org import Org
from app.models.insight import Insight
from app.models.agent_action import AgentAction
from app.deps import get_current_tenant
from app.celery_worker import run_org_analysis

router = APIRouter(prefix="/api/v1", tags=["agent-runs"])


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel


class TriggerAnalysisRequest(BaseModel):
    """Trigger analysis for an org."""

    org_id: str
    analysis_window_days: int = 7


class AgentRunResponse(BaseModel):
    """Agent run details."""

    id: str
    thread_id: str
    status: str
    window_start: str
    window_end: str
    anomalies_count: int = 0
    insights_count: int = 0
    actions_count: int = 0
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


class InsightResponse(BaseModel):
    """Insight details."""

    id: str
    title: str
    body: str
    severity: str
    score: Optional[int] = None


class ActionResponse(BaseModel):
    """Agent action details."""

    id: str
    action_type: str
    status: str
    payload: dict
    created_at: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/orgs/{org_id}/agent-runs")
async def trigger_agent_run(
    org_id: str,
    request: TriggerAnalysisRequest,
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Trigger a manual agent run for an organization.

    Validates org ownership, creates AgentRun record, and queues Celery task.
    """
    # Verify org belongs to tenant
    org_query = select(Org).where(
        Org.id == org_id,
        Org.tenant_id == tenant_id,
    )
    org_result = await session.execute(org_query)
    org = org_result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Queue task
    task = run_org_analysis.delay(tenant_id, org_id)

    return {
        "status": "queued",
        "task_id": task.id,
        "org_id": org_id,
        "message": "Analysis queued. Check back shortly for results.",
    }


@router.get("/orgs/{org_id}/agent-runs")
async def list_agent_runs(
    org_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    List agent runs for an organization.

    Returns paginated list of recent agent runs with status.
    """
    # Verify org belongs to tenant
    org_query = select(Org).where(
        Org.id == org_id,
        Org.tenant_id == tenant_id,
    )
    org_result = await session.execute(org_query)
    org = org_result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get agent runs for this org's repos
    runs_query = (
        select(AgentRun)
        .where(AgentRun.tenant_id == tenant_id)
        .order_by(desc(AgentRun.started_at))
        .offset(offset)
        .limit(limit)
    )
    runs_result = await session.execute(runs_query)
    runs = runs_result.scalars().all()

    return {
        "runs": [
            AgentRunResponse(
                id=str(r.id),
                thread_id=r.thread_id,
                status=r.status,
                window_start=r.window_start.isoformat(),
                window_end=r.window_end.isoformat(),
                started_at=r.started_at.isoformat(),
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
                error=r.error,
            ).model_dump()
            for r in runs
        ],
        "total": len(runs),
    }


@router.get("/agent-runs/{run_id}")
async def get_agent_run(
    run_id: str,
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Get details of a specific agent run.

    Includes insights, actions, and metrics.
    """
    # Get run
    run_query = select(AgentRun).where(
        AgentRun.id == run_id,
        AgentRun.tenant_id == tenant_id,
    )
    run_result = await session.execute(run_query)
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    # Get insights for this run
    insights_query = select(Insight).where(Insight.agent_run_id == run_id)
    insights_result = await session.execute(insights_query)
    insights = insights_result.scalars().all()

    # Get actions for this run
    actions_query = select(AgentAction).where(AgentAction.agent_run_id == run_id)
    actions_result = await session.execute(actions_query)
    actions = actions_result.scalars().all()

    return {
        "run": AgentRunResponse(
            id=str(run.id),
            thread_id=run.thread_id,
            status=run.status,
            window_start=run.window_start.isoformat(),
            window_end=run.window_end.isoformat(),
            anomalies_count=0,  # TODO: count anomalies from insights
            insights_count=len(insights),
            actions_count=len(actions),
            started_at=run.started_at.isoformat(),
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            error=run.error,
        ).model_dump(),
        "insights": [
            InsightResponse(
                id=str(i.id),
                title=i.title,
                body=i.body,
                severity=i.severity,
                score=i.score,
            ).model_dump()
            for i in insights
        ],
        "actions": [
            ActionResponse(
                id=str(a.id),
                action_type=a.action_type,
                status=a.status,
                payload=a.payload,
                created_at=a.created_at.isoformat(),
            ).model_dump()
            for a in actions
        ],
    }
