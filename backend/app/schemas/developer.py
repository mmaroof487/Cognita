from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class DeveloperRead(BaseModel):
    id: UUID
    tenant_id: UUID
    org_id: UUID
    github_id: int
    github_login: str

class DeveloperMetrics(BaseModel):
    developer_id: str
    commit_count: int
    after_hours_ratio: float
    high_churn_count: int
    avg_merge_h: Optional[float]
    health_score: float
