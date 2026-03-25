"""
Authority response caching system for GMNAP.
Implements disk-based caching with TTL and size limits.
"""

import hashlib
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached authority response."""

    key: str
    service: str
    query: str
    response: Dict[str, Any]
    timestamp: float
    ttl: int  # seconds
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > (self.timestamp + self.ttl)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        return cls(**data)


class AuthorityCache:
    """
    Disk-based cache for authority API responses.

    Features:
    - SQLite backend for persistence
    - TTL support per service
    - LRU eviction when size limit reached
    - Thread-safe operations
    - Query normalization for better hit rates
    """

    def __init__(self, cache_dir: Path, max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "authority_cache.db"
        self.max_size_bytes = max_size_mb * 1024 * 1024

        # Default TTLs per service (in seconds)
        self.default_ttls = {
            "OpenAlex": 86400 * 7,  # 7 days
            "Crossref": 86400 * 7,  # 7 days
            "ORCID": 86400 * 30,  # 30 days (stable data)
            "zbMATH": 86400 * 14,  # 14 days
            "DBLP": 86400 * 14,  # 14 days
            "MathSciNet": 86400 * 30,  # 30 days
            "default": 86400,  # 1 day default
        }

        self._init_db()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    ttl INTEGER NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    size_bytes INTEGER NOT NULL
                )
            """
            )

            # Create indexes for efficient queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_service_query 
                ON cache_entries(service, query)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON cache_entries(timestamp)
            """
            )

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _generate_key(self, service: str, query: str) -> str:
        """Generate cache key from service and query."""
        # Normalize query for better cache hits
        normalized_query = self._normalize_query(query)
        key_data = f"{service}:{normalized_query}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _normalize_query(self, query: str) -> str:
        """Normalize query for better cache hit rate."""
        # Remove extra whitespace
        normalized = " ".join(query.split())

        # Convert to lowercase for case-insensitive matching
        normalized = normalized.lower()

        # Remove common punctuation variations
        normalized = normalized.replace(",", " ").replace(".", " ")

        return normalized.strip()

    def get(self, service: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a query.

        Args:
            service: Authority service name
            query: Search query

        Returns:
            Cached response or None if not found/expired
        """
        key = self._generate_key(service, query)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM cache_entries WHERE key = ?
            """,
                (key,),
            )

            row = cursor.fetchone()

            if row:
                # Check expiration
                if time.time() > (row["timestamp"] + row["ttl"]):
                    # Expired, delete it
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    self._stats["misses"] += 1
                    return None

                # Update hit count
                conn.execute(
                    """
                    UPDATE cache_entries 
                    SET hit_count = hit_count + 1 
                    WHERE key = ?
                """,
                    (key,),
                )

                self._stats["hits"] += 1

                # Parse and return response
                try:
                    return json.loads(row["response"])
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse cached response for {service}:{query}")
                    return None

            self._stats["misses"] += 1
            return None

    def put(
        self, service: str, query: str, response: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """
        Cache an authority response.

        Args:
            service: Authority service name
            query: Search query
            response: API response to cache
            ttl: Time to live in seconds (uses default if not specified)
        """
        key = self._generate_key(service, query)

        # Use service-specific TTL or default
        if ttl is None:
            ttl = self.default_ttls.get(service, self.default_ttls["default"])

        # Serialize response
        response_json = json.dumps(response)
        size_bytes = len(response_json.encode())

        # Check if we need to evict entries
        self._evict_if_needed(size_bytes)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_entries 
                (key, service, query, response, timestamp, ttl, hit_count, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
                (key, service, query, response_json, time.time(), ttl, size_bytes),
            )

    def _evict_if_needed(self, new_size: int) -> None:
        """Evict old entries if cache size limit exceeded."""
        with self._get_connection() as conn:
            # Get current cache size
            cursor = conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
            current_size = cursor.fetchone()[0] or 0

            if current_size + new_size > self.max_size_bytes:
                # Need to evict - use LRU strategy
                needed_space = (current_size + new_size) - self.max_size_bytes
                freed_space = 0

                # Select least recently used entries
                cursor = conn.execute(
                    """
                    SELECT key, size_bytes 
                    FROM cache_entries 
                    ORDER BY timestamp + (hit_count * 3600) ASC
                """
                )

                keys_to_delete = []
                for row in cursor:
                    keys_to_delete.append(row["key"])
                    freed_space += row["size_bytes"]
                    self._stats["evictions"] += 1

                    if freed_space >= needed_space:
                        break

                # Delete selected entries
                if keys_to_delete:
                    placeholders = ",".join("?" * len(keys_to_delete))
                    conn.execute(
                        f"""
                        DELETE FROM cache_entries 
                        WHERE key IN ({placeholders})
                    """,
                        keys_to_delete,
                    )

    def clear(self, service: Optional[str] = None) -> None:
        """
        Clear cache entries.

        Args:
            service: Clear only entries for this service, or all if None
        """
        with self._get_connection() as conn:
            if service:
                conn.execute("DELETE FROM cache_entries WHERE service = ?", (service,))
            else:
                conn.execute("DELETE FROM cache_entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_entries,
                    SUM(size_bytes) as total_size,
                    AVG(hit_count) as avg_hits
                FROM cache_entries
            """
            )

            row = cursor.fetchone()

            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": self._stats["hits"]
                / max(1, self._stats["hits"] + self._stats["misses"]),
                "total_entries": row["total_entries"] or 0,
                "total_size_mb": (row["total_size"] or 0) / (1024 * 1024),
                "avg_hits_per_entry": row["avg_hits"] or 0,
            }

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        current_time = time.time()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM cache_entries 
                WHERE timestamp + ttl < ?
            """,
                (current_time,),
            )

            return cursor.rowcount
