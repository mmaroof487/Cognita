from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.schemas.org import OrgRead, OrgCreate
from app.schemas.common import PaginatedResponse
from app.database import get_async_session as get_db
from app.deps import get_current_tenant, rate_limit_check, require_admin
from app.models import Org, Tenant, User, Repo, Developer
from app.providers.github import GitHubProvider
from app.core.security import fernet_decrypt

router = APIRouter(prefix="/orgs", tags=["orgs"], dependencies=[Depends(rate_limit_check)])

@router.get("", response_model=PaginatedResponse[OrgRead])
async def list_orgs(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Org).where(Org.tenant_id == tenant.id)
    res = await db.execute(stmt)
    orgs = res.scalars().all()
    return PaginatedResponse(
        items=[OrgRead.model_validate(o, from_attributes=True) for o in orgs],
        total=len(orgs),
        page=1,
        page_size=100
    )

@router.post("", response_model=OrgRead)
async def connect_org(
    org_in: OrgCreate,
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    gh = GitHubProvider(fernet_decrypt(admin.access_token))
    try:
        user_orgs = await gh.client.get(f"https://api.github.com/orgs/{org_in.name}")
        user_orgs.raise_for_status()
        gh_org = user_orgs.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GitHub org or lacking access")

    org_login = gh_org.get("login", org_in.name)

    # Check if org already connected for this tenant
    stmt = select(Org).where(Org.tenant_id == tenant.id, Org.github_org == org_login)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Org already connected")

    org = Org(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        github_org=org_login,
        display_name=gh_org.get("name") or org_login,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return OrgRead.model_validate(org, from_attributes=True)

@router.get("/{org_id}")
async def get_org(
    org_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Org).where(Org.id == org_id, Org.tenant_id == tenant.id)
    res = await db.execute(stmt)
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404)
        
    repo_count_res = await db.execute(
        select(func.count()).select_from(Repo).where(Repo.org_id == org_id)
    )
    repo_count = repo_count_res.scalar() or 0

    # Developers are tenant-scoped; join through repos to count per-org developers
    dev_count_res = await db.execute(
        select(func.count()).select_from(Developer).where(
            Developer.tenant_id == tenant.id
        )
    )
    dev_count = dev_count_res.scalar() or 0

    org_dict = OrgRead.model_validate(org, from_attributes=True).model_dump()
    org_dict["repo_count"] = repo_count
    org_dict["developer_count"] = dev_count
    return org_dict

@router.get("/{org_id}/repos")
async def get_org_repos(
    org_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Repo).where(Repo.org_id == org_id, Repo.tenant_id == tenant.id).order_by(Repo.name)
    res = await db.execute(stmt)
    repos = res.scalars().all()
    
    return {
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "github_id": r.github_id,
                "is_tracked": r.tracked,
                "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None
            }
            for r in repos
        ],
        "total": len(repos)
    }


@router.delete("/{org_id}", status_code=204)
async def delete_org(
    org_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Org).where(Org.id == org_id, Org.tenant_id == tenant.id)
    res = await db.execute(stmt)
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404)
        
    await db.delete(org)
    await db.commit()
