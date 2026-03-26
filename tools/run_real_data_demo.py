#!/usr/bin/env python3
"""
GMNAP Real Data Demo — Fetch real mathematicians from OpenAlex, run full pipeline.

Fetches ~1,000 real mathematician profiles from OpenAlex (free, no API key),
converts to pipeline input format, runs the V7 pipeline with tier-0 enrichment,
and produces a human-readable report.

Usage:
    PYTHONPATH=. python3 tools/run_real_data_demo.py
    PYTHONPATH=. python3 tools/run_real_data_demo.py --count 500 --offline
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── OpenAlex fetching ────────────────────────────────────────────────────────

MATH_QUERIES = [
    "pure mathematics",
    "applied mathematics",
    "algebra",
    "topology",
    "number theory",
    "mathematical analysis",
    "geometry",
    "combinatorics",
    "probability theory",
    "differential equations",
    "algebraic geometry",
    "functional analysis",
    "graph theory",
    "dynamical systems",
    "mathematical logic",
]

OPENALEX_BASE = "https://api.openalex.org"


MATH_TOPIC_IDS = [
    "T10020",  # Mathematics
    "T10120",  # Pure mathematics
    "T10319",  # Applied mathematics
    "T10152",  # Algebra
    "T11475",  # Number theory
    "T10621",  # Mathematical analysis
    "T10146",  # Geometry
    "T10898",  # Topology
    "T11526",  # Combinatorics
    "T10080",  # Probability and statistics
]


def fetch_mathematicians(target: int = 1000) -> list[dict]:
    """Fetch real mathematician profiles from OpenAlex using topic filters."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "GMNAP/7.0 (mailto:gmnap@example.com)",
        "Accept": "application/json",
    })

    seen_ids: set[str] = set()
    authors: list[dict] = []
    per_page = 200  # Max allowed by OpenAlex

    for topic_id in MATH_TOPIC_IDS:
        if len(authors) >= target:
            break

        pages_needed = max(1, (target - len(authors)) // per_page + 1)
        print(f"  Topic {topic_id} (have {len(authors)}/{target})...")

        for page in range(1, min(pages_needed + 1, 6)):  # Max 5 pages per topic
            if len(authors) >= target:
                break

            params = {
                "filter": f"topics.id:{topic_id}",
                "per_page": per_page,
                "page": page,
                "sort": "cited_by_count:desc",
                "select": "id,display_name,last_known_institutions,works_count,"
                          "cited_by_count,summary_stats,ids",
                "mailto": "gmnap@example.com",
            }

            try:
                r = session.get(f"{OPENALEX_BASE}/authors", params=params, timeout=15)
            except requests.RequestException as e:
                print(f"    ⚠ Request failed: {e}")
                break

            if r.status_code == 429:
                print("    ⚠ Rate limited, waiting 5s...")
                time.sleep(5)
                continue
            if r.status_code != 200:
                print(f"    ⚠ HTTP {r.status_code}")
                break

            results = r.json().get("results", [])
            if not results:
                break

            added = 0
            for author in results:
                oa_id = author.get("id", "")
                if oa_id in seen_ids:
                    continue
                seen_ids.add(oa_id)

                name = author.get("display_name", "").strip()
                institutions = author.get("last_known_institutions") or []
                if not name or not institutions:
                    continue

                country = None
                inst_name = None
                for inst in institutions:
                    cc = inst.get("country_code")
                    if cc:
                        country = cc
                        inst_name = inst.get("display_name")
                        break

                if not country:
                    continue

                orcid = None
                ids = author.get("ids", {})
                if isinstance(ids, dict):
                    orcid_url = ids.get("orcid", "")
                    if orcid_url:
                        orcid = orcid_url.split("/")[-1]

                authors.append({
                    "openalex_id": oa_id,
                    "display_name": name,
                    "country_code": country,
                    "institution": inst_name,
                    "works_count": author.get("works_count", 0),
                    "cited_by_count": author.get("cited_by_count", 0),
                    "h_index": (author.get("summary_stats") or {}).get("h_index", 0),
                    "orcid": orcid,
                })
                added += 1

            print(f"    Page {page}: +{added} authors")
            time.sleep(0.15)

    authors = authors[:target]
    print(f"  ✅ Fetched {len(authors)} unique mathematicians with affiliations")
    return authors


# ── Convert to pipeline format ───────────────────────────────────────────────


def to_pipeline_entry(raw: dict) -> dict:
    """Convert OpenAlex author record to GMNAP pipeline input."""
    name = raw["display_name"]

    # Split into Family, Given — last word is family name
    parts = name.strip().split()
    if len(parts) >= 2:
        family = parts[-1]
        given = " ".join(parts[:-1])
        canonical = f"{family}, {given}"
    else:
        canonical = name

    entry: dict[str, Any] = {
        "CanonicalLatin": canonical,
        "CountryCodes": [raw["country_code"]],
    }

    if raw.get("orcid"):
        entry["ORCID"] = raw["orcid"]

    return entry


# ── Run pipeline ─────────────────────────────────────────────────────────────


async def run_pipeline(entries: list[dict], offline: bool = False) -> dict:
    """Run V7 pipeline on entries."""
    if offline:
        os.environ["GMNAP_NO_NETWORK"] = "1"
    else:
        os.environ.pop("GMNAP_NO_NETWORK", None)
        os.environ["OFFLINE"] = "1"  # Block tier-1+, allow tier-0

    from src.core.pipeline_v7 import PipelineMode, V7Pipeline

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    return await pipeline.process_batch(entries)


# ── Report ───────────────────────────────────────────────────────────────────


def generate_report(
    raw_authors: list[dict], report: dict, elapsed: float, output_dir: Path
) -> str:
    """Generate human-readable demo report."""
    entries = report.get("entries", [])
    metrics = report.get("metrics", {})
    gates = report.get("quality_gates", {})

    lines = [
        "=" * 72,
        "GMNAP V7 — REAL DATA DEMO REPORT",
        "=" * 72,
        "",
        f"Date:            {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Input entries:   {len(raw_authors)}",
        f"Output entries:  {len(entries)}",
        f"Elapsed:         {elapsed:.1f}s ({len(entries)/elapsed:.0f} entries/sec)",
        f"Quality gates:   {'PASS' if gates.get('passed') else 'FAIL'}",
        f"Schema errors:   {metrics.get('schema_errors', 0)}",
        f"Dup GlobalIDs:   {metrics.get('duplicate_global_ids', 0)}",
        f"Graph coherence: {metrics.get('graph_coherence', 'N/A')}",
        f"Peak RSS:        {metrics.get('peak_rss_gb', 0):.2f} GB",
        "",
    ]

    # Region distribution
    region_counts = Counter(e.get("RegionCode", e.get("DetectedRegion", "?")) for e in entries)
    lines.append("─" * 40)
    lines.append("REGION DISTRIBUTION")
    lines.append("─" * 40)
    for region, count in sorted(region_counts.items(), key=lambda x: -x[1]):
        bar = "█" * (count // 3) if count > 0 else ""
        lines.append(f"  {region:5s} {count:>4d}  {bar}")
    lines.append("")

    # Country distribution
    country_counts = Counter()
    for a in raw_authors:
        country_counts[a["country_code"]] += 1
    lines.append("─" * 40)
    lines.append("TOP 15 COUNTRIES")
    lines.append("─" * 40)
    for country, count in country_counts.most_common(15):
        lines.append(f"  {country:5s} {count:>4d}")
    lines.append("")

    # Authority source hits
    source_counts = Counter()
    for e in entries:
        for s in e.get("_sources", []):
            source_counts[s] += 1
    if source_counts:
        lines.append("─" * 40)
        lines.append("AUTHORITY SOURCE HITS")
        lines.append("─" * 40)
        for src, count in source_counts.most_common():
            pct = count / len(entries) * 100
            lines.append(f"  {src:25s} {count:>5d} ({pct:.0f}%)")
        lines.append("")

    # Top 20 most-cited (from raw data)
    top = sorted(raw_authors, key=lambda x: x.get("cited_by_count", 0), reverse=True)[:20]
    lines.append("─" * 40)
    lines.append("TOP 20 MOST-CITED MATHEMATICIANS")
    lines.append("─" * 40)
    for i, a in enumerate(top, 1):
        # Find the corresponding pipeline entry
        match = None
        for e in entries:
            if a["display_name"].split()[-1] in e.get("CanonicalLatin", ""):
                match = e
                break
        gid = match.get("GlobalID", "?")[:20] + "..." if match else "?"
        region = match.get("RegionCode", "?") if match else "?"
        lines.append(
            f"  {i:2d}. {a['display_name']:35s} "
            f"cites={a.get('cited_by_count',0):>7,d}  "
            f"h={a.get('h_index',0):>3d}  "
            f"{a['country_code']:2s}  "
            f"→ {region}"
        )
    lines.append("")

    # Sample enriched entries
    lines.append("─" * 40)
    lines.append("SAMPLE ENRICHED ENTRIES (first 5)")
    lines.append("─" * 40)
    for e in entries[:5]:
        lines.append(f"  GlobalID:      {e.get('GlobalID', '?')}")
        lines.append(f"  CanonicalLatin: {e.get('CanonicalLatin', '?')}")
        lines.append(f"  Region:        {e.get('RegionCode', e.get('DetectedRegion', '?'))}")
        lines.append(f"  Confidence:    {e.get('Confidence', '?')}")
        lines.append(f"  Sources:       {e.get('_sources', [])}")
        lines.append(f"  OrderKey:      {e.get('OrderKey', '?')}")
        if e.get("ShortFormClusters"):
            lines.append(f"  ShortForms:    {list(e['ShortFormClusters'].keys())[:4]}")
        lines.append("")

    lines.append("=" * 72)
    lines.append(f"Full output: {output_dir}/pipeline_output.json")
    lines.append("=" * 72)

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="GMNAP Real Data Demo")
    parser.add_argument("--count", type=int, default=1000, help="Number of mathematicians to fetch")
    parser.add_argument("--offline", action="store_true", help="Run pipeline in full offline mode")
    parser.add_argument("--output", default="data/real_demo", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("GMNAP V7 — REAL DATA DEMO")
    print("=" * 72)
    print()

    # Step 1: Fetch real mathematicians
    print(f"[1/4] Fetching {args.count} real mathematicians from OpenAlex...")
    raw_authors = fetch_mathematicians(args.count)

    # Save raw data
    with open(output_dir / "entries_raw.json", "w") as f:
        json.dump(raw_authors, f, indent=2, ensure_ascii=False)
    print(f"       Saved raw data to {output_dir}/entries_raw.json")

    # Step 2: Convert to pipeline format
    print(f"\n[2/4] Converting to pipeline input format...")
    entries = [to_pipeline_entry(a) for a in raw_authors]
    with open(output_dir / "entries_input.json", "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"       {len(entries)} entries ready")

    # Step 3: Run pipeline
    mode = "OFFLINE" if args.offline else "ONLINE (tier-0)"
    print(f"\n[3/4] Running V7 pipeline ({mode})...")
    start = time.time()
    report = asyncio.run(run_pipeline(entries, offline=args.offline))
    elapsed = time.time() - start
    print(f"       Pipeline completed in {elapsed:.1f}s")

    # Save pipeline output
    output_entries = report.get("entries", [])
    with open(output_dir / "pipeline_output.json", "w") as f:
        json.dump(output_entries, f, indent=2, ensure_ascii=False, default=str)
    print(f"       {len(output_entries)} entries processed")

    # Step 4: Generate report
    print(f"\n[4/4] Generating report...")
    report_text = generate_report(raw_authors, report, elapsed, output_dir)
    with open(output_dir / "report.txt", "w") as f:
        f.write(report_text)

    print()
    print(report_text)


if __name__ == "__main__":
    main()
