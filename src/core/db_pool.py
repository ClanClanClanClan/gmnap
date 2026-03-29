from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from ..ops.metrics import POOL_AVAIL, POOL_IN_USE

try:
    from neo4j import AsyncGraphDatabase  # type: ignore
except Exception:  # pragma: no cover
    AsyncGraphDatabase = None


class _SessionStub:
    def __init__(self, store: List[str]):
        self._store = store

    async def run(self, query: str, **params):
        self._store.append(query.strip())

        class _Result:
            async def data(self):
                return []

        return _Result()

    async def close(self):
        pass

    # transaction-like helpers for compatibility
    async def begin_transaction(self):
        return _TxStub(self._store)


class _TxStub:
    def __init__(self, store: List[str]):
        self._store = store

    async def run(self, query: str, **params):
        self._store.append(query.strip())

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass


class _DriverStub:
    def __init__(self, pool_size: int = 5):
        self._queries: List[str] = []
        self._sem = asyncio.Semaphore(pool_size)
        self._pool_size = pool_size

    async def session(self):
        await self._sem.acquire()
        POOL_IN_USE.inc()
        POOL_AVAIL.dec()

        class _SessionCtx:
            def __init__(self, sem, store, on_close):
                self.sem = sem
                self.store = store
                self.on_close = on_close
                self.sess = _SessionStub(store)

            async def __aenter__(self):
                return self.sess

            async def __aexit__(self, exc_type, exc, tb):
                await self.sess.close()
                self.on_close()

        def _on_close():
            self._sem.release()
            POOL_IN_USE.dec()
            POOL_AVAIL.inc()

        return _SessionCtx(self._sem, self._queries, _on_close)

    async def verify_connectivity(self):
        return True

    @property
    def queries(self) -> List[str]:
        return self._queries


class DBPool:
    def __init__(
        self,
        uri: str | None = None,
        auth: tuple[str, str] | None = None,
        pool_size: int = 10,
    ):
        self.uri = uri or os.getenv("MG_URI", "bolt://localhost:7687")
        self.auth = auth or (os.getenv("MG_USER") or "", os.getenv("MG_PASSWORD") or "")
        self.pool_size = pool_size
        self._driver = None
        self._is_stub = False
        POOL_AVAIL.set(pool_size)

    async def start(self):
        if AsyncGraphDatabase is None:
            self._driver = _DriverStub(self.pool_size)
            self._is_stub = True
        else:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=self.auth, max_connection_pool_size=self.pool_size
            )
            self._is_stub = False
        return self

    async def stop(self):
        # neo4j driver has .close(); stub doesn't need
        try:
            if self._driver and not self._is_stub:
                await self._driver.close()
        except Exception:
            pass

    @asynccontextmanager
    async def get_session(self):
        # For both stub and real driver, use async context manager
        if self._is_stub:
            # stub .session() already returns async context manager
            sess_ctx = await self._driver.session()
            async with sess_ctx as sess:
                yield sess
        else:
            # real neo4j
            sess = await self._driver.session()
            try:
                yield sess
            finally:
                await sess.close()

    async def execute(self, query: str, **params):
        async with self.get_session() as s:
            res = await s.run(query, **params)
            try:
                return await res.data()
            except Exception:
                return []

    async def health(self) -> Dict[str, Any]:
        try:
            await self._driver.verify_connectivity()
            ok = True
        except Exception:
            ok = False
        return {
            "ok": ok,
            "uri": self.uri,
            "pool_size": self.pool_size,
            "is_stub": self._is_stub,
        }

    @property
    def is_stub(self) -> bool:
        return self._is_stub

    @property
    def driver(self):
        return self._driver


# Alias for compatibility
BoltPool = DBPool
