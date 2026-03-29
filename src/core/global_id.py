"""
GlobalID generation for GMNAP V7.

V7 Specification:
- 128-bit truncated SHA-256 (22 Base32) of {CanonicalNative, BirthYear?, DeathYear?}
- Collisions are suffixed with "--1, --2 ..."
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Expert solution: Replace unbounded cache with sized LRU
from src.core.cache.sized_lru import SizedLRU

_cross_batch = SizedLRU(max_bytes=256 * 1024 * 1024)  # 256MB max
# Track number of duplicates resolved
_duplicate_count: int = 0


def cache_put(k, v):
    _cross_batch.put(k, v)


def cache_get(k, default=None):
    return _cross_batch.get(k, default)


def cache_contains(k):
    return k in _cross_batch


def global_id(canonical_native: str, birth: int | None, death: int | None) -> str:
    """
    V7 GlobalID: 128‑bit truncated SHA‑256 (22 Base32) of {CanonicalNative, BirthYear?, DeathYear?}.
    We implement a 110‑bit cut to yield 22 Base32 characters (RFC 4648, no padding).
    If you require full 128‑bit, increase to 26 chars (take 16 bytes, adjust trimming).
    """
    payload = f"{canonical_native}|{birth or ''}|{death or ''}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    fourteen = digest[:14]  # 112 bits
    trimmed = bytearray(fourteen)
    trimmed[-1] &= 0b11111100  # drop 2 bits to get 110
    # Base32 encode and ensure exactly 22 chars
    encoded = base64.b32encode(bytes(trimmed)).decode("ascii").rstrip("=")
    return encoded[:22]  # Ensure exactly 22 characters


def generate_global_id(entry: Dict[str, Any]) -> str:
    """
    Generate GlobalID from entry per V7 specification.

    Args:
        entry: Entry containing CanonicalNative, BirthYear, DeathYear

    Returns:
        GlobalID string (22 chars Base32)
    """
    # Extract components
    canonical_native = entry.get("CanonicalNative", "")
    birth_year = entry.get("BirthYear")
    death_year = entry.get("DeathYear")

    # If no native name, fall back to Latin
    if not canonical_native:
        canonical_native = entry.get("CanonicalLatin", "")

    return global_id(canonical_native, birth_year, death_year)


def generate_unique_global_id(entry: Dict[str, Any]) -> str:
    """
    Generate a unique GlobalID, handling collisions automatically per V7 spec.

    Args:
        entry: Entry to generate ID for

    Returns:
        Unique GlobalID string (with collision suffix if needed)
    """
    base_id = generate_global_id(entry)

    # Check for collision
    if not cache_contains(base_id):
        cache_put(base_id, True)
        return base_id

    # Handle collision with suffix per V7 spec: "--1, --2 ..."
    global _duplicate_count
    _duplicate_count += 1
    suffix = 1
    while True:
        suffixed_id = f"{base_id}--{suffix}"
        if not cache_contains(suffixed_id):
            cache_put(suffixed_id, True)
            logger.info(f"GlobalID collision resolved: {base_id} -> {suffixed_id}")
            return suffixed_id
        suffix += 1


def reset_collision_tracking():
    """Reset the collision tracking set (useful for testing and new pipeline runs)."""
    global _cross_batch, _duplicate_count
    _cross_batch = SizedLRU(max_bytes=256 * 1024 * 1024)  # Create new cache
    _duplicate_count = 0


def get_duplicate_count() -> int:
    """Get the number of duplicates resolved so far."""
    return _duplicate_count


def generate_batch_global_ids(entries: list[Dict[str, Any]]) -> list[str]:
    """
    Generate GlobalIDs for a batch of entries efficiently.

    Args:
        entries: List of entries to generate IDs for

    Returns:
        List of generated GlobalIDs
    """
    global _duplicate_count
    from collections import defaultdict

    ids = []
    suffix_counters = defaultdict(int)

    # Pre-compute base IDs
    base_ids = [generate_global_id(entry) for entry in entries]

    # Batch collision detection and resolution
    for i, base_id in enumerate(base_ids):
        if cache_contains(base_id) or base_id in [
            bid for j, bid in enumerate(base_ids) if j < i
        ]:
            # This is a duplicate - need to suffix it
            _duplicate_count += 1
            suffix_counters[base_id] += 1
            final_id = f"{base_id}--{suffix_counters[base_id]}"

            # Ensure the suffixed ID is also unique
            while cache_contains(final_id):
                suffix_counters[base_id] += 1
                final_id = f"{base_id}--{suffix_counters[base_id]}"
        else:
            final_id = base_id

        cache_put(final_id, True)
        ids.append(final_id)

    return ids


def validate_global_id(global_id_str: str) -> bool:
    """
    Validate that a GlobalID follows V7 spec format.

    Args:
        global_id_str: ID to validate

    Returns:
        True if valid format
    """
    if not global_id_str:
        return False

    # Check for collision suffix
    if "--" in global_id_str:
        parts = global_id_str.split("--")
        if len(parts) != 2:
            return False
        base_id, suffix = parts
        try:
            suffix_num = int(suffix)
            if suffix_num < 1:
                return False
        except ValueError:
            return False
    else:
        base_id = global_id_str

    # Base ID should be exactly 22 chars
    if len(base_id) != 22:
        return False

    # Should be valid Base32 (uppercase letters and digits 2-7)
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
    if not all(c in valid_chars for c in base_id):
        return False

    return True


def compute_global_id_for_pipeline(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute and add GlobalID to entry for V7 pipeline.

    Args:
        entry: Entry to process

    Returns:
        Entry with GlobalID added
    """
    if "GlobalID" not in entry or not entry["GlobalID"]:
        entry["GlobalID"] = generate_unique_global_id(entry)
    else:
        # Track pre-existing GlobalID for collision detection
        existing_id = entry["GlobalID"]
        if cache_contains(existing_id):
            # This is a duplicate - generate a new suffixed ID
            global _duplicate_count
            _duplicate_count += 1
            suffix = 1
            while cache_contains(f"{existing_id}--{suffix}"):
                suffix += 1
            entry["GlobalID"] = f"{existing_id}--{suffix}"
            cache_put(entry["GlobalID"], True)
        else:
            cache_put(existing_id, True)

    return entry


def add_global_id(entry: Dict[str, Any]) -> str:
    """
    Add GlobalID to entry and return it.

    Args:
        entry: Entry to add ID to

    Returns:
        The generated GlobalID
    """
    global_id_str = generate_unique_global_id(entry)
    entry["GlobalID"] = global_id_str
    return global_id_str
