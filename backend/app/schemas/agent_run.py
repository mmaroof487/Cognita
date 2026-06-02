from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class AgentRunCreate(BaseModel):
    triggered_by: str

class AgentRunRead(BaseModel):
    id: UUID
    tenant_id: UUID
    org_id: UUID
    thread_id: str
    status: str
    triggered_by: str
    started_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str] = None
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    cost_usd: Optional[float]
