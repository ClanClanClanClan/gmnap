#!/usr/bin/env python3
"""
Test GlobalID implementation for V7 compliance.

V7 Specification:
- 128-bit truncated SHA-256 (22 Base32) of {CanonicalNative, BirthYear?, DeathYear?}
- Collisions are suffixed with "--1, --2 ..."
"""

import pytest

from src.core.global_id import (
    add_global_id,
    compute_global_id_for_pipeline,
    generate_global_id,
    generate_unique_global_id,
    global_id,
    reset_collision_tracking,
    validate_global_id,
)


class TestGlobalID:
    """Test GlobalID functionality per V7 specification."""

    def setup_method(self):
        """Reset collision tracking before each test."""
        reset_collision_tracking()

    @pytest.mark.timeout(15)
    def test_basic_global_id_generation(self):
        """Test basic GlobalID generation."""
        # Test with all fields
        id1 = global_id("Leonhard Euler", 1707, 1783)
        assert len(id1) == 22
        assert validate_global_id(id1)

        # Test with missing death year
        id2 = global_id("Carl Friedrich Gauss", 1777, None)
        assert len(id2) == 22
        assert validate_global_id(id2)

        # Test with no years
        id3 = global_id("Anonymous Mathematician", None, None)
        assert len(id3) == 22
        assert validate_global_id(id3)

    @pytest.mark.timeout(15)
    def test_global_id_deterministic(self):
        """Test that GlobalID generation is deterministic."""
        id1 = global_id("Leonhard Euler", 1707, 1783)
        id2 = global_id("Leonhard Euler", 1707, 1783)
        assert id1 == id2

        # Different input should give different ID
        id3 = global_id("Carl Gauss", 1777, 1855)
        assert id3 != id1

    @pytest.mark.timeout(15)
    def test_generate_from_entry(self):
        """Test GlobalID generation from entry dict."""
        entry = {
            "CanonicalNative": "김민준",
            "CanonicalLatin": "Kim Min-jun",
            "BirthYear": 1990,
            "DeathYear": None,
        }

        global_id_str = generate_global_id(entry)
        assert len(global_id_str) == 22
        assert validate_global_id(global_id_str)

    @pytest.mark.timeout(15)
    def test_fallback_to_latin(self):
        """Test fallback to CanonicalLatin when Native is missing."""
        entry1 = {
            "CanonicalNative": "",
            "CanonicalLatin": "John Smith",
            "BirthYear": 1950,
        }

        entry2 = {"CanonicalLatin": "John Smith", "BirthYear": 1950}

        id1 = generate_global_id(entry1)
        id2 = generate_global_id(entry2)
        assert id1 == id2

    @pytest.mark.timeout(15)
    def test_collision_handling(self):
        """Test collision suffix handling per V7 spec."""
        # Create two identical entries
        entry1 = {"CanonicalNative": "John Doe", "BirthYear": 1980}

        entry2 = {"CanonicalNative": "John Doe", "BirthYear": 1980}

        # First should get base ID
        id1 = generate_unique_global_id(entry1)
        assert len(id1) == 22
        assert "--" not in id1

        # Second should get collision suffix
        id2 = generate_unique_global_id(entry2)
        assert id2 == f"{id1}--1"

        # Third should get next suffix
        id3 = generate_unique_global_id(entry2)
        assert id3 == f"{id1}--2"

    @pytest.mark.timeout(15)
    def test_validate_global_id(self):
        """Test GlobalID validation."""
        # Valid base ID
        assert validate_global_id("ABCDEFGHIJKLMNOPQRSTUV")

        # Valid with collision suffix
        assert validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--1")
        assert validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--99")

        # Invalid: too short
        assert not validate_global_id("ABCDEF")

        # Invalid: too long
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        # Invalid: contains invalid characters
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRST01")  # 0 and 1 not valid
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRST!@")

        # Invalid: bad suffix format
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--")
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--0")
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUV--abc")
        assert not validate_global_id("ABCDEFGHIJKLMNOPQRSTUV---1")

    @pytest.mark.timeout(15)
    def test_pipeline_integration(self):
        """Test pipeline integration functions."""
        entry = {"CanonicalNative": "Test Name", "BirthYear": 2000}

        # Test compute_global_id_for_pipeline
        result = compute_global_id_for_pipeline(entry.copy())
        assert "GlobalID" in result
        assert len(result["GlobalID"]) == 22

        # Should not overwrite existing GlobalID
        entry_with_id = {
            "CanonicalNative": "Test Name",
            "GlobalID": "EXISTINGIDEXISTINGIDAA",
        }
        result = compute_global_id_for_pipeline(entry_with_id.copy())
        assert result["GlobalID"] == "EXISTINGIDEXISTINGIDAA"

    @pytest.mark.timeout(15)
    def test_add_global_id(self):
        """Test add_global_id helper function."""
        entry = {
            "CanonicalNative": "Emmy Noether",
            "BirthYear": 1882,
            "DeathYear": 1935,
        }

        global_id_str = add_global_id(entry)
        assert "GlobalID" in entry
        assert entry["GlobalID"] == global_id_str
        assert len(global_id_str) == 22
        assert validate_global_id(global_id_str)

    @pytest.mark.timeout(15)
    def test_base32_characters(self):
        """Test that generated IDs only contain valid Base32 characters."""
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")

        test_cases = [
            {"CanonicalNative": "Test 1", "BirthYear": 1900},
            {"CanonicalNative": "测试", "BirthYear": 2000},
            {"CanonicalNative": "Тест", "DeathYear": 1999},
            {"CanonicalNative": "🔬", "BirthYear": 1850, "DeathYear": 1900},
        ]

        for entry in test_cases:
            global_id_str = generate_global_id(entry)
            assert all(c in valid_chars for c in global_id_str)

    @pytest.mark.timeout(15)
    def test_v7_compliance_examples(self):
        """Test with examples that should match V7 spec behavior."""
        # Test known mathematicians
        euler = {
            "CanonicalNative": "Leonhard Euler",
            "BirthYear": 1707,
            "DeathYear": 1783,
        }

        gauss = {
            "CanonicalNative": "Carl Friedrich Gauss",
            "BirthYear": 1777,
            "DeathYear": 1855,
        }

        euler_id = generate_global_id(euler)
        gauss_id = generate_global_id(gauss)

        # IDs should be different
        assert euler_id != gauss_id

        # Both should be valid
        assert validate_global_id(euler_id)
        assert validate_global_id(gauss_id)

        # Both should be exactly 22 chars
        assert len(euler_id) == 22
        assert len(gauss_id) == 22


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ── Collision-cache eviction safety (R39) ─────────────────────────────


def test_collision_cache_cap_exceeds_target_workload():
    """The collision dedup set must hold the marquee 1M run (~150 MB)
    without evicting. Eviction silently breaks GlobalID uniqueness."""
    import src.core.global_id as gid

    assert gid._COLLISION_CACHE_MAX_BYTES >= 512 * 1024 * 1024


def test_collision_cache_eviction_is_loud(caplog):
    """If the collision cache ever evicts (extreme batch), it must log a
    loud error rather than silently emit colliding GlobalIDs."""
    import logging

    import src.core.global_id as gid
    from src.core.cache.sized_lru import SizedLRU

    orig = gid._cross_batch
    gid._cross_batch = SizedLRU(max_bytes=400)  # tiny -> forces eviction
    gid._collision_evict_warned = False
    try:
        with caplog.at_level(logging.ERROR, logger="src.core.global_id"):
            for i in range(200):
                gid.cache_put(f"ID{i:08d}", True)
        msgs = " ".join(r.getMessage() for r in caplog.records)
        assert "NO LONGER" in msgs and "uniqueness" in msgs
    finally:
        gid._cross_batch = orig
        gid._collision_evict_warned = False
