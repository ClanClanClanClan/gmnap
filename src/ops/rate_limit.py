from __future__ import annotations
import time, os
from typing import Dict

try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None


class TokenBucket:
    def __init__(self, capacity: int, refill_per_sec: float):
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self.tokens = capacity
        self.last = time.time()

    def allow(self, cost: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last
        self.last = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class RateLimiter:
    def __init__(self, rpm_free: int = 60, rpm_paid: int = 10000):
        self._buckets: Dict[str, TokenBucket] = {}
        self.rps_free = rpm_free / 60.0
        self.rps_paid = rpm_paid / 60.0
        self.redis = None
        if aioredis and os.getenv("REDIS_URL"):
            try:
                self.redis = aioredis.from_url(os.getenv("REDIS_URL"))
            except Exception:
                self.redis = None

    def _bucket_for(self, key: str, paid: bool) -> TokenBucket:
        rps = self.rps_paid if paid else self.rps_free
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(capacity=int(rps * 2), refill_per_sec=rps)
        return self._buckets[key]

    async def allow(self, key: str, paid: bool, cost: int = 1) -> bool:
        if self.redis is None:
            return self._bucket_for(key, paid).allow(cost=cost)
        # Redis token bucket (approximate): use INCR with TTL window
        window = 60
        now = int(time.time())
        slot = now - (now % window)
        k = f"rl:{'paid' if paid else 'free'}:{key}:{slot}"
        try:
            cnt = await self.redis.incr(k)
            if cnt == 1:
                await self.redis.expire(k, window)
            limit = (self.rps_paid if paid else self.rps_free) * window
            return cnt <= limit
        except Exception:
            # Fallback to local
            return self._bucket_for(key, paid).allow(cost=cost)
