from __future__ import annotations
from typing import Awaitable, Callable, Any, List, Tuple
from ..ops.metrics import TX_SUCCESS, TX_ROLLBACK

Operation = Callable[[Any], Awaitable[Any]]  # receives tx/session-like


class TransactionManager:
    """Transactional executor using a DBPool session/transaction if available; otherwise stub."""

    def __init__(self, pool):
        self.pool = pool

    async def execute(self, ops: List[Operation]) -> Tuple[bool, list]:
        async with self.pool.get_session() as sess:
            # Try to open a transaction; if not available, run ops directly
            tx = None
            try:
                tx = await sess.begin_transaction()
            except Exception:
                tx = None
            results = []
            try:
                for op in ops:
                    results.append(await op(tx or sess))
                if tx:
                    await tx.commit()
                TX_SUCCESS.inc()
                return True, results
            except Exception as e:
                if tx:
                    try:
                        await tx.rollback()
                    except Exception:
                        pass
                TX_ROLLBACK.inc()
                return False, [str(e)]
