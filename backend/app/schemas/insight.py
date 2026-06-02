from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class InsightRead(BaseModel):
    id: UUID
    tenant_id: UUID
    agent_run_id: UUID
    developer_id: Optional[UUID] = None
    insight_type: str
    title: str
    body: str
    severity: str
    score: Optional[float] = None
    meta_data: Optional[dict] = None
    created_at: datetime
