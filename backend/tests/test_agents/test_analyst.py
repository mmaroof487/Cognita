"""
Tests for Analyst agent node.

Tests pure Python logic: computing metrics and detecting anomalies.
"""

import pytest
from datetime import datetime, timedelta

from app.agents.nodes.analyst import run as analyst_node
from app.agents.state import AxonState

@pytest.fixture

def sample_state_with_data():
    """Fixture: state with sample commits and PRs."""
    return {
        "tenant_id": "tenant-1",
        "org_id": "org-1",
        "window_start": datetime.utcnow() - timedelta(days=7),
        "window_end": datetime.utcnow(),
        "commits": [
            {
                "sha": "abc123",
                "message": "Fix bug",
                "developer_id": "alice",
                "additions": 100,
                "deletions": 50,
                "files_changed": 3,
                "committed_at": datetime(2023, 1, 1, 23, 0, 0).isoformat(),
                "ingested_at": datetime.utcnow().isoformat(),
                "lines_added": 100,
                "lines_removed": 50,
            }
            for _ in range(20)  # 20 commits (burnout risk!)
        ],
        "prs": [
            {
                "id": "pr-1",
                "title": "Feature",
                "state": "merged",
                "developer_id": "alice",
                "additions": 500,
                "deletions": 100,
                "review_comments": 5,
                "time_to_merge_h": 100,  # 100 hours (slow!)
                "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "merged_at": (datetime.utcnow() - timedelta(days=4)).isoformat(),
            },
            {
                "id": "pr-2",
                "title": "Cleanup",
                "state": "merged",
                "developer_id": "bob",
                "additions": 50,
                "deletions": 200,  # High churn!
                "review_comments": 0,
                "time_to_merge_h": 2,
                "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "merged_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            },
        ],
        "developers": [
            {"id": "alice", "github_login": "alice", "name": "Alice", "avatar_url": "..."},
            {"id": "bob", "github_login": "bob", "name": "Bob", "avatar_url": "..."},
        ],
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


@pytest.mark.asyncio
async def test_analyst_empty_state():
    """Test analyst with no commits/PRs (empty window)."""
    state = {
        "commits": [],
        "prs": [],
        "developers": [],
        "anomalies": [],
        "insights": [],
        "actions_queued": [],
    }

    result = await analyst_node(state)

    assert result["developer_metrics"] == {}
    assert result["anomalies"] == []
    assert result["team_metrics"]["total_commits"] == 0
    assert result["team_metrics"]["total_prs"] == 0


@pytest.mark.asyncio
async def test_analyst_computes_team_metrics(sample_state_with_data):
    """Test analyst computes team-level metrics."""
    result = await analyst_node(sample_state_with_data)

    team_metrics = result["team_metrics"]
    assert team_metrics["total_commits"] == 20
    assert team_metrics["total_prs"] == 2
    assert team_metrics["developer_count"] == 2
    assert "avg_health_score" in team_metrics


@pytest.mark.asyncio
async def test_analyst_detects_burnout_risk(sample_state_with_data):
    """Test analyst detects burnout risk anomaly."""
    result = await analyst_node(sample_state_with_data)

    anomalies = result["anomalies"]

    # Find burnout_risk anomaly
    burnout_anomalies = [a for a in anomalies if a["type"] == "burnout_risk"]
    assert len(burnout_anomalies) > 0

    # Alice should be flagged
    alice_burnout = [a for a in burnout_anomalies if a.get("developer_id") == "alice"]
    assert len(alice_burnout) > 0
    assert alice_burnout[0]["severity"] == "critical"

@pytest.mark.asyncio
async def test_analyst_detects_high_churn(sample_state_with_data):
    """Test analyst detects high code churn anomaly."""
    result = await analyst_node(sample_state_with_data)

    anomalies = result["anomalies"]

    # Find high_churn anomaly
    churn_anomalies = [a for a in anomalies if a["type"] == "high_churn"]
    assert len(churn_anomalies) > 0

    # PR #2 (Bob) should be flagged (deletions > 2*additions)
    bob_churn = [a for a in churn_anomalies if a.get("developer_id") == "bob"]
    assert len(bob_churn) > 0


@pytest.mark.asyncio
async def test_analyst_detects_slow_review(sample_state_with_data):
    """Test analyst detects slow review cycle anomaly."""
    result = await analyst_node(sample_state_with_data)

    anomalies = result["anomalies"]

    # Find slow_review anomaly
    slow_anomalies = [a for a in anomalies if a["type"] == "slow_review"]
    assert len(slow_anomalies) > 0

    # Alice should be flagged (100h > 72h)
    assert any(a.get("developer_id") == "alice" for a in slow_anomalies)


@pytest.mark.asyncio
async def test_analyst_developer_metrics(sample_state_with_data):
    """Test analyst computes per-developer metrics correctly."""
    result = await analyst_node(sample_state_with_data)

    dev_metrics = result["developer_metrics"]

    assert "alice" in dev_metrics
    assert dev_metrics["alice"]["commit_count"] == 20
    assert "health_score" in dev_metrics["alice"]

    assert "bob" in dev_metrics
    assert dev_metrics["bob"]["commit_count"] == 0
