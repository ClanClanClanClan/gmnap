"""
2M Synthetic Stress Test (V7 spec §8: stress: "2M synthetic weekly").

Generates 2,000,000 synthetic entries across all 37 regions and runs
a lightweight validation pipeline to verify quality gates hold at scale.

Run with: make stress
Mark: @pytest.mark.stress — not included in regular CI.
"""

import hashlib
import random
import string
import time

import pytest

# 37 V7 regions with representative country codes
REGIONS = {
    "A1": ["US", "GB", "CA", "AU", "NZ", "IE"],
    "A2": ["FR", "DE", "IT", "ES", "PT", "NL", "CH", "AT"],
    "A3": ["DK", "NO", "SE", "FI", "IS", "EE", "LV", "LT"],
    "A4": ["FJ", "PG", "WS", "TO"],
    "A5": ["CW", "MQ", "GP"],
    "B1": ["RU", "UA", "BY"],
    "B2": ["PL", "CZ", "HU", "RO", "BG", "RS", "HR"],
    "B3": ["GR", "CY"],
    "C1": ["TR", "AZ", "UZ", "KZ"],
    "C2": ["IR", "AF", "TJ"],
    "C3": ["IQ", "JO", "EG", "SY"],
    "C4": ["SA", "AE", "QA", "KW"],
    "C5": ["MA", "DZ", "TN"],
    "C6": ["IL"],
    "C7": ["AM"],
    "C8": ["GE"],
    "C9": ["RU", "AZ"],
    "D1": ["IN", "NP"],
    "D2": ["IN", "LK"],
    "D3": ["BD", "IN"],
    "D4": ["PK"],
    "D5": ["LK"],
    "E1": ["CN"],
    "E2": ["TW", "HK"],
    "E3": ["JP"],
    "E4": ["KR"],
    "E5": ["VN"],
    "E6": ["TH", "KH", "LA"],
    "E7": ["ID", "MY", "PH", "SG"],
    "F1": ["SN", "CI", "CM"],
    "F2": ["NG", "GH", "KE"],
    "F3": ["ET", "ER"],
    "F4": ["AO", "MZ"],
    "G1": ["BR", "MX", "AR", "CL", "CO"],
    "H1": ["GB", "FR", "DE", "IT"],
    "R0": ["XX"],
    "Z0": ["XX"],
}

# Sample surname pools per script family
LATIN_SURNAMES = [
    "Smith",
    "Müller",
    "García",
    "Dubois",
    "Rossi",
    "da Silva",
    "O'Brien",
    "van der Berg",
    "Johansson",
    "Nielsen",
    "Kovács",
    "Nowak",
    "Svoboda",
]
CYRILLIC_SURNAMES = ["Иванов", "Петров", "Козлов", "Новиков", "Морозов"]
ARABIC_SURNAMES = ["الحسن", "العربي", "محمد", "عبدالله", "الشريف"]
CJK_SURNAMES = ["王", "李", "张", "刘", "陈", "杨", "黄", "赵"]
GIVEN_NAMES = [
    "John",
    "Maria",
    "Ahmed",
    "Wei",
    "Yuki",
    "Sven",
    "Anna",
    "Boris",
    "Priya",
    "Carlos",
    "Fatima",
    "Hiroshi",
    "Olga",
    "Kwame",
    "Mei",
]


def _generate_global_id(name: str, birth: int) -> str:
    """Generate a deterministic GlobalID."""
    raw = hashlib.sha256(f"{name}:{birth}".encode()).digest()[:16]
    import base64

    b32 = base64.b32encode(raw).decode().rstrip("=")[:22]
    return b32.upper()


