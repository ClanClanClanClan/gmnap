from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None


class _NullCache:
    def __init__(self):
        self._m: Dict[str, Any] = {}

    async def get_json(self, key: str):
        return self._m.get(key)

    async def set_json(self, key: str, value: Any):
        self._m[key] = value


class _Limiter:
    def __init__(self, rps: int = 1):
        self._sem = asyncio.Semaphore(rps)

    async def acquire(self):
        # simple cooperative throttle
        await asyncio.sleep(0)


class AuthorityContext:
    def __init__(
        self,
        name: str,
        base_url: str,
        rps: int = 1,
        burst: int = 1,
        cache_ttl: int = 3600,
    ):
        self.name = name
        self.base_url = base_url
        self.cache = _NullCache()
        self.limiter = _Limiter(rps=rps)
        self.http = httpx.AsyncClient() if httpx else None


def canonical_query_key(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Transient-error retry helper (used by every authority adapter)
# ---------------------------------------------------------------------------


# Errors we treat as transient — worth backing off and retrying.
# Anything else (ValueError, KeyError, application-level exceptions)
# raises immediately so a real bug isn't masked by 3 silent retries.
#
# Both httpx and aiohttp are in use in the codebase (httpx for the
# adapter shims under ``src/authority/*_adapter.py``; aiohttp for the
# genealogy connectors and the inline Wikidata SPARQL call in
# ``manager_tier01._fetch_wikidata_p184``). We pick up whichever
# exception classes are importable so a single retry helper covers
# both stacks.
def _transient_excs() -> tuple:
    excs: list = [asyncio.TimeoutError, OSError]
    if httpx is not None:
        excs.extend(
            [
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadError,
                httpx.RemoteProtocolError,
            ]
        )
    try:
        import aiohttp  # type: ignore

        # ClientError is the base class for *all* aiohttp client-side
        # failures (connection drop, DNS, server disconnect, payload
        # decode). It does NOT cover ServerDisconnectedError exception
        # paths that surface as RuntimeError, so we add asyncio's
        # TimeoutError above as belt-and-braces.
        excs.append(aiohttp.ClientError)
    except ImportError:
        pass
    return tuple(excs)


async def retry_with_backoff(
    func,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
):
    """Call ``func()`` with exponential-backoff retries on transient
    network errors.

    - ``max_retries`` is the number of retries *after* the initial
      attempt (so total attempts = max_retries + 1).
    - Backoff schedule: ``base_delay * 2 ** attempt`` for ``attempt``
      ∈ [0, max_retries-1].
    - Only ``httpx.TimeoutException``, ``httpx.ConnectError``,
      ``httpx.ReadError``, ``httpx.RemoteProtocolError``, ``OSError``
      and ``asyncio.TimeoutError`` are retried. Everything else
      propagates on the first raise.

    Used by every authority adapter as the wrapper around its outer
    HTTP call so a single transient hiccup doesn't poison a 1 000-
    entry batch.
    """
    transient = _transient_excs()
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except transient as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            await asyncio.sleep(base_delay * (2**attempt))
    # Should be unreachable — the loop either returns or raises.
    raise last_exc if last_exc else RuntimeError("retry_with_backoff: no attempts")
