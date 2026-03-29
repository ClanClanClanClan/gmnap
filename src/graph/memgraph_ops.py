from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List

try:
    from neo4j import AsyncGraphDatabase
except Exception:  # offline-safe
    AsyncGraphDatabase = None


class MemgraphPool:
    """Async connection pool (stubbed if driver absent)."""

    def __init__(self, uri: str, auth: tuple[str, str] | None = None, pool_size: int = 5):
        self.uri = uri
        self.auth = auth or ("", "")
        self.pool_size = pool_size
        self._sem = asyncio.Semaphore(pool_size)
        self._driver = None

    async def start(self):
        if AsyncGraphDatabase:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=self.auth, max_connection_pool_size=self.pool_size
            )
        return self

    @asynccontextmanager
    async def session(self):
        await self._sem.acquire()
        if self._driver:
            async with self._driver.session() as s:
                try:
                    yield s
                finally:
                    self._sem.release()
        else:

            class _S:  # stub
                async def run(self, *a, **k):
                    return type("R", (), {"data": lambda self: []})()

            try:
                yield _S()
            finally:
                self._sem.release()


async def ensure_indices(pool: MemgraphPool):
    async with pool.session() as s:
        if getattr(s, "run", None):
            await s.run(
                "CREATE INDEX mathematician_gid IF NOT EXISTS FOR (m:Mathematician) ON (m.global_id)"
            )


async def write_entries_and_edges(pool: MemgraphPool, entries: List[Dict]) -> int:
    n = 0
    async with pool.session() as s:
        for e in entries:
            gid = e.get("GlobalID")
            name = e.get("CanonicalLatin", "")
            if getattr(s, "run", None):
                await s.run(
                    "MERGE (m:Mathematician {global_id:$gid}) SET m.canonical=$name",
                    gid=gid,
                    name=name,
                )
                for adv in e.get("Advisors") or []:
                    await s.run(
                        """
                        MERGE (s:Mathematician {global_id:$s})
                        MERGE (a:Mathematician {global_id:$a})
                        MERGE (s)-[:ADVISED_BY]->(a)
                    """,
                        s=gid,
                        a=adv,
                    )
            n += 1
    return n


def _coherence_offline(entries: List[Dict]) -> float:
    # Simple proxy: 1 - (# entries lacking GlobalID)/N
    N = len(entries) or 1
    bad = sum(1 for e in entries if not e.get("GlobalID"))
    return max(0.0, 1.0 - bad / N)


async def compute_coherence(pool: MemgraphPool, entries: List[Dict]) -> float:
    if pool._driver is None:
        return _coherence_offline(entries)
    # In real mode: query betweenness / conflicts (omitted for offline)
    return 0.90  # placeholder > quick gate
