"""
Tenant model — represents a multi-tenant customer.
Each tenant is isolated by tenant_id in all queries (application-layer RLS).
"""

from sqlalchemy import Column, String, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import BaseModel


class Tenant(BaseModel):
    """
    A Tenant represents a GitHub organization using DevPulse.

    NOTE: Row-level security is implemented at the application layer via tenant_id
    filtering in all queries, NOT via Postgres RLS. This simplifies testing and
    migrations while maintaining security.
    """
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_org: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free",
        comment="free | pro | enterprise"
    )
    rate_limit_per_min: Mapped[int] = mapped_column(
        default=60,
        nullable=False,
        comment="Override default rate limit per minute"
    )

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    orgs = relationship("Org", back_populates="tenant", cascade="all, delete-orphan")
    repos = relationship("Repo", back_populates="tenant", cascade="all, delete-orphan")
    developers = relationship("Developer", back_populates="tenant", cascade="all, delete-orphan")
    settings = relationship("TenantSettings", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    jira_templates = relationship("JiraTemplate", back_populates="tenant", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="tenant", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="tenant", cascade="all, delete-orphan")
    agent_actions = relationship("AgentAction", back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tenants_plan", "plan"),
    )
