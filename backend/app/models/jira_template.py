"""
JiraTemplate model — template for Jira tickets created by the ActionAgent.
Three templates: one per anomaly type (burnout_risk, high_churn, slow_review).
"""

from sqlalchemy import Column, String, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.models.base import BaseModel


class JiraTemplate(BaseModel):
    """
    A JiraTemplate defines how to structure a Jira ticket for a specific anomaly.
    - summary_template and description_template use {placeholder} syntax
    - Seeded with 3 default templates on migration
    - Can be customized per tenant
    """
    __tablename__ = "jira_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    anomaly_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="burnout_risk | high_churn | slow_review"
    )

    summary_template: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Template with {developer_login}, {metric} placeholders"
    )

    description_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Longer template with same placeholders"
    )

    issue_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Task",
        comment="Jira issue type: Task, Bug, Story"
    )

    priority_default: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Medium",
        comment="High, Medium, Low"
    )

    labels: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Default labels: ['devpulse', 'engineering-health', ...]"
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="jira_templates")

    __table_args__ = (
        Index("idx_jira_templates_tenant", "tenant_id"),
        Index("idx_jira_templates_type", "anomaly_type"),
    )
