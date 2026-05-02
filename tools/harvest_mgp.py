#!/usr/bin/env python3
"""Bulk Mathematics Genealogy Project harvester.

The MGP (mathgenealogy.org) is the authoritative source for ~280k
mathematician records with full advisor / student chains. Their
robots.txt allows scraping but mandates ``Crawl-delay: 10`` — the
full corpus at that rate is ~780 hours (~33 days) of continuous
polite crawling. Not feasible inline; this script is built for
overnight / weekend / multi-session runs.

Design:

  - Sequential ID crawl (`/id.php?id=N`) for N in a configurable
    range. MGP uses dense integer IDs starting at 1; the highest
    public ID as of 2026 is around ~290000.
  - Resumable: writes a progress checkpoint after every successful
    fetch. Re-running picks up from the checkpoint.
  - Cached: each ID's parsed record is appended to a JSONL file
    so a later partial run can be merged without re-fetching.
  - Polite: respects ``Crawl-delay: 10`` (configurable via
    ``--delay``, but never below 1.0). Single-threaded by design.
  - Tolerant: malformed pages, HTTP errors, and empty IDs (gaps in
    MGP's numbering) are logged and skipped without aborting the
    whole run.

Usage:

  # First run, fresh
  PYTHONPATH=. python3 tools/harvest_mgp.py --start 1 --end 1000

  # Resume from checkpoint
  PYTHONPATH=. python3 tools/harvest_mgp.py --resume

  # Run a tiny smoke (50 IDs, ~9 minutes at default delay)
  PYTHONPATH=. python3 tools/harvest_mgp.py --start 1 --end 50

Outputs:

  - ``data/mgp_full.jsonl``: one JSON record per line, append-only.
    Format: ``{"mgp_id": "1", "name": "...", "advisors": [...], ...}``.
  - ``data/mgp_harvest_checkpoint.json``: ``{"last_id": N}``.

The harvester does NOT update ``data/genealogy_enrichment.json``
directly — that's a separate merge step in
``tools/build_genealogy_enrichment.py`` once the harvest is complete
or partially complete enough to be useful.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.authorities.mathgenealogy import MathGenealogyAPI  # noqa: E402

OUTPUT = REPO / "data" / "mgp_full.jsonl"
CHECKPOINT = REPO / "data" / "mgp_harvest_checkpoint.json"

# MGP's robots.txt mandates Crawl-delay: 10. Anything lower is rude.
MIN_DELAY_SECONDS = 10.0


def _load_checkpoint() -> int:
    if not CHECKPOINT.exists():
        return 0
    try:
        return int(json.loads(CHECKPOINT.read_text()).get("last_id", 0))
    except (json.JSONDecodeError, ValueError):
        return 0


def _save_checkpoint(last_id: int) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps({"last_id": last_id}))


def _append_record(record: dict) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def harvest(
    start: int, end: int, delay: float, log_every: int = 10
) -> tuple[int, int]:
    """Fetch IDs in [start, end). Returns (n_fetched, n_skipped)."""
    fetched = 0
    skipped = 0
    print(
        f"Harvesting MGP IDs {start}..{end - 1} at {delay}s/req "
        f"(~{(end - start) * delay / 60:.0f} min total)…",
        flush=True,
    )
    async with MathGenealogyAPI() as api:
        for mgp_id in range(start, end):
            try:
                person = await api.get_person(str(mgp_id))
            except Exception as exc:
                print(f"  id={mgp_id}: error: {exc}", file=sys.stderr)
                skipped += 1
                _save_checkpoint(mgp_id)
                await asyncio.sleep(delay)
                continue
            if person is None:
                # Empty / nonexistent ID — common in MGP's numbering
                skipped += 1
            else:
                # Convert dataclass to dict; advisors/students may
                # be None on the dataclass (default), normalize.
                record = asdict(person)
                if record.get("advisors") is None:
                    record["advisors"] = []
                if record.get("students") is None:
                    record["students"] = []
                _append_record(record)
                fetched += 1
            _save_checkpoint(mgp_id)
            if (fetched + skipped) % log_every == 0:
                print(
                    f"  id={mgp_id}  fetched={fetched}  skipped={skipped}",
                    flush=True,
                )
            await asyncio.sleep(delay)
    return fetched, skipped


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", type=int, default=None, help="First MGP ID")
    ap.add_argument("--end", type=int, default=None, help="Last MGP ID (exclusive)")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Resume from data/mgp_harvest_checkpoint.json",
    )
    ap.add_argument(
        "--delay",
        type=float,
        default=MIN_DELAY_SECONDS,
        help=f"Seconds between requests (>= {MIN_DELAY_SECONDS}; MGP robots.txt mandate)",
    )
    args = ap.parse_args()

    if args.delay < MIN_DELAY_SECONDS:
        sys.exit(
            f"--delay must be >= {MIN_DELAY_SECONDS} (MGP robots.txt: "
            f"`Crawl-delay: 10`). Refusing to scrape impolitely."
        )

    if args.resume:
        if args.start is not None:
            sys.exit("--resume conflicts with --start")
        args.start = _load_checkpoint() + 1
        if args.end is None:
            args.end = args.start + 1000  # default: 1000-id chunk
    elif args.start is None or args.end is None:
        sys.exit("Pass --start AND --end, or --resume")

    if args.start >= args.end:
        sys.exit(f"--start ({args.start}) must be < --end ({args.end})")

    t0 = time.time()
    fetched, skipped = asyncio.run(harvest(args.start, args.end, delay=args.delay))
    dt = time.time() - t0
    print(
        f"\nDone. fetched={fetched} skipped={skipped} "
        f"in {dt:.0f}s ({dt / max(fetched + skipped, 1):.1f}s/id avg)"
    )
    print(f"Output → {OUTPUT.relative_to(REPO)}")
    print(f"Checkpoint → {CHECKPOINT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
