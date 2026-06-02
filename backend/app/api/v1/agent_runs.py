from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid as uuid_lib
import json
import asyncio
from datetime import datetime, timedelta, timezone

from app.database import get_async_session as get_db
from app.deps import get_current_tenant
from app.models import Tenant, AgentRun, TenantSettings
from app.schemas.agent_run import AgentRunRead, AgentRunCreate
from app.celery_worker import run_org_analysis

router = APIRouter(tags=["agent_runs"])


@router.get("/orgs/{org_id}/agent-runs")
async def list_agent_runs(
    org_id: uuid_lib.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AgentRun)
        .where(AgentRun.org_id == org_id, AgentRun.tenant_id == tenant.id)
        .order_by(AgentRun.started_at.desc())
    )
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return {
        "items": [AgentRunRead.model_validate(r, from_attributes=True) for r in runs],
        "total": len(runs),
        "page": 1,
        "page_size": 100,
    }


@router.post("/orgs/{org_id}/agent-runs")
async def trigger_agent_run(
    org_id: uuid_lib.UUID,
    run_in: AgentRunCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    FIX 7: Create the AgentRun record in the route handler so the client
    receives a run_id immediately for SSE polling.
    The Celery task updates the SAME record (status: queued → running → ...).
    """
    # Load tenant settings for window size
    ts_stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    ts_res = await db.execute(ts_stmt)
    ts = ts_res.scalar_one_or_none()
    window_days = ts.analysis_window_days if ts else 7

    thread_id = f"run_{uuid_lib.uuid4()}"
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=window_days)

    agent_run = AgentRun(
        id=uuid_lib.uuid4(),
        tenant_id=tenant.id,
        org_id=org_id,
        thread_id=thread_id,
        status="queued",
        triggered_by="manual",
        window_start=window_start,
        window_end=window_end,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        started_at=datetime.now(timezone.utc),
    )
    db.add(agent_run)
    await db.commit()
    await db.refresh(agent_run)

    # Pass run_id + thread_id to Celery so it updates this same record
    run_org_analysis.delay(
        str(tenant.id),
        str(org_id),
        str(agent_run.id),
        thread_id,
    )

    return {
        "run_id": str(agent_run.id),
        "thread_id": thread_id,
        "status": "queued",
    }


@router.get("/agent-runs/{run_id}", response_model=AgentRunRead)
async def get_agent_run(
    run_id: uuid_lib.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AgentRun).where(AgentRun.id == run_id, AgentRun.tenant_id == tenant.id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404)
    return AgentRunRead.model_validate(run, from_attributes=True)


@router.get("/agent-runs/{run_id}/stream")
async def stream_agent_run(
    run_id: uuid_lib.UUID,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events stream for real-time agent run status updates.
    Polls the DB every 2 seconds until run reaches a terminal state.
    """
    async def event_generator():
        last_status = None
        while True:
            if await request.is_disconnected():
                break

            stmt = select(AgentRun).where(
                AgentRun.id == run_id, AgentRun.tenant_id == tenant.id
            )
            res = await db.execute(stmt)
            run = res.scalar_one_or_none()

            if not run:
                break

            if run.status != last_status:
                ts = run.completed_at or run.started_at
                data = {
                    "status": run.status,
                    "run_id": str(run.id),
                    "updated_at": ts.isoformat() if ts else None,
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_status = run.status

            if run.status in ("completed", "failed", "awaiting_human"):
                break

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
