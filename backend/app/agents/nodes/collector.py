from app.agents.state import AxonState
import app.database
from sqlalchemy import select
from app.models import CommitEvent, PrEvent, Developer, Repo
import json

async def run(state: AxonState) -> dict:
    if not state.get("tenant_id"):
        raise ValueError("Missing tenant_id in state")
    
    async with app.database.async_session_factory() as db:
        commits_stmt = select(CommitEvent).where(
            CommitEvent.tenant_id == state["tenant_id"],
            CommitEvent.committed_at.between(state["window_start"], state["window_end"])
        )
        commits_res = await db.execute(commits_stmt)
        commits_raw = commits_res.scalars().all()
        
        prs_stmt = select(PrEvent).where(
            PrEvent.tenant_id == state["tenant_id"],
            PrEvent.opened_at >= state["window_start"]
        )
        prs_res = await db.execute(prs_stmt)
        prs_raw = prs_res.scalars().all()
        
        devs_stmt = select(Developer).where(
            Developer.tenant_id == state["tenant_id"],
            Developer.tenant_id == state["tenant_id"]
        )
        devs_res = await db.execute(devs_stmt)
        devs_raw = devs_res.scalars().all()
        
        repos_stmt = select(Repo).where(
            Repo.tenant_id == state["tenant_id"]
        )
        repos_res = await db.execute(repos_stmt)
        repos_raw = repos_res.scalars().all()
        
    def to_dict(obj):
        d = obj.__dict__.copy()
        d.pop("_sa_instance_state", None)
        for k, v in d.items():
            import uuid, datetime
            if isinstance(v, uuid.UUID):
                d[k] = str(v)
            elif isinstance(v, datetime.datetime):
                d[k] = v.isoformat()
        return d
        
    return {
        "commits": [to_dict(c) for c in commits_raw],
        "prs": [to_dict(p) for p in prs_raw],
        "developers": [to_dict(d) for d in devs_raw],
        "repos": [to_dict(r) for r in repos_raw]
    }
