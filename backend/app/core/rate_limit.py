"""
Rate limiting — Redis sliding window per tenant.
"""

import redis
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import time
from app.config import settings


class RateLimiter:
    """Redis-based sliding window rate limiter."""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def is_allowed(self, tenant_id: str, limit: int, window_seconds: int = 60) -> bool:
        """
        Check if a request from tenant is allowed.
        Uses sliding window algorithm.

        Args:
            tenant_id: Tenant identifier
            limit: Max requests in window
            window_seconds: Time window (default 60s)

        Returns:
            True if allowed, False if rate limited
        """
        key = f"rl:{tenant_id}"
        now = time.time()
        window_start = now - window_seconds

        try:
            # Remove old entries outside the window
            self.redis.zremrangebyscore(key, 0, window_start)

            # Count requests in the window
            count = self.redis.zcard(key)

            if count < limit:
                # Add this request
                self.redis.zadd(key, {str(now): now})
                self.redis.expire(key, window_seconds + 1)
                return True
            else:
                return False
        except Exception as e:
            # On error, allow the request (fail open)
            print(f"Rate limiter error: {e}")
            return True

    def get_remaining(self, tenant_id: str, limit: int, window_seconds: int = 60) -> int:
        """Get remaining requests for tenant."""
        key = f"rl:{tenant_id}"
        now = time.time()
        window_start = now - window_seconds

        try:
            self.redis.zremrangebyscore(key, 0, window_start)
            count = self.redis.zcard(key)
            return max(0, limit - count)
        except Exception:
            return limit


# Global rate limiter instance
rate_limiter = RateLimiter(settings.redis_url)


async def check_rate_limit(tenant_id: str, limit: int) -> tuple[bool, int]:
    """
    Check rate limit and return (allowed, remaining).
    Raises HTTP 429 if rate limited.
    """
    allowed = await rate_limiter.is_allowed(tenant_id, limit)
    remaining = rate_limiter.get_remaining(tenant_id, limit)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            }
        )

    return allowed, remaining
