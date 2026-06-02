from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ActionRead(BaseModel):
    id: UUID
    tenant_id: UUID
    agent_run_id: UUID
    insight_id: Optional[UUID] = None
    action_type: str
    status: str
    payload: dict
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    error: Optional[str] = None
    rejection_reason: Optional[str] = None

class ApproveRequest(BaseModel):
    reason: Optional[str] = None

class RejectRequest(BaseModel):
    reason: str
