import asyncio
import pytest, asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.ops.conn_pool import ConnectionPool
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.ops.transactions import execute_transaction


@pytest.mark.asyncio
async def test_pool_health_and_execute():
    pool = ConnectionPool(pool_size=3)
    h = await pool.health()
    assert h["available"] == 3
    res = await pool.execute("MATCH (n) RETURN count(n) AS c")
    assert res["ok"]


@pytest.mark.asyncio
async def test_execute_transaction_success_and_fail():
    seen = {"n": 0}

    async def op_ok():
        seen["n"] += 1

    async def op_fail():
        raise RuntimeError("boom")

    ok, _ = await execute_transaction([op_ok, op_ok])
    assert ok and seen["n"] == 2
    ok2, msg = await execute_transaction([op_ok, op_fail])
    assert not ok2 and "boom" in msg
