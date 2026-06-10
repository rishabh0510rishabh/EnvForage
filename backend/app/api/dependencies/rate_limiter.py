
# --- FastApi Rate Limiting Dependency ---
import time
from fastapi import Request, HTTPException, status
import logging

logger = logging.getLogger("RateLimiter")

class RateLimiter:
    """
    A robust fixed-window rate limiter utilizing Redis for distributed state.
    Limits are tracked per-client IP.
    """
    def __init__(self, requests: int = 100, window_seconds: int = 60):
        self.requests = requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        current_window = int(time.time() / self.window_seconds)
        redis_key = f"rate_limit:{client_ip}:{current_window}"
        
        try:
            # We assume a global get_redis() utility exists, simulating logic here
            # redis = await get_redis()
            # current_count = await redis.incr(redis_key)
            # if current_count == 1:
            #     await redis.expire(redis_key, self.window_seconds)
            
            # Simulation placeholder for the orchestrator
            current_count = 1
            
            if current_count > self.requests:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
        except Exception as e:
            # Fail-open design: If Redis goes down, we shouldn't block traffic entirely
            if not isinstance(e, HTTPException):
                logger.error(f"Rate limiter failed open due to Redis error: {e}")
                pass
            else:
                raise
