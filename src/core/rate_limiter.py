"""
Rate limiting implementation for GMNAP pipeline security.
Prevents DoS attacks and resource exhaustion.
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 1000
    requests_per_hour: int = 50000
    burst_size: int = 100
    cooldown_seconds: int = 60


@dataclass
class TestRateLimitConfig:
    """Test-friendly configuration with much higher limits."""

    requests_per_minute: int = 100000  # 100x higher
    requests_per_hour: int = 5000000  # 100x higher
    burst_size: int = 50000  # ULTRAFIX: Increased from 10,000 to 50,000
    cooldown_seconds: int = 1  # Much shorter cooldown


@dataclass
class ProductionRateLimitConfig:
    """Production-ready configuration optimized for batch processing."""

    requests_per_minute: int = 10000  # 10,000 requests/minute
    requests_per_hour: int = 500000  # 500K requests/hour
    burst_size: int = 5000  # 5,000 burst capacity
    cooldown_seconds: int = 5  # 5 second cooldown


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    pass


class CoreRateLimiter:
    """
    Token bucket rate limiter with sliding window.
    Thread-safe implementation for production use.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._lock = threading.Lock()

        # Client-specific tracking
        self._client_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "tokens": self.config.burst_size,
                "last_refill": time.time(),
                "minute": deque(),
                "hour": deque(),
            }
        )

        # Cooldown tracking for blocked clients
        self._cooldowns: Dict[str, float] = {}

    def check_rate_limit(self, client_id: str = "global") -> Tuple[bool, Optional[str]]:
        """
        Check if a request is allowed under rate limits.

        Args:
            client_id: Identifier for the client (IP, API key, etc.)

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        with self._lock:
            current_time = time.time()

            # Check cooldown
            if client_id in self._cooldowns:
                if current_time < self._cooldowns[client_id]:
                    remaining = int(self._cooldowns[client_id] - current_time)
                    return False, f"Rate limit cooldown: {remaining}s remaining"
                else:
                    del self._cooldowns[client_id]

            # Clean old entries from windows
            self._clean_windows(current_time)

            # Get client data
            client_data = self._client_data[client_id]

            # Check burst limit (token bucket)
            self._refill_tokens(client_id, current_time)
            if client_data["tokens"] <= 0:
                self._cooldowns[client_id] = current_time + self.config.cooldown_seconds
                return False, "Burst limit exceeded"

            # Check minute limit
            minute_count = len(client_data["minute"])
            if minute_count >= self.config.requests_per_minute:
                self._cooldowns[client_id] = current_time + self.config.cooldown_seconds
                return (
                    False,
                    f"Minute limit exceeded: {minute_count}/{self.config.requests_per_minute}",
                )

            # Check hour limit
            hour_count = len(client_data["hour"])
            if hour_count >= self.config.requests_per_hour:
                self._cooldowns[client_id] = current_time + self.config.cooldown_seconds
                return (
                    False,
                    f"Hour limit exceeded: {hour_count}/{self.config.requests_per_hour}",
                )

            # Request allowed - update tracking
            client_data["tokens"] -= 1
            client_data["minute"].append(current_time)
            client_data["hour"].append(current_time)

            return True, None

    def _refill_tokens(self, client_id: str, current_time: float) -> None:
        """Refill tokens based on elapsed time."""
        client_data = self._client_data[client_id]
        elapsed = current_time - client_data["last_refill"]
        tokens_to_add = int(
            elapsed * (self.config.burst_size / 60.0)
        )  # Refill rate: burst_size per minute

        if tokens_to_add > 0:
            client_data["tokens"] = min(
                self.config.burst_size, client_data["tokens"] + tokens_to_add
            )
            client_data["last_refill"] = current_time

    def _clean_windows(self, current_time: float) -> None:
        """Remove old entries from sliding windows and cleanup inactive clients."""
        minute_cutoff = current_time - 60
        hour_cutoff = current_time - 3600
        # ULTRAFIX: Add client cleanup cutoff (inactive for 24 hours)
        client_cleanup_cutoff = current_time - 86400  # 24 hours

        # Track clients to remove (to avoid modifying dict during iteration)
        clients_to_remove = []

        # Clean all client windows
        for client_id, client_data in self._client_data.items():
            # Clean minute window
            while client_data["minute"] and client_data["minute"][0] < minute_cutoff:
                client_data["minute"].popleft()

            # Clean hour window
            while client_data["hour"] and client_data["hour"][0] < hour_cutoff:
                client_data["hour"].popleft()

            # ULTRAFIX: Mark inactive clients for removal
            # Client is inactive if no requests in last 24 hours
            last_activity = max(
                client_data["last_refill"],
                client_data["hour"][-1] if client_data["hour"] else 0,
            )

            if last_activity < client_cleanup_cutoff:
                clients_to_remove.append(client_id)

        # ULTRAFIX: Remove inactive clients to prevent memory leak
        for client_id in clients_to_remove:
            del self._client_data[client_id]

        # ULTRAFIX: Clean expired cooldowns
        expired_cooldowns = [
            client_id
            for client_id, cooldown_end in self._cooldowns.items()
            if current_time >= cooldown_end
        ]
        for client_id in expired_cooldowns:
            del self._cooldowns[client_id]

    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        with self._lock:
            if client_id in self._client_data:
                del self._client_data[client_id]
            if client_id in self._cooldowns:
                del self._cooldowns[client_id]

    def get_stats(self, client_id: str = "global") -> Dict[str, Any]:
        """Get current rate limit statistics."""
        with self._lock:
            current_time = time.time()
            self._clean_windows(current_time)

            if client_id not in self._client_data:
                return {
                    "tokens_available": self.config.burst_size,
                    "minute_requests": 0,
                    "hour_requests": 0,
                    "cooldown_active": False,
                }

            client_data = self._client_data[client_id]
            self._refill_tokens(client_id, current_time)

            return {
                "tokens_available": client_data["tokens"],
                "minute_requests": len(client_data["minute"]),
                "hour_requests": len(client_data["hour"]),
                "cooldown_active": client_id in self._cooldowns,
                "cooldown_remaining": max(
                    0, self._cooldowns.get(client_id, 0) - current_time
                ),
            }

    def force_cleanup(self) -> Dict[str, int]:
        """ULTRAFIX: Force cleanup of inactive clients and return cleanup stats."""
        with self._lock:
            current_time = time.time()

            # Count before cleanup
            clients_before = len(self._client_data)
            cooldowns_before = len(self._cooldowns)

            # Force cleanup
            self._clean_windows(current_time)

            # Count after cleanup
            clients_after = len(self._client_data)
            cooldowns_after = len(self._cooldowns)

            return {
                "clients_removed": clients_before - clients_after,
                "cooldowns_removed": cooldowns_before - cooldowns_after,
                "clients_remaining": clients_after,
                "cooldowns_remaining": cooldowns_after,
            }

    def get_memory_stats(self) -> Dict[str, int]:
        """ULTRAFIX: Get memory usage statistics for debugging."""
        with self._lock:
            total_minute_entries = sum(
                len(data["minute"]) for data in self._client_data.values()
            )
            total_hour_entries = sum(
                len(data["hour"]) for data in self._client_data.values()
            )

            return {
                "total_clients": len(self._client_data),
                "total_cooldowns": len(self._cooldowns),
                "total_minute_entries": total_minute_entries,
                "total_hour_entries": total_hour_entries,
                "estimated_memory_kb": (
                    len(self._client_data) * 200  # Client data structures
                    + total_minute_entries * 8  # Minute timestamps
                    + total_hour_entries * 8  # Hour timestamps
                    + len(self._cooldowns) * 50  # Cooldown data
                )
                // 1024,
            }


# Global rate limiter instance
# ULTRAFIX: Environment-aware rate limiter configuration
def _get_rate_limiter_config():
    """Get rate limiter config based on environment."""
    import os

    # Check for test mode
    if os.getenv("GMNAP_TEST_MODE") == "true":
        return TestRateLimitConfig()

    # Check for production mode
    environment = os.getenv("GMNAP_ENVIRONMENT", "development").lower()
    if environment == "production":
        return ProductionRateLimitConfig()

    # Default to test-friendly for development
    return TestRateLimitConfig()


global_rate_limiter = CoreRateLimiter(_get_rate_limiter_config())


def check_rate_limit(client_id: str = "global") -> None:
    """
    Convenience function to check rate limit.
    Raises RateLimitExceeded if limit is exceeded.

    Args:
        client_id: Client identifier

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    allowed, reason = global_rate_limiter.check_rate_limit(client_id)
    if not allowed:
        raise RateLimitExceeded(reason)
