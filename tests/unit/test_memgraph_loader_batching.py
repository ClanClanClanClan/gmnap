"""R60.3 pins — the Memgraph loader issues ONE round-trip per batch.

The loader looked batched but was not: it opened one transaction per
500-row batch and then ran a per-row Python loop inside it
(`for p in batch: tx.run(UPSERT_PERSON, **p)`), so each of the ~39 k
persons and ~21 k advisor edges still cost its own Bolt round-trip —
~60 k in total. Same defect class as R56's row-wise DuckDB load and
R54's per-entry changelog writes. Runtime drifted into the e2e
fixture's 900 s ceiling (memgraph-test: 12m29s green -> loader timeout)
and started failing CI.

The queries are now UNWIND-batched and take a single `rows` parameter.
These tests pin the property that actually regressed — the number of
round-trips — using a stub driver, so they run without a Memgraph
server (the e2e suite in tests/integration/ covers real behavior).
"""

import json
from pathlib import Path

import pytest

import tools.load_memgraph_from_enrichment as loader


class _StubTx:
    def __init__(self, calls):
        self.calls = calls

    def run(self, query, **params):
        self.calls.append((query, params))

    def commit(self):
        pass

    def rollback(self):  # pragma: no cover - only on failure paths
        pass


class _StubSession:
    def __init__(self, calls):
        self.calls = calls

    def begin_transaction(self):
        return _StubTx(self.calls)

    def run(self, stmt, **kw):  # schema statements
        class _R:
            def consume(self_inner):
                return None

        return _R()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _StubDriver:
    def __init__(self, calls):
        self.calls = calls

    def verify_connectivity(self):
        pass

    def session(self, **kw):
        return _StubSession(self.calls)

    def close(self):
        pass


@pytest.fixture
def enrichment(tmp_path: Path) -> Path:
    """120 persons, each with one advisor -> 120 person + 120 edge rows."""
    by_name = {}
    for i in range(120):
        by_name[f"person{i:03d}"] = {
            "CanonicalLatin": f"Person{i:03d}, Test",
            "GlobalID": f"gid{i:03d}",
            "BirthYear": 1900 + (i % 100),
            "Institution": "Test University",
            "Country": "Testland",
            "Source": "unit-test",
            "Advisors": [{"name": f"Advisor{i % 7:03d} Test"}],
        }
    p = tmp_path / "enrichment.json"
    p.write_text(json.dumps({"by_name": by_name}), encoding="utf-8")
    return p


def _load(monkeypatch, enrichment: Path, batch_size: int):
    calls: list = []
    monkeypatch.setattr(
        loader.GraphDatabase, "driver", lambda *a, **k: _StubDriver(calls)
    )
    stats = loader.load(enrichment, "bolt://stub:7687", batch_size=batch_size)
    return stats, calls


def test_one_roundtrip_per_batch_not_per_row(monkeypatch, enrichment):
    stats, calls = _load(monkeypatch, enrichment, batch_size=50)
    # 120 persons at batch 50 -> 3 flushes; 120 edges -> 3 flushes.
    assert len(calls) == 6, (
        f"expected 6 round-trips (3 person + 3 edge batches), got {len(calls)} "
        "— the per-row tx.run loop is back"
    )
    assert stats["persons"] == 120
    assert stats["edges"] == 120


def test_rows_parameter_carries_the_whole_batch(monkeypatch, enrichment):
    _, calls = _load(monkeypatch, enrichment, batch_size=50)
    for query, params in calls:
        assert "UNWIND $rows AS row" in query, "query is not UNWIND-batched"
        assert set(params) == {"rows"}, f"unexpected params: {sorted(params)}"
        assert isinstance(params["rows"], list) and params["rows"]
        assert len(params["rows"]) <= 50


def test_batch_contents_are_not_aliased_after_flush(monkeypatch, enrichment):
    """The flush clears the batch list in place — rows must not go empty.

    `batch.clear()` after passing the SAME list object as a query
    parameter would blank out what the driver is about to send. The
    loader must hand over a copy (or the driver must have consumed it);
    this pins that the recorded payloads still hold their rows.
    """
    _, calls = _load(monkeypatch, enrichment, batch_size=50)
    sizes = [len(p["rows"]) for _, p in calls]
    assert all(s > 0 for s in sizes), f"a batch arrived empty: {sizes}"
    assert sum(sizes[:3]) == 120, f"person rows lost: {sizes[:3]}"


def test_scales_roundtrips_with_batch_size(monkeypatch, enrichment):
    _, small = _load(monkeypatch, enrichment, batch_size=10)
    _, large = _load(monkeypatch, enrichment, batch_size=120)
    assert len(small) == 24, len(small)  # 12 person + 12 edge flushes
    assert len(large) == 2, len(large)  # 1 person + 1 edge flush
