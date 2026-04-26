"""
AuditLog model — immutable append-only log of all significant events.
Used for compliance, debugging, and understanding system behavior.
"""

from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid


class AuditLog:
    """
    AuditLog is NOT a BaseModel (no id/created_at/updated_at).
    It uses auto-increment id and immutable write-only semantics.

    Implemented via raw table without ORM mapping to enforce immutability
    and use Postgres native type system for performance.

    Table definition:
        CREATE TABLE audit_log (
            id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id UUID,
            diff JSONB,
            ts TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
        CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;

    Usage example:
        session.add(AuditLog(
            tenant_id=tenant_id,
            actor="agent:analyst",
            action="insights.created",
            entity_type="insight",
            entity_id=insight_id,
            diff={"count": 5, "severity": "critical"}
        ))
        await session.commit()
    """
    pass


# The AuditLog will be created via Alembic migration as raw SQL to ensure immutability.
# ORM models above can reference it, but writes should go directly to the table via raw SQL.
