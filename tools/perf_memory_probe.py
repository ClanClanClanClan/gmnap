import gc
import json
import os
import time

import psutil


def synth(N):
    L = []
    for i in range(N):
        L.append(
            {
                "GlobalID": f"G-{i:07d}",
                "CanonicalLatin": f"Name {i}",
                "BirthYear": 1900 + (i % 120),
            }
        )
        if i % 50000 == 0:
            gc.collect()
    return L


def peak_rss_gb():
    p = psutil.Process(os.getpid())
    try:
        rss = p.memory_info().rss
    except Exception:
        rss = max((m.rss for m in p.memory_maps()), default=0)
    return rss / (1024**3)


if __name__ == "__main__":
    start = time.time()
    data = synth(2_000_000)
    rss = peak_rss_gb()
    print(
        json.dumps({"peak_rss_gb_on_2M": rss, "seconds": time.time() - start}, indent=2)
    )
    assert rss <= 6.0, "Peak RSS exceeds 6 GB (Extreme)"
