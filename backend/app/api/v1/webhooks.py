from fastapi import APIRouter, Request, HTTPException
from app.providers.github import GitHubProvider
from app.celery_worker import ingest_push_event, ingest_pr_event

router = APIRouter(tags=["webhooks"])

@router.post("/webhooks/github")
async def github_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")
        
    gh = GitHubProvider()
    if not await gh.validate_webhook(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    event = request.headers.get("X-GitHub-Event")
    data = await request.json()
    
    from app.database import async_session_factory
    from app.models import Org
    from sqlalchemy import select
    
    github_org_id = data.get("organization", {}).get("id")
    if not github_org_id:
        return {"status": "accepted"}
        
    async with async_session_factory() as db:
        stmt = select(Org).where(Org.github_org_id == github_org_id)
        res = await db.execute(stmt)
        org = res.scalar_one_or_none()
        if not org:
            return {"status": "accepted"}
            
    if event == "push":
        ingest_push_event.delay(str(org.id), data)
    elif event == "pull_request":
        ingest_pr_event.delay(str(org.id), data)
        
    return {"status": "accepted"}
