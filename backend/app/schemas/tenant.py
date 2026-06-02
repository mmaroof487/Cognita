from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class TenantSettingsUpdate(BaseModel):
    analysis_window_days: Optional[int] = None
    slack_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notification_email: Optional[str] = None

class TenantSettingsRead(BaseModel):
    tenant_id: UUID
    analysis_window_days: int
    slack_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    notification_email: Optional[str] = None

class TenantRead(BaseModel):
    id: UUID
    name: str
    plan: str
    rate_limit_per_min: int
