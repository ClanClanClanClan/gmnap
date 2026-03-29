#!/usr/bin/env python3
# Exercises thread-safety of the SQLite TTL cache under concurrency.
import threading, tempfile, os, time
from src.core.cache_manager import TTLCache


def worker(c: TTLCache, idx: int, loops: int = 1000):
    for i in range(loops):
        c.set(f"k{idx}-{i}", {"v": i})
        _ = c.get(f"k{idx}-{i}")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as td:
        c = TTLCache(
            path=os.path.join(td, "c.db"), namespace="T", capacity=10000, ttl_seconds=10
        )
        ths = [threading.Thread(target=worker, args=(c, i)) for i in range(8)]
        [t.start() for t in ths]
        [t.join() for t in ths]
        print("OK: concurrent access complete")
