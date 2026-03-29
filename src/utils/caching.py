from __future__ import annotations

import os
import time
from typing import Optional

try:
    import redis  # type: ignore
except Exception:
    redis = None


class Cache:
    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def setex(self, key: str, ttl_sec: int, value: str) -> None:
        raise NotImplementedError


class InMemoryCache(Cache):
    def __init__(self):
        self.store = {}

    def get(self, key: str) -> Optional[str]:
        item = self.store.get(key)
        if not item:
            return None
        expires, value = item
        if expires and time.time() > expires:
            self.store.pop(key, None)
            return None
        return value

    def setex(self, key: str, ttl_sec: int, value: str) -> None:
        self.store[key] = (time.time() + ttl_sec, value)


class RedisCache(Cache):
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "")
        self.client = None
        if redis and self.url:
            try:
                self.client = redis.Redis.from_url(self.url, decode_responses=True)
                # test
                self.client.ping()
            except Exception:
                self.client = None

    def get(self, key: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            return self.client.get(key)
        except Exception:
            return None

    def setex(self, key: str, ttl_sec: int, value: str) -> None:
        if not self.client:
            return
        try:
            self.client.setex(key, ttl_sec, value)
        except Exception:
            pass


def build_cache() -> Cache:
    if os.getenv("OFFLINE") == "1":
        return InMemoryCache()
    c = RedisCache()
    return c if c.client else InMemoryCache()
