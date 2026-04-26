"""
Developer model — represents a contributor tracked within a tenant.
Developers emerge from commit authors during ingest operations.
"""

from sqlalchemy import Column, String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import BaseModel


class Developer(BaseModel):
    """
    A Developer is a GitHub user whose commits are tracked within a tenant.
    - github_login is the unique identifier
    - Developers are upserted during commit ingest
    - name and avatar_url are optional, synced from GitHub
    """
    __tablename__ = "developers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    github_login: Mapped[str] = mapped_column(String(255), nullable=False)

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="developers")
    commit_events = relationship("CommitEvent", back_populates="developer", cascade="all, delete-orphan")
    pr_events = relationship("PrEvent", back_populates="author", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="developer")

    __table_args__ = (
        Index("idx_developers_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "github_login", name="uq_developers_tenant_login"),
    )
