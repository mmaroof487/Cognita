from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import uuid
from datetime import datetime, timezone

from app.database import get_async_session as get_db
from app.deps import get_current_tenant, get_current_user
from app.models import Tenant, User, AgentAction, AgentRun, TenantSettings, JiraTemplate, Insight
from app.schemas.action import ActionRead, ApproveRequest, RejectRequest
from app.services.notification import send_slack, send_email, create_jira_ticket

router = APIRouter(tags=["actions"])

@router.get("/orgs/{org_id}/actions")
async def list_actions(
    org_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentAction).join(AgentRun, AgentAction.agent_run_id == AgentRun.id).where(
        AgentRun.org_id == org_id,
        AgentAction.tenant_id == tenant.id,
        AgentAction.status == "pending"
    )
    res = await db.execute(stmt)
    actions = res.scalars().all()
    return {
        "items": [ActionRead.model_validate(a, from_attributes=True) for a in actions],
        "total": len(actions),
        "page": 1,
        "page_size": 100
    }

@router.post("/actions/{action_id}/approve", response_model=ActionRead)
async def approve_action(
    action_id: uuid.UUID,
    req: ApproveRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentAction).where(AgentAction.id == action_id, AgentAction.tenant_id == tenant.id)
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404)
    if action.status != "pending":
        raise HTTPException(status_code=400, detail="Action is not pending")
        
    ts_stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    ts_res = await db.execute(ts_stmt)
    settings = ts_res.scalar_one_or_none()
    
    if action.action_type == "send_slack":
        await send_slack(settings, action.payload)
    elif action.action_type == "send_email":
        await send_email(settings, action.payload)
    elif action.action_type == "create_jira":
        # Look up the insight to get its type for template matching
        ins_stmt = select(Insight).where(Insight.id == action.insight_id)
        ins_res = await db.execute(ins_stmt)
        linked_insight = ins_res.scalar_one_or_none()
        anomaly_type = linked_insight.insight_type if linked_insight else "burnout_risk"

        # Match template to the insight's anomaly type
        jt_stmt = select(JiraTemplate).where(
            JiraTemplate.anomaly_type == anomaly_type,
            JiraTemplate.tenant_id == tenant.id,
        )
        jt_res = await db.execute(jt_stmt)
        template = jt_res.scalar_one_or_none()

        # Fallback: any template for this tenant
        if not template:
            fb_stmt = select(JiraTemplate).where(JiraTemplate.tenant_id == tenant.id).limit(1)
            template = (await db.execute(fb_stmt)).scalar_one_or_none()

        if template:
            developer_login = "Unknown"
            if linked_insight and linked_insight.developer_id:
                from app.models import Developer as Dev
                dev_stmt = select(Dev).where(Dev.id == linked_insight.developer_id)
                dev_res = await db.execute(dev_stmt)
                dev_obj = dev_res.scalar_one_or_none()
                if dev_obj:
                    developer_login = dev_obj.github_login
            payload = {
                "developer_login": developer_login,
                "metric": anomaly_type,
                "detail": action.payload.get("message", ""),
                "score": str(linked_insight.score) if linked_insight and linked_insight.score else "0",
            }
            await create_jira_ticket(settings, payload, template)
            
    now = datetime.now(timezone.utc)
    action.status = "executed"
    action.reviewed_by = user.id
    action.reviewed_at = now
    
    # AuditLog is a raw SQL table (not ORM), insert via text
    await db.execute(
        text("INSERT INTO audit_log (tenant_id, actor, action, entity_type, entity_id) VALUES (:tid, :actor, :action, :etype, :eid)"),
        {"tid": str(tenant.id), "actor": f"user:{user.id}", "action": "action.approved", "etype": "agent_action", "eid": str(action.id)}
    )
    
    run_stmt = select(AgentRun).where(AgentRun.id == action.agent_run_id)
    run_res = await db.execute(run_stmt)
    run = run_res.scalar_one_or_none()
    
    await db.commit()
    await db.refresh(action)
    
    if run and run.status == "awaiting_human":
        from app.agents.graph import build_graph
        graph = await build_graph()
        await graph.ainvoke(None, config={"configurable": {"thread_id": run.thread_id}})
        run.status = "completed"
        db.add(run)
        await db.commit()
        
    return ActionRead.model_validate(action, from_attributes=True)

@router.post("/actions/{action_id}/reject", response_model=ActionRead)
async def reject_action(
    action_id: uuid.UUID,
    req: RejectRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentAction).where(AgentAction.id == action_id, AgentAction.tenant_id == tenant.id)
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404)
    if action.status != "pending":
        raise HTTPException(status_code=400, detail="Action is not pending")
        
    now = datetime.now(timezone.utc)
    action.status = "rejected"
    action.reviewed_by = user.id
    action.reviewed_at = now
    action.error = req.reason  # Store rejection reason in error column
    
    # AuditLog is a raw SQL table (not ORM), insert via text
    await db.execute(
        text("INSERT INTO audit_log (tenant_id, actor, action, entity_type, entity_id) VALUES (:tid, :actor, :action, :etype, :eid)"),
        {"tid": str(tenant.id), "actor": f"user:{user.id}", "action": "action.rejected", "etype": "agent_action", "eid": str(action.id)}
    )
    await db.commit()
    await db.refresh(action)
    return ActionRead.model_validate(action, from_attributes=True)