def _generate_entry(region: str, idx: int) -> dict:
    """Generate a single synthetic entry for a region."""
    rng = random.Random(hash((region, idx)))
    countries = REGIONS[region]
    country = rng.choice(countries)
    birth = rng.randint(1900, 2000)

    surname = rng.choice(LATIN_SURNAMES)
    given = rng.choice(GIVEN_NAMES)
    # Append index to ensure unique names across large batches
    canonical = f"{surname}, {given} {region}{idx}"

    return {
        "CanonicalLatin": canonical,
        "CanonicalNative": canonical,
        "BirthYear": birth,
        "CountryCodes": [country],
        "Gender": rng.choice(["male", "female", "unspecified"]),
        "FamilyNameType": "surname",
        "LanguageOfPublication": ["eng"],
        "Historic": birth < 1850,
        "GDPR_DATA": False,
        "Confidence": rng.randint(50, 100),
        "GlobalID": _generate_global_id(canonical, birth),
        "RegionCode": region,
    }


def _generate_batch(size: int) -> list:
    """Generate a batch of synthetic entries distributed across regions."""
    entries = []
    regions = list(REGIONS.keys())
    per_region = size // len(regions)
    remainder = size % len(regions)

    for i, region in enumerate(regions):
        count = per_region + (1 if i < remainder else 0)
        for j in range(count):
            entries.append(_generate_entry(region, j))

    return entries


@pytest.mark.stress
class TestSyntheticStress:
    """2M synthetic entry stress tests."""

    def test_generate_2m_entries(self):
        """Verify we can generate 2M entries without OOM."""
        start = time.time()
        count = 0
        # Generate in chunks to avoid memory spikes
        for chunk_start in range(0, 2_000_000, 50_000):
            chunk_size = min(50_000, 2_000_000 - chunk_start)
            batch = _generate_batch(chunk_size)
            count += len(batch)
            # Basic sanity checks on each chunk
            assert all("GlobalID" in e for e in batch)
            assert all("CanonicalLatin" in e for e in batch)
            del batch  # Free memory

        elapsed = time.time() - start
        assert count == 2_000_000, f"Expected 2M entries, got {count}"
        assert elapsed < 300, f"Generation took {elapsed:.1f}s (max 300s)"

    def test_global_id_uniqueness_at_scale(self):
        """GlobalIDs should be unique across 100K entries."""
        batch = _generate_batch(100_000)
        ids = set(e["GlobalID"] for e in batch)
        # Allow small collision rate (hash truncation)
        collision_rate = 1 - len(ids) / len(batch)
        assert collision_rate < 0.001, f"Collision rate {collision_rate:.4f} exceeds 0.1%"

    def test_region_distribution(self):
        """Entries should be distributed across all 37 regions."""
        batch = _generate_batch(37_000)
        region_counts = {}
        for e in batch:
            r = e["RegionCode"]
            region_counts[r] = region_counts.get(r, 0) + 1

        assert len(region_counts) == 37, f"Expected 37 regions, got {len(region_counts)}"
        for region, count in region_counts.items():
            assert count >= 900, f"Region {region} has only {count} entries (expected ~1000)"

    def test_schema_validity_at_scale(self):
        """All generated entries should have required fields."""
        batch = _generate_batch(10_000)
        required = [
            "GlobalID",
            "CanonicalLatin",
            "CanonicalNative",
            "BirthYear",
            "CountryCodes",
            "Gender",
            "FamilyNameType",
            "LanguageOfPublication",
            "Historic",
            "GDPR_DATA",
            "Confidence",
        ]
        for e in batch:
            for field in required:
                assert field in e, f"Missing {field} in entry {e.get('CanonicalLatin', '?')}"

    def test_memory_usage_within_bounds(self):
        """Memory usage should stay within 6GB RSS limit (spec quality gate)."""
        import resource

        batch = _generate_batch(500_000)
        rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
        # macOS reports in bytes, Linux in KB
        import sys

        if sys.platform == "darwin":
            rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
        else:
            rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

        assert rss_mb < 6000, f"RSS {rss_mb:.0f}MB exceeds 6GB limit"
        del batch
