"""
LangGraph agent state definition.
Shared state passed through all agent nodes.
"""

from typing import Annotated, TypedDict, Optional
from datetime import datetime
import operator


class DevPulseState(TypedDict):
    """
    State schema for the LangGraph StateGraph.
    Passed through: Collector -> Analyst -> Insight -> Action nodes.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Input Parameters (set when triggering agent)
    # ─────────────────────────────────────────────────────────────────────────
    tenant_id: str
    org_id: str
    window_start: datetime
    window_end: datetime
    agent_run_id: str

    # ─────────────────────────────────────────────────────────────────────────
    # Collector Output (normalized events from DB)
    # ─────────────────────────────────────────────────────────────────────────
    commits: list[dict]      # List of commit events
    prs: list[dict]          # List of PR events
    developers: list[dict]   # Developer metadata

    # ─────────────────────────────────────────────────────────────────────────
    # Analyst Output (metrics and anomalies)
    # ─────────────────────────────────────────────────────────────────────────
    developer_metrics: dict  # {github_login: MetricsDict}
    team_metrics: dict       # Aggregate stats
    anomalies: list[dict]    # Flagged issues

    # ─────────────────────────────────────────────────────────────────────────
    # Insight Output (human-readable findings — accumulates)
    # ─────────────────────────────────────────────────────────────────────────
    insights: Annotated[list[dict], operator.add]

    # ─────────────────────────────────────────────────────────────────────────
    # Action Output (queued actions for HITL gate — accumulates)
    # ─────────────────────────────────────────────────────────────────────────
    actions_queued: Annotated[list[dict], operator.add]

    # ─────────────────────────────────────────────────────────────────────────
    # Control Fields
    # ─────────────────────────────────────────────────────────────────────────
    retry_count: int                         # For insight retry logic
    errors: Annotated[list[str], operator.add]  # Error accumulation
    tokens_used: int                         # Total LLM tokens consumed
    cost_usd: float                          # Total cost in USD
