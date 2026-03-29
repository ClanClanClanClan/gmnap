#!/usr/bin/env python3
# Runs a target function with tracemalloc and prints top allocators.
import argparse, tracemalloc, time, json, importlib

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True, help="module:function")
    ap.add_argument("--args", default="[]")
    ap.add_argument("--kwargs", default="{}")
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    modname, funcname = a.module.split(":")
    mod = importlib.import_module(modname)
    fn = getattr(mod, funcname)
    args = json.loads(a.args)
    kwargs = json.loads(a.kwargs)
    tracemalloc.start()
    t0 = time.time()
    fn(*args, **kwargs)
    dt = time.time() - t0
    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics("lineno")[: a.top]
    out = [
        {"trace": str(s.traceback[0]), "size_kb": s.size / 1024, "count": s.count} for s in stats
    ]
    print(json.dumps({"seconds": dt, "top": out}, indent=2))
