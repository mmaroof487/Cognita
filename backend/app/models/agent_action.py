"""
AgentAction model — represents an action queued by the agent for human approval.
HITL (Human-In-The-Loop) gate for critical operations (Jira, Slack, email).
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from app.models.base import BaseModel


class AgentAction(BaseModel):
    """
    An AgentAction represents a proposed action by the agent.
    - Status is pending until human approves/rejects
    - payload contains action-specific data (Jira fields, Slack message, etc.)
    """
    __tablename__ = "agent_actions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    insight_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("insights.id", ondelete="SET NULL"),
        nullable=True,
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="create_jira | send_slack | send_email | escalate"
    )

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="pending | approved | rejected | executed | failed"
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Error message if execution failed")

    # Relationships
    tenant = relationship("Tenant", back_populates="agent_actions")
    agent_run = relationship("AgentRun", back_populates="actions")
    insight = relationship("Insight", back_populates="actions")

    __table_args__ = (
        Index("idx_agent_actions_tenant", "tenant_id"),
        Index("idx_agent_actions_status", "status"),
        Index("idx_agent_actions_reviewed", "reviewed_by"),
    )
