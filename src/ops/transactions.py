from __future__ import annotations
from typing import Awaitable, Callable, List, Tuple


class TransactionError(Exception):
    pass


async def execute_transaction(ops: List[Callable[[], Awaitable[None]]]) -> Tuple[bool, str]:
    try:
        for op in ops:
            await op()
        return True, ""
    except Exception as e:
        return False, str(e)
