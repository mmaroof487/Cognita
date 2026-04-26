"""
Analyst Agent Node — Compute metrics and detect anomalies from collected data.

Pure Python logic (no LLM). Analyzes commits and PRs to compute per-developer
metrics and flag anomalies (burnout_risk, high_churn, slow_review).
"""

from datetime import datetime
from collections import defaultdict
from app.agents.state import DevPulseState


def analyst_node(state: DevPulseState) -> dict:
    """
    Analyst node: Compute metrics and detect anomalies.

    Args:
        state: DevPulseState with commits, prs, developers populated

    Returns:
        Dict with developer_metrics, team_metrics, anomalies
    """
    commits = state.get("commits", [])
    prs = state.get("prs", [])
    developers = state.get("developers", [])

    # ─────────────────────────────────────────────────────────────────────────
    # Compute per-developer metrics
    # ─────────────────────────────────────────────────────────────────────────
    developer_metrics = defaultdict(lambda: {
        "commit_count": 0,
        "total_additions": 0,
        "total_deletions": 0,
        "total_files_changed": 0,
        "pr_count": 0,
        "pr_additions": 0,
        "pr_deletions": 0,
        "total_review_comments": 0,
        "avg_pr_merge_time_h": 0,
        "prs_reviewed": [],
    })

    # Count commits per developer
    for commit in commits:
        author_login = commit.get("author_login", "unknown")
        if author_login != "unknown":
            m = developer_metrics[author_login]
            m["commit_count"] += 1
            m["total_additions"] += commit.get("additions", 0)
            m["total_deletions"] += commit.get("deletions", 0)
            m["total_files_changed"] += commit.get("files_changed", 0)

    # Count PRs and reviews per developer
    merge_times = []
    for pr in prs:
        author_login = pr.get("author_login", "unknown")
        if author_login != "unknown":
            m = developer_metrics[author_login]
            m["pr_count"] += 1
            m["pr_additions"] += pr.get("additions", 0)
            m["pr_deletions"] += pr.get("deletions", 0)
            m["total_review_comments"] += pr.get("review_comments", 0)

            # Track merge time (only for merged PRs)
            merge_time = pr.get("time_to_merge_h", 0)
            if merge_time > 0:
                merge_times.append(merge_time)
                m["prs_reviewed"].append({
                    "pr_id": pr.get("github_pr_id"),
                    "merge_time_h": merge_time,
                })

    # Calculate average PR merge time per developer (total across all their PRs)
    if merge_times:
        avg_merge_time = sum(merge_times) / len(merge_times)
        for login in developer_metrics:
            if developer_metrics[login]["prs_reviewed"]:
                developer_metrics[login]["avg_pr_merge_time_h"] = avg_merge_time

    # ─────────────────────────────────────────────────────────────────────────
    # Team-level metrics
    # ─────────────────────────────────────────────────────────────────────────
    team_metrics = {
        "total_commits": len(commits),
        "total_prs": len(prs),
        "total_developers": len(developers),
        "total_additions": sum(m["total_additions"] for m in developer_metrics.values()),
        "total_deletions": sum(m["total_deletions"] for m in developer_metrics.values()),
        "avg_commit_size_lines": 0,
        "avg_pr_review_time_h": 0,
        "code_churn_ratio": 0.0,
    }

    if commits:
        total_lines = team_metrics["total_additions"] + team_metrics["total_deletions"]
        team_metrics["avg_commit_size_lines"] = total_lines / len(commits)

    if prs:
        merge_times = [p.get("time_to_merge_h", 0) for p in prs if p.get("time_to_merge_h", 0) > 0]
        if merge_times:
            team_metrics["avg_pr_review_time_h"] = sum(merge_times) / len(merge_times)

    if team_metrics["total_additions"] > 0:
        team_metrics["code_churn_ratio"] = (
            team_metrics["total_deletions"] / team_metrics["total_additions"]
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Detect anomalies
    # ─────────────────────────────────────────────────────────────────────────
    anomalies = []

    # ANOMALY 1: Burnout Risk
    # Heuristic: >15 commits/week + avg >4h/PR review time suggests overwork
    for login, metrics in developer_metrics.items():
        if metrics["commit_count"] > 15 and metrics["avg_pr_merge_time_h"] > 4:
            anomalies.append({
                "type": "burnout_risk",
                "developer_login": login,
                "severity": "high",
                "score": min(100, 50 + metrics["commit_count"] * 2),
                "reason": f"High commit count ({metrics['commit_count']}) + slow PRs ({metrics['avg_pr_merge_time_h']:.1f}h avg)",
                "metric": {
                    "commit_count": metrics["commit_count"],
                    "avg_pr_merge_time_h": metrics["avg_pr_merge_time_h"],
                }
            })

    # ANOMALY 2: High Code Churn
    # Heuristic: PR with deletions > additions * 2 suggests refactoring or cleanup
    for pr in prs:
        deletions = pr.get("deletions", 0)
        additions = pr.get("additions", 0)
        if additions > 0 and deletions > additions * 2:
            anomalies.append({
                "type": "high_churn",
                "developer_login": pr.get("author_login", "unknown"),
                "pr_id": pr.get("github_pr_id"),
                "severity": "medium",
                "score": min(100, 30 + (deletions / max(1, additions)) * 10),
                "reason": f"High churn ratio: {deletions} deletions vs {additions} additions",
                "metric": {
                    "additions": additions,
                    "deletions": deletions,
                    "churn_ratio": deletions / max(1, additions),
                }
            })

    # ANOMALY 3: Slow Review Cycle
    # Heuristic: PR takes >72h to merge
    for pr in prs:
        merge_time = pr.get("time_to_merge_h", 0)
        if merge_time > 72:
            anomalies.append({
                "type": "slow_review",
                "pr_id": pr.get("github_pr_id"),
                "developer_login": pr.get("author_login", "unknown"),
                "severity": "medium",
                "score": min(100, 40 + (merge_time / 24)),  # Score increases with days
                "reason": f"Slow review cycle: {merge_time:.1f}h to merge (>72h threshold)",
                "metric": {
                    "time_to_merge_h": merge_time,
                }
            })

    print(
        f"[Analyst] Computed metrics for {len(developer_metrics)} developers. "
        f"Flagged {len(anomalies)} anomalies."
    )

    return {
        "developer_metrics": dict(developer_metrics),
        "team_metrics": team_metrics,
        "anomalies": anomalies,
    }
