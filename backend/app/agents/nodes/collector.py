"""
Collector Agent Node — Reads GitHub data from database and emits normalized events.

Pure deterministic logic (no LLM). Fetches commits, PRs, and developers
for the analysis window from the database and populates DevPulseState.
"""

from datetime import datetime
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.commit_event import CommitEvent
from app.models.pr_event import PrEvent
from app.models.developer import Developer
from app.agents.state import DevPulseState


async def collector_node(state: DevPulseState, session: AsyncSession) -> dict:
    """
    Collector node: Read commits, PRs, and developers from database.

    Args:
        state: Current DevPulseState with tenant_id, org_id, window_start, window_end
        session: Async database session

    Returns:
        Dict with commits, prs, developers to update state
    """
    tenant_id = state.get("tenant_id")
    org_id = state.get("org_id")
    window_start = state.get("window_start")
    window_end = state.get("window_end")

    if not all([tenant_id, org_id, window_start, window_end]):
        raise ValueError("Missing required state parameters: tenant_id, org_id, window_start, window_end")

    # ─────────────────────────────────────────────────────────────────────────
    # Fetch Commits
    # ─────────────────────────────────────────────────────────────────────────
    commits_query = select(CommitEvent).where(
        CommitEvent.tenant_id == tenant_id,
        CommitEvent.repo.has(org_id=org_id),
        CommitEvent.committed_at >= window_start,
        CommitEvent.committed_at <= window_end,
    )
    commits_result = await session.execute(commits_query)
    commit_rows = commits_result.scalars().all()

    commits = [
        {
            "sha": c.sha,
            "message": c.message,
            "author_login": c.developer.github_login if c.developer else "unknown",
            "additions": c.additions,
            "deletions": c.deletions,
            "files_changed": c.files_changed,
            "committed_at": c.committed_at.isoformat(),
            "ingested_at": c.ingested_at.isoformat(),
        }
        for c in commit_rows
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # Fetch Pull Requests
    # ─────────────────────────────────────────────────────────────────────────
    prs_query = select(PrEvent).where(
        PrEvent.tenant_id == tenant_id,
        PrEvent.repo.has(org_id=org_id),
        PrEvent.created_at >= window_start,
        PrEvent.created_at <= window_end,
    )
    prs_result = await session.execute(prs_query)
    pr_rows = prs_result.scalars().all()

    prs = [
        {
            "github_pr_id": p.github_pr_id,
            "title": p.title,
            "state": p.state,
            "author_login": p.author.github_login if p.author else "unknown",
            "additions": p.additions,
            "deletions": p.deletions,
            "review_comments": p.review_comments,
            "time_to_merge_h": p.time_to_merge_h if p.time_to_merge_h is not None else 0,
            "created_at": p.created_at.isoformat(),
            "merged_at": p.merged_at.isoformat() if p.merged_at else None,
        }
        for p in pr_rows
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # Fetch Developers (for context)
    # ─────────────────────────────────────────────────────────────────────────
    developers_query = select(Developer).where(
        Developer.tenant_id == tenant_id,
    )
    developers_result = await session.execute(developers_query)
    developer_rows = developers_result.scalars().all()

    developers = [
        {
            "github_login": d.github_login,
            "name": d.name or d.github_login,
            "avatar_url": d.avatar_url,
        }
        for d in developer_rows
    ]

    print(
        f"[Collector] Collected {len(commits)} commits, {len(prs)} PRs, "
        f"{len(developers)} developers for tenant={tenant_id}, org={org_id}"
    )

    return {
        "commits": commits,
        "prs": prs,
        "developers": developers,
    }
