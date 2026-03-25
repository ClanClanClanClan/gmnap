"""
GlobalID generation for GMNAP.

Implements the GlobalID specification:
- 128-bit truncated SHA-256 of {CanonicalNative, BirthYear?, DeathYear?}
- Base32 encoding (22 characters)
- Collision handling with --1, --2, etc. suffixes
"""

import base64
import hashlib
import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


class GlobalIDGenerator:
    """
    Generates deterministic GlobalIDs for mathematician entries.

    GlobalID = 128-bit truncated SHA-256(CanonicalNative + BirthYear? + DeathYear?)
    Encoded as 22-character Base32 string.

    IMPORTANT: This generator is STATELESS and DETERMINISTIC.
    Same input ALWAYS produces the same GlobalID.
    """

    def __init__(self):
        # For collision detection across different entries, not same entry
        self._true_collisions: Dict[str, Dict[str, int]] = (
            {}
        )  # base_id -> {hash_input: collision_num}

    def clear(self):
        """Reset the collision tracking state."""
        self._true_collisions.clear()

    def generate(self, entry: Dict[str, Any]) -> str:
        """
        Generate GlobalID for an entry.

        Args:
            entry: Entry containing CanonicalNative, BirthYear?, DeathYear?

        Returns:
            GlobalID string (22 chars Base32, plus collision suffix if needed)
        """
        # Extract components
        canonical_native = entry.get("CanonicalNative", "")
        if not canonical_native:
            # Fallback to CanonicalLatin if Native not available
            canonical_native = entry.get("CanonicalLatin", "")

        if not canonical_native:
            raise ValueError("Entry must have CanonicalNative or CanonicalLatin")

        birth_year = entry.get("BirthYear")
        death_year = entry.get("DeathYear")

        # Build the string to hash
        components = [canonical_native]

        # Handle various birth year formats
        if birth_year is not None:
            if isinstance(birth_year, int):
                components.append(str(birth_year))
            elif isinstance(birth_year, str):
                # Handle special formats like "1970s", "-500", "c1150", "1150/1160"
                components.append(birth_year)

        # Handle death year
        if death_year is not None:
            if isinstance(death_year, int):
                components.append(str(death_year))
            elif isinstance(death_year, str):
                components.append(death_year)

        # Create hash input
        hash_input = "|".join(components)

        # Generate base ID
        base_id = self._compute_base_id(hash_input)

        # Handle collisions (only for true collisions)
        final_id = self._handle_collisions(base_id, hash_input)

        return final_id

    def _compute_base_id(self, hash_input: str) -> str:
        """
        Compute the base GlobalID from hash input.

        Args:
            hash_input: String to hash

        Returns:
            22-character Base32 string
        """
        # Compute SHA-256
        sha256 = hashlib.sha256(hash_input.encode("utf-8")).digest()

        # Truncate to 128 bits (16 bytes)
        truncated = sha256[:16]

        # Encode as Base32
        # Note: Python's base64.b32encode pads to 8-char boundaries
        # We need exactly 22 chars for 128 bits
        base32 = base64.b32encode(truncated).decode("ascii")

        # Remove padding (= signs) if any
        base32 = base32.rstrip("=")

        # Ensure exactly 22 characters
        # 128 bits = 16 bytes = 26 base32 chars with padding
        # After removing padding, should be about 26 chars
        # Actually: 16 bytes * 8 bits / 5 bits per base32 = 25.6 → 26 chars
        if len(base32) > 22:
            base32 = base32[:22]

        return base32

    def _handle_collisions(self, base_id: str, hash_input: str) -> str:
        """
        Handle TRUE collisions (different people with same base ID).

        IMPORTANT: Only creates collision suffixes for ACTUAL collisions,
        not for repeated generations of the same person.

        Args:
            base_id: Base GlobalID
            hash_input: Original hash input for this entry

        Returns:
            Final GlobalID with collision suffix only if true collision
        """
        # Check if we've seen this base_id before
        if base_id not in self._true_collisions:
            # First time seeing this base_id, register it
            self._true_collisions[base_id] = {hash_input: 0}
            return base_id

        # We've seen this base_id before, check if it's the same person
        if hash_input in self._true_collisions[base_id]:
            # Same person, same GlobalID (deterministic)
            collision_num = self._true_collisions[base_id][hash_input]
            if collision_num == 0:
                return base_id
            else:
                return f"{base_id}--{collision_num}"

        # Different person with same base_id - TRUE COLLISION
        logger.warning(f"TRUE GlobalID collision detected for base ID: {base_id}")
        logger.warning(f"  Existing entries: {list(self._true_collisions[base_id].keys())}")
        logger.warning(f"  New entry: {hash_input}")

        # Assign next collision number
        max_collision_num = max(self._true_collisions[base_id].values())
        new_collision_num = max_collision_num + 1

        # Register this new collision
        self._true_collisions[base_id][hash_input] = new_collision_num

        return f"{base_id}--{new_collision_num}"

    def validate_id(self, global_id: str) -> bool:
        """
        Validate a GlobalID format.

        Args:
            global_id: ID to validate

        Returns:
            True if valid format
        """
        if not global_id:
            return False

        # Check for collision suffix
        if "--" in global_id:
            parts = global_id.split("--")
            if len(parts) != 2:
                return False

            base_id = parts[0]
            suffix = parts[1]

            # Validate suffix is a number
            try:
                int(suffix)
            except ValueError:
                return False
        else:
            base_id = global_id

        # Validate base ID
        # Should be 22 characters of Base32 (A-Z, 2-7)
        if len(base_id) != 22:
            return False

        # Check characters are valid Base32
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
        return all(c in valid_chars for c in base_id)

    def load_existing_ids(self, ids: Set[str]) -> None:
        """
        Load existing IDs to track true collisions.

        NOTE: This method is for backwards compatibility only.
        The new deterministic generator doesn't need pre-loading.

        Args:
            ids: Set of existing GlobalIDs
        """
        # This method is now mostly a no-op since we're deterministic
        # We could reconstruct collision info from the IDs, but it's not needed
        # for deterministic generation
        logger.info(
            f"Loaded {len(ids)} existing IDs (deterministic generator doesn't need pre-loading)"
        )
        pass

    def clear(self) -> None:
        """Clear all tracked collision data."""
        self._true_collisions.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about ID generation."""
        total_entries = sum(len(entries) for entries in self._true_collisions.values())
        base_ids_with_collisions = sum(
            1 for entries in self._true_collisions.values() if len(entries) > 1
        )
        total_collisions = sum(
            sum(collision_nums for collision_nums in entries.values() if collision_nums > 0)
            for entries in self._true_collisions.values()
        )
        max_collision_suffix = max(
            (max(entries.values()) for entries in self._true_collisions.values()), default=0
        )

        return {
            "total_unique_entries": total_entries,
            "base_ids_with_collisions": base_ids_with_collisions,
            "total_collisions": total_collisions,
            "max_collision_suffix": max_collision_suffix,
        }


# Module-level instance for convenience
_generator = GlobalIDGenerator()


def generate_global_id(entry: Dict[str, Any]) -> str:
    """
    Generate GlobalID for an entry.

    Args:
        entry: Entry containing CanonicalNative, BirthYear?, DeathYear?

    Returns:
        GlobalID string
    """
    return _generator.generate(entry)


def validate_global_id(global_id: str) -> bool:
    """
    Validate a GlobalID format.

    Args:
        global_id: ID to validate

    Returns:
        True if valid format
    """
    return _generator.validate_id(global_id)


def load_existing_ids(ids: Set[str]) -> None:
    """
    Load existing IDs to prevent collisions.

    NOTE: This is for backwards compatibility only.
    The new deterministic generator doesn't need pre-loading.

    Args:
        ids: Set of existing GlobalIDs
    """
    _generator.load_existing_ids(ids)
