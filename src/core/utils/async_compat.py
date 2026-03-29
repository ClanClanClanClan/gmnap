import asyncio


async def run_maybe_async(fn, *a, **k):
    rv = fn(*a, **k)
    if asyncio.iscoroutine(rv) or isinstance(rv, asyncio.Future):
        return await rv
    return rv
