from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import Optional

from app.database import get_async_session as get_db
from app.deps import get_current_tenant
from app.models import Tenant, Insight, AgentRun
from app.schemas.insight import InsightRead

router = APIRouter(tags=["insights"])

@router.get("/orgs/{org_id}/insights")
async def list_insights(
    org_id: uuid.UUID,
    severity: Optional[str] = None,
    type: Optional[str] = Query(None, alias="type"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Insight).join(AgentRun, Insight.agent_run_id == AgentRun.id).where(AgentRun.org_id == org_id, Insight.tenant_id == tenant.id)
    if severity:
        stmt = stmt.where(Insight.severity == severity)
    if type:
        stmt = stmt.where(Insight.insight_type == type)
        
    res = await db.execute(stmt)
    insights = res.scalars().all()
    return {
        "items": [InsightRead.model_validate(i, from_attributes=True) for i in insights],
        "total": len(insights),
        "page": 1,
        "page_size": 100
    }

@router.get("/insights/{insight_id}")
async def get_insight(
    insight_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Insight).where(Insight.id == insight_id, Insight.tenant_id == tenant.id)
    res = await db.execute(stmt)
    insight = res.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404)
    return InsightRead.model_validate(insight, from_attributes=True)
