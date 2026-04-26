"""
AgentRun model — represents a single LangGraph agent execution.
Tracks status, token usage, cost, and checkpointing.
"""

from sqlalchemy import Column, String, Integer, DateTime, Numeric, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.base import BaseModel


class AgentRun(BaseModel):
    """
    An AgentRun represents one execution of the LangGraph agent.
    - thread_id is the LangGraph checkpoint thread identifier
    - Status tracks the run lifecycle
    """
    __tablename__ = "agent_runs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="LangGraph checkpoint thread_id"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="running",
        comment="running | completed | failed | awaiting_human"
    )

    triggered_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="schedule",
        comment="schedule | manual | webhook"
    )

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)

    cost_usd: Mapped[float | None] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=True,
        comment="Cost in USD (based on token usage)"
    )

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="agent_runs")
    insights = relationship("Insight", back_populates="agent_run", cascade="all, delete-orphan")
    actions = relationship("AgentAction", back_populates="agent_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_agent_runs_tenant_started", "tenant_id", "started_at"),
        Index("idx_agent_runs_status", "status"),
    )
