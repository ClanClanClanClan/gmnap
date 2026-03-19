
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
        if httpx:
            self.http = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
                headers={"User-Agent": "GMNAP/7.0 (mailto:gmnap@example.com)"},
            )
        else:
            self.http = None

    async def close(self):
        if self.http:
            await self.http.aclose()

def canonical_query_key(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",",":"))
