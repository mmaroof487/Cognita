"""
Celery application and task definitions.
Handles background jobs (agent runs, ingest, etc).
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory, engine
from app.models.tenant import Tenant
from app.models.org import Org
from app.models.agent_run import AgentRun
from app.agents.graph import build_graph

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
    task_time_limit=30 * 60,  # Hard limit: 30 min per task
    task_soft_time_limit=25 * 60,  # Soft limit: 25 min per task
)

# ─────────────────────────────────────────────────────────────────────────────
# Scheduled Tasks (Beat Schedule)
# ─────────────────────────────────────────────────────────────────────────────

celery.conf.beat_schedule = {
    "weekly-analysis-all-tenants": {
        "task": "app.celery_worker.run_weekly_analysis",
        "schedule": crontab(hour=9, minute=0, day_of_week="1"),  # Monday 9 AM UTC
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Run async code from Celery (sync context)
# ─────────────────────────────────────────────────────────────────────────────

def run_async(coro):
    """Run async coroutine in sync context (Celery)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────────

@celery.task(name="app.celery_worker.run_weekly_analysis")
def run_weekly_analysis():
    """
    Triggered weekly (Monday 9 AM UTC): run analysis for all active tenants.

    Iterates through all tenants and triggers run_org_analysis for each org.
    """
    async def async_main():
        async with async_session_factory() as session:
            # Get all tenants
            tenants_query = select(Tenant)
            tenants_result = await session.execute(tenants_query)
            tenants = tenants_result.scalars().all()

            logger.info(f"Weekly analysis: found {len(tenants)} tenants")

            for tenant in tenants:
                # Get all orgs for this tenant
                orgs_query = select(Org).where(Org.tenant_id == tenant.id)
                orgs_result = await session.execute(orgs_query)
                orgs = orgs_result.scalars().all()

                logger.info(f"Tenant {tenant.github_org}: {len(orgs)} orgs")

                for org in orgs:
                    # Trigger run_org_analysis task
                    run_org_analysis.delay(str(tenant.id), str(org.id))

        return {"status": "ok", "tenants_processed": len(tenants)}

    return run_async(async_main())


@celery.task(name="app.celery_worker.run_org_analysis", bind=True, max_retries=3)
def run_org_analysis(self, tenant_id: str, org_id: str):
    """
    Run LangGraph analysis for a single org/tenant.

    Invokes the agent graph (Collector -> Analyst -> Insight -> Action nodes)
    and persists results to DB.

    Args:
        tenant_id: UUID of tenant
        org_id: UUID of org
    """
    async def async_main():
        async with async_session_factory() as session:
            # Create AgentRun record
            agent_run = AgentRun(
                tenant_id=tenant_id,
                thread_id=f"run_{uuid4()}",
                status="running",
                window_start=datetime.utcnow() - timedelta(days=7),  # Last 7 days
                window_end=datetime.utcnow(),
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                started_at=datetime.utcnow(),
            )
            session.add(agent_run)
            await session.flush()
            agent_run_id = str(agent_run.id)

            logger.info(f"[AgentRun {agent_run_id}] Starting analysis for tenant={tenant_id}, org={org_id}")

            try:
                # Import here to avoid circular imports
                from anthropic import Anthropic

                anthropic_client = Anthropic(api_key=settings.anthropic_api_key)

                # Build LangGraph
                graph = build_graph(
                    session=session,
                    anthropic_client=anthropic_client,
                )

                # Prepare input state
                input_state = {
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "agent_run_id": agent_run_id,
                    "window_start": agent_run.window_start,
                    "window_end": agent_run.window_end,
                    "commits": [],
                    "prs": [],
                    "developers": [],
                    "developer_metrics": {},
                    "team_metrics": {},
                    "anomalies": [],
                    "insights": [],
                    "actions_queued": [],
                    "retry_count": 0,
                    "errors": [],
                    "tokens_used": 0,
                    "cost_usd": 0.0,
                }

                # Invoke graph
                final_state = await graph.ainvoke(
                    input_state,
                    config={"configurable": {"thread_id": agent_run.thread_id}},
                )

                # Update AgentRun with results
                agent_run.status = "completed"
                agent_run.tokens_in = final_state.get("tokens_used", 0)
                agent_run.tokens_out = 0
                agent_run.cost_usd = final_state.get("cost_usd", 0.0)
                agent_run.completed_at = datetime.utcnow()

                await session.commit()

                logger.info(
                    f"[AgentRun {agent_run_id}] Completed. "
                    f"Anomalies: {len(final_state.get('anomalies', []))}, "
                    f"Insights: {len(final_state.get('insights', []))}, "
                    f"Actions: {len(final_state.get('actions_queued', []))}"
                )

                return {
                    "status": "completed",
                    "agent_run_id": agent_run_id,
                    "anomalies_found": len(final_state.get("anomalies", [])),
                    "insights_generated": len(final_state.get("insights", [])),
                    "actions_queued": len(final_state.get("actions_queued", [])),
                }

            except Exception as e:
                logger.error(f"[AgentRun {agent_run_id}] Error: {e}", exc_info=True)
                agent_run.status = "failed"
                agent_run.error = str(e)
                agent_run.completed_at = datetime.utcnow()
                await session.commit()

                # Retry with exponential backoff
                raise self.retry(exc=e, countdown=2 ** self.request.retries)

    return run_async(async_main())
