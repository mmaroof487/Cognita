"""
TenantSettings model — per-tenant notification and analysis configuration.
Stores Slack webhook, SMTP credentials, and analysis window preferences.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import BaseModel


class TenantSettings(BaseModel):
    """
    TenantSettings stores tenant-specific configuration.
    - All URL/credential fields are encrypted at app layer (Fernet)
    - Fields are nullable to allow disabling notification channels
    - analysis_window_days: default 7, can be 14 or 30
    """
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    analysis_window_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        nullable=False,
        comment="Analysis window: 7, 14, or 30 days"
    )

    slack_webhook_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Encrypted Slack webhook URL; null = disabled"
    )

    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)

    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    smtp_user: Mapped[str | None] = mapped_column(String(255), nullable=True)

    smtp_password: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Encrypted SMTP password"
    )

    notification_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    jira_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    jira_api_user: Mapped[str | None] = mapped_column(String(255), nullable=True)

    jira_api_token: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Encrypted Jira API token"
    )

    jira_project_key: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Jira project key for ticket creation"
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="settings")

    __table_args__ = (
        Index("idx_tenant_settings_tenant", "tenant_id"),
    )
