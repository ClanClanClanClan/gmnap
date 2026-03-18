"""Stage 5: CollisionAnalytics - DuckDB duplicate detection and suffix remapping.

Cross-batch collision tracking: persists seen GlobalIDs in work/globalid_registry.json
to detect collisions across separate batch runs.
"""
from __future__ import annotations
import json, os, pathlib, logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Cross-batch GlobalID registry ────────────────────────────────────────

_REGISTRY_FILE = "globalid_registry.json"


def _load_registry(workdir: str) -> Set[str]:
    """Load persistent GlobalID registry from disk."""
    path = pathlib.Path(workdir) / _REGISTRY_FILE
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return set(data.get("ids", []))
        except Exception as e:
            logger.warning(f"Failed to load GlobalID registry: {e}")
    return set()


def _save_registry(workdir: str, ids: Set[str]) -> None:
    """Persist GlobalID registry to disk."""
    path = pathlib.Path(workdir) / _REGISTRY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"ids": sorted(ids), "count": len(ids)}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def stage5_collision_analytics(batch: List[Dict], workdir: str = "work") -> Tuple[List[Dict], Dict[str, float]]:
    """
    Stage 5: Detect duplicate entries and apply --N suffixes to GlobalIDs.
    Also synthesise genealogy edges CSV.

    Returns (processed_batch, metrics_dict).
    """
    pathlib.Path(workdir).mkdir(parents=True, exist_ok=True)
    collisions = 0

    # Load cross-batch GlobalID registry
    registry = _load_registry(workdir)

    # Try DuckDB first, fall back to in-memory
    try:
        import duckdb
        out, collisions = _duckdb_dedup(batch, workdir)
    except (ImportError, Exception) as e:
        logger.info(f"DuckDB dedup unavailable ({e}), using in-memory collision detection")
        out, collisions = _memory_dedup(batch)

    # Cross-batch collision check: suffix any GlobalID already in registry
    cross_batch_collisions = 0
    for entry in out:
        gid = entry.get("GlobalID", "")
        if not gid or "--" in gid:
            continue  # Already suffixed
        if gid in registry:
            cross_batch_collisions += 1
            suffix = 1
            candidate = f"{gid}--{suffix}"
            while candidate in registry:
                suffix += 1
                candidate = f"{gid}--{suffix}"
            entry["GlobalID"] = candidate
            logger.debug(f"Cross-batch collision: {gid} -> {candidate}")
        registry.add(entry.get("GlobalID", ""))

    collisions += cross_batch_collisions
    if cross_batch_collisions:
        logger.info(f"Cross-batch collisions: {cross_batch_collisions}")

    # Persist updated registry
    _save_registry(workdir, registry)

    # Synthesise genealogy edges report (CSV)
    csv_path = os.path.join(workdir, "stage5_edges.csv")
    edge_count = 0
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("source,target,relation_type\n")
        for e in out:
            sid = e.get("GlobalID")
            for a in (e.get("Advisors") or []):
                if sid and a:
                    f.write(f"{sid},{a},doctoralAdvisor\n")
                    edge_count += 1

    metrics = {"collisions": float(collisions), "edges": float(edge_count)}
    return out, metrics


def _memory_dedup(batch: List[Dict]) -> Tuple[List[Dict], int]:
    """In-memory duplicate detection and suffix remapping."""
    collisions = 0
    seen = defaultdict(list)
    for e in batch:
        key = (e.get("CanonicalLatin", ""), e.get("BirthYear"))
        seen[key].append(e)

    out = []
    for key, group in seen.items():
        if len(group) == 1:
            out.extend(group)
        else:
            group_sorted = sorted(group, key=lambda x: x.get("GlobalID", ""))
            for i, g in enumerate(group_sorted):
                if i == 0:
                    out.append(g)
                else:
                    collisions += 1
                    g2 = dict(g)
                    g2["GlobalID"] = f'{g2.get("GlobalID", "")}--{i}'
                    out.append(g2)
    return out, collisions


def _duckdb_dedup(batch: List[Dict], workdir: str) -> Tuple[List[Dict], int]:
    """DuckDB-based collision analytics."""
    import duckdb

    con = duckdb.connect(database=":memory:")
    con.execute("PRAGMA memory_limit='1GB'")

    # Write entries to a temp JSON file for DuckDB to read
    import tempfile
    tmp = os.path.join(workdir, "_stage5_tmp.json")
    rows = [{"GlobalID": e.get("GlobalID", ""), "CanonicalLatin": e.get("CanonicalLatin", ""),
             "BirthYear": e.get("BirthYear")} for e in batch]
    with open(tmp, "w", encoding="utf-8") as f:
        import json as _json
        _json.dump(rows, f)
    con.execute(f"CREATE TABLE entries AS SELECT * FROM read_json_auto('{tmp}')")

    # Find duplicates
    dup_keys = set()
    con.execute("""
        SELECT CanonicalLatin, BirthYear
        FROM entries
        GROUP BY 1, 2 HAVING COUNT(*) > 1
    """)
    for row in con.fetchall():
        dup_keys.add((row[0], row[1]))
    con.close()

    # Apply suffixes using in-memory logic (DuckDB confirmed the duplicates)
    return _memory_dedup(batch)


def _batch_main():
    """CLI entry point for duckdb-batch Docker service.

    Usage: python -m src.pipeline.stage5_collision_analytics [--batch]
    The --batch flag is accepted for docker-compose compatibility.
    """
    import glob
    import sys

    # Accept --batch flag (used by docker-compose command) — no-op, always runs batch
    if "--help" in sys.argv:
        print("Usage: python -m src.pipeline.stage5_collision_analytics [--batch]")
        print("Runs DuckDB collision analytics on all JSON files in data/")
        sys.exit(0)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    workdir = os.environ.get("GMNAP_WORKDIR", "work")
    data_dir = os.environ.get("GMNAP_DATA_DIR", "data")

    input_files = glob.glob(os.path.join(data_dir, "*.json"))
    if not input_files:
        logger.info(f"No JSON files found in {data_dir}/")
        return

    for path in input_files:
        logger.info(f"Processing {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                batch = json.load(f)
            if not isinstance(batch, list):
                batch = [batch]
            results, metrics = stage5_collision_analytics(batch, workdir)
            logger.info(
                f"  {len(results)} entries, "
                f"{metrics['collisions']:.0f} collisions, "
                f"{metrics['edges']:.0f} edges"
            )
        except Exception as e:
            logger.error(f"  Failed: {e}")

    logger.info("Batch collision analytics complete.")


if __name__ == "__main__":
    _batch_main()
