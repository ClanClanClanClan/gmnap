from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager


class FakeSession:
    async def run(self, query: str, **params):
        await asyncio.sleep(0)
        return {"ok": True, "query": query, "params": params}

    async def close(self):
        pass


class ConnectionPool:
    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.available: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self.in_use = set()
        for _ in range(pool_size):
            self.available.put_nowait(FakeSession())

    @asynccontextmanager
    async def get(self):
        s = await self.available.get()
        self.in_use.add(s)
        try:
            yield s
        finally:
            self.in_use.remove(s)
            await self.available.put(s)

    async def execute(self, query: str, **params):
        async with self.get() as session:
            return await session.run(query, **params)

    async def health(self):
        return {
            "pool_size": self.pool_size,
            "available": self.available.qsize(),
            "in_use": len(self.in_use),
        }
