"""Self-tests for the two guard tools themselves (R53 §2b.2/.3).

The 20-check audit battery gates CI, and the perf tool produces the
documented benchmark numbers — but nothing verified THEY work. The
critical property for the audit: a seeded violation is actually CAUGHT
(a battery that always passes protects nothing).
"""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load(modname, relpath):
    spec = importlib.util.spec_from_file_location(modname, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def audit():
    return _load("audit_repo", "tools/audit_repo.py")


@pytest.fixture(scope="module")
def bench():
    return _load("run_benchmark", "tools/run_benchmark.py")


@pytest.mark.timeout(60)
def test_audit_a1_catches_seeded_broken_reference(audit, tmp_path_factory, monkeypatch):
    """Seed a doc referencing a missing file — A1 must report it."""
    fake = tmp_path_factory.mktemp("fake_repo")
    (fake / "docs").mkdir()
    (fake / "README.md").write_text("See docs/does_not_exist.md for details.\n")
    for doc in (
        "CLAUDE.md",
        "DEMO.md",
        "ARCHITECTURE.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
    ):
        (fake / doc).write_text("clean\n")
    monkeypatch.setattr(audit, "REPO", fake)
    name, errors = audit._check_referenced_files_exist()
    assert errors, "A1 failed to catch a seeded broken doc reference"
    assert any("does_not_exist" in e for e in errors)


@pytest.mark.timeout(60)
def test_audit_a1_passes_on_clean_fixture(audit, tmp_path_factory, monkeypatch):
    fake = tmp_path_factory.mktemp("clean_repo")
    (fake / "docs").mkdir()
    (fake / "docs" / "real.md").write_text("hi\n")
    (fake / "README.md").write_text("See docs/real.md.\n")
    for doc in (
        "CLAUDE.md",
        "DEMO.md",
        "ARCHITECTURE.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
    ):
        (fake / doc).write_text("clean\n")
    monkeypatch.setattr(audit, "REPO", fake)
    _, errors = audit._check_referenced_files_exist()
    assert errors == []


@pytest.mark.timeout(30)
def test_bench_synthetic_generator_shape(bench):
    entries = bench.generate_entries(50)
    assert len(entries) == 50
    assert all(e.get("CanonicalLatin") for e in entries)
    # country codes must rotate (the generator's documented behaviour) so
    # the benchmark exercises multiple regions, not one hot path
    ccs = {tuple(e.get("CountryCodes") or ()) for e in entries}
    assert len(ccs) > 1
    # deterministic: same n -> same entries (benchmarks must be comparable)
    assert bench.generate_entries(50) == entries
