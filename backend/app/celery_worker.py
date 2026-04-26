"""
Celery application and task definitions.
Handles background jobs (agent runs, ingest, etc).
"""

from celery import Celery
from celery.schedules import crontab
from app.config import settings

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
# Tasks (Stub — will be implemented in week 2)
# ─────────────────────────────────────────────────────────────────────────────

@celery.task(name="app.celery_worker.run_weekly_analysis")
def run_weekly_analysis():
    """
    Triggered weekly: run analysis for all active tenants.
    Stub for now — will trigger agent runs in week 2.
    """
    print("Weekly analysis task triggered")
    return {"status": "ok"}


@celery.task(name="app.celery_worker.run_org_analysis", bind=True, max_retries=3)
def run_org_analysis(self, tenant_id: str, org_id: str):
    """
    Run analysis for a single org/tenant.
    Stub for now — will invoke LangGraph agent in week 2.
    """
    print(f"Running analysis for tenant={tenant_id}, org={org_id}")
    return {"status": "ok"}
