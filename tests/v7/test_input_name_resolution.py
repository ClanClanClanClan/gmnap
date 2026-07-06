"""R54: input name resolution + nameless-entry flagging.

Before R54, an entry keyed {"Name": ...} (or with an empty CanonicalLatin)
reached GlobalID assignment with no name content, so every such entry hashed
the empty string to the SAME base id — distinct people collapsed onto one
identity, masked by --1/--2 collision suffixes. Now aliases resolve into
CanonicalLatin, and a truly-nameless entry is flagged Status='failed'.
"""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("OFFLINE", "1")
os.environ.setdefault("GMNAP_NO_PARALLEL", "1")

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _run(batch):
    return asyncio.run(
        V7Pipeline(mode=PipelineMode.QUICK).process_batch([dict(e) for e in batch])
    )


@pytest.mark.timeout(60)
def test_name_alias_resolves_and_ids_are_distinct():
    """Five different people under the "Name" key get five DISTINCT base
    GlobalIDs (not one empty-hash base + collision suffixes)."""
    rows = _run([{"Name": f"Distinct Person {i}"} for i in range(5)])
    assert all(r.get("CanonicalLatin") for r in rows)  # alias -> CanonicalLatin
    bases = {r["GlobalID"].split("--")[0] for r in rows}
    assert len(bases) == 5, (
        f"expected 5 distinct base GlobalIDs, got {len(bases)} — nameless "
        f"collapse regressed: {[r['GlobalID'] for r in rows]}"
    )


@pytest.mark.timeout(60)
def test_nameless_entry_is_flagged_failed():
    rows = _run([{"CountryCodes": ["US"]}, {"CanonicalLatin": "Valid, Name"}])
    nameless, valid = rows[0], rows[1]
    # Flagged as a failure state (stage 8 may relabel "failed" ->
    # "failed_validation" for the missing CanonicalLatin) — never "success".
    assert str(nameless.get("Status")).startswith("failed"), nameless.get("Status")
    assert "no usable name" in (nameless.get("StatusError") or "")
    assert valid.get("Status") == "success"


@pytest.mark.timeout(60)
def test_gdpr_mask_does_not_leak_exact_year():
    """A small cohort's exact birth year must NOT survive on the record."""
    rows = _run(
        [
            {"CanonicalLatin": f"Person {i}", "CountryCodes": ["FR"], "BirthYear": 1980}
            for i in range(3)
        ]
    )
    for r in rows:
        assert r.get("BirthYear") == "1980s"
        assert "BirthYear_Original" not in r, "exact year leaked past the mask"
