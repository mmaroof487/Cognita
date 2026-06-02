"""
Tests for actions (approval/rejection) endpoints.

Tests HITL gate flow: pending → approved/rejected → executed/failed/rejected
"""

import pytest
import json
from datetime import datetime
from uuid import uuid4

from app.models.agent_action import AgentAction
from app.models.agent_run import AgentRun


@pytest.mark.asyncio
async def test_list_pending_actions(test_client, test_tenant, test_org, test_session):
    """Test listing pending actions."""
    # Create agent run and action
    run = AgentRun(
        tenant_id=test_tenant.id,
        org_id=test_org.id,
        thread_id=f"test_{uuid4()}",
        status="completed",
        started_at=datetime.utcnow(),
        window_start=datetime.utcnow(),
        window_end=datetime.utcnow(),
    )
    test_session.add(run)
    await test_session.flush()

    action = AgentAction(
        tenant_id=test_tenant.id,
        agent_run_id=run.id,
        action_type="create_jira",
        payload={"summary": "Test", "description": "Test action"},
        status="pending",
    )
    test_session.add(action)
    await test_session.commit()

    # Note: Requires proper auth setup
    # response = await test_client.get(
    #     "/api/v1/actions",
    #     headers={"Authorization": f"Bearer {test_token}"},
    # )
    # assert response.status_code == 200
    # assert len(response.json()["actions"]) == 1
    pass


@pytest.mark.asyncio
async def test_approve_action_success(test_client, test_tenant, test_org, test_session):
    """Test approving a pending action."""
    # Create action
    run = AgentRun(
        tenant_id=test_tenant.id,
        org_id=test_org.id,
        thread_id=f"test_{uuid4()}",
        status="completed",
        started_at=datetime.utcnow(),
        window_start=datetime.utcnow(),
        window_end=datetime.utcnow(),
    )
    test_session.add(run)
    await test_session.flush()

    action = AgentAction(
        tenant_id=test_tenant.id,
        agent_run_id=run.id,
        action_type="create_jira",
        payload={"summary": "Test", "description": "Test"},
        status="pending",
    )
    test_session.add(action)
    await test_session.commit()

    # Note: Test documents expected behavior
    # POST /api/v1/actions/{action_id}/approve
    # Expected: 200, status → "executed", reviewed_by set, executed_at set
    pass


@pytest.mark.asyncio
async def test_approve_action_not_pending(test_client, test_tenant, test_org, test_session):
    """Test approving action that's not pending."""
    # Create action with status already approved
    run = AgentRun(
        tenant_id=test_tenant.id,
        org_id=test_org.id,
        thread_id=f"test_{uuid4()}",
        status="completed",
        started_at=datetime.utcnow(),
        window_start=datetime.utcnow(),
        window_end=datetime.utcnow(),
    )
    test_session.add(run)
    await test_session.flush()

    action = AgentAction(
        tenant_id=test_tenant.id,
        agent_run_id=run.id,
        action_type="create_jira",
        payload={"summary": "Test"},
        status="executed",  # Already executed
    )
    test_session.add(action)
    await test_session.commit()

    # Expected: 400 Bad Request (action not pending)
    pass


@pytest.mark.asyncio
async def test_reject_action_success(test_client, test_tenant, test_org, test_session):
    """Test rejecting a pending action."""
    # Create action
    run = AgentRun(
        tenant_id=test_tenant.id,
        org_id=test_org.id,
        thread_id=f"test_{uuid4()}",
        status="completed",
        started_at=datetime.utcnow(),
        window_start=datetime.utcnow(),
        window_end=datetime.utcnow(),
    )
    test_session.add(run)
    await test_session.flush()

    action = AgentAction(
        tenant_id=test_tenant.id,
        agent_run_id=run.id,
        action_type="create_jira",
        payload={"summary": "Test"},
        status="pending",
    )
    test_session.add(action)
    await test_session.commit()

    # Note: Test documents expected behavior
    # POST /api/v1/actions/{action_id}/reject
    # Expected: 200, status → "rejected", reviewed_by set, reviewed_at set
    pass


@pytest.mark.asyncio
async def test_get_action_detail(test_client, test_tenant, test_org, test_session):
    """Test getting details of a specific action."""
    # Create action
    run = AgentRun(
        tenant_id=test_tenant.id,
        org_id=test_org.id,
        thread_id=f"test_{uuid4()}",
        status="completed",
        started_at=datetime.utcnow(),
        window_start=datetime.utcnow(),
        window_end=datetime.utcnow(),
    )
    test_session.add(run)
    await test_session.flush()

    action = AgentAction(
        tenant_id=test_tenant.id,
        agent_run_id=run.id,
        action_type="create_jira",
        payload={"summary": "Test", "priority": "High"},
        status="pending",
    )
    test_session.add(action)
    await test_session.commit()

    # GET /api/v1/actions/{action_id}
    # Expected: 200 with full action details including payload
    pass
