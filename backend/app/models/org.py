"""
Org model — represents a GitHub organization.
Sits between Tenant and Repo: 1 tenant -> many orgs -> many repos.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.base import BaseModel


class Org(BaseModel):
    """
    An Org represents a GitHub organization tracked by the tenant.
    - Multiple orgs per tenant enable cross-org analytics
    - last_synced_at tracks when repos/developers were last synced
    """
    __tablename__ = "orgs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    github_org: Mapped[str] = mapped_column(String(255), nullable=False)

    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time repos/developers were synced from GitHub"
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="orgs")
    repos = relationship("Repo", back_populates="org", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_orgs_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "github_org", name="uq_orgs_tenant_github_org"),
    )
