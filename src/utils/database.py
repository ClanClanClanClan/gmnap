"""
Database layer for GMNAP with DuckDB primary and SQLite fallback.
Handles collision analytics and surname statistics.
"""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

try:
    import duckdb

    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    duckdb = None

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Configuration for database operations."""

    db_path: str = "data/gmnap.db"
    memory_threshold_gb: float = 2.0
    use_duckdb: bool = True
    enable_wal: bool = True
    cache_size_mb: int = 256


class DatabaseManager:
    """
    Manages database operations with DuckDB primary and SQLite fallback.
    Automatically switches to SQLite if memory usage exceeds threshold.
    """

    # Class-level lock for thread-safe initialization
    _init_lock = threading.Lock()
    _initialized_databases = set()  # Track which databases have been initialized

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.db_path = Path(self.config.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = None
        self.db_type = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database connection with fallback logic."""
        # Use class-level lock to prevent concurrent initialization
        with self._init_lock:
            # Check if this database has already been initialized
            db_key = str(self.db_path.absolute())

            # Check memory availability
            memory_available = psutil.virtual_memory().available / (1024**3)  # GB

            if (
                DUCKDB_AVAILABLE
                and self.config.use_duckdb
                and memory_available >= self.config.memory_threshold_gb
            ):
                try:
                    self._initialize_duckdb()
                    logger.info("Initialized DuckDB database")
                except Exception as e:
                    logger.warning(f"Failed to initialize DuckDB: {e}, falling back to SQLite")
                    self._initialize_sqlite()
            else:
                self._initialize_sqlite()
                if not DUCKDB_AVAILABLE:
                    logger.info("DuckDB not available, using SQLite")
                else:
                    logger.info("Using SQLite due to memory constraints")

            # Mark this database as initialized
            self._initialized_databases.add(db_key)

    def _initialize_duckdb(self):
        """Initialize DuckDB connection."""
        self.connection = duckdb.connect(str(self.db_path))
        self.db_type = "duckdb"

        # Configure DuckDB
        self.connection.execute(f"PRAGMA memory_limit='{self.config.memory_threshold_gb}GB'")
        self.connection.execute("PRAGMA threads=4")

        self._create_duckdb_tables()

    def _initialize_sqlite(self):
        """Initialize SQLite connection."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.db_type = "sqlite"

        # Configure SQLite
        if self.config.enable_wal:
            self.connection.execute("PRAGMA journal_mode=WAL")

        self.connection.execute(
            f"PRAGMA cache_size={self.config.cache_size_mb * 1024 // 4}"
        )  # 4KB pages
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute("PRAGMA temp_store=MEMORY")

        self._create_sqlite_tables()

    def _create_duckdb_tables(self):
        """Create tables for DuckDB."""
        # Use BEGIN/COMMIT to ensure table creation is atomic
        self.connection.execute("BEGIN TRANSACTION")
        try:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS initial_stats (
                    global_id VARCHAR PRIMARY KEY,
                    canonical_latin VARCHAR NOT NULL,
                    canonical_native VARCHAR NOT NULL,
                    family_name VARCHAR NOT NULL,
                    given_name VARCHAR NOT NULL,
                    birth_year INTEGER,
                    death_year INTEGER,
                    country_codes VARCHAR[],
                    region_code VARCHAR,
                    confidence INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS surname_stats (
                    surname VARCHAR NOT NULL,
                    surname_prefix VARCHAR NOT NULL,
                    birth_decade INTEGER,
                    country_code VARCHAR,
                    region_code VARCHAR,
                    count INTEGER DEFAULT 1,
                    PRIMARY KEY (surname, birth_decade, country_code)
                )
            """
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS collision_analysis (
                    collision_type VARCHAR NOT NULL,
                    collision_key VARCHAR NOT NULL,
                    global_ids VARCHAR[],
                    count INTEGER,
                    severity VARCHAR,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            self.connection.execute("COMMIT")
        except Exception as e:
            self.connection.execute("ROLLBACK")
            raise e

    def _create_sqlite_tables(self):
        """Create tables for SQLite with partial indexing."""
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS initial_stats (
                global_id TEXT PRIMARY KEY,
                canonical_latin TEXT NOT NULL,
                canonical_native TEXT NOT NULL,
                family_name TEXT NOT NULL,
                given_name TEXT NOT NULL,
                birth_year INTEGER,
                death_year INTEGER,
                country_codes TEXT,  -- JSON array as string
                region_code TEXT,
                confidence INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS surname_stats (
                surname TEXT NOT NULL,
                surname_prefix TEXT NOT NULL,
                birth_decade INTEGER,
                country_code TEXT,
                region_code TEXT,
                count INTEGER DEFAULT 1,
                PRIMARY KEY (surname, birth_decade, country_code)
            )
        """
        )

        # Partial index for memory efficiency
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_surname_prefix_decade 
            ON surname_stats(surname_prefix, birth_decade) 
            WHERE birth_decade IS NOT NULL
        """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS collision_analysis (
                collision_type TEXT NOT NULL,
                collision_key TEXT NOT NULL,
                global_ids TEXT,  -- JSON array as string
                count INTEGER,
                severity TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.connection.commit()

    def insert_initial_stats(self, entries: List[Dict[str, Any]]) -> int:
        """
        Insert entries into initial_stats table.

        Args:
            entries: List of entry dictionaries

        Returns:
            Number of entries inserted
        """
        if not entries:
            return 0

        if self.db_type == "duckdb":
            return self._insert_initial_stats_duckdb(entries)
        else:
            return self._insert_initial_stats_sqlite(entries)

    def _insert_initial_stats_duckdb(self, entries: List[Dict[str, Any]]) -> int:
        """Insert entries using DuckDB."""
        values = []
        for entry in entries:
            canonical_latin = list(entry.keys())[0]
            data = entry[canonical_latin]

            # Parse family and given names
            family_name, given_name = self._parse_canonical_name(canonical_latin)

            values.append(
                (
                    data.get("GlobalID"),
                    canonical_latin,
                    data.get("CanonicalNative", canonical_latin),
                    family_name,
                    given_name,
                    data.get("BirthYear"),
                    data.get("DeathYear"),
                    data.get("CountryCodes", []),
                    self._determine_region_code(data),
                    data.get("Confidence", 0),
                )
            )

        # DuckDB doesn't support executemany well with complex types
        for value in values:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO initial_stats 
                (global_id, canonical_latin, canonical_native, family_name, given_name, 
                 birth_year, death_year, country_codes, region_code, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                value,
            )

        return len(values)

    def _insert_initial_stats_sqlite(self, entries: List[Dict[str, Any]]) -> int:
        """Insert entries using SQLite."""
        import json

        values = []
        for entry in entries:
            canonical_latin = list(entry.keys())[0]
            data = entry[canonical_latin]

            # Parse family and given names
            family_name, given_name = self._parse_canonical_name(canonical_latin)

            values.append(
                (
                    data.get("GlobalID"),
                    canonical_latin,
                    data.get("CanonicalNative", canonical_latin),
                    family_name,
                    given_name,
                    data.get("BirthYear"),
                    data.get("DeathYear"),
                    json.dumps(data.get("CountryCodes", [])),
                    self._determine_region_code(data),
                    data.get("Confidence", 0),
                )
            )

        self.connection.executemany(
            """
            INSERT OR REPLACE INTO initial_stats 
            (global_id, canonical_latin, canonical_native, family_name, given_name, 
             birth_year, death_year, country_codes, region_code, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            values,
        )

        self.connection.commit()
        return len(values)

    def build_surname_stats(self) -> Dict[str, Any]:
        """
        Build surname statistics from initial_stats.

        Returns:
            Statistics dictionary
        """
        logger.info("Building surname statistics...")

        # Clear existing stats
        self.connection.execute("DELETE FROM surname_stats")

        if self.db_type == "duckdb":
            return self._build_surname_stats_duckdb()
        else:
            return self._build_surname_stats_sqlite()

    def _build_surname_stats_duckdb(self) -> Dict[str, Any]:
        """Build surname statistics using DuckDB."""
        # Group by surname and birth decade
        self.connection.execute(
            """
            INSERT INTO surname_stats (surname, surname_prefix, birth_decade, country_code, region_code, count)
            SELECT 
                family_name as surname,
                SUBSTR(family_name, 1, 3) as surname_prefix,
                (birth_year // 10) * 10 as birth_decade,
                country_codes[1] as country_code,
                region_code,
                COUNT(*) as count
            FROM initial_stats
            WHERE family_name IS NOT NULL
            GROUP BY family_name, birth_decade, country_codes[1], region_code
        """
        )

        # Get statistics
        stats = self.connection.execute(
            """
            SELECT 
                COUNT(DISTINCT surname) as unique_surnames,
                COUNT(*) as total_combinations,
                AVG(count) as avg_count,
                MAX(count) as max_count
            FROM surname_stats
        """
        ).fetchone()

        return {
            "unique_surnames": stats[0],
            "total_combinations": stats[1],
            "avg_count": stats[2],
            "max_count": stats[3],
        }

    def _build_surname_stats_sqlite(self) -> Dict[str, Any]:
        """Build surname statistics using SQLite."""
        import json

        # Get all entries
        cursor = self.connection.execute(
            """
            SELECT family_name, birth_year, country_codes, region_code
            FROM initial_stats
            WHERE family_name IS NOT NULL
        """
        )

        surname_counts = {}
        for row in cursor:
            family_name, birth_year, country_codes_json, region_code = row

            # Parse country codes
            try:
                country_codes = json.loads(country_codes_json) if country_codes_json else []
            except json.JSONDecodeError:
                country_codes = []

            # Get birth decade
            birth_decade = (birth_year // 10) * 10 if birth_year else None
            country_code = country_codes[0] if country_codes else None

            # Create key
            key = (family_name, birth_decade, country_code, region_code)
            surname_counts[key] = surname_counts.get(key, 0) + 1

        # Insert into database
        values = []
        for (surname, birth_decade, country_code, region_code), count in surname_counts.items():
            surname_prefix = surname[:3] if surname else ""
            values.append((surname, surname_prefix, birth_decade, country_code, region_code, count))

        self.connection.executemany(
            """
            INSERT INTO surname_stats (surname, surname_prefix, birth_decade, country_code, region_code, count)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            values,
        )

        self.connection.commit()

        # Get statistics
        stats = self.connection.execute(
            """
            SELECT 
                COUNT(DISTINCT surname) as unique_surnames,
                COUNT(*) as total_combinations,
                AVG(count) as avg_count,
                MAX(count) as max_count
            FROM surname_stats
        """
        ).fetchone()

        return {
            "unique_surnames": stats[0],
            "total_combinations": stats[1],
            "avg_count": stats[2],
            "max_count": stats[3],
        }

    def detect_collisions(self, threshold: int = 2) -> List[Dict[str, Any]]:
        """
        Detect potential name collisions.

        Args:
            threshold: Minimum count to consider a collision

        Returns:
            List of collision records
        """
        logger.info(f"Detecting collisions with threshold {threshold}...")

        # Clear existing collision analysis
        self.connection.execute("DELETE FROM collision_analysis")

        collisions = []

        # Detect surname collisions
        if self.db_type == "duckdb":
            result = self.connection.execute(
                """
                SELECT surname, birth_decade, country_code, count, 
                       STRING_AGG(DISTINCT region_code, ',') as regions
                FROM surname_stats
                WHERE count >= ?
                GROUP BY surname, birth_decade, country_code, count
                ORDER BY count DESC
            """,
                (threshold,),
            ).fetchall()
        else:
            cursor = self.connection.execute(
                """
                SELECT surname, birth_decade, country_code, count, 
                       GROUP_CONCAT(DISTINCT region_code) as regions
                FROM surname_stats
                WHERE count >= ?
                GROUP BY surname, birth_decade, country_code, count
                ORDER BY count DESC
            """,
                (threshold,),
            )
            result = cursor.fetchall()

        for row in result:
            surname, birth_decade, country_code, count, regions = row

            # Get specific entries for this collision
            global_ids = self._get_global_ids_for_surname(surname, birth_decade, country_code)

            severity = self._determine_collision_severity(count)

            collision = {
                "collision_type": "surname",
                "collision_key": f"{surname}_{birth_decade}_{country_code}",
                "global_ids": global_ids,
                "count": count,
                "severity": severity,
                "metadata": {
                    "surname": surname,
                    "birth_decade": birth_decade,
                    "country_code": country_code,
                    "regions": regions,
                },
            }

            collisions.append(collision)

        # Insert collision analysis
        self._insert_collision_analysis(collisions)

        logger.info(f"Detected {len(collisions)} potential collisions")
        return collisions

    def _get_global_ids_for_surname(
        self, surname: str, birth_decade: Optional[int], country_code: Optional[str]
    ) -> List[str]:
        """Get GlobalIDs for a specific surname collision."""

        query = "SELECT global_id FROM initial_stats WHERE family_name = ?"
        params = [surname]

        if birth_decade is not None:
            query += " AND (birth_year // 10) * 10 = ?"
            params.append(birth_decade)

        if country_code:
            if self.db_type == "duckdb":
                query += " AND ? = ANY(country_codes)"
            else:
                query += " AND country_codes LIKE ?"
                params.append(f'%"{country_code}"%')

        cursor = self.connection.execute(query, params)
        return [row[0] for row in cursor]

    def _insert_collision_analysis(self, collisions: List[Dict[str, Any]]):
        """Insert collision analysis into database."""
        import json

        values = []
        for collision in collisions:
            if self.db_type == "duckdb":
                global_ids = collision["global_ids"]
            else:
                global_ids = json.dumps(collision["global_ids"])

            values.append(
                (
                    collision["collision_type"],
                    collision["collision_key"],
                    global_ids,
                    collision["count"],
                    collision["severity"],
                )
            )

        self.connection.executemany(
            """
            INSERT INTO collision_analysis 
            (collision_type, collision_key, global_ids, count, severity)
            VALUES (?, ?, ?, ?, ?)
        """,
            values,
        )

        if self.db_type == "sqlite":
            self.connection.commit()

    def _parse_canonical_name(self, canonical_latin: str) -> Tuple[str, str]:
        """Parse canonical name into family and given names."""
        if ", " in canonical_latin:
            family_name, given_name = canonical_latin.split(", ", 1)
        else:
            # Handle mononyms or other formats
            family_name = canonical_latin
            given_name = ""

        return family_name.strip(), given_name.strip()

    def _determine_region_code(self, data: Dict[str, Any]) -> str:
        """Determine region code from entry data."""
        # Simple heuristic - would be replaced with actual region detection
        country_codes = data.get("CountryCodes", [])
        if not country_codes:
            return "R0"  # Catch-all

        # Basic mapping for testing
        region_mapping = {
            "US": "A1",
            "GB": "A1",
            "CA": "A1",
            "AU": "A1",
            "NZ": "A1",
            "FR": "A2",
            "DE": "A2",
            "IT": "A2",
            "ES": "A2",
            "PT": "A2",
            "RU": "B1",
            "UA": "B1",
            "BY": "B1",
            "CN": "E1",
            "JP": "E3",
            "KR": "E4",
        }

        return region_mapping.get(country_codes[0], "R0")

    def _determine_collision_severity(self, count: int) -> str:
        """Determine collision severity based on count."""
        if count >= 10:
            return "high"
        elif count >= 5:
            return "medium"
        else:
            return "low"

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}

        # Initial stats count
        cursor = self.connection.execute("SELECT COUNT(*) FROM initial_stats")
        stats["total_entries"] = cursor.fetchone()[0]

        # Surname stats count
        cursor = self.connection.execute("SELECT COUNT(*) FROM surname_stats")
        stats["surname_combinations"] = cursor.fetchone()[0]

        # Collision count
        cursor = self.connection.execute("SELECT COUNT(*) FROM collision_analysis")
        stats["potential_collisions"] = cursor.fetchone()[0]

        # Database type and size
        stats["database_type"] = self.db_type
        stats["database_size_mb"] = (
            self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        )

        return stats

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience functions
def create_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Create a database manager with optional configuration."""
    return DatabaseManager(config)


@contextmanager
def get_database_connection(config: Optional[DatabaseConfig] = None):
    """Context manager for database operations."""
    manager = DatabaseManager(config)
    try:
        yield manager
    finally:
        manager.close()
