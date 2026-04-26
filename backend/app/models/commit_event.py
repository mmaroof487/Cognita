"""
CommitEvent model — normalized GitHub commit data.
Stores raw commit metrics for analysis.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.base import BaseModel


class CommitEvent(BaseModel):
    """
    A CommitEvent represents a single commit normalized from GitHub.
    - Ingested during the Collector agent node
    - TimescaleDB can compress these time-series events
    """
    __tablename__ = "commit_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repos.id", ondelete="CASCADE"),
        nullable=False,
    )

    developer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
    )

    sha: Mapped[str] = mapped_column(String(40), nullable=False, comment="Git commit SHA")

    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    files_changed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When commit was created (GitHub timestamp)"
    )

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=lambda: datetime.now(datetime.UTC),
        nullable=False,
        comment="When DevPulse ingested this event"
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id], viewonly=True)
    repo = relationship("Repo", back_populates="commit_events")
    developer = relationship("Developer", back_populates="commit_events")

    __table_args__ = (
        Index("idx_commits_developer_time", "developer_id", "committed_at"),
        Index("idx_commits_tenant", "tenant_id"),
        Index("idx_commits_repo", "repo_id"),
        UniqueConstraint("tenant_id", "sha", name="uq_commits_tenant_sha"),
    )
