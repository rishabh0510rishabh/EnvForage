
# --- Distributed Caching Abstraction ---
import json
import random
import logging
from typing import Any, Optional, Callable
from datetime import timedelta

logger = logging.getLogger("CacheService")

class CacheService:
    """
    A robust distributed caching service that attempts to use Redis, 
    but falls back transparently to an in-memory dictionary if Redis is unavailable.
    Includes cache stampede protection via TTL jitter.
    """
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._memory_fallback: dict[str, dict] = {}
        import time
        self.time = time

    def _get_jittered_ttl(self, ttl_seconds: int) -> int:
        """Adds +/- 10% jitter to TTL to prevent cache stampedes."""
        jitter = random.uniform(0.9, 1.1)
        return int(ttl_seconds * jitter)

    async def get(self, key: str) -> Optional[Any]:
        if self.redis:
            try:
                val = await self.redis.get(key)
                return json.loads(val) if val else None
            except Exception as e:
                logger.warning(f"Redis get failed for {key}: {e}. Falling back to memory.")
                
        # Memory fallback
        if key in self._memory_fallback:
            item = self._memory_fallback[key]
            if item["expires_at"] is None or item["expires_at"] > self.time.time():
                return item["value"]
            else:
                del self._memory_fallback[key]
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        jittered_ttl = self._get_jittered_ttl(ttl_seconds)
        if self.redis:
            try:
                await self.redis.set(key, json.dumps(value), ex=jittered_ttl)
                return
            except Exception as e:
                logger.warning(f"Redis set failed for {key}: {e}. Falling back to memory.")

        # Memory fallback
        self._memory_fallback[key] = {
            "value": value,
            "expires_at": self.time.time() + jittered_ttl
        }

    async def delete(self, key: str):
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception:
                pass
        if key in self._memory_fallback:
            del self._memory_fallback[key]

    async def get_or_set(self, key: str, fetch_func: Callable, ttl_seconds: int = 3600) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
            
        logger.debug(f"Cache miss for {key}, executing fetch func.")
        import asyncio
        if asyncio.iscoroutinefunction(fetch_func):
            fresh_data = await fetch_func()
        else:
            fresh_data = fetch_func()
            
        await self.set(key, fresh_data, ttl_seconds)
        return fresh_data
