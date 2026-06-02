from fastapi import HTTPException
import time
import redis.asyncio as redis

async def check_rate_limit(tenant_id: str, limit: int, redis_client: redis.Redis) -> tuple[int, int]:
    key = f"rl:{tenant_id}"
    now = int(time.time())
    window = 60

    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, now - window)
        # To ensure uniqueness in sorted set for the same second, append a random component
        import random
        member = f"{now}_{random.randint(0, 9999)}"
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()
    
    count = results[2]
    
    if count > limit:
        oldest_entries = await redis_client.zrange(key, 0, 0, withscores=True)
        if oldest_entries:
            reset_in_seconds = window - (now - int(oldest_entries[0][1]))
        else:
            reset_in_seconds = window
            
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(reset_in_seconds),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0"
            }
        )
    
    remaining = limit - count
    reset_in_seconds = window
    return remaining, reset_in_seconds
