from __future__ import annotations
from typing import List, Dict, Any
from .db_pool import BoltPool
from ..ops.metrics import WRITE_LATENCY, WRITE_ERRORS, WRITES_TOTAL
import time

CREATE_NODE = """
MERGE (m:Mathematician {global_id: $GlobalID})
SET m += $props
"""

CREATE_EDGE = """
MATCH (s:Mathematician {global_id: $student}), (a:Mathematician {global_id: $advisor})
MERGE (s)-[:ADVISED_BY {source: $source, confidence: coalesce($confidence,0)}]->(a)
"""


class TransactionalWriter:
    def __init__(self, pool: BoltPool):
        self.pool = pool

    async def batch_upsert(self, entries: List[Dict[str, Any]]) -> None:
        start = time.perf_counter()
        try:
            async with self.pool._driver.session() as session:

                async def _ops(tx):
                    for e in entries:
                        props = {
                            k: v
                            for k, v in e.items()
                            if k not in ("Advisors", "Students")
                        }
                        await tx.run(CREATE_NODE, GlobalID=e["GlobalID"], props=props)
                    for e in entries:
                        for adv in e.get("Advisors", []):
                            await tx.run(
                                CREATE_EDGE,
                                student=e["GlobalID"],
                                advisor=adv,
                                source=e.get("Source", ""),
                                confidence=e.get("Confidence", 0),
                            )

                await session.execute_write(_ops)
            WRITES_TOTAL.inc(len(entries))
        except Exception:
            WRITE_ERRORS.inc()
            raise
        finally:
            WRITE_LATENCY.observe(time.perf_counter() - start)
