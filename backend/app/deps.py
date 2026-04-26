"""
FastAPI dependencies for injection across endpoints.
Provides: current_user, current_tenant, db session, etc.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_async_session
from app.core.security import verify_token
from app.models import User, Tenant


async def get_current_user(
    token: str = Depends(lambda: None),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """
    Extract and verify JWT token, return current User.

    NOTE: Token extraction from headers is done by the endpoints themselves
    (via Bearer token parsing). This dependency expects the token to be passed.

    For now, we'll implement this as a placeholder that will be wired into
    the auth endpoints.
    """
    # This will be fully implemented in auth.py endpoint
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
) -> Tenant:
    """Get current tenant from authenticated user."""
    if not current_user.tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found"
        )
    return current_user.tenant


async def verify_tenant_access(
    session: AsyncSession = Depends(get_async_session),
) -> str:
    """
    Dependency that returns tenant_id after verifying access.
    Used by endpoints that need tenant isolation.

    NOTE: Application-layer RLS via tenant_id filtering in all queries.
    See deps.py header: "RLS considered, rejected for v1 complexity/test overhead"
    """
    # Will be implemented to extract tenant_id from token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )
