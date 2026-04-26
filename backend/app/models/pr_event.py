"""
PrEvent model — normalized GitHub pull request data.
"""

from sqlalchemy import Column, String, Integer, DateTime, BigInteger, ForeignKey, Index, UniqueConstraint, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.base import BaseModel


class PrEvent(BaseModel):
    """
    A PrEvent represents a single pull request normalized from GitHub.
    - Includes metrics for review cycle time and complexity
    """
    __tablename__ = "pr_events"

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

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
    )

    github_pr_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="open | closed | merged"
    )

    additions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    deletions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    review_comments: Mapped[int | None] = mapped_column(Integer, nullable=True)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    time_to_merge_h: Mapped[float | None] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Hours from open to merge (computed on insert)"
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id], viewonly=True)
    repo = relationship("Repo", back_populates="pr_events")
    author = relationship("Developer", back_populates="pr_events", foreign_keys=[author_id])

    __table_args__ = (
        Index("idx_prs_tenant", "tenant_id"),
        Index("idx_prs_repo", "repo_id"),
        Index("idx_prs_author", "author_id"),
        UniqueConstraint("tenant_id", "github_pr_id", name="uq_prs_tenant_github_id"),
    )
