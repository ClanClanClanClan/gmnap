#!/usr/bin/env python3
# Tracemalloc + RSS sampler for profiling.
import argparse, tracemalloc, time, json, threading, resource, importlib


def rss_gb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if rss < 1 << 20:  # assume KB
        return rss / (1024 * 1024)
    return rss / (1024 * 1024 * 1024)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fn", required=True, help="module:function (async allowed)")
    ap.add_argument("--args", default="[]")
    ap.add_argument("--kwargs", default="{}")
    ap.add_argument("--interval", type=float, default=0.5)
    a = ap.parse_args()
    mod, fn = a.fn.split(":")
    m = importlib.import_module(mod)
    f = getattr(m, fn)
    tracemalloc.start()
    import asyncio, ast, json

    args = json.loads(a.args)
    kwargs = json.loads(a.kwargs)

    async def run():
        if asyncio.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: f(*args, **kwargs))

    t0 = time.time()
    res = asyncio.run(run())
    snap = tracemalloc.take_snapshot()
    stats = snap.statistics("lineno")[:20]
    print(
        json.dumps(
            {
                "seconds": time.time() - t0,
                "rss_gb": rss_gb(),
                "top": [str(s.traceback[0]) for s in stats],
            },
            indent=2,
        )
    )
