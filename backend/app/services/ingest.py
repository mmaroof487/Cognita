from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from datetime import datetime
from uuid import UUID

from app.models import Developer, CommitEvent, PrEvent, Repo

async def ingest_commits(org_id: UUID, repo_id: UUID, tenant_id: UUID, commits: list[dict], db: AsyncSession):
    if not commits:
        return
    
    authors = set()
    for c in commits:
        author = c.get("author")
        if author and author.get("login"):
            authors.add(author["login"])
    
    for login in authors:
        stmt = insert(Developer).values(
            tenant_id=tenant_id,
            github_login=login,
        ).on_conflict_do_nothing(
            index_elements=["tenant_id", "github_login"]
        )
        await db.execute(stmt)
        
    await db.flush()
    
    dev_stmt = select(Developer).where(Developer.tenant_id == tenant_id)
    dev_res = await db.execute(dev_stmt)
    dev_map = {d.github_login: d.id for d in dev_res.scalars()}
    
    for c in commits:
        author_login = c.get("author", {}).get("login")
        dev_id = dev_map.get(author_login) if author_login else None
        
        commit_date_str = c.get("commit", {}).get("author", {}).get("date")
        if not commit_date_str:
            continue
        try:
            committed_at = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
        except ValueError:
            continue
            
        stmt = insert(CommitEvent).values(
            tenant_id=tenant_id,
            repo_id=repo_id,
            developer_id=dev_id,
            sha=c["sha"],
            message=c.get("commit", {}).get("message", ""),
            additions=c.get("stats", {}).get("additions", 0),
            deletions=c.get("stats", {}).get("deletions", 0),
            files_changed=len(c.get("files", [])),
            committed_at=committed_at
        ).on_conflict_do_nothing(
            index_elements=["tenant_id", "sha"]
        )
        await db.execute(stmt)
        
    repo_stmt = select(Repo).where(Repo.id == repo_id)
    repo_res = await db.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()
    if repo:
        from datetime import timezone
        repo.last_synced_at = datetime.now(timezone.utc)

    await db.commit()

async def ingest_prs(org_id: UUID, repo_id: UUID, tenant_id: UUID, prs: list[dict], db: AsyncSession):
    if not prs:
        return
        
    authors = set()
    for pr in prs:
        user = pr.get("user")
        if user and user.get("login"):
            authors.add(user["login"])
            
    for login in authors:
        stmt = insert(Developer).values(
            tenant_id=tenant_id,
            github_login=login,
        ).on_conflict_do_nothing(
            index_elements=["tenant_id", "github_login"]
        )
        await db.execute(stmt)
        
    await db.flush()
    
    dev_stmt = select(Developer).where(Developer.tenant_id == tenant_id)
    dev_res = await db.execute(dev_stmt)
    dev_map = {d.github_login: d.id for d in dev_res.scalars()}
    
    for pr in prs:
        user_login = pr.get("user", {}).get("login")
        dev_id = dev_map.get(user_login) if user_login else None
        
        opened_at_str = pr.get("created_at")
        merged_at_str = pr.get("merged_at")
        
        if not opened_at_str:
            continue
            
        opened_at = datetime.fromisoformat(opened_at_str.replace("Z", "+00:00"))
        merged_at = datetime.fromisoformat(merged_at_str.replace("Z", "+00:00")) if merged_at_str else None
        
        time_to_merge_h = None
        if merged_at:
            time_to_merge_h = (merged_at - opened_at).total_seconds() / 3600.0
            
        stmt = insert(PrEvent).values(
            tenant_id=tenant_id,
            repo_id=repo_id,
            author_id=dev_id,
            github_pr_id=pr["id"],
            title=pr.get("title", ""),
            state=pr.get("state", ""),
            opened_at=opened_at,
            merged_at=merged_at,
            time_to_merge_h=time_to_merge_h,
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0)
        ).on_conflict_do_update(
            index_elements=["tenant_id", "github_pr_id"],
            set_=dict(
                state=pr.get("state", ""),
                merged_at=merged_at,
                time_to_merge_h=time_to_merge_h,
                title=pr.get("title", "")
            )
        )
        await db.execute(stmt)
        
    await db.commit()

async def ingest_org_repos(org_id: UUID, tenant_id: UUID, repos: list[dict], db: AsyncSession):
    if not repos:
        return
        
    for r in repos:
        stmt = insert(Repo).values(
            tenant_id=tenant_id,
            org_id=org_id,
            github_repo_id=r["id"],
            name=r["name"],
            full_name=r["full_name"],
            is_tracked=True
        ).on_conflict_do_nothing(
            index_elements=["tenant_id", "github_repo_id"]
        )
        await db.execute(stmt)
        
    await db.commit()
