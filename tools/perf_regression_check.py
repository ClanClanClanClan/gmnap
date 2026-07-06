#!/usr/bin/env python3
"""Performance regression gate.

Runs a small but representative pipeline batch, measures wall-clock
throughput, compares against the pinned baseline. Fails non-zero if
throughput dropped more than the configured tolerance.

Honest baseline numbers (R54, 2026-07-06, 8-core Apple-silicon laptop,
OFFLINE=1, real names, clean output dir). The pre-R54 "1M in 362 s /
2763-per-s" figure was RETRACTED: it measured a no-op path that skipped
region detection and the whole batch-global tail. See
docs/perf_characterization.md.

    Size      Serial     Parallel   Source
    4 k       184 / s    268 / s    docs/perf_characterization.md
    10 k      233 / s    348 / s    docs/perf_characterization.md

CI uses a 1 k synthetic point — fast enough for a CI job's budget,
large enough to amortize cold start. This gate checks BOTH a throughput
floor AND a correctness floor (region coverage), because a no-op is fast.

Tolerance choice (25 %): laptop-to-CI variance + Python-version
variance + GHA shared-runner noise typically bands ±15 %. A 25 %
floor catches genuine regressions (e.g. an O(n) → O(n²) blow-up,
or a re-introduced re.compile-in-hot-loop bug like round-28) while
leaving headroom for run-to-run jitter. Tighten this only after
collecting baseline distribution data on the CI runner over a few
runs.

Usage:
    PYTHONPATH=. python3 tools/perf_regression_check.py
    PYTHONPATH=. python3 tools/perf_regression_check.py --size 1000 --tolerance 0.25

Exit codes:
    0   throughput meets baseline (within tolerance)
    1   throughput regressed past tolerance
    2   benchmark crashed
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["OFFLINE"] = "1"
os.environ["GMNAP_NO_NETWORK"] = "1"

# REGRESSION FLOORS (not aspirational targets) — pinned conservatively
# below the R54 honest numbers so the test catches genuine regressions
# without being flaky across hardware tiers.
#
# R54 on an 8-core Apple-silicon laptop, real names, serial: 4k=184/s,
# 10k=233/s. CI on GHA shared runners is typically 2-3× slower (no
# fastText wheel, slower CPU, contended I/O), and the round-28 regression
# this gate catches was 7/s end-to-end. So a 30 / s floor at 1k catches
# anything in that class while leaving comfortable CI-vs-laptop variance.
#
# Each entry: minimum acceptable entries-per-second at the given batch
# size BEFORE the --tolerance multiplier is applied.
_BASELINES = {
    1000: 30.0,
    10_000: 40.0,
    100_000: 80.0,
}


def _make_entries(n: int) -> list:
    """Same generator as tools/run_benchmark.py — kept independent so
    a regression in the benchmark harness can't mask a real regression
    in the pipeline."""
    from src.regions.base import TERRITORY_TO_REGION

    ccs = list(set(TERRITORY_TO_REGION.keys()))
    return [
        {
            "CanonicalLatin": f"Surname{i}, Given{i}",
            "CountryCodes": [ccs[i % len(ccs)]],
        }
        for i in range(n)
    ]


async def _run(entries: list) -> list:
    from src.core.pipeline_v7 import PipelineMode, V7Pipeline

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    return await pipeline.process_batch(entries)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--size", type=int, default=1000, help="Batch size to benchmark (default 1000)"
    )
    ap.add_argument(
        "--tolerance",
        type=float,
        default=0.25,
        help="Allowed throughput drop vs baseline (default 0.25 = 25%%)",
    )
    ap.add_argument(
        "--baseline",
        type=float,
        default=None,
        help="Override baseline entries/sec (default: pinned from round-30 table)",
    )
    ap.add_argument(
        "--warmup",
        type=int,
        default=100,
        help="Entries to discard before timing (amortize cold start)",
    )
    args = ap.parse_args()

    baseline = args.baseline or _BASELINES.get(args.size)
    if baseline is None:
        print(
            f"::error::no pinned baseline for size={args.size}; "
            f"add to _BASELINES or pass --baseline"
        )
        return 2

    floor = baseline * (1 - args.tolerance)

    print(f"Generating {args.size:,} synthetic entries…")
    entries = _make_entries(args.size + args.warmup)

    print(f"Warming up ({args.warmup} entries)…")
    try:
        asyncio.run(_run(entries[: args.warmup]))
    except Exception as exc:
        print(f"::error::warmup crashed: {exc}")
        return 2

    print(f"Timing {args.size:,}-entry run…")
    start = time.perf_counter()
    try:
        rows = asyncio.run(_run(entries[args.warmup :]))
    except Exception as exc:
        print(f"::error::benchmark crashed: {exc}")
        return 2
    elapsed = time.perf_counter() - start
    eps = args.size / elapsed if elapsed > 0 else 0.0

    # CORRECTNESS FLOOR (R54): throughput alone is not enough — the pre-R54
    # ">100k streaming" path was "fast" precisely because it SKIPPED region
    # detection (a dict-copy no-op that still cleared the throughput bar).
    # These synthetic entries all carry a CountryCode, so region detection
    # via the geo branch must classify ~100%. If coverage collapses, real
    # work is being skipped again — fail regardless of speed.
    classified = sum(
        1
        for r in rows
        if isinstance(r, dict)
        and r.get("DetectedRegion")
        and r["DetectedRegion"] != "unknown"
    )
    coverage = classified / len(rows) if rows else 0.0
    if len(rows) != args.size or coverage < 0.90:
        print()
        print(
            f"::error::CORRECTNESS REGRESSION: {classified}/{len(rows)} entries "
            f"classified ({coverage:.0%}); expected {args.size} rows at >=90%. "
            f"A path is skipping region detection (the R54 no-op class) — "
            f"throughput is meaningless if the work isn't done."
        )
        return 1

    print()
    print(f"Result : {eps:>7.1f} entries/s ({elapsed:.1f}s for {args.size:,})")
    print(f"Baseline: {baseline:>7.1f} entries/s (R54 pinned)")
    print(f"Floor   : {floor:>7.1f} entries/s (baseline × {1 - args.tolerance:.0%})")

    if eps < floor:
        delta_pct = (baseline - eps) / baseline * 100
        print()
        print(
            f"::error::PERF REGRESSION: throughput {eps:.1f}/s is "
            f"{delta_pct:.1f}% below baseline {baseline:.1f}/s "
            f"(floor {floor:.1f}/s). Check the round-30 numbers in "
            f"docs/perf_characterization.md — if the regression is "
            f"intentional (e.g. you added stage 1b LLM extract), "
            f"update _BASELINES in tools/perf_regression_check.py."
        )
        return 1

    headroom_pct = (eps - baseline) / baseline * 100
    print()
    print(
        f"✅ Within tolerance ({headroom_pct:+.1f}% vs baseline; "
        f"floor would be {(eps - floor) / baseline * 100:+.1f}% headroom)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
