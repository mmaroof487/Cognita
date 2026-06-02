import asyncio
import argparse
import sys
import os
from datetime import datetime, timezone, timedelta
from uuid import UUID

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.database import async_session_factory
from app.config import settings
from app.services.github import GitHubClient
from app.models.tenant import Tenant
from app.models.org import Org
from app.models.repo import Repo
from app.models.developer import Developer
from app.models.commit_event import CommitEvent
from app.models.pr_event import PrEvent

async def sync_repo(tenant_id: UUID, org_id: UUID, owner: str, repo_name: str):
    client = GitHubClient(settings.github_access_token)
    
    async with async_session_factory() as db:
        # Create or Get Repo
        stmt = insert(Repo).values(
            tenant_id=tenant_id,
            org_id=org_id,
            github_repo_id=123, # Dummy, we don't have it easily
            name=repo_name,
            full_name=f"{owner}/{repo_name}",
            is_tracked=True
        ).on_conflict_do_nothing(index_elements=["tenant_id", "github_repo_id"])
        await db.execute(stmt)
        await db.commit()
        
        repo_stmt = select(Repo).where(Repo.tenant_id == tenant_id, Repo.name == repo_name)
        repo_res = await db.execute(repo_stmt)
        repo = repo_res.scalar_one()

        print(f"Fetching commits for {owner}/{repo_name}...")
        since = datetime.now(timezone.utc) - timedelta(days=90)
        commits = await client.get_commits(owner, repo_name, since=since, per_page=100)
        
        print(f"Fetched {len(commits)} commits.")
        
        # Insert Developers
        dev_logins = set(c["author_login"] for c in commits if c.get("author_login"))
        for login in dev_logins:
            dev_stmt = insert(Developer).values(
                tenant_id=tenant_id,
                github_login=login
            ).on_conflict_do_nothing(index_elements=["tenant_id", "github_login"])
            await db.execute(dev_stmt)
        await db.commit()
        
        dev_res = await db.execute(select(Developer).where(Developer.tenant_id == tenant_id))
        dev_map = {d.github_login: d.id for d in dev_res.scalars()}
        
        # Insert Commits
        for c in commits:
            if not c.get("committed_at"):
                continue
            committed_at = datetime.fromisoformat(c["committed_at"].replace("Z", "+00:00"))
            
            c_stmt = insert(CommitEvent).values(
                tenant_id=tenant_id,
                repo_id=repo.id,
                developer_id=dev_map.get(c.get("author_login")),
                sha=c["sha"],
                message=c["message"],
                additions=c["additions"],
                deletions=c["deletions"],
                files_changed=c["files_changed"],
                committed_at=committed_at
            ).on_conflict_do_nothing(index_elements=["tenant_id", "sha"])
            await db.execute(c_stmt)
            
        print("Fetching PRs...")
        prs = await client.get_pull_requests(owner, repo_name, state="all", per_page=100)
        print(f"Fetched {len(prs)} PRs.")
        
        # Insert Developers for PRs
        pr_dev_logins = set(p["author_login"] for p in prs if p.get("author_login"))
        for login in pr_dev_logins:
            if login not in dev_logins:
                dev_stmt = insert(Developer).values(
                    tenant_id=tenant_id,
                    github_login=login
                ).on_conflict_do_nothing(index_elements=["tenant_id", "github_login"])
                await db.execute(dev_stmt)
        await db.commit()
        
        dev_res = await db.execute(select(Developer).where(Developer.tenant_id == tenant_id))
        dev_map = {d.github_login: d.id for d in dev_res.scalars()}
        
        # Insert PRs
        for p in prs:
            if not p.get("created_at"):
                continue
            opened_at = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
            merged_at = datetime.fromisoformat(p["merged_at"].replace("Z", "+00:00")) if p.get("merged_at") else None
            
            time_to_merge = None
            if merged_at:
                time_to_merge = (merged_at - opened_at).total_seconds() / 3600.0
                
            p_stmt = insert(PrEvent).values(
                tenant_id=tenant_id,
                repo_id=repo.id,
                author_id=dev_map.get(p.get("author_login")),
                github_pr_id=p["id"] or hash(p["number"]),
                title=p["title"],
                state=p["state"],
                opened_at=opened_at,
                merged_at=merged_at,
                time_to_merge_h=time_to_merge,
                additions=p["additions"],
                deletions=p["deletions"]
            ).on_conflict_do_nothing(index_elements=["tenant_id", "github_pr_id"])
            await db.execute(p_stmt)
            
        await db.commit()
        print("Sync complete!")

async def main():
    parser = argparse.ArgumentParser(description="Sync GitHub repo history")
    parser.add_argument("owner", help="GitHub Organization or Username (e.g. facebook)")
    parser.add_argument("repo", help="GitHub Repository Name (e.g. react)")
    args = parser.parse_args()
    
    if not settings.github_access_token:
        print("ERROR: GITHUB_ACCESS_TOKEN is not set in .env")
        return

    async with async_session_factory() as db:
        res = await db.execute(select(Tenant))
        tenant = res.scalars().first()
        if not tenant:
            print("ERROR: No tenant found. Run setup_real.py first.")
            return
            
        res = await db.execute(select(Org).where(Org.tenant_id == tenant.id))
        org = res.scalars().first()
        if not org:
            print("ERROR: No org found. Run setup_real.py first.")
            return

        await sync_repo(tenant.id, org.id, args.owner, args.repo)

if __name__ == "__main__":
    asyncio.run(main())
