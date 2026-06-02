from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class OrgCreate(BaseModel):
    name: str

class OrgRead(BaseModel):
    id: UUID
    tenant_id: UUID
    github_org: str
    display_name: str | None = None
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
