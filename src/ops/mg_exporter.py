from __future__ import annotations
import asyncio
from ..ops.metrics import MEMGRAPH_NODES, MEMGRAPH_EDGES
from ..core.db_pool import BoltPool


async def _probe_once(pool: BoltPool) -> None:
    async def _count_nodes(tx):
        res = await tx.run("MATCH (n) RETURN count(n) AS c")
        rows = await res.data()
        return rows[0]["c"] if rows else 0

    async def _count_edges(tx):
        res = await tx.run("MATCH ()-[r]->() RETURN count(r) AS c")
        rows = await res.data()
        return rows[0]["c"] if rows else 0

    async with pool._driver.session() as session:
        nodes = await session.execute_read(_count_nodes)
        edges = await session.execute_read(_count_edges)
    MEMGRAPH_NODES.set(nodes)
    MEMGRAPH_EDGES.set(edges)


async def run_exporter(pool: BoltPool, interval_seconds: int = 15) -> None:
    while True:
        try:
            await _probe_once(pool)
        except Exception:
            # Best-effort exporter – swallow to avoid killing the process
            pass
        await asyncio.sleep(interval_seconds)
