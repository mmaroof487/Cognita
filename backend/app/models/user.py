"""
User model — authenticated users within a tenant.
Stores GitHub OAuth credentials and tenant role.
"""

from sqlalchemy import Column, String, BigInteger, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import BaseModel


class User(BaseModel):
    """
    A User is a GitHub user authenticated via OAuth within a tenant.
    - Stores encrypted GitHub access token for ingest operations
    - Role determines permissions (owner, admin, member)
    """
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    github_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        comment="GitHub user ID"
    )

    github_login: Mapped[str] = mapped_column(String(255), nullable=False)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="member",
        comment="owner | admin | member"
    )

    access_token: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Encrypted GitHub personal access token (PAT)"
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    __table_args__ = (
        Index("idx_users_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "github_id", name="uq_users_tenant_github_id"),
    )
