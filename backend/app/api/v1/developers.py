from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_async_session as get_db
from app.deps import get_current_tenant
from app.models import Tenant, Developer, CommitEvent, PrEvent, Insight
from app.schemas.developer import DeveloperRead, DeveloperMetrics

router = APIRouter(tags=["developers"])

@router.get("/orgs/{org_id}/developers")
async def list_org_developers(
    org_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Developer).where(Developer.tenant_id == tenant.id)
    res = await db.execute(stmt)
    devs = res.scalars().all()
    return {
        "items": [DeveloperRead.model_validate(d, from_attributes=True) for d in devs],
        "total": len(devs),
        "page": 1,
        "page_size": 100
    }

@router.get("/developers/{dev_id}", response_model=DeveloperRead)
async def get_developer(
    dev_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Developer).where(Developer.id == dev_id, Developer.tenant_id == tenant.id)
    res = await db.execute(stmt)
    dev = res.scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404)
    return DeveloperRead.model_validate(dev, from_attributes=True)

@router.get("/developers/{dev_id}/commits")
async def get_developer_commits(
    dev_id: uuid.UUID,
    days: int = 7,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    import datetime
    window_start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    
    stmt = select(CommitEvent).where(
        CommitEvent.developer_id == dev_id,
        CommitEvent.tenant_id == tenant.id,
        CommitEvent.committed_at >= window_start
    )
    res = await db.execute(stmt)
    commits = res.scalars().all()
    return {"items": [c.__dict__ for c in commits if not c.__dict__.pop("_sa_instance_state", None)]}

@router.get("/developers/{dev_id}/prs")
async def get_developer_prs(
    dev_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PrEvent).where(
        PrEvent.author_id == dev_id,
        PrEvent.tenant_id == tenant.id
    )
    res = await db.execute(stmt)
    prs = res.scalars().all()
    return {"items": [p.__dict__ for p in prs if not p.__dict__.pop("_sa_instance_state", None)]}

@router.get("/developers/{dev_id}/insights")
async def get_developer_insights(
    dev_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Insight).where(
        Insight.developer_id == dev_id,
        Insight.tenant_id == tenant.id
    ).order_by(Insight.created_at.desc()).limit(10)
    res = await db.execute(stmt)
    insights = res.scalars().all()
    return {"items": [i.__dict__ for i in insights if not i.__dict__.pop("_sa_instance_state", None)]}
