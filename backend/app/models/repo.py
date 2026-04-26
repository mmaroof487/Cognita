"""
Repo model — represents a GitHub repository.
"""

from sqlalchemy import Column, String, Boolean, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.base import BaseModel


class Repo(BaseModel):
    """
    A Repo represents a GitHub repository being tracked.
    - tracked: boolean to enable/disable analysis without deleting
    - last_synced_at: timestamp of last commit/PR sync
    """
    __tablename__ = "repos"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
    )

    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="owner/repo format"
    )

    private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tracked: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="If false, this repo is skipped in analysis"
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="repos")
    org = relationship("Org", back_populates="repos")
    commit_events = relationship("CommitEvent", back_populates="repo", cascade="all, delete-orphan")
    pr_events = relationship("PrEvent", back_populates="repo", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_repos_tenant", "tenant_id"),
        Index("idx_repos_org", "org_id"),
        UniqueConstraint("tenant_id", "github_id", name="uq_repos_tenant_github_id"),
    )
