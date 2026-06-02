from typing import Annotated, TypedDict
from datetime import datetime
import operator

class DevMetrics(TypedDict):
    developer_id: str
    commit_count: int
    after_hours_ratio: float
    high_churn_count: int
    avg_merge_h: float | None
    health_score: float

class Anomaly(TypedDict):
    type: str          # burnout_risk | high_churn | slow_review
    developer_id: str
    detail: str
    severity: str      # info | warning | critical

class AxonState(TypedDict):
    # Input
    tenant_id: str
    org_id: str
    agent_run_id: str
    window_start: datetime
    window_end: datetime
    analysis_window_days: int

    # Collector output
    commits: list[dict]
    prs: list[dict]
    developers: list[dict]
    repos: list[dict]

    # Analyst output
    developer_metrics: dict[str, DevMetrics]
    team_metrics: dict
    anomalies: list[Anomaly]

    # Insight output
    insights: Annotated[list[dict], operator.add]

    # Action output
    actions_queued: Annotated[list[dict], operator.add]

    # Control
    retry_count: int
    errors: Annotated[list[str], operator.add]
    tokens_in: int
    tokens_out: int
    cost_usd: float
