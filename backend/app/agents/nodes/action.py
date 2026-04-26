"""
Action Agent Node — Generate actionable outputs and HITL gates.

Creates:
- AgentAction records with status=pending (HITL gate)
- Audit log entries
- Insight records in DB

Does NOT immediately execute actions; waits for human approval via approve/reject endpoints.
"""

import json
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.agents.state import DevPulseState
from app.models.insight import Insight
from app.models.agent_action import AgentAction
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.models.jira_template import JiraTemplate


async def action_node(
    state: DevPulseState,
    session: AsyncSession,
) -> dict:
    """
    Action agent node: Create actionable items and HITL gates.

    Args:
        state: DevPulseState with insights, anomalies populated
        session: Async database session

    Returns:
        Dict with actions_queued to update state
    """
    tenant_id = state.get("tenant_id")
    org_id = state.get("org_id")
    agent_run_id = state.get("agent_run_id")
    anomalies = state.get("anomalies", [])
    insights = state.get("insights", [])

    if not insights:
        print("[ActionAgent] No insights to act on, skipping")
        return {"actions_queued": []}

    actions_queued = []

    # ─────────────────────────────────────────────────────────────────────────
    # Write Insights to DB
    # ─────────────────────────────────────────────────────────────────────────
    for insight in insights:
        try:
            insight_record = Insight(
                tenant_id=tenant_id,
                agent_run_id=agent_run_id,
                insight_type=insight.get("severity", "medium"),
                severity=insight.get("severity", "medium"),
                title=insight.get("title", ""),
                body=insight.get("explanation", ""),
                score=75,  # Default score, could be enhanced
                metadata={
                    "recommended_action": insight.get("recommended_action", ""),
                    "source": "claude_insight_agent",
                },
            )
            session.add(insight_record)
            await session.flush()

            actions_queued.append({
                "type": "insight_created",
                "insight_id": str(insight_record.id),
                "title": insight.get("title"),
                "status": "executed",  # Insights don't need approval
            })
        except Exception as e:
            print(f"[ActionAgent] Error writing insight: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Generate Jira Tickets (HITL Gate)
    # ─────────────────────────────────────────────────────────────────────────

    # Get Jira templates for this tenant
    templates_query = select(JiraTemplate).where(
        JiraTemplate.tenant_id == tenant_id
    )
    templates_result = await session.execute(templates_query)
    templates_list = templates_result.scalars().all()
    templates_by_type = {t.anomaly_type: t for t in templates_list}

    for anomaly in anomalies:
        anomaly_type = anomaly.get("type")  # burnout_risk, high_churn, slow_review
        template = templates_by_type.get(anomaly_type)

        if not template:
            print(f"[ActionAgent] No template for anomaly type: {anomaly_type}")
            continue

        # Build Jira payload
        developer_login = anomaly.get("developer_login", "unknown")
        metric_value = anomaly.get("metric", {})

        try:
            summary = template.summary_template.format(
                developer_login=developer_login,
                metric=json.dumps(metric_value),
            )
            description = template.description_template.format(
                developer_login=developer_login,
                reason=anomaly.get("reason", ""),
                metric=json.dumps(metric_value),
                score=anomaly.get("score", 0),
            )
        except KeyError as e:
            print(f"[ActionAgent] Template formatting error: {e}")
            summary = f"{anomaly_type}: {developer_login}"
            description = anomaly.get("reason", "")

        # Create AgentAction with HITL gate
        jira_payload = {
            "summary": summary,
            "description": description,
            "issue_type": template.issue_type,
            "priority": template.priority_default,
            "labels": template.labels,
        }

        action = AgentAction(
            tenant_id=tenant_id,
            agent_run_id=agent_run_id,
            action_type="create_jira",
            payload=jira_payload,
            status="pending",  # HITL gate: pending approval
        )
        session.add(action)
        await session.flush()

        actions_queued.append({
            "type": "create_jira",
            "action_id": str(action.id),
            "summary": summary,
            "status": "pending",
            "anomaly_type": anomaly_type,
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Write Audit Log
    # ─────────────────────────────────────────────────────────────────────────
    try:
        audit = AuditLog(
            tenant_id=tenant_id,
            actor="agent",
            action="generate_actions",
            entity_type="agent_run",
            entity_id=agent_run_id,
            diff={
                "actions_created": len(actions_queued),
                "anomalies_processed": len(anomalies),
                "insights_created": len(insights),
            },
        )
        session.add(audit)
        await session.flush()
    except Exception as e:
        print(f"[ActionAgent] Error writing audit log: {e}")

    # Commit all changes
    await session.commit()

    print(f"[ActionAgent] Created {len(actions_queued)} actions in HITL gate")

    return {"actions_queued": actions_queued}
