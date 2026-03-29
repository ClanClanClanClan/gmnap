"""
Cache Manager for V7 pipeline.
Supports both in-memory and file-based caching with compression.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import zstandard as zstd

    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False


class CacheManager:
    """Cache manager with optional file-based persistence and compression."""

    def __init__(
        self,
        ttl: int = 3600,
        cache_dir: Optional[Path] = None,
        max_size_gb: float = 1.0,
        max_days: int = 7,
        compression_level: int = 3,
    ):
        """Initialize cache with TTL in seconds.

        Args:
            ttl: Time-to-live in seconds for in-memory cache
            cache_dir: Optional directory for file-based cache
            max_size_gb: Maximum cache size in GB
            max_days: Maximum age of cache files in days
            compression_level: Zstandard compression level (1-22)
        """
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl
        self.cache_dir = cache_dir
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.max_age = timedelta(days=max_days)
        self.compression_level = compression_level

        if cache_dir:
            self.cache_dir = Path(cache_dir)
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                # If we can't create the cache directory, continue with memory-only cache
                self.cache_dir = None
                print(f"Warning: Could not create cache directory {cache_dir}: {e}")
            if self.cache_dir and HAS_ZSTD:
                self.compressor = zstd.ZstdCompressor(level=compression_level)
                self.decompressor = zstd.ZstdDecompressor()

    def _get_cache_path(self, key: str) -> Optional[Path]:
        """Get file path for a cache key."""
        if not self.cache_dir:
            return None
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash[:2]}" / f"{key_hash}.cache"

    def set(self, key: str, value: Any) -> bool:
        """Set a value in cache."""
        try:
            # In-memory cache
            self.cache[key] = (value, time.time())

            # File-based cache if configured
            if self.cache_dir and HAS_ZSTD:
                cache_path = self._get_cache_path(key)
                if cache_path:
                    try:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        data = json.dumps(value).encode()
                        compressed = self.compressor.compress(data)
                        cache_path.write_bytes(compressed)
                    except (OSError, PermissionError):
                        # File cache failed but memory cache succeeded
                        return False
            return True
        except Exception:
            # Complete failure
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if not expired."""
        # Check in-memory cache first
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp <= self.ttl:
                return value
            else:
                del self.cache[key]

        # Check file-based cache if configured
        if self.cache_dir and HAS_ZSTD:
            cache_path = self._get_cache_path(key)
            if cache_path and cache_path.exists():
                # Check age
                mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
                if datetime.now() - mtime <= self.max_age:
                    try:
                        compressed = cache_path.read_bytes()
                        data = self.decompressor.decompress(compressed)
                        value = json.loads(data)
                        # Store in memory cache
                        self.cache[key] = (value, time.time())
                        return value
                    except Exception:
                        # Corrupted cache file
                        cache_path.unlink(missing_ok=True)
                else:
                    # Expired
                    cache_path.unlink(missing_ok=True)

        return None

    def evict(self, key: str) -> None:
        """Remove a key from cache."""
        if key in self.cache:
            del self.cache[key]

        if self.cache_dir:
            cache_path = self._get_cache_path(key)
            if cache_path and cache_path.exists():
                cache_path.unlink()

    def delete(self, key: str) -> None:
        """Alias for evict."""
        self.evict(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

        if self.cache_dir and self.cache_dir.exists():
            for cache_file in self.cache_dir.rglob("*.cache"):
                cache_file.unlink()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "memory_entries": len(self.cache),
            "file_entries": 0,
            "total_size_bytes": 0,
        }

        if self.cache_dir and self.cache_dir.exists():
            cache_files = list(self.cache_dir.rglob("*.cache"))
            stats["file_entries"] = len(cache_files)
            stats["total_size_bytes"] = sum(f.stat().st_size for f in cache_files)

        return stats

    def cleanup_expired(self) -> int:
        """Remove expired cache files."""
        removed = 0
        if self.cache_dir and self.cache_dir.exists():
            now = datetime.now()
            for cache_file in self.cache_dir.rglob("*.cache"):
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if now - mtime > self.max_age:
                    cache_file.unlink()
                    removed += 1
        return removed
