"""
Caching system for GMNAP with Zstandard compression.

Implements the caching strategy from specs v6:
- Zstandard compression
- 20GB cache limit (CACHE_MAX_SIZE_GB)
- 30-day TTL (CACHE_MAX_DAYS)
- Cache keys: Query hash + service + date
"""

import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import zstandard as zstd
except ImportError:
    zstd = None
    logging.warning("zstandard not installed, falling back to uncompressed cache")


logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages cached API responses with Zstandard compression.

    Features:
    - Automatic compression/decompression
    - Size-based and time-based eviction
    - Thread-safe operations
    - Google Scholar special handling
    """

    def __init__(
        self,
        cache_dir: Path,
        max_size_gb: float = 20.0,
        max_days: int = 30,
        compression_level: int = 6,
    ):
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.max_age = timedelta(days=max_days)
        self.compression_level = compression_level

        # Create cache directories
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.gs_cache_dir = self.cache_dir / "gs"  # Google Scholar special
            self.gs_cache_dir.mkdir(exist_ok=True)
            self.bad_json_dir = self.cache_dir / "bad_json"
            self.bad_json_dir.mkdir(exist_ok=True)
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to create cache directory {cache_dir}: {e}")
            # Continue with initialization but operations will fail gracefully
            self.gs_cache_dir = self.cache_dir / "gs"
            self.bad_json_dir = self.cache_dir / "bad_json"

        # Initialize compression settings
        self.compression_enabled = zstd is not None
        self.compression_level = compression_level

        # Cache statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Thread safety
        self._lock = threading.RLock()
        self._file_locks = {}  # Per-file locks
        self._file_locks_lock = threading.Lock()  # Lock for file locks dictionary

    def _get_compressor(self):
        """Get thread-local compressor instance."""
        if not self.compression_enabled:
            return None
        return zstd.ZstdCompressor(level=self.compression_level)

    def _get_decompressor(self):
        """Get thread-local decompressor instance."""
        if not self.compression_enabled:
            return None
        return zstd.ZstdDecompressor()

    def _normalize_cache_key(self, key: str) -> str:
        """
        Normalize cache key for consistent lookup.

        Args:
            key: Raw cache key

        Returns:
            Normalized cache key
        """
        # Convert to lowercase
        normalized = key.lower()

        # Replace common separators with underscores
        normalized = normalized.replace(" ", "_").replace("-", "_")

        # Remove extra underscores
        normalized = "_".join(part for part in normalized.split("_") if part)

        return normalized

    def _generate_cache_key(self, service: str, query: str, date: Optional[str] = None) -> str:
        """
        Generate cache key from service, query, and date.

        Args:
            service: Service name (e.g., "OpenAlex")
            query: Query string
            date: Optional date string (defaults to today)

        Returns:
            Cache key string
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Normalize the query for consistent hashing
        normalized_query = self._normalize_cache_key(query)

        # Create hash of normalized query
        query_hash = hashlib.sha256(normalized_query.encode()).hexdigest()[:16]

        # Combine components
        key = f"{service}_{query_hash}_{date}"

        return key

    def _get_cache_path(self, key: str, service: str) -> Path:
        """
        Get file path for cache key.

        Args:
            key: Cache key
            service: Service name (for special handling)

        Returns:
            Path to cache file
        """
        # Google Scholar gets special directory
        if service.lower() == "googlescholar" or service.lower() == "gs":
            base_dir = self.gs_cache_dir
        else:
            base_dir = self.cache_dir

        # Use subdirectories to avoid too many files in one directory
        subdir = key[:2]
        cache_path = base_dir / subdir / f"{key}.zst"

        return cache_path

    def _get_internal(self, service: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Internal method to retrieve cached data.

        Args:
            service: Service name
            query: Query string

        Returns:
            Cached data or None if not found/expired
        """
        key = self._generate_cache_key(service, query)
        cache_path = self._get_cache_path(key, service)

        # Get file-specific lock - use separate lock for file locks dictionary
        with self._file_locks_lock:
            if cache_path not in self._file_locks:
                self._file_locks[cache_path] = threading.Lock()
            file_lock = self._file_locks[cache_path]

        with file_lock:
            if not cache_path.exists():
                with self._lock:
                    self._misses += 1
                return None

        try:
            # Check age
            file_stat = cache_path.stat()
            age = datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)

            if age > self.max_age:
                logger.debug(f"Cache expired for {key}")
                cache_path.unlink()
                with self._lock:
                    self._evictions += 1
                    self._misses += 1
                return None

            # Read and decompress
            with open(cache_path, "rb") as f:
                compressed_data = f.read()

            decompressor = self._get_decompressor()
            if decompressor:
                json_data = decompressor.decompress(compressed_data)
            else:
                json_data = compressed_data

            data = json.loads(json_data)

            with self._lock:
                self._hits += 1
            logger.debug(f"Cache hit for {key}")
            return data

        except Exception as e:
            logger.error(f"Failed to read cache {key}: {e}")
            # Move to bad_json if corrupted
            if cache_path.exists():
                bad_path = self.bad_json_dir / cache_path.name
                cache_path.rename(bad_path)

            with self._lock:
                self._misses += 1
            return None

    def put(self, service: str, query: str, data: Dict[str, Any]) -> bool:
        """
        Store data in cache.

        Args:
            service: Service name
            query: Query string
            data: Data to cache

        Returns:
            True if stored successfully
        """
        key = self._generate_cache_key(service, query)
        cache_path = self._get_cache_path(key, service)

        # Get file-specific lock - use separate lock for file locks dictionary
        with self._file_locks_lock:
            if cache_path not in self._file_locks:
                self._file_locks[cache_path] = threading.Lock()
            file_lock = self._file_locks[cache_path]

        with file_lock:
            try:
                # Ensure directory exists - use global lock to prevent race condition
                with self._lock:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)

                # Serialize to JSON
                json_data = json.dumps(data, separators=(",", ":"))

                # Compress
                compressor = self._get_compressor()
                if compressor:
                    compressed_data = compressor.compress(json_data.encode())
                else:
                    compressed_data = json_data.encode()

                # Write atomically
                temp_path = cache_path.with_suffix(".tmp")
                with open(temp_path, "wb") as f:
                    f.write(compressed_data)

                # Move into place
                temp_path.replace(cache_path)

                logger.debug(f"Cached {key} ({len(compressed_data)} bytes)")

                return True

            except Exception as e:
                logger.error(f"Failed to cache {key}: {e}")
                return False

        # Check if eviction needed (outside file lock)
        with self._lock:
            self._check_size_limit()

    def set(self, key: str, data: Dict[str, Any], service: str = "default") -> bool:
        """
        Store data in cache (alias for put() for API consistency).

        Args:
            key: Cache key
            data: Data to cache
            service: Service name (defaults to "default")

        Returns:
            True if stored successfully
        """
        return self.put(service, key, data)

    def get(self, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data (overloaded for API consistency).

        Can be called as:
        - get(key, default=None) - uses default service
        - get(service, key) - original API

        Returns:
            Cached data or default value if not found/expired
        """
        default = kwargs.get("default", None)

        if len(args) == 1:
            # get(key) - use default service
            result = self._get_internal("default", args[0])
            return result if result is not None else default
        elif len(args) == 2:
            # get(service, key) - original API
            result = self._get_internal(args[0], args[1])
            return result if result is not None else default
        else:
            raise TypeError(f"get() takes 1 or 2 arguments ({len(args)} given)")

    def delete(self, key: str, service: str = "default") -> bool:
        """
        Delete cached entry.

        Args:
            key: Cache key to delete
            service: Service name (defaults to "default")

        Returns:
            True if entry was deleted, False if not found
        """
        cache_key = self._generate_cache_key(service, key)
        cache_path = self._get_cache_path(cache_key, service)

        try:
            if cache_path.exists():
                cache_path.unlink()
                logger.debug(f"Deleted cache entry: {cache_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete cache entry {cache_key}: {e}")
            return False

    def set_batch(
        self, batch_data: Dict[str, Dict[str, Any]], service: str = "default"
    ) -> Dict[str, bool]:
        """
        Store multiple entries in cache.

        Args:
            batch_data: Dictionary of key -> data pairs
            service: Service name (defaults to "default")

        Returns:
            Dictionary of key -> success status
        """
        results = {}
        for key, data in batch_data.items():
            results[key] = self.set(key, data, service)
        return results

    def get_batch(
        self, keys: List[str], service: str = "default"
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Retrieve multiple entries from cache.

        Args:
            keys: List of cache keys
            service: Service name (defaults to "default")

        Returns:
            Dictionary of key -> data pairs (None for missing entries)
        """
        results = {}
        for key in keys:
            results[key] = self.get(key)
        return results

    def get_metadata(self, key: str, service: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get metadata for cached entry.

        Args:
            key: Cache key
            service: Service name (defaults to "default")

        Returns:
            Metadata dictionary or None if not found
        """
        cache_key = self._generate_cache_key(service, key)
        cache_path = self._get_cache_path(cache_key, service)

        if not cache_path.exists():
            return None

        try:
            stat = cache_path.stat()
            # Calculate compression ratio
            with open(cache_path, "rb") as f:
                compressed_size = len(f.read())

            # Try to get original size by decompressing
            try:
                with open(cache_path, "rb") as f:
                    compressed_data = f.read()
                decompressor = self._get_decompressor()
                if decompressor:
                    original_data = decompressor.decompress(compressed_data)
                    original_size = len(original_data)
                    compression_ratio = (
                        compressed_size / original_size if original_size > 0 else 1.0
                    )
                else:
                    original_size = compressed_size
                    compression_ratio = 1.0
            except:
                original_size = compressed_size
                compression_ratio = 1.0

            return {
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "expires_at": (datetime.fromtimestamp(stat.st_mtime) + self.max_age).isoformat(),
                "size_bytes": compressed_size,
                "compression_ratio": compression_ratio,
            }
        except Exception as e:
            logger.error(f"Failed to get metadata for {cache_key}: {e}")
            return None

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        removed_count = 0
        now = datetime.now()

        for cache_file in self.cache_dir.rglob("*.zst"):
            if cache_file.parent == self.bad_json_dir:
                continue

            try:
                stat = cache_file.stat()
                age = now - datetime.fromtimestamp(stat.st_mtime)

                if age > self.max_age:
                    cache_file.unlink()
                    removed_count += 1
                    logger.debug(f"Removed expired cache file: {cache_file.name}")
            except Exception as e:
                logger.error(f"Failed to check/remove expired file {cache_file}: {e}")

        return removed_count

    def create_backup(self, backup_path: Path) -> None:
        """
        Create backup of cache directory.

        Args:
            backup_path: Path for backup file (.tar.gz)
        """
        import tarfile

        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(self.cache_dir, arcname="cache")

        logger.info(f"Created cache backup: {backup_path}")

    def restore_from_backup(self, backup_path: Path) -> None:
        """
        Restore cache from backup.

        Args:
            backup_path: Path to backup file (.tar.gz)
        """
        import shutil
        import tarfile

        # Clear existing cache
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

        # Extract backup
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(self.cache_dir.parent)

        logger.info(f"Restored cache from backup: {backup_path}")

    def _check_size_limit(self) -> None:
        """Check and enforce cache size limit."""
        total_size = 0
        cache_files = []

        # Collect all cache files
        for cache_file in self.cache_dir.rglob("*.zst"):
            if cache_file.parent == self.bad_json_dir:
                continue

            stat = cache_file.stat()
            total_size += stat.st_size
            cache_files.append((cache_file, stat.st_mtime, stat.st_size))

        if total_size <= self.max_size_bytes:
            return

        # Need to evict - sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[1])

        # Evict oldest files until under limit
        for cache_file, mtime, size in cache_files:
            if total_size <= self.max_size_bytes:
                break

            try:
                cache_file.unlink()
                total_size -= size
                self._evictions += 1
                logger.debug(f"Evicted {cache_file.name}")
            except Exception as e:
                logger.error(f"Failed to evict {cache_file}: {e}")

    def clear(self, service: Optional[str] = None) -> None:
        """
        Clear cache for a service or all services.

        Args:
            service: Optional service name to clear
        """
        if service:
            # Clear specific service
            pattern = f"{service}_*"
            count = 0

            for cache_file in self.cache_dir.rglob(pattern):
                try:
                    cache_file.unlink()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {cache_file}: {e}")

            logger.info(f"Cleared {count} cache entries for {service}")

        else:
            # Clear all cache
            count = 0

            for cache_file in self.cache_dir.rglob("*.zst"):
                if cache_file.parent == self.bad_json_dir:
                    continue

                try:
                    cache_file.unlink()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {cache_file}: {e}")

            logger.info(f"Cleared {count} cache entries")

        # Reset statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        # Calculate hit rate
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        # Calculate cache size
        total_size = 0
        file_count = 0

        for cache_file in self.cache_dir.rglob("*.zst"):
            if cache_file.parent == self.bad_json_dir:
                continue

            total_size += cache_file.stat().st_size
            file_count += 1

        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_entries": file_count,  # Alias for total_files
            "total_files": file_count,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_gb": self.max_size_bytes / (1024 * 1024 * 1024),
            "compression_enabled": self.compression_enabled,
        }

    def migrate_uncompressed(self) -> int:
        """
        Migrate uncompressed cache files to compressed format.

        Returns:
            Number of files migrated
        """
        if not self.compression_enabled:
            logger.warning("Compression not available")
            return 0

        migrated = 0

        # Find uncompressed files
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                # Read uncompressed
                with open(cache_file, "r") as f:
                    data = json.load(f)

                # Write compressed
                new_path = cache_file.with_suffix(".zst")
                json_data = json.dumps(data, separators=(",", ":"))
                compressor = self._get_compressor()
                compressed_data = compressor.compress(json_data.encode())

                with open(new_path, "wb") as f:
                    f.write(compressed_data)

                # Remove old file
                cache_file.unlink()
                migrated += 1

            except Exception as e:
                logger.error(f"Failed to migrate {cache_file}: {e}")

        logger.info(f"Migrated {migrated} files to compressed format")
        return migrated


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(
    cache_dir: Optional[Path] = None, max_size_gb: float = 20.0, max_days: int = 30
) -> CacheManager:
    """
    Get or create global cache manager.

    Args:
        cache_dir: Cache directory (defaults to ./cache)
        max_size_gb: Maximum cache size in GB
        max_days: Maximum age in days

    Returns:
        CacheManager instance
    """
    global _cache_manager

    if _cache_manager is None:
        if cache_dir is None:
            cache_dir = Path("./cache")

        _cache_manager = CacheManager(
            cache_dir=cache_dir, max_size_gb=max_size_gb, max_days=max_days
        )

    return _cache_manager
