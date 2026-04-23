#!/usr/bin/env python3
"""Load ``data/genealogy_enrichment.json`` into Memgraph.

Idempotent: re-running updates existing nodes/edges via MERGE rather
than duplicating. Creates one ``:Person`` node per entry and one
``-[:DOCTORAL_ADVISOR]->`` edge per advisor relation.

Usage::

    # Start Memgraph first
    docker compose up -d memgraph

    # Load (reads MEMGRAPH_BOLT, MEMGRAPH_USER, MEMGRAPH_PASSWORD env)
    PYTHONPATH=. python3 tools/load_memgraph_from_enrichment.py

    # Or explicitly
    PYTHONPATH=. python3 tools/load_memgraph_from_enrichment.py \\
        --bolt bolt://localhost:7687 --user gmnap --password v7_lineage

The schema matches what ``src/genealogy/query.py`` expects::

    (p:Person {
        key         : "<normalized, lowercase, 'surname, given'>",   // PK
        name        : "<display form, e.g. 'Euler, Leonhard'>",
        global_id   : "<optional GMNAP GlobalID>",
        birth_year  : <optional int>,
        death_year  : <optional int>,
        institution : "<optional>",
        country     : "<optional>"
    })
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.genealogy.query import _normalize_key  # reuse the exact convention

try:
    from neo4j import GraphDatabase  # type: ignore
except ImportError:
    print(
        "neo4j driver not installed.\n" "Install with:  pip install neo4j\n",
        file=sys.stderr,
    )
    sys.exit(2)

logger = logging.getLogger(__name__)

ENRICHMENT = Path("data/genealogy_enrichment.json")


# ─── Cypher fragments ──────────────────────────────────────────────────

CONSTRAINT_KEY = "CREATE CONSTRAINT ON (p:Person) ASSERT p.key IS UNIQUE;"
INDEX_GID = "CREATE INDEX ON :Person(global_id);"
INDEX_NAME = "CREATE INDEX ON :Person(name);"

# UPSERT a person node. All optional fields are set via COALESCE so
# re-runs don't overwrite richer data with NULL.
UPSERT_PERSON = """
MERGE (p:Person {key: $key})
SET  p.name        = COALESCE(p.name, $name),
     p.global_id   = COALESCE(p.global_id, $global_id),
     p.birth_year  = COALESCE(p.birth_year, $birth_year),
     p.death_year  = COALESCE(p.death_year, $death_year),
     p.institution = COALESCE(p.institution, $institution),
     p.country     = COALESCE(p.country, $country),
     p.source      = COALESCE(p.source, $source)
"""

UPSERT_EDGE = """
MATCH (src:Person {key: $src_key})
MERGE (adv:Person {key: $adv_key})
  ON CREATE SET adv.name = $adv_name
MERGE (src)-[r:DOCTORAL_ADVISOR]->(adv)
"""


# ─── Loader ────────────────────────────────────────────────────────────


def _run_safe(session, stmt: str) -> None:
    """Run a statement; ignore "already exists" style errors."""
    try:
        session.run(stmt).consume()
    except Exception as exc:  # Memgraph throws on duplicate constraints
        logger.debug("ignored: %s (%s)", stmt, exc)


def load(
    enrichment_path: Path,
    bolt_uri: str,
    user: str = "",
    password: str = "",
    dry_run: bool = False,
    batch_size: int = 500,
) -> dict:
    if not enrichment_path.exists():
        raise SystemExit(f"enrichment file not found: {enrichment_path}")
    data = json.loads(enrichment_path.read_text(encoding="utf-8"))
    by_name: dict[str, dict] = data.get("by_name") or {}
    if not by_name:
        raise SystemExit("enrichment file has no 'by_name' records")

    print(f"loading {len(by_name)} persons from {enrichment_path}")
    if dry_run:
        print("(dry run — connection not established)")
        return {"persons": len(by_name), "dry_run": True}

    auth = (user, password) if user else None
    driver = GraphDatabase.driver(bolt_uri, auth=auth, connection_timeout=5)
    driver.verify_connectivity()
    print(f"connected to {bolt_uri}")

    stats = {"persons": 0, "edges": 0}
    t0 = time.time()

    with driver.session() as session:
        # Schema setup (idempotent)
        _run_safe(session, CONSTRAINT_KEY)
        _run_safe(session, INDEX_GID)
        _run_safe(session, INDEX_NAME)

        # Phase 1: upsert persons. Batch via explicit transactions.
        batch: list[dict] = []

        def _flush_persons():
            if not batch:
                return
            tx = session.begin_transaction()
            try:
                for p in batch:
                    tx.run(UPSERT_PERSON, **p)
                tx.commit()
            except Exception:
                tx.rollback()
                raise
            stats["persons"] += len(batch)
            batch.clear()

        for key, rec in by_name.items():
            batch.append(
                {
                    "key": key,
                    "name": rec.get("CanonicalLatin", key),
                    "global_id": rec.get("GlobalID"),
                    "birth_year": rec.get("BirthYear"),
                    "death_year": rec.get("DeathYear"),
                    "institution": rec.get("Institution"),
                    "country": rec.get("Country"),
                    "source": rec.get("Source"),
                }
            )
            if len(batch) >= batch_size:
                _flush_persons()
                print(f"  persons: {stats['persons']}", end="\r", flush=True)
        _flush_persons()
        print(f"  persons loaded: {stats['persons']}")

        # Phase 2: upsert advisor edges.
        edge_batch: list[dict] = []

        def _flush_edges():
            if not edge_batch:
                return
            tx = session.begin_transaction()
            try:
                for e in edge_batch:
                    tx.run(UPSERT_EDGE, **e)
                tx.commit()
            except Exception:
                tx.rollback()
                raise
            stats["edges"] += len(edge_batch)
            edge_batch.clear()

        for src_key, rec in by_name.items():
            for adv in rec.get("Advisors") or []:
                adv_name = adv.get("name") if isinstance(adv, dict) else adv
                if not adv_name:
                    continue
                adv_key = _normalize_key(adv_name)
                if not adv_key:
                    continue
                edge_batch.append(
                    {"src_key": src_key, "adv_key": adv_key, "adv_name": adv_name}
                )
                if len(edge_batch) >= batch_size:
                    _flush_edges()
                    print(f"  edges: {stats['edges']}", end="\r", flush=True)
        _flush_edges()
        print(f"  edges loaded: {stats['edges']}")

    driver.close()
    stats["elapsed_s"] = round(time.time() - t0, 1)
    print(f"done in {stats['elapsed_s']}s")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bolt", default=os.getenv("MEMGRAPH_BOLT", "bolt://localhost:7687")
    )
    parser.add_argument("--user", default=os.getenv("MEMGRAPH_USER", ""))
    parser.add_argument("--password", default=os.getenv("MEMGRAPH_PASSWORD", ""))
    parser.add_argument("--source", default=str(ENRICHMENT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch", type=int, default=500)
    args = parser.parse_args()

    stats = load(
        Path(args.source),
        bolt_uri=args.bolt,
        user=args.user,
        password=args.password,
        dry_run=args.dry_run,
        batch_size=args.batch,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
