#!/usr/bin/env python3
# Simulated authority stress tester; replace with real fetches when LIVE_AUTH=1.
import os, time, random, json


def fetch_mock(name):
    time.sleep(random.random() * 0.05)
    return {"name": name, "source": "Crossref", "ok": True}


if __name__ == "__main__":
    N = int(os.getenv("N", "1000"))
    for i in range(N):
        print(json.dumps(fetch_mock(f"Name-{i}")))
