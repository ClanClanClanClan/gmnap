"""
SQLite-based analytics as a fallback for DuckDB.

This module provides collision detection and analytics using SQLite,
which is built into Python and doesn't require external installation.
"""

import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SQLiteAnalytics:
    """
    SQLite-based analytics engine for V7 pipeline.

    Provides:
    - Collision detection
    - Field distribution analytics
    - Authority coverage metrics
    - Graph coherence analysis
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize SQLite analytics.

        Args:
            db_path: Path to SQLite database (in-memory if None)
        """
        self.db_path = db_path or ":memory:"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self):
        """Create necessary tables for analytics."""
        cursor = self.conn.cursor()

        # Main entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                global_id TEXT PRIMARY KEY,
                canonical_native TEXT,
                canonical_latin TEXT,
                region_code TEXT,
                authority_sources TEXT,
                graph_coherence REAL,
                entry_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Collision tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_value TEXT,
                global_id_1 TEXT,
                global_id_2 TEXT,
                collision_type TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Field distribution table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_distribution (
                field_name TEXT PRIMARY KEY,
                count INTEGER,
                percentage REAL,
                distinct_values INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Authority coverage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authority_coverage (
                source_name TEXT PRIMARY KEY,
                entries_covered INTEGER,
                coverage_percentage REAL,
                avg_confidence REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def analyze_collisions(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze entries for collisions.

        Args:
            entries: List of entry dictionaries

        Returns:
            Collision analysis results
        """
        cursor = self.conn.cursor()
        collisions = []
        collision_types = {
            "exact_duplicate": 0,
            "canonical_latin_collision": 0,
            "canonical_native_collision": 0,
            "hash_collision": 0,
        }

        # Build collision detection maps
        latin_map = {}
        native_map = {}
        hash_map = {}

        for entry in entries:
            global_id = entry.get("GlobalID", "")
            canonical_latin = entry.get("CanonicalLatin", "")
            canonical_native = entry.get("CanonicalNative", "")

            # Generate entry hash
            hash_input = f"{canonical_native}_{canonical_latin}"
            entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

            # Check for Latin collisions
            if canonical_latin and canonical_latin in latin_map:
                collisions.append(
                    {
                        "type": "canonical_latin_collision",
                        "global_id_1": latin_map[canonical_latin],
                        "global_id_2": global_id,
                        "value": canonical_latin,
                    }
                )
                collision_types["canonical_latin_collision"] += 1

                # Record in database
                cursor.execute(
                    """
                    INSERT INTO collisions (hash_value, global_id_1, global_id_2, collision_type)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        canonical_latin,
                        latin_map[canonical_latin],
                        global_id,
                        "canonical_latin",
                    ),
                )
            else:
                latin_map[canonical_latin] = global_id

            # Check for Native collisions
            if canonical_native and canonical_native in native_map:
                collisions.append(
                    {
                        "type": "canonical_native_collision",
                        "global_id_1": native_map[canonical_native],
                        "global_id_2": global_id,
                        "value": canonical_native,
                    }
                )
                collision_types["canonical_native_collision"] += 1

                cursor.execute(
                    """
                    INSERT INTO collisions (hash_value, global_id_1, global_id_2, collision_type)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        canonical_native,
                        native_map[canonical_native],
                        global_id,
                        "canonical_native",
                    ),
                )
            else:
                native_map[canonical_native] = global_id

            # Check for hash collisions
            if entry_hash in hash_map and hash_map[entry_hash] != global_id:
                collisions.append(
                    {
                        "type": "hash_collision",
                        "global_id_1": hash_map[entry_hash],
                        "global_id_2": global_id,
                        "hash": entry_hash,
                    }
                )
                collision_types["hash_collision"] += 1

                cursor.execute(
                    """
                    INSERT INTO collisions (hash_value, global_id_1, global_id_2, collision_type)
                    VALUES (?, ?, ?, ?)
                """,
                    (entry_hash, hash_map[entry_hash], global_id, "hash"),
                )
            else:
                hash_map[entry_hash] = global_id

            # Store entry
            cursor.execute(
                """
                INSERT OR REPLACE INTO entries (global_id, canonical_native, canonical_latin, entry_hash)
                VALUES (?, ?, ?, ?)
            """,
                (global_id, canonical_native, canonical_latin, entry_hash),
            )

        self.conn.commit()

        # Calculate collision rate
        total_entries = len(entries)
        total_collisions = sum(collision_types.values())
        collision_rate = (
            (total_collisions / total_entries * 100) if total_entries > 0 else 0
        )

        return {
            "total_entries": total_entries,
            "total_collisions": total_collisions,
            "collision_rate": collision_rate,
            "collision_types": collision_types,
            "collisions": collisions[:10],  # First 10 for review
        }

    def compute_field_distribution(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute field distribution statistics.

        Args:
            entries: List of entry dictionaries

        Returns:
            Field distribution analysis
        """
        cursor = self.conn.cursor()
        field_counts = {}
        field_distinct = {}
        total_entries = len(entries)

        # Count field occurrences
        for entry in entries:
            for field, value in entry.items():
                if field not in field_counts:
                    field_counts[field] = 0
                    field_distinct[field] = set()

                if value is not None and value != "":
                    field_counts[field] += 1
                    field_distinct[field].add(str(value))

        # Store distribution
        distribution = {}
        for field, count in field_counts.items():
            percentage = (count / total_entries * 100) if total_entries > 0 else 0
            distinct_count = len(field_distinct[field])

            cursor.execute(
                """
                INSERT OR REPLACE INTO field_distribution (field_name, count, percentage, distinct_values)
                VALUES (?, ?, ?, ?)
            """,
                (field, count, percentage, distinct_count),
            )

            distribution[field] = {
                "count": count,
                "percentage": percentage,
                "distinct_values": distinct_count,
            }

        self.conn.commit()

        return {
            "total_fields": len(field_counts),
            "total_entries": total_entries,
            "field_distribution": distribution,
        }

    def analyze_authority_coverage(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze authority source coverage.

        Args:
            entries: List of entry dictionaries

        Returns:
            Authority coverage analysis
        """
        cursor = self.conn.cursor()
        authority_stats = {}
        total_entries = len(entries)
        entries_with_authority = 0

        for entry in entries:
            authority_sources = entry.get("AuthoritySources", [])
            if authority_sources:
                entries_with_authority += 1
                for source in authority_sources:
                    source_name = (
                        source
                        if isinstance(source, str)
                        else source.get("source", "unknown")
                    )
                    if source_name not in authority_stats:
                        authority_stats[source_name] = {"count": 0, "confidence_sum": 0}
                    authority_stats[source_name]["count"] += 1
                    # Add confidence if available
                    if isinstance(source, dict):
                        confidence = source.get("confidence", 1.0)
                        authority_stats[source_name]["confidence_sum"] += confidence

        # Calculate coverage percentages
        coverage_analysis = {}
        for source, stats in authority_stats.items():
            coverage_pct = (
                (stats["count"] / total_entries * 100) if total_entries > 0 else 0
            )
            avg_confidence = (
                (stats["confidence_sum"] / stats["count"]) if stats["count"] > 0 else 0
            )

            cursor.execute(
                """
                INSERT OR REPLACE INTO authority_coverage (source_name, entries_covered, coverage_percentage, avg_confidence)
                VALUES (?, ?, ?, ?)
            """,
                (source, stats["count"], coverage_pct, avg_confidence),
            )

            coverage_analysis[source] = {
                "entries_covered": stats["count"],
                "coverage_percentage": coverage_pct,
                "average_confidence": avg_confidence,
            }

        self.conn.commit()

        overall_coverage = (
            (entries_with_authority / total_entries * 100) if total_entries > 0 else 0
        )

        return {
            "total_entries": total_entries,
            "entries_with_authority": entries_with_authority,
            "overall_coverage_percentage": overall_coverage,
            "source_coverage": coverage_analysis,
        }

    def compute_graph_coherence(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute graph coherence metrics.

        Args:
            entries: List of entry dictionaries

        Returns:
            Graph coherence analysis
        """
        total_coherence = 0
        coherence_count = 0
        coherence_distribution = {
            "high": 0,
            "medium": 0,
            "low": 0,
        }  # > 0.8  # 0.5 - 0.8  # < 0.5

        for entry in entries:
            coherence = entry.get("GraphCoherence", 0)
            if coherence > 0:
                total_coherence += coherence
                coherence_count += 1

                if coherence > 0.8:
                    coherence_distribution["high"] += 1
                elif coherence > 0.5:
                    coherence_distribution["medium"] += 1
                else:
                    coherence_distribution["low"] += 1

        avg_coherence = (
            (total_coherence / coherence_count) if coherence_count > 0 else 0
        )

        return {
            "average_coherence": avg_coherence,
            "entries_with_coherence": coherence_count,
            "distribution": coherence_distribution,
            "meets_threshold": avg_coherence >= 0.85,  # V7 requirement
        }

    def generate_analytics_report(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report.

        Args:
            entries: List of entry dictionaries

        Returns:
            Complete analytics report
        """
        logger.info(f"Generating analytics report for {len(entries)} entries")

        # Run all analyses
        collision_analysis = self.analyze_collisions(entries)
        field_distribution = self.compute_field_distribution(entries)
        authority_coverage = self.analyze_authority_coverage(entries)
        graph_coherence = self.compute_graph_coherence(entries)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_entries": len(entries),
            "collision_analysis": collision_analysis,
            "field_distribution": field_distribution,
            "authority_coverage": authority_coverage,
            "graph_coherence": graph_coherence,
            "database": "SQLite (DuckDB alternative)",
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
