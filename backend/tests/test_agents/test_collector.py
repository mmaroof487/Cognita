"""
Tests for Collector agent node.

Tests pure deterministic logic: fetching data from DB and normalizing events.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.agents.nodes.collector import collector_node
from app.agents.state import DevPulseState
from app.models.tenant import Tenant
from app.models.org import Org
from app.models.repo import Repo
from app.models.developer import Developer
from app.models.commit_event import CommitEvent
from app.models.pr_event import PrEvent


@pytest.mark.asyncio
async def test_collector_empty_window(test_session, test_tenant):
    """Test collector with empty data (no commits/PRs in window)."""
    # Create org
    org = Org(
        tenant_id=test_tenant.id,
        github_id=123,
        name="test-org",
    )
    test_session.add(org)
    await test_session.flush()

    # Test state
    state = {
        "tenant_id": str(test_tenant.id),
        "org_id": str(org.id),
        "window_start": datetime.utcnow() - timedelta(days=7),
        "window_end": datetime.utcnow(),
        "commits": [],
        "prs": [],
        "developers": [],
        "developer_metrics": {},
        "team_metrics": {},
        "anomalies": [],
        "insights": [],
        "actions_queued": [],
        "retry_count": 0,
        "errors": [],
        "tokens_used": 0,
        "cost_usd": 0.0,
    }

    result = await collector_node(state, test_session)

    assert result["commits"] == []
    assert result["prs"] == []
    assert result["developers"] == []


@pytest.mark.asyncio
async def test_collector_with_commits(test_session, test_tenant):
    """Test collector fetches commits correctly."""
    # Create org and repo
    org = Org(
        tenant_id=test_tenant.id,
        github_id=123,
        name="test-org",
    )
    test_session.add(org)
    await test_session.flush()

    repo = Repo(
        tenant_id=test_tenant.id,
        org_id=org.id,
        github_id=456,
        name="test-repo",
        full_name="test-org/test-repo",
    )
    test_session.add(repo)
    await test_session.flush()

    # Create developer
    dev = Developer(
        tenant_id=test_tenant.id,
        github_login="alice",
        name="Alice",
    )
    test_session.add(dev)
    await test_session.flush()

    # Create commit
    now = datetime.utcnow()
    commit = CommitEvent(
        tenant_id=test_tenant.id,
        repo_id=repo.id,
        developer_id=dev.id,
        sha="abc123",
        message="Fix bug",
        additions=10,
        deletions=5,
        files_changed=2,
        committed_at=now - timedelta(days=1),
    )
    test_session.add(commit)
    await test_session.commit()

    # Test state
    state = {
        "tenant_id": str(test_tenant.id),
        "org_id": str(org.id),
        "window_start": now - timedelta(days=7),
        "window_end": now,
        "commits": [],
        "prs": [],
        "developers": [],
        "developer_metrics": {},
        "team_metrics": {},
        "anomalies": [],
        "insights": [],
        "actions_queued": [],
        "retry_count": 0,
        "errors": [],
        "tokens_used": 0,
        "cost_usd": 0.0,
    }

    result = await collector_node(state, test_session)

    assert len(result["commits"]) == 1
    assert result["commits"][0]["sha"] == "abc123"
    assert result["commits"][0]["author_login"] == "alice"
    assert result["commits"][0]["additions"] == 10
    assert len(result["developers"]) == 1
    assert result["developers"][0]["github_login"] == "alice"


@pytest.mark.asyncio
async def test_collector_missing_state_params(test_session):
    """Test collector raises error with missing state parameters."""
    state = {
        "tenant_id": None,  # Missing!
        "org_id": "org-id",
        "window_start": datetime.utcnow() - timedelta(days=7),
        "window_end": datetime.utcnow(),
    }

    with pytest.raises(ValueError):
        await collector_node(state, test_session)
