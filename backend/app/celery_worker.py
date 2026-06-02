"""
Celery application and task definitions.
Handles background jobs (agent runs, ingest, beat scheduling).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.tenant import Tenant
from app.models.org import Org
from app.models.agent_run import AgentRun

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Celery App
# ─────────────────────────────────────────────────────────────────────────────

celery = Celery(
    "devpulse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,      # Hard limit: 30 min per task
    task_soft_time_limit=25 * 60, # Soft limit: 25 min
)

# ─────────────────────────────────────────────────────────────────────────────
# Beat Schedule
# ─────────────────────────────────────────────────────────────────────────────

celery.conf.beat_schedule = {
    "weekly-analysis-all-tenants": {
        "task": "app.celery_worker.run_weekly_analysis",
        "schedule": crontab(hour=9, minute=0, day_of_week="1"),  # Monday 09:00 UTC
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _mark_run_failed(run_id: str, error: str) -> None:
    """Mark an AgentRun as failed."""
    async with async_session_factory() as db:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        res = await db.execute(stmt)
        run = res.scalar_one_or_none()
        if run:
            run.status = "failed"
            run.error = error
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()


async def _mark_run_awaiting_human(run_id: str) -> None:
    """
    Mark an AgentRun as awaiting_human after a GraphInterrupt.
    completed_at is left NULL — the run is still in progress.
    """
    async with async_session_factory() as db:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        res = await db.execute(stmt)
        run = res.scalar_one_or_none()
        if run:
            run.status = "awaiting_human"
            run.completed_at = None
            await db.commit()


async def _mark_run_completed(run_id: str, result: dict) -> None:
    """Mark an AgentRun as completed and update token/cost fields."""
    async with async_session_factory() as db:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        res = await db.execute(stmt)
        run = res.scalar_one_or_none()
        if run:
            run.status = "completed"
            run.tokens_in = result.get("tokens_in", 0)
            run.tokens_out = result.get("tokens_out", 0)
            run.cost_usd = result.get("cost_usd", 0.0)
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────────

@celery.task(name="app.celery_worker.run_weekly_analysis")
def run_weekly_analysis():
    """
    Triggered weekly (Monday 09:00 UTC): run analysis for all active tenants.
    Iterates all tenants → orgs and fires run_org_analysis for each.
    """
    async def async_main():
        async with async_session_factory() as session:
            tenants_result = await session.execute(select(Tenant))
            tenants = tenants_result.scalars().all()
            logger.info(f"Weekly analysis: found {len(tenants)} tenants")

            for tenant in tenants:
                orgs_result = await session.execute(
                    select(Org).where(Org.tenant_id == tenant.id)
                )
                orgs = orgs_result.scalars().all()
                # FIX 8: use tenant.name (Tenant has no .github_org attribute)
                logger.info(f"Tenant '{tenant.name}': {len(orgs)} orgs")

                for org in orgs:
                    # Create the AgentRun record here so we have a run_id
                    thread_id = f"run_{uuid4()}"
                    window_end = datetime.now(timezone.utc)
                    window_start = window_end - timedelta(days=7)

                    agent_run = AgentRun(
                        tenant_id=tenant.id,
                        org_id=org.id,
                        thread_id=thread_id,
                        status="queued",
                        triggered_by="schedule",
                        window_start=window_start,
                        window_end=window_end,
                        tokens_in=0,
                        tokens_out=0,
                        cost_usd=0.0,
                        started_at=datetime.now(timezone.utc),
                    )
                    session.add(agent_run)
                    await session.flush()
                    run_id = str(agent_run.id)

                run_org_analysis.delay(str(tenant.id), str(org.id), run_id, thread_id)

        await session.commit()
        return {"status": "ok", "tenants_processed": len(tenants)}

    return run_async(async_main())


@celery.task(
    bind=True,
    name="app.celery_worker.run_org_analysis",
    max_retries=3,
)
def run_org_analysis(
    self,
    tenant_id: str,
    org_id: str,
    run_id: str | None = None,
    thread_id: str | None = None,
):
    """
    Run LangGraph analysis for a single org/tenant.

    FIX 7: Accepts run_id + thread_id so it updates the AgentRun record
    that was already created by the route handler or beat scheduler.

    FIX 2: Retries with exponential back-off on failure (max 3 attempts).

    FIX 5: Catches GraphInterrupt to set status='awaiting_human'.
    """
    # Late import to avoid circular dependency
    from langgraph.errors import GraphInterrupt
    from app.agents.graph import run_graph

    async def async_main():
        nonlocal run_id, thread_id

        async with async_session_factory() as session:
            if run_id:
                # Update the pre-created run to running
                stmt = select(AgentRun).where(AgentRun.id == run_id)
                res = await session.execute(stmt)
                agent_run = res.scalar_one_or_none()
                if agent_run:
                    agent_run.status = "running"
                    agent_run.started_at = datetime.now(timezone.utc)
                    await session.commit()
                    thread_id = thread_id or agent_run.thread_id
            else:
                # Fallback: create a new AgentRun (called from legacy code)
                thread_id = thread_id or f"run_{uuid4()}"
                window_end = datetime.now(timezone.utc)
                window_start = window_end - timedelta(days=7)
                agent_run = AgentRun(
                    tenant_id=tenant_id,
                    org_id=org_id,
                    thread_id=thread_id,
                    status="running",
                    triggered_by="manual",
                    window_start=window_start,
                    window_end=window_end,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    started_at=datetime.now(timezone.utc),
                )
                session.add(agent_run)
                await session.flush()
                run_id = str(agent_run.id)
                await session.commit()

        logger.info(f"[AgentRun {run_id}] Starting analysis tenant={tenant_id} org={org_id}")

        try:
            # FIX 5: Catch GraphInterrupt to handle HITL pause
            result = await run_graph(
                tenant_id=tenant_id,
                org_id=org_id,
                agent_run_id=run_id,
                thread_id=thread_id,
            )
            # Graph completed successfully (no interrupt)
            await _mark_run_completed(run_id, result)
            logger.info(
                f"[AgentRun {run_id}] Completed. "
                f"Insights: {len(result.get('insights', []))}, "
                f"Actions: {len(result.get('actions_queued', []))}"
            )
            return {
                "status": "completed",
                "agent_run_id": run_id,
                "insights_generated": len(result.get("insights", [])),
                "actions_queued": len(result.get("actions_queued", [])),
            }

        except GraphInterrupt:
            # FIX 5: Graph paused at interrupt_before=["action"]
            # Insights are already in DB (persisted by insight node).
            # AgentAction rows will be written when graph resumes.
            await _mark_run_awaiting_human(run_id)
            logger.info(f"[AgentRun {run_id}] Paused — awaiting human approval.")
            return {"status": "awaiting_human", "agent_run_id": run_id}

        except Exception as e:
            # FIX 2: Retry with exponential back-off
            logger.error(f"[AgentRun {run_id}] Error: {e}", exc_info=True)
            try:
                await _mark_run_failed(run_id, str(e))
            except Exception:
                pass
            # Re-raise via self.retry so Celery handles retry countdown
            raise self.retry(
                exc=e,
                countdown=60 * (2 ** self.request.retries),
            )

    return run_async(async_main())


@celery.task(name="app.celery_worker.ingest_push_event")
def ingest_push_event(org_id: str, payload: dict):
    """Ingest commit events from a GitHub push webhook payload."""
    from app.services.ingest import ingest_commits
    from app.models import Repo, Org
    import uuid

    repo_name = payload.get("repository", {}).get("name")
    commits = payload.get("commits", [])
    if not repo_name or not commits:
        return

    async def _ingest():
        async with async_session_factory() as db:
            org_stmt = select(Org).where(Org.id == uuid.UUID(org_id))
            org_res = await db.execute(org_stmt)
            org = org_res.scalar_one_or_none()
            if not org:
                return

            repo_stmt = select(Repo).where(Repo.org_id == org.id, Repo.name == repo_name)
            repo_res = await db.execute(repo_stmt)
            repo = repo_res.scalar_one_or_none()
            if not repo:
                return

            await ingest_commits(org.id, repo.id, org.tenant_id, commits, db)

    asyncio.run(_ingest())


@celery.task(name="app.celery_worker.ingest_pr_event")
def ingest_pr_event(org_id: str, payload: dict):
    """Ingest PR events from a GitHub pull_request webhook payload."""
    from app.services.ingest import ingest_prs
    from app.models import Repo, Org
    import uuid

    repo_name = payload.get("repository", {}).get("name")
    pr = payload.get("pull_request")
    if not repo_name or not pr:
        return

    async def _ingest():
        async with async_session_factory() as db:
            org_stmt = select(Org).where(Org.id == uuid.UUID(org_id))
            org_res = await db.execute(org_stmt)
            org = org_res.scalar_one_or_none()
            if not org:
                return

            repo_stmt = select(Repo).where(Repo.org_id == org.id, Repo.name == repo_name)
            repo_res = await db.execute(repo_stmt)
            repo = repo_res.scalar_one_or_none()
            if not repo:
                return

            await ingest_prs(org.id, repo.id, org.tenant_id, [pr], db)

    asyncio.run(_ingest())
