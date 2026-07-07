from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union

try:
    import duckdb  # type: ignore
except Exception:
    duckdb = None


class DuckDBAnalytics:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if duckdb is None:
            self.conn = None
            self.skipped = True
        else:
            self.conn = duckdb.connect(db_path)
            self.skipped = False
            # DuckDB syntax (not SQLite)
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS entries(GlobalID VARCHAR PRIMARY KEY, order_key VARCHAR, BirthYear INTEGER, payload VARCHAR)"
            )
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS changes(ts TIMESTAMP DEFAULT current_timestamp, action VARCHAR, GlobalID VARCHAR)"
            )

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and close connection if needed."""
        if self.conn is not None and hasattr(self.conn, "close"):
            self.conn.close()
        return False

    def load_entries(self, rows: List[Dict[str, Any]]):
        """Bulk-load (GlobalID, order_key, BirthYear) into the entries table.

        Performance (R56): the previous implementation built a
        ``json.dumps(r)`` payload per row and pushed everything through
        ``executemany``, whose per-row Python->DuckDB parameter conversion
        measures ~1.5 ms/row even for tiny rows (~26 min/1M) — and far worse
        with multi-KB payloads. A 1M synthetic benchmark spent SIX HOURS in
        this one call before being stopped. Rows are now streamed to a temp
        CSV and ingested via DuckDB's vectorized ``read_csv`` (~2 s/1M,
        measured). Two deliberate semantic reductions, both safe:

        - The ``payload`` column is left NULL: nothing reads it back — the
          collision queries use only GlobalID/order_key/BirthYear, and
          ``write_change_log`` writes its own payloads for its own rows.
        - ``BirthYear`` is coerced to int when possible, else NULL (the old
          path let DuckDB coerce and CRASHED the stage on junk input).
        """
        if self.skipped:
            return

        import csv
        import os
        import tempfile

        self.conn.execute("DELETE FROM entries")

        # Track seen GlobalIDs to handle duplicates: real duplicate ids are
        # detected/reported elsewhere; the table keeps first occurrence.
        seen_gids = set()

        fd, path = tempfile.mkstemp(suffix=".csv", prefix="gmnap_s5_")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                for r in rows:
                    gid = r.get("GlobalID")
                    if not gid or gid in seen_gids:
                        continue
                    seen_gids.add(gid)
                    by = r.get("BirthYear")
                    try:
                        by = int(by) if by not in (None, "") else None
                    except (TypeError, ValueError):
                        by = None  # masked/junk year -> NULL, never a crash
                    w.writerow([gid, (r.get("CanonicalLatin") or "").lower(), by])
            if seen_gids:
                safe_path = path.replace("'", "''")
                self.conn.execute(
                    "INSERT INTO entries "
                    "SELECT column0, column1, column2, NULL FROM read_csv("
                    f"'{safe_path}', header=false, "
                    "columns={'column0':'VARCHAR','column1':'VARCHAR',"
                    "'column2':'INTEGER'})"
                )
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def suffix_duplicates(
        self, entries: List[Dict[str, Any]] = None
    ) -> Union[Tuple[List[Dict[str, Any]], int], List[Tuple[str, str]]]:
        """
        Detect and suffix duplicate entries based on order_key and BirthYear.

        Args:
            entries: Optional list of entries to modify in place

        Returns:
            If entries provided: (modified_entries, suffix_count)
            Otherwise: List of (original_id, suffixed_id) tuples
        """
        if self.skipped:
            # Return a 2-tuple whenever the caller passed ``entries``
            # (even when the list is empty). Previously this returned a
            # bare ``[]`` for empty-list inputs, which broke callers
            # doing ``entries, n = analytics.suffix_duplicates(entries)``
            # with ``ValueError: not enough values to unpack``. This
            # path fires whenever Stage 2 strips all entries (e.g.
            # security rejected them) and Stage 5 then unpacks the
            # result.
            if entries is not None:
                return (entries, 0)
            return []

        # When entries are passed (the stage-5 "resolve" call) make NO
        # GlobalID changes. The old behavior rewrote the id of every
        # name+birth-year group member after the first (B -> B--1), but
        # those entries already have DISTINCT, unique ids: the GlobalID
        # encodes CanonicalNative + birth + death, and stage 1 suffixes any
        # TRUE id collision. So two genuinely-different people who merely
        # share an order_key + BirthYear (e.g. different death year or
        # native script) have different ids — re-suffixing them by NAME
        # corrupted a correct id. GlobalID uniqueness is stage 1's job;
        # name collisions (same name, different id) are a REPORTING concern
        # (detect_collisions / analyze_collisions), not an id rewrite.
        if entries is not None:
            return entries, 0

        out = []
        # Report-only path (entries is None): list name + birth-year
        # collision groups for diagnostics. This does NOT mutate any id.
        # Only consider entries with non-empty order_key as potential duplicates
        # Empty order_key means no CanonicalLatin, which shouldn't be considered a duplicate
        dup_keys = self.conn.execute(
            "SELECT order_key, BirthYear, COUNT(*) AS c FROM entries WHERE order_key != '' GROUP BY 1,2 HAVING c>1"
        ).fetchall()
        for ok, by, _ in dup_keys:
            # Handle NULL BirthYear properly
            if by is None:
                gids = [
                    x[0]
                    for x in self.conn.execute(
                        "SELECT GlobalID FROM entries WHERE order_key=? AND BirthYear IS NULL ORDER BY GlobalID",
                        [ok],
                    ).fetchall()
                ]
            else:
                gids = [
                    x[0]
                    for x in self.conn.execute(
                        "SELECT GlobalID FROM entries WHERE order_key=? AND BirthYear = ? ORDER BY GlobalID",
                        [ok, by],
                    ).fetchall()
                ]
            for i, g in enumerate(gids[1:], start=1):
                # Check if GlobalID already has a suffix (--N pattern)
                if "--" in g and g.split("--")[-1].isdigit():
                    # Already suffixed, skip it
                    continue
                out.append((g, f"{g}--{i}"))

        # Diagnostics list only — never applied to any entry's GlobalID
        # (the entries-provided path returned above without mutating ids).
        return out

    def analyze_collisions(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze entries for collisions and duplicates.

        Args:
            entries: List of entries to analyze

        Returns:
            Analytics results including collision stats
        """
        if self.skipped:
            return {
                "total_entries": len(entries),
                "unique_names": len(entries),
                "collisions": 0,
                "duplicates": [],
                "status": "skipped",
            }

        # Load entries for analysis
        self.load_entries(entries)

        # Get name collision information (same name, different GlobalID)
        # These are NOT duplicate GlobalIDs, just content collisions
        name_collisions = self.suffix_duplicates()

        # Count actual GlobalID duplicates (should be 0 if IDs are unique)
        from collections import Counter

        global_ids = [e.get("GlobalID") for e in entries if e.get("GlobalID")]
        id_counts = Counter(global_ids)
        actual_duplicate_count = sum(1 for count in id_counts.values() if count > 1)

        # Compute statistics
        unique_names = len(set(e.get("CanonicalLatin", "").lower() for e in entries))

        return {
            "total_entries": len(entries),
            "unique_names": unique_names,
            "collisions": actual_duplicate_count,  # Report actual GlobalID duplicates, not name collisions
            "duplicates": name_collisions,  # Keep name collisions for suffixing
            "collision_rate": (
                actual_duplicate_count / len(entries) * 100 if entries else 0
            ),
            "status": "analyzed",
        }

    def detect_collisions(self) -> List[Tuple[str, str]]:
        """
        Detect collision groups in loaded entries.

        Returns:
            List of collision groups (duplicate GlobalIDs)
        """
        if self.skipped:
            return []

        # Call suffix_duplicates without entries to get list of duplicates
        return self.suffix_duplicates()

    def write_change_log(
        self, old_rows: List[Dict[str, Any]], new_rows: List[Dict[str, Any]]
    ):
        if self.skipped:
            return "SKIPPED"
        import json

        o = {r.get("GlobalID"): r for r in old_rows if r.get("GlobalID")}
        n = {r.get("GlobalID"): r for r in new_rows if r.get("GlobalID")}
        for gid in sorted(set(n) - set(o)):
            # First delete if exists, then insert (workaround for INSERT OR REPLACE)
            self.conn.execute("DELETE FROM entries WHERE GlobalID = ?", [gid])
            self.conn.execute(
                "INSERT INTO entries VALUES (?, ?, ?, ?)",
                [
                    gid,
                    (n[gid].get("CanonicalLatin") or "").lower(),
                    n[gid].get("BirthYear"),
                    json.dumps(n[gid]),
                ],
            )
            self.conn.execute(
                "INSERT INTO changes(action, GlobalID) VALUES ('INSERT', ?)", [gid]
            )
        for gid in sorted(set(o) - set(n)):
            self.conn.execute("DELETE FROM entries WHERE GlobalID=?", [gid])
            self.conn.execute(
                "INSERT INTO changes(action, GlobalID) VALUES ('DELETE', ?)", [gid]
            )
        for gid in sorted(set(o) & set(n)):
            if o[gid] != n[gid]:
                self.conn.execute(
                    "UPDATE entries SET payload=?, order_key=?, BirthYear=? WHERE GlobalID=?",
                    [
                        json.dumps(n[gid]),
                        (n[gid].get("CanonicalLatin") or "").lower(),
                        n[gid].get("BirthYear"),
                        gid,
                    ],
                )
                self.conn.execute(
                    "INSERT INTO changes(action, GlobalID) VALUES ('UPDATE', ?)", [gid]
                )
        return "OK"

    def generate_analytics_report(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report for the entries.

        Args:
            entries: List of entries to analyze

        Returns:
            Dictionary containing analytics metrics
        """
        if self.skipped:
            return {
                "status": "skipped",
                "reason": "DuckDB not available",
                "total_entries": len(entries),
            }

        # Load entries for analysis
        self.load_entries(entries)

        # Gather metrics
        total = len(entries)

        # Get collision information
        collisions = self.detect_collisions()
        collision_count = len(collisions)
        collision_rate = (collision_count / total * 100) if total > 0 else 0

        # Get field completeness
        field_completeness = {}
        for field in ["CanonicalNative", "CanonicalLatin", "GlobalID", "BirthYear"]:
            count = sum(1 for e in entries if e.get(field))
            field_completeness[field] = (count / total * 100) if total > 0 else 0

        # Authority source coverage
        sources_used = set()
        for entry in entries:
            if entry.get("Sources"):
                sources_used.update(entry["Sources"])

        # Quality metrics
        with_region = sum(1 for e in entries if e.get("DetectedRegion"))
        with_coherence = sum(1 for e in entries if e.get("BayesianCoherence"))

        return {
            "total_entries": total,
            "collision_rate": collision_rate,
            "collision_count": collision_count,
            "field_completeness": field_completeness,
            "authority_sources": list(sources_used),
            "quality_metrics": {
                "with_region": (with_region / total * 100) if total > 0 else 0,
                "with_coherence": (with_coherence / total * 100) if total > 0 else 0,
            },
        }
