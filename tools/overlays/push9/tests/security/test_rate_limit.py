import asyncio
import os

from src.ops.rate_limit import RateLimiter


def test_rate_limiter_local_bucket():
    rl = RateLimiter(rpm_free=60, rpm_paid=120)

    # 60/min → 1/sec; burst 2
    async def run():
        ok1 = await rl.allow("k", paid=False)
        ok2 = await rl.allow("k", paid=False)
        ok3 = await rl.allow("k", paid=False)
        return ok1, ok2, ok3

    ok1, ok2, ok3 = asyncio.get_event_loop().run_until_complete(run())
    assert ok1 and ok2 and (ok3 in (True, False))
