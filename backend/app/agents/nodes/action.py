"""
Action node — creates pending AgentAction rows from insights and calls interrupt().

Insight rows are already persisted by the insight node.
This node reads insight dicts from state (with _db_insight_id populated),
creates pending AgentAction rows, writes AuditLog, and interrupts for HITL.
"""

from langgraph.types import interrupt
from app.agents.state import AxonState
import app.database
from sqlalchemy import select, text
from app.models import AgentAction, Insight as InsightModel
from app.core.telemetry import axon_hitl_pending
import uuid


async def run(state: AxonState) -> dict:
    insights_data = state.get("insights", [])
    actions_queued: list[dict] = []
    interrupt_actions: list[dict] = []

    async with app.database.async_session_factory() as db:
        for ins in insights_data:
            sev = ins.get("severity", "info").lower()

            # Resolve the DB insight ID — either set by insight node or look up
            db_insight_id_str = ins.get("_db_insight_id")
            if db_insight_id_str:
                insight_id = uuid.UUID(db_insight_id_str)
            else:
                # Fallback: try to find by agent_run_id + title
                lookup_stmt = select(InsightModel).where(
                    InsightModel.agent_run_id == uuid.UUID(state["agent_run_id"]),
                    InsightModel.title == ins.get("title", ""),
                )
                lookup_res = await db.execute(lookup_stmt)
                found = lookup_res.scalar_one_or_none()
                insight_id = found.id if found else uuid.uuid4()

            # Critical → create Jira ticket (requires HITL)
            if sev == "critical":
                act_id = uuid.uuid4()
                act = AgentAction(
                    id=act_id,
                    tenant_id=uuid.UUID(state["tenant_id"]),
                    agent_run_id=uuid.UUID(state["agent_run_id"]),
                    insight_id=insight_id,
                    action_type="create_jira",
                    status="pending",
                    payload={"message": ins.get("title", "")},
                )
                db.add(act)
                actions_queued.append(act)
                interrupt_actions.append({"id": str(act_id), "type": "create_jira"})
                axon_hitl_pending.labels(tenant_id=state["tenant_id"]).inc()

            # Critical or Warning → send Slack notification (requires HITL)
            if sev in ("critical", "warning"):
                act_id = uuid.uuid4()
                act = AgentAction(
                    id=act_id,
                    tenant_id=uuid.UUID(state["tenant_id"]),
                    agent_run_id=uuid.UUID(state["agent_run_id"]),
                    insight_id=insight_id,
                    action_type="send_slack",
                    status="pending",
                    payload={"message": ins.get("title", "")},
                )
                db.add(act)
                actions_queued.append(act)
                axon_hitl_pending.labels(tenant_id=state["tenant_id"]).inc()

        # Write AuditLog via raw SQL (table is not ORM-mapped)
        await db.execute(
            text(
                "INSERT INTO audit_log (tenant_id, actor, action, entity_type, entity_id) "
                "VALUES (:tid, :actor, :action, :etype, :eid)"
            ),
            {
                "tid": str(state["tenant_id"]),
                "actor": "agent:action",
                "action": "actions.queued",
                "etype": "agent_run",
                "eid": state["agent_run_id"],
            },
        )
        await db.commit()

    # HITL interrupt — fires when critical insights need human approval
    if interrupt_actions:
        interrupt(
            {
                "message": "Critical insights require HITL approval to create Jira tickets.",
                "actions": interrupt_actions,
            }
        )

    return {
        "actions_queued": [{"id": str(a.id), "type": a.action_type} for a in actions_queued]
    }
