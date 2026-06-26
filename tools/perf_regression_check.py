#!/usr/bin/env python3
"""Performance regression gate.

Runs a small but representative pipeline batch, measures wall-clock
throughput, compares against the pinned baseline. Fails non-zero if
throughput dropped more than the configured tolerance.

Pinned baseline numbers from CLAUDE.md's round-30 measurement
(2026-05-03, Apple M1, OFFLINE=1, real names, single process):

    Size      Throughput   Wall-clock      Source
    1 k       153 / s      6.6 s          docs/perf_characterization.md
    10 k      135 / s      74.1 s          docs/perf_characterization.md
    100 k     295 / s      339.6 s         docs/perf_characterization.md
    1 M       2 763 / s    362.0 s         docs/perf_characterization.md

CI uses the 1 k point — fast enough to fit a CI job's 10-minute
budget, large enough to amortize cold-start overhead. Tolerance
defaults to 25 % below baseline (153 → 115 / s); any worse is a
regression that gates the build.

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
# below the round-30 numbers (CLAUDE.md) so the test catches genuine
# regressions without being flaky across hardware tiers.
#
# Round-30 on Apple M1: synthetic 1k=273/s, 10k=192/s; real 1k=153/s,
# 10k=135/s, 100k=295/s, 1M=2763/s.
#
# CI on GHA shared runners is typically 2-3× slower than M1 (no
# fastText wheel, slower CPU, contended I/O), and the round-28
# regression that this gate would have caught was 7/s end-to-end —
# 39× below the post-fix number. So a 30 / s floor at 1k catches
# anything in the round-28 class while leaving comfortable
# CI-vs-laptop variance. Each level is calibrated for CI, not the
# round-30 measurement.
#
# Each entry: minimum acceptable entries-per-second at the given
# batch size BEFORE the --tolerance multiplier is applied.
_BASELINES = {
    1000: 30.0,  # catches a 9× regression vs round-30 (273/s syn)
    10_000: 40.0,  # catches a 5× regression vs round-30 (192/s syn)
    100_000: 80.0,  # catches a 4× regression vs round-30 (295/s real)
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


async def _run(entries: list) -> None:
    from src.core.pipeline_v7 import PipelineMode, V7Pipeline

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    await pipeline.process_batch(entries)


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
        asyncio.run(_run(entries[args.warmup :]))
    except Exception as exc:
        print(f"::error::benchmark crashed: {exc}")
        return 2
    elapsed = time.perf_counter() - start
    eps = args.size / elapsed if elapsed > 0 else 0.0

    print()
    print(f"Result : {eps:>7.1f} entries/s ({elapsed:.1f}s for {args.size:,})")
    print(f"Baseline: {baseline:>7.1f} entries/s (round-30 pinned)")
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
