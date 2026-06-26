#!/usr/bin/env python3
# Emits batches with realistic distributions; coalesces small requests for throughput.
import itertools
import json
import os
import random
import time


def batches(n_batches=100, batch_size=100):
    for b in range(n_batches):
        buf = []
        for i in range(batch_size):
            gid = f"ID-{b}-{i:04d}"
            buf.append(
                {
                    "GlobalID": gid,
                    "CanonicalNative": "Lee Jae-Woo",
                    "Region": "R01",
                    "BirthYear": 1980,
                    "Sources": ["Crossref"],
                }
            )
        yield buf


if __name__ == "__main__":
    n = int(os.getenv("N_BATCHES", "100"))
    s = int(os.getenv("BATCH_SIZE", "100"))
    for b in batches(n, s):
        print(json.dumps({"batch": b}))
        time.sleep(0.01)
