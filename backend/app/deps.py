from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis
from typing import AsyncGenerator

from app.database import get_async_session as get_db
from app.core.security import decode_token
from app.core.rate_limit import check_rate_limit
from app.models import User, Tenant
from app.config import settings

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.from_url(settings.redis_url)
    try:
        yield client
    finally:
        await client.aclose() if hasattr(client, 'aclose') else await client.close()

security = HTTPBearer()

async def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = auth.credentials
    try:
        payload = decode_token(token)
    except HTTPException as e:
        raise e
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID"
        )
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found"
        )
    stmt = select(Tenant).where(Tenant.id == user.tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found"
        )
    return tenant

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

async def rate_limit_check(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    redis_client: redis.Redis = Depends(get_redis)
):
    # Fallback to rate_limit_default since tenant.plan logic is not strictly defined in model
    # Or assume tenant has a rate_limit_per_min column
    limit = getattr(tenant, "rate_limit_per_min", settings.rate_limit_default)
    remaining, reset_in = await check_rate_limit(
        tenant_id=str(tenant.id),
        limit=limit,
        redis_client=redis_client
    )
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_reset = reset_in
    request.state.rate_limit_limit = limit
