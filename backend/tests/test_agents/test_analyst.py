"""
Tests for Analyst agent node.

Tests pure Python logic: computing metrics and detecting anomalies.
"""

import pytest
from datetime import datetime, timedelta

from app.agents.nodes.analyst import analyst_node
from app.agents.state import DevPulseState


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
                "author_login": "alice",
                "additions": 100,
                "deletions": 50,
                "files_changed": 3,
                "committed_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "ingested_at": datetime.utcnow().isoformat(),
            }
            for _ in range(20)  # 20 commits (burnout risk!)
        ],
        "prs": [
            {
                "github_pr_id": 1,
                "title": "Feature",
                "state": "merged",
                "author_login": "alice",
                "additions": 500,
                "deletions": 100,
                "review_comments": 5,
                "time_to_merge_h": 100,  # 100 hours (slow!)
                "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "merged_at": (datetime.utcnow() - timedelta(days=4)).isoformat(),
            },
            {
                "github_pr_id": 2,
                "title": "Cleanup",
                "state": "merged",
                "author_login": "bob",
                "additions": 50,
                "deletions": 200,  # High churn!
                "review_comments": 0,
                "time_to_merge_h": 2,
                "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "merged_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            },
        ],
        "developers": [
            {"github_login": "alice", "name": "Alice", "avatar_url": "..."},
            {"github_login": "bob", "name": "Bob", "avatar_url": "..."},
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


def test_analyst_empty_state():
    """Test analyst with no commits/PRs (empty window)."""
    state = {
        "commits": [],
        "prs": [],
        "developers": [],
        "anomalies": [],
        "insights": [],
        "actions_queued": [],
    }

    result = analyst_node(state)

    assert result["developer_metrics"] == {}
    assert result["anomalies"] == []
    assert result["team_metrics"]["total_commits"] == 0
    assert result["team_metrics"]["total_prs"] == 0


def test_analyst_computes_team_metrics(sample_state_with_data):
    """Test analyst computes team-level metrics."""
    result = analyst_node(sample_state_with_data)

    team_metrics = result["team_metrics"]
    assert team_metrics["total_commits"] == 20
    assert team_metrics["total_prs"] == 2
    assert team_metrics["total_developers"] == 2
    assert team_metrics["total_additions"] > 0
    assert team_metrics["total_deletions"] > 0


def test_analyst_detects_burnout_risk(sample_state_with_data):
    """Test analyst detects burnout risk anomaly."""
    result = analyst_node(sample_state_with_data)

    anomalies = result["anomalies"]

    # Find burnout_risk anomaly
    burnout_anomalies = [a for a in anomalies if a["type"] == "burnout_risk"]
    assert len(burnout_anomalies) > 0

    # Alice should be flagged
    alice_burnout = [a for a in burnout_anomalies if a["developer_login"] == "alice"]
    assert len(alice_burnout) > 0
    assert alice_burnout[0]["severity"] == "high"


def test_analyst_detects_high_churn(sample_state_with_data):
    """Test analyst detects high code churn anomaly."""
    result = analyst_node(sample_state_with_data)

    anomalies = result["anomalies"]

    # Find high_churn anomaly
    churn_anomalies = [a for a in anomalies if a["type"] == "high_churn"]
    assert len(churn_anomalies) > 0

    # PR #2 (Bob) should be flagged (deletions > 2*additions)
    bob_churn = [a for a in churn_anomalies if a["developer_login"] == "bob"]
    assert len(bob_churn) > 0


def test_analyst_detects_slow_review(sample_state_with_data):
    """Test analyst detects slow review cycle anomaly."""
    result = analyst_node(sample_state_with_data)

    anomalies = result["anomalies"]

    # Find slow_review anomaly
    slow_anomalies = [a for a in anomalies if a["type"] == "slow_review"]
    assert len(slow_anomalies) > 0

    # PR #1 should be flagged (100h > 72h)
    assert any(a["pr_id"] == 1 for a in slow_anomalies)


def test_analyst_developer_metrics(sample_state_with_data):
    """Test analyst computes per-developer metrics correctly."""
    result = analyst_node(sample_state_with_data)

    dev_metrics = result["developer_metrics"]

    assert "alice" in dev_metrics
    assert dev_metrics["alice"]["commit_count"] == 20
    assert dev_metrics["alice"]["pr_count"] == 1

    assert "bob" in dev_metrics
    assert dev_metrics["bob"]["pr_count"] == 1
