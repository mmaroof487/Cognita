from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from pydantic import BaseModel

from app.database import get_async_session as get_db
from app.deps import get_current_tenant, require_admin
from app.models import Repo, Tenant, User

router = APIRouter(prefix="/repos", tags=["repos"])

class RepoPatch(BaseModel):
    is_tracked: bool

@router.patch("/{repo_id}")
async def update_repo(
    repo_id: uuid.UUID,
    patch: RepoPatch,
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Repo).where(Repo.id == repo_id, Repo.tenant_id == tenant.id)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404)
        
    repo.is_tracked = patch.is_tracked
    await db.commit()
    return {"status": "ok"}
