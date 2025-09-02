
from __future__ import annotations
import json, asyncio
from typing import Any, Dict
try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

class _NullCache:
    def __init__(self): self._m: Dict[str, Any] = {}
    async def get_json(self, key: str):
        return self._m.get(key)
    async def set_json(self, key: str, value: Any):
        self._m[key] = value

class _Limiter:
    def __init__(self, rps: int = 1): self._sem = asyncio.Semaphore(rps)
    async def acquire(self):
        # simple cooperative throttle
        await asyncio.sleep(0)

class AuthorityContext:
    def __init__(self, name: str, base_url: str, rps: int = 1, burst: int = 1, cache_ttl: int = 3600):
        self.name = name
        self.base_url = base_url
        self.cache = _NullCache()
        self.limiter = _Limiter(rps=rps)
        self.http = httpx.AsyncClient() if httpx else None

def canonical_query_key(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",",":"))
