from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.schemas.auth import TokenResponse, RefreshRequest
from app.core.security import create_access_token, create_refresh_token, fernet_encrypt, decode_token
from app.config import settings
from app.database import get_async_session as get_db
from app.models import Tenant, TenantSettings, User
from app.providers.github import GitHubProvider
import redis.asyncio as redis
from app.deps import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/github")
async def github_login():
    url = f"https://github.com/login/oauth/authorize?client_id={settings.github_client_id}&scope=repo user"
    return RedirectResponse(url)

@router.get("/github/callback", response_model=TokenResponse)
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code
            },
            headers={"Accept": "application/json"}
        )
        data = res.json()
        access_token = data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Could not get access token")
            
    gh = GitHubProvider(access_token)
    user_info = await gh.get_user_info(access_token)
    
    github_id = user_info["id"]
    github_login = user_info["login"]
    email = user_info.get("email", f"{github_login}@users.noreply.github.com")
    
    stmt = select(User).where(User.github_id == github_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        tenant_id = uuid.uuid4()
        new_tenant = Tenant(
            id=tenant_id,
            name=f"{github_login}'s Organization",
            plan="free",
            rate_limit_per_min=60
        )
        db.add(new_tenant)
        
        new_settings = TenantSettings(
            tenant_id=tenant_id,
            analysis_window_days=7
        )
        db.add(new_settings)
        
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            github_id=github_id,
            github_login=github_login,
            email=email,
            role="owner",
            access_token=fernet_encrypt(access_token)
        )
        db.add(user)
    else:
        user.access_token = fernet_encrypt(access_token)
        
    await db.commit()
    
    token_data = {"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, redis_client: redis.Redis = Depends(get_redis)):
    try:
        payload = decode_token(req.refresh_token)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    jti = payload.get("jti", req.refresh_token[-20:])
    if await redis_client.get(f"refresh_blacklist:{jti}"):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
        
    token_data = {"sub": payload.get("sub"), "tenant_id": payload.get("tenant_id"), "role": payload.get("role")}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )

@router.delete("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: RefreshRequest, redis_client: redis.Redis = Depends(get_redis)):
    try:
        payload = decode_token(req.refresh_token)
    except HTTPException:
        return
        
    jti = payload.get("jti", req.refresh_token[-20:])
    exp = payload.get("exp", 0)
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = max(0, exp - now)
    
    if ttl > 0:
        await redis_client.setex(f"refresh_blacklist:{jti}", ttl, "1")
