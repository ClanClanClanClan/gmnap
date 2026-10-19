#!/usr/bin/env python3
"""Comprehensive repository invariant audit.

Born out of the 2026-04-30 meta-audit conversation: every "check
everything again" round across rounds 7, 8, 9 found new real issues
that the previous round missed. The pattern was hand-grep + memory
checking ad-hoc invariants. This script formalizes ALL of them into
one runnable battery that exits non-zero if anything regresses.

Run on every CI build (gating). Run before every release. Run any
time you change a number anywhere — if it's also documented or
referenced elsewhere, this catches the docs that didn't follow.

Categories:

  A. File-tree integrity         — referenced files exist, no orphans
  B. Python parse + import       — no broken modules, no dead imports
  C. JSON / YAML parse           — every config / data file is valid
  D. Numerical-claim consistency — doc numbers == measured numbers
  E. Config-version consistency  — Memgraph + dep versions align
  F. Make-target integrity       — every advertised target resolves
  G. CI/test wiring (both ways)  — every test file CI names exists (G1),
                                   imports (G2) and holds >= 1 test (G4);
                                   and every test file a plain `pytest
                                   tests/` collects is run by some
                                   workflow (G3). G1/G2/G4 walk CI →
                                   disk; G3 walks disk → CI, which is
                                   the direction that let 474 tests sit
                                   unrun until R72.
  H. Test-name uniqueness        — no shadowing module basenames
  I. Tool idempotency            — re-runs produce same output
  J. Doc cross-references        — links / paths actually resolve

Usage:

    make audit-repo
    # or:
    PYTHONPATH=. python3 tools/audit_repo.py

Exits 0 on a clean repo; non-zero with a per-check breakdown if
anything is broken. Any new invariant we want to enforce → add a
``_check_*`` function and register it in ``CHECKS`` below.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Set, Tuple

REPO = Path(__file__).resolve().parent.parent

Result = Tuple[str, List[str]]  # (check_name, list of failure messages)


# ─── A. File-tree integrity ────────────────────────────────────────────


def _check_referenced_files_exist() -> Result:
    """Every doc that references a file path: that file must exist.

    CHANGELOG.md is intentionally excluded — by design it documents
    past states including deletions ("Removed: foo.py"), so its
    references *should* point at files that no longer exist.
    """
    errors: List[str] = []
    docs = [
        "README.md",
        "CLAUDE.md",
        "DEMO.md",
        "ARCHITECTURE.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "PRIVACY.md",  # R55: the data-protection notice cites code paths too
        # CHANGELOG.md excluded: documents historical state
    ]
    pattern = re.compile(
        r"\b(docs/[A-Za-z0-9_/.\-]+\.(?:md|json|yaml|yml|html))\b"
        r"|\b(tests/[A-Za-z0-9_/.\-]+\.(?:py|json))\b"
        r"|\b(tools/[A-Za-z0-9_/.\-]+\.py)\b"
        r"|\b(src/[A-Za-z0-9_/.\-]+\.py)\b"
    )
    for doc in docs:
        path = REPO / doc
        if not path.exists():
            errors.append(f"{doc}: doc itself does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            ref = next(g for g in match.groups() if g)
            # Skip codeblocks / placeholders / glob patterns
            if "*" in ref or "<" in ref or "{" in ref:
                continue
            target = REPO / ref
            if not target.exists():
                errors.append(f"{doc} → {ref} (does not exist)")
    return ("A1: referenced files exist", errors)


def _check_no_stale_dead_module_refs() -> Result:
    """No production-path file references the modules deleted in
    rounds 2 and 4."""
    errors: List[str] = []
    deleted = [
        "v7_quality_gates",
        "end_to_end_orchestration",
        "pipeline_v7_hotfix",
        "pipeline_stage_implementation",
        "real_compliance_tracker",
        "performance_benchmarker",
        "v7_orchestrator",
        "authority_source_integration",
        # Deleted *_adapter.py files in src/authority/:
        "openalex_adapter",
        "crossref_adapter",
        "gnd_adapter",
        "hal_adapter",
        "wikidata_p184_adapter",
        "zbmath_open_adapter",
        "crossref_thesis_adapter",
        "oai_university_adapter",
        "orcid_etd_adapter",
    ]
    scope = [
        "src/",
        "tests/unit/",
        "tests/authority/",
        "tests/cjk/",
        "tests/db/",
        "tests/v7/",
        "tests/integration/",
    ]
    for sub in scope:
        for path in (REPO / sub).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for mod in deleted:
                if re.search(rf"\b{re.escape(mod)}\b", text):
                    rel = path.relative_to(REPO)
                    # Allow self-references in the few legacy sites
                    # that still mention the names in comments only:
                    if mod in ("end_to_end_orchestration",) and rel.name.startswith(
                        "test_"
                    ):
                        continue
                    errors.append(f"{rel}: still references deleted module `{mod}`")
    return ("A2: no stale dead-module refs", errors)


# ─── B. Python parse + import ──────────────────────────────────────────


def _check_python_files_parse() -> Result:
    """Every tracked Python file in src/ + tests/ + tools/ parses."""
    errors: List[str] = []
    for sub in ["src/", "tests/", "tools/"]:
        for path in (REPO / sub).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError as exc:
                errors.append(
                    f"{path.relative_to(REPO)}: SyntaxError line {exc.lineno}: {exc.msg}"
                )
    return ("B1: python files parse", errors)


def _check_production_imports() -> Result:
    """The handful of paths the API + CLI depend on must import."""
    errors: List[str] = []
    targets = [
        "src.core.pipeline_v7",
        "src.api.server",
        "src.cli.gmnap",
        "src.regions.manager_optimized",
        "src.regions.benchmark_split",
        "src.regions.calibration",
        "src.authorities.manager_tier01",
        "src.authorities.common",
    ]
    for mod in targets:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            cwd=str(REPO),
            env={**os.environ, "PYTHONPATH": str(REPO)},
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:]
            errors.append(f"{mod}: import failed — {tail}")
    return ("B2: production imports succeed", errors)


# ─── C. JSON / YAML parse ──────────────────────────────────────────────


def _check_json_files_parse() -> Result:
    """Every committed JSON file under data/ docs/ tests/fixtures/
    + the OpenAPI export — parse cleanly."""
    errors: List[str] = []
    for sub in ["data/", "docs/", "tests/fixtures/", "tests/integration/"]:
        for path in (REPO / sub).rglob("*.json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                errors.append(f"{path.relative_to(REPO)}: {exc}")
    return ("C1: JSON files parse", errors)


def _check_yaml_files_parse() -> Result:
    """Every committed YAML file parses."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return ("C2: YAML files parse", ["pyyaml not installed (skipping)"])
    errors: List[str] = []
    for path in [
        REPO / ".github" / "workflows" / "ci.yml",
        REPO / "docker-compose.yml",
    ]:
        if not path.exists():
            errors.append(f"{path.relative_to(REPO)}: missing")
            continue
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(REPO)}: {exc}")
    # Also any region YAML overrides we might have
    if (REPO / "config" / "regions").exists():
        for path in (REPO / "config" / "regions").rglob("*.yaml"):
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                errors.append(f"{path.relative_to(REPO)}: {exc}")
    return ("C2: YAML files parse", errors)


# ─── D. Numerical-claim consistency ────────────────────────────────────


def _check_calibration_doc_matches_json() -> Result:
    """The numbers in docs/calibration.md must match docs/calibration.json
    to within float-formatting tolerance."""
    errors: List[str] = []
    cal = json.loads((REPO / "docs" / "calibration.json").read_text())
    md = (REPO / "docs" / "calibration.md").read_text()
    expectations = [
        (cal["ece"], "raw test ECE"),
        (cal["calibrated"]["ece"], "calibrated test ECE"),
        (cal["cv"]["ece"], "CV ECE"),
        (cal["brier"], "raw Brier"),
        (cal["calibrated"]["brier"], "calibrated Brier"),
    ]
    for value, label in expectations:
        # Both 4-decimal and 3-decimal renderings are acceptable.
        candidates = {f"{value:.4f}", f"{value:.3f}", f"{value:.2f}"}
        if not any(c in md for c in candidates):
            errors.append(
                f"docs/calibration.md missing {label}: "
                f"expected one of {candidates} (json: {value})"
            )
    return ("D1: calibration md ↔ json", errors)


def _check_calibration_apply_matches_knots() -> Result:
    """The calibration knots file produces the documented apply()
    outputs."""
    errors: List[str] = []
    knots_path = REPO / "data" / "calibration_isotonic.json"
    if not knots_path.exists():
        return ("D2: calibration knots → apply", ["knots file missing"])
    payload = json.loads(knots_path.read_text())
    knots = payload.get("knots") or []
    if not knots:
        errors.append("knots list empty")
    # Walk: every threshold/cal_p in [0,1]; thresholds non-decreasing
    last_thresh = -1.0
    last_cal = -1.0
    for k in knots:
        if not (isinstance(k, list) and len(k) == 2):
            errors.append(f"malformed knot {k!r}")
            continue
        t, c = k
        if not (0.0 <= t <= 1.0):
            errors.append(f"threshold {t} out of [0,1]")
        if not (0.0 <= c <= 1.0):
            errors.append(f"cal_p {c} out of [0,1]")
        if t < last_thresh - 1e-9:
            errors.append(f"thresholds not sorted: {last_thresh} → {t}")
        if c < last_cal - 1e-9:
            errors.append(f"cal_p not monotone: {last_cal} → {c}")
        last_thresh = t
        last_cal = c
    return ("D2: calibration knots well-formed", errors)


def _check_benchmark_split_sums() -> Result:
    """train + test must equal full set with no overlap."""
    errors: List[str] = []
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.regions.benchmark_split import load_all,load_train,load_test;"
            "a=set(e['full_name'] for e in load_all());"
            "tr=set(e['full_name'] for e in load_train());"
            "te=set(e['full_name'] for e in load_test());"
            "print(f'{len(a)},{len(tr)},{len(te)},{len(tr&te)}')",
        ],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        errors.append(f"split helper failed: {proc.stderr.strip()}")
    else:
        parts = proc.stdout.strip().split(",")
        if len(parts) != 4:
            errors.append(f"unexpected helper output: {proc.stdout.strip()}")
        else:
            n_all, n_tr, n_te, n_overlap = map(int, parts)
            if n_overlap != 0:
                errors.append(f"train ∩ test = {n_overlap} (must be 0)")
            if n_all != n_tr + n_te:
                errors.append(f"train+test ({n_tr+n_te}) != all ({n_all})")
    return ("D3: benchmark split is a partition", errors)


def _check_genealogy_count_matches_docs() -> Result:
    """data/genealogy_enrichment.json count must match the
    ~39,500 claim in docs (within ±3000 to handle natural growth).

    Round 23 expanded the Wikidata harvest from 9,216 → 20,833
    entries via decade-partitioned SPARQL (the offset-paginated
    version of round 18 hit 504s at offset >28k). Rebuilt
    enrichment: ~39,497 entries, ~20,810 with advisor chains,
    ~17,348 with BirthYear, ~34,591 with Institution.
    """
    errors: List[str] = []
    path = REPO / "data" / "genealogy_enrichment.json"
    if not path.exists():
        return ("D4: genealogy count claim", ["genealogy file missing — git lfs pull?"])
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"file unparseable: {exc}")
        return ("D4: genealogy count claim", errors)
    count = len(payload.get("by_global_id") or {})
    # Allow LFS-stub files (tiny payload). Real file has ~67,500 (R63
    # theses.fr harvest added ~15k IdRef-disambiguated French math students +
    # ~21k advisor edges on top of the R62 Wikidata base).
    if count < 1000:
        errors.append(
            f"by_global_id count={count} — looks like an LFS stub, "
            f"run `git lfs install && git lfs pull`"
        )
        return ("D4: genealogy count claim", errors)
    # Docs say ~67,500. Allow 62,000-74,000 range.
    if not (62000 <= count <= 74000):
        errors.append(
            f"by_global_id count={count} outside expected ~67,500 range; "
            f"update README + CLAUDE if data has grown"
        )
    return ("D4: genealogy count claim", errors)


# ─── E. Config-version consistency ─────────────────────────────────────


def _check_memgraph_version_match() -> Result:
    """docker-compose.yml and ci.yml must pin the same Memgraph image
    + version so local dev and CI exercise the same code paths."""
    errors: List[str] = []
    compose = (REPO / "docker-compose.yml").read_text()
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    pat = re.compile(r"image:\s*memgraph/memgraph:(\d+\.\d+\.\d+)")
    cv = pat.search(compose)
    civ = pat.search(ci)
    if not cv:
        errors.append("docker-compose.yml: no `image: memgraph/memgraph:X.Y.Z`")
    if not civ:
        errors.append("ci.yml: no `image: memgraph/memgraph:X.Y.Z`")
    if cv and civ and cv.group(1) != civ.group(1):
        errors.append(
            f"version skew: docker-compose pins {cv.group(1)}, "
            f"ci.yml pins {civ.group(1)}"
        )
    return ("E1: Memgraph version match", errors)


def _check_lockfile_in_sync() -> Result:
    """requirements.lock body (sans header) must be reproducible from
    requirements.txt via pip-compile (matches what CI's lint job
    asserts)."""
    # Local pip-compile may not be installed; just verify the file
    # exists and the body uses the expected pin format. The CI job
    # already runs the actual diff.
    errors: List[str] = []
    lock = REPO / "requirements.lock"
    if not lock.exists():
        errors.append("requirements.lock missing")
        return ("E2: lockfile present", errors)
    body = [
        ln
        for ln in lock.read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    if not body:
        errors.append("requirements.lock has no pinned-deps body")
    return ("E2: lockfile present + non-empty", errors)


# ─── F. Make-target integrity ──────────────────────────────────────────


def _check_make_targets_resolve() -> Result:
    """Every PHONY target in the Makefile must `make -n` resolve."""
    errors: List[str] = []
    mk = (REPO / "Makefile").read_text()
    phony = re.search(r"^\.PHONY:\s*(.+)$", mk, re.MULTILINE)
    if not phony:
        return ("F1: PHONY targets resolve", ["no .PHONY line in Makefile"])
    targets = phony.group(1).split()
    # Drop "help" since `make -n help` echoes — fine, but already covered.
    for t in targets:
        proc = subprocess.run(
            ["make", "-n", t],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            errors.append(
                f"{t}: `make -n` failed: {proc.stderr.strip().splitlines()[:3]}"
            )
    return ("F1: every Make target resolves", errors)


# ─── G. CI-yaml file references ────────────────────────────────────────


def _check_ci_test_files_exist() -> Result:
    """Every test path enumerated in CI's yaml must exist on disk."""
    errors: List[str] = []
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    # Match indented `tests/...py` lines (one path per line)
    for m in re.finditer(r"(?m)^\s+(tests/[A-Za-z0-9_/.\-]+\.py)\s*$", ci):
        ref = m.group(1)
        if not (REPO / ref).exists():
            errors.append(f".github/workflows/ci.yml → {ref} (does not exist)")
    return ("G1: CI test paths exist", errors)


def _check_ci_test_files_collect() -> Result:
    """Every CI-listed test file must collect cleanly (import successfully).

    G1 only checks that the file *exists*. This check goes further: it
    asks pytest to collect each file the way CI does (explicit-path
    invocation). If collection errors — typically `ModuleNotFoundError`
    on a deleted dependency — the audit fails, locally, before push.

    Round-18 caught this gap the hard way: pipeline_v6.py was deleted,
    `tests/conftest.py:collect_ignore_glob` skipped the broken files
    when running `pytest tests/`, but CI's explicit file enumeration
    bypassed `collect_ignore_glob` and tripped on the same files. CI
    went red. This check reproduces CI's collection step locally so
    the trip happens before push.

    NOT in --fast mode (subprocess-spawning + ~5 s cost). Full audit
    runs it; CI's audit-repo job runs it.
    """
    errors: List[str] = []
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    files = sorted(
        {
            m.group(1)
            for m in re.finditer(r"(?m)^\s+(tests/[A-Za-z0-9_/.\-]+\.py)\s*$", ci)
        }
    )
    if not files:
        return ("G2: CI test files collect cleanly", errors)
    # Filter to those that exist (G1 catches missing ones; we don't
    # need to double-report the same failure shape).
    extant = [f for f in files if (REPO / f).exists()]
    if not extant:
        return ("G2: CI test files collect cleanly", errors)
    # Verify pytest is importable before shelling out — if it's
    # missing the subprocess exits with "No module named pytest",
    # which looks like a collection failure but is actually an
    # environment mismatch (caught in CI round 19, where the
    # `audit-repo` job didn't install pytest).
    sentinel = subprocess.run(
        [sys.executable, "-c", "import pytest"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if sentinel.returncode != 0:
        errors.append(
            "pytest is not installed in the current Python environment; "
            "G2 cannot run. Install with `pip install pytest pytest-timeout "
            "pytest-mock pytest-asyncio` (the set CI's `test` job uses)."
        )
        return ("G2: CI test files collect cleanly", errors)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--no-header",
            *extant,
        ],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        # Surface only the import errors — pytest's full output is
        # noisy (warnings, deprecations). The signal we want is
        # `ImportError while importing test module ...`.
        for line in (proc.stdout + "\n" + proc.stderr).splitlines():
            if (
                "ImportError" in line
                or "ModuleNotFoundError" in line
                or "errors" in line.lower()
                and "during collection" in line.lower()
            ):
                errors.append(line.strip())
        if not errors:
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
            errors.append("collect failed; tail: " + " | ".join(tail))
    return ("G2: CI test files collect cleanly", errors)


# ── G3 helpers: the two populations, measured the same way CI does ─────

_WORKFLOW_DIR = Path(".github") / "workflows"

# Test files that `pytest tests/` collects but NO workflow runs, which
# we accept. THE ONLY PERMITTED EXCEPTION to G3 — every entry needs a
# reason, and G3 fails on a stale entry (one that is now wired, or no
# longer collected), so the list cannot rot into a silent hole.
#
# Deliberately EMPTY as of R72: all 124 collected files are wired. If
# you are tempted to add an entry, the bar is "this file cannot run on
# a CI runner" (needs network, a GPU, a paid API key) — and the right
# home for such a file is a `norecursedirs` tree in pyproject.toml
# (tests/live, tests/performance, …), not this list.
_G3_UNWIRED_OK: Dict[str, str] = {}

# Workflow-named test files that legitimately contribute zero collected
# tests. Same rules as above: G4 fails on a stale entry.
_G4_ZERO_TEST_OK: Dict[str, str] = {}


def _collect_counts(paths: List[str] | None) -> Tuple[Dict[str, int], List[str]]:
    """Run `pytest --collect-only -q` and return {path: n_tests}, errors.

    ``paths=None`` collects ``tests/`` the way a developer does (so
    pyproject's ``norecursedirs`` and ``tests/conftest.py``'s
    ``collect_ignore_glob`` both apply). A list collects those explicit
    paths, the way CI's enumerated steps do (which bypasses
    ``collect_ignore_glob``).

    Shelling out to pytest is deliberate: re-implementing the
    norecursedirs + collect_ignore_glob resolution in this file would
    be a second, drifting copy of pytest's rules — i.e. the exact
    "guard measures something adjacent to the real thing" failure this
    check exists to catch.
    """
    errors: List[str] = []
    sentinel = subprocess.run(
        [sys.executable, "-c", "import pytest"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if sentinel.returncode != 0:
        errors.append(
            "pytest is not installed in the current Python environment; "
            "cannot enumerate tests. Install with `pip install pytest "
            "pytest-timeout pytest-mock pytest-asyncio`."
        )
        return {}, errors
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            *(paths if paths is not None else ["tests/"]),
        ],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
        capture_output=True,
        text=True,
        timeout=900,
    )
    counts: Dict[str, int] = {}
    for line in proc.stdout.splitlines():
        m = re.match(r"^(tests/[A-Za-z0-9_/.\-]+\.py): (\d+)$", line.strip())
        if m:
            counts[m.group(1)] = int(m.group(2))
    if proc.returncode != 0:
        # A non-zero collect is itself a finding — never swallow it,
        # or the whole check degrades to "nothing to compare".
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-4:]
        errors.append(
            "`pytest --collect-only` exited "
            f"{proc.returncode}; tail: " + " | ".join(t.strip() for t in tail)
        )
    if not counts and not errors:
        errors.append("`pytest --collect-only` reported no test files at all")
    return counts, errors


def _workflow_named_tests() -> Dict[str, Set[str]]:
    """Map every `tests/...py` path named in a workflow → the workflows.

    Scans ALL of ``.github/workflows/*.yml``, not just ci.yml, because
    "does this file run anywhere" is the question. YAML comments are
    stripped first: a path mentioned only in a comment does not run,
    and must not satisfy the check.
    """
    named: Dict[str, Set[str]] = {}
    wf_dir = REPO / _WORKFLOW_DIR
    for wf in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
        for raw in wf.read_text().splitlines():
            line = re.sub(r"(^|\s)#.*$", "", raw)
            for ref in re.findall(r"tests/[A-Za-z0-9_/.\-]+\.py", line):
                named.setdefault(ref, set()).add(wf.name)
    return named


def _check_every_collected_test_runs_in_ci() -> Result:
    """Every test file `pytest tests/` collects must run in some workflow.

    THE DIRECTION NOTHING CHECKED BEFORE R72. G1 and G2 both start from
    ci.yml and ask "does this path exist / import?" — they walk CI → disk.
    Nothing walked disk → CI, so a test file that no workflow named was
    invisible: it collected locally, passed locally, and was never run by
    CI. Adding a guard was a silent no-op.

    Measured at c68b734, before this check existed: `pytest tests/`
    collected 124 files, the workflows named 103, and the 44-file
    difference carried 474 tests that no CI run had ever executed. They
    were disproportionately the pin batteries of the most recent rounds
    (test_fetcher_contract.py, test_vetting_risk.py,
    test_genealogy_integrity.py, test_corrections_ledger.py,
    test_licence_and_origin_leaks.py, test_edge_provenance.py,
    test_spec_gates_blocking.py), including the two the docs name as the
    evidence for a claim: test_spec_gates_blocking.py ("pins the full
    set" of the 8 quality gates, CLAUDE.md) and test_vetting_risk.py
    ("Pinned by ...", docs/regime_coverage.md:109).

    Scope note: the authority here is `pytest tests/`, so a file parked
    under a ``norecursedirs`` tree in pyproject.toml (tests/live,
    tests/performance, tests/security, …) is out of scope by
    construction — parking is a visible, reviewed decision in a config
    file. This check governs the files that a plain test run DOES pick
    up, which is where a new guard lands by default.

    Known limitation, deliberately on the safe side: matching is
    FILE-level. A workflow that ran a whole directory (`pytest
    tests/unit/`) would not satisfy G3 for the files inside it, and G3
    would ask for them by name. That direction is a false ALARM, never a
    false pass — the failure mode this check must never have. No
    workflow does that today (ci.yml enumerates files; korean.yml runs
    FST tooling, not pytest). If one ever should, teach this function
    about directory prefixes rather than widening the allow-list.
    """
    errors: List[str] = []
    counts, collect_errors = _collect_counts(None)
    errors.extend(collect_errors)
    if not counts:
        return ("G3: every collected test file runs in CI", errors)

    named = _workflow_named_tests()
    collected = set(counts)

    unwired = sorted(collected - set(named) - set(_G3_UNWIRED_OK))
    if unwired:
        total = sum(counts[f] for f in unwired)
        errors.append(
            f"{len(unwired)} test file(s) collect under `pytest tests/` but no "
            f"workflow in {_WORKFLOW_DIR}/ runs them ({total} tests never "
            f"execute in CI). Add them to ci.yml's `Core tests` step, or park "
            f"the directory in pyproject.toml's norecursedirs, or add a "
            f"documented entry to _G3_UNWIRED_OK in {Path(__file__).name}:"
        )
        for f in unwired:
            errors.append(f"    {f}  ({counts[f]} tests)")

    # A stale allow-list entry is the same silent hole one level up.
    for f, why in sorted(_G3_UNWIRED_OK.items()):
        if f in named:
            errors.append(
                f"_G3_UNWIRED_OK is stale: {f} IS now run by "
                f"{sorted(named[f])} — drop the entry (reason given: {why})"
            )
        elif f not in collected:
            errors.append(
                f"_G3_UNWIRED_OK is stale: {f} is no longer collected by "
                f"`pytest tests/` — drop the entry (reason given: {why})"
            )
    return ("G3: every collected test file runs in CI", errors)


def _defines_a_test(path: Path) -> bool:
    """True if the file DEFINES at least one pytest test, statically.

    Deliberately an AST check, not a collection count. "pytest collected
    zero items from this file" conflates two opposite situations:

      (a) the file holds no test at all — a `__main__` demo script. A
          real defect: CI runs it and asserts nothing.
      (b) every test in it skipped at module level because an optional
          dependency is missing in THAT environment. Legitimate, and
          environment-dependent.

    Measured: in the `audit-repo` job's narrower dep set (no fasttext
    wheel, no requirements-dev), tests/unit/test_encryption.py and
    tests/unit/test_ft_negative_battery.py both collect zero items via
    `pytest.skip(allow_module_level=True)` — while defining 4 and 48
    tests respectively. A collection-count G4 failed on exactly those
    two and would have been "fixed" by allow-listing two healthy files.

    Asking what the source DEFINES is environment-independent, so the
    check gives the same answer on every runner, and needs no
    subprocess.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        # B1 reports unparseable files; don't double-report here, and
        # don't claim the file has no test when we could not look.
        return True
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test"):
                return True
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name.startswith("test"):
                        return True
    return False


def _check_ci_test_files_contribute_tests() -> Result:
    """Every test file a workflow names must DEFINE at least one test.

    G1 says the path exists, G2 says it imports, G3 says nothing is
    unwired — none of them asks whether the file actually holds a test.
    A `__main__`-style script under tests/ satisfies all three and
    contributes nothing: pytest collects zero items from it, the step
    goes green, and the file reads in ci.yml like coverage that isn't
    there.

    Measured at c68b734: two of CI's 103 named files
    (tests/v7/test_v7_full_pipeline.py and
    tests/v7/test_v7_complete_integration.py) are async demo scripts
    whose entry points sit behind `if __name__ == "__main__"`, with no
    `test_*` function and no `Test*` class. CI "ran" both on every push
    and asserted nothing. R72 removed them from ci.yml.

    See ``_defines_a_test`` for why this is static rather than a
    collection count — a count answers differently per environment and
    punishes files whose optional dependency is simply absent.
    """
    errors: List[str] = []
    named = _workflow_named_tests()
    extant = sorted(f for f in named if (REPO / f).exists())
    if not extant:
        # G1 reports missing paths; an empty extant set here means the
        # scan itself broke, which must not pass quietly.
        errors.append(
            f"no extant test files found in {_WORKFLOW_DIR}/ — the workflow "
            f"scan is broken (named: {len(named)})"
        )
        return ("G4: CI-named test files hold tests", errors)

    testless = sorted(
        f for f in extant if f not in _G4_ZERO_TEST_OK and not _defines_a_test(REPO / f)
    )
    if testless:
        errors.append(
            f"{len(testless)} workflow-named test file(s) define NO test "
            f"(no module-level `test_*` function, no `Test*` class with a "
            f"`test_*` method) — the step runs them and asserts nothing. "
            f"Give each a real test, drop it from the workflow, or add a "
            f"documented entry to _G4_ZERO_TEST_OK:"
        )
        for f in testless:
            errors.append(f"    {f}  (named in {sorted(named[f])})")

    for f, why in sorted(_G4_ZERO_TEST_OK.items()):
        if f in extant and _defines_a_test(REPO / f):
            errors.append(
                f"_G4_ZERO_TEST_OK is stale: {f} now defines a test — "
                f"drop the entry (reason given: {why})"
            )
        elif f not in named:
            errors.append(
                f"_G4_ZERO_TEST_OK is stale: {f} is no longer named in any "
                f"workflow — drop the entry (reason given: {why})"
            )
    return ("G4: CI-named test files hold tests", errors)


# ─── H. Test-name uniqueness (shadowing) ───────────────────────────────


def _check_no_test_module_shadowing() -> Result:
    """No two test_*.py files resolve to the same pytest module name.

    Pytest computes a test file's module name by walking up from the
    file *until it finds a directory without ``__init__.py``*. The
    module ID is the relative path from there, dot-separated. Two
    files only shadow each other when this computed name collides —
    a bare basename match is NOT enough (a file under
    ``tests/integration/`` with ``__init__.py`` is namespaced and
    can't collide with the same-basename file under ``tests/unit/``
    that has no ``__init__.py``).
    """
    errors: List[str] = []
    seen: dict = {}
    norecurse = {
        # Mirrors pyproject.toml::norecursedirs after round-34 phase-5
        # cleanup. Dirs that were both broken AND not contributing to
        # CI (coherence, compliance, error_recovery, extreme,
        # genealogy, idempotency, memory, mock_api, production,
        # regional, regions/e6_mainland_sea, roundtrip) were deleted
        # outright; the four remaining are kept-parked with
        # justification (see pyproject.toml).
        "docs/orphaned_tests",
        "tests/hardcore",
        "tests/integration/stages",
        "tests/live",
        "tests/paranoid",
        "tests/performance",
        "tests/security",
    }

    def _module_id(p: Path) -> str:
        """Replicate pytest's rootdir module-name computation."""
        parts = [p.stem]
        cur = p.parent
        while (cur / "__init__.py").exists():
            parts.append(cur.name)
            cur = cur.parent
        return ".".join(reversed(parts))

    for path in (REPO / "tests").rglob("test_*.py"):
        rel_dir = str(path.relative_to(REPO).parent)
        if any(rel_dir.startswith(skip) for skip in norecurse):
            continue
        if "__pycache__" in path.parts:
            continue
        mid = _module_id(path)
        seen.setdefault(mid, []).append(str(path.relative_to(REPO)))
    for mid, paths in seen.items():
        if len(paths) > 1:
            errors.append(
                f"module name '{mid}' resolves to {len(paths)} files: {paths}"
            )
    return ("H1: no test-module shadowing in CI scope", errors)


def _check_no_test_bandaid_swallows() -> Result:
    """No test function body silently swallows exceptions.

    Pattern caught: ``try: <stmt>; except Exception: pass`` (or
    bare ``except: pass``) directly inside a ``def test_*``. This
    turns the test into coverage-padding — a regression that breaks
    the wrapped statement still leaves the test green.

    Round-20 example: ``test_region_processors_full.py`` had 148
    such tests. De-bandaiding immediately surfaced a real production
    bug (``E7MaritimeSEAProcessor._detect_islamic_compounds`` was
    called but never defined; every E7 augment() raised
    AttributeError silently).

    Whitelisted patterns (NOT flagged):
      - ``except ImportError`` / ``except ModuleNotFoundError`` —
        skip patterns for optional dependencies are legit
      - try/except outside a ``def test_*`` (module-level fixtures,
        setUp/tearDown teardown best-effort cleanup)

    Scope: only files under ``tests/`` that end in ``test_*.py``,
    skipping the same norecurse directories as H1.
    """
    errors: List[str] = []
    # Mirror pyproject.toml's norecursedirs (round-34 phase-5
    # collapsed it from 19 entries to 7 by deleting the broken
    # dirs). H2 only flags test files that pytest can actually
    # collect on a default run.
    norecurse_prefixes = (
        "docs/orphaned_tests",
        "tests/hardcore",
        "tests/integration",  # whole tree (CI enumerates memgraph_e2e + orcid_etd_live)
        "tests/live",
        "tests/paranoid",
        "tests/performance",
        "tests/security",
    )
    for path in (REPO / "tests").rglob("test_*.py"):
        rel = str(path.relative_to(REPO))
        if any(rel.startswith(p) for p in norecurse_prefixes):
            continue
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # B1 catches parse errors

        # Walk only ``def test_*`` function bodies.
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            for try_node in ast.walk(node):
                if not isinstance(try_node, ast.Try):
                    continue
                for handler in try_node.handlers:
                    # Whitelist: ImportError / ModuleNotFoundError
                    exc_type = handler.type
                    is_optional_import = False
                    if isinstance(exc_type, ast.Name) and exc_type.id in (
                        "ImportError",
                        "ModuleNotFoundError",
                    ):
                        is_optional_import = True
                    elif isinstance(exc_type, ast.Tuple):
                        # except (ImportError, OSError) → if any name
                        # is an optional-import sentinel, allow.
                        names = {
                            elt.id for elt in exc_type.elts if isinstance(elt, ast.Name)
                        }
                        if names & {"ImportError", "ModuleNotFoundError"}:
                            is_optional_import = True
                    if is_optional_import:
                        continue

                    # Flag: body is exactly `pass` AND catches broadly.
                    body_is_pass = len(handler.body) == 1 and isinstance(
                        handler.body[0], ast.Pass
                    )
                    catches_broad = exc_type is None or (
                        isinstance(exc_type, ast.Name)
                        and exc_type.id in ("Exception", "BaseException")
                    )
                    if body_is_pass and catches_broad:
                        errors.append(
                            f"{rel}:{handler.lineno} in def {node.name}: "
                            f"`except {exc_type.id if isinstance(exc_type, ast.Name) else 'Exception'}: pass` "
                            "swallows regressions silently"
                        )
    return ("H2: no test-body bandaid swallows", errors)


def _check_no_self_method_called_but_not_defined() -> Result:
    """Every ``self.method()`` call must reference a method defined on
    the class (or one of its bases declared in the same module).

    Round-20 caught ``E7MaritimeSEAProcessor._detect_islamic_compounds``
    silently `AttributeError`-ing on every augment() call — the method
    was called but never defined. Round-22 caught ``F3._analyze_patronymic
    _structure``. Round-27 caught the ORCID-ETD parser walking against
    a v2 API shape. Same class-of-bug each time: code calls a name
    that isn't there. H3 catches it at audit time, before the live
    run that would expose it.

    Scope: every ``.py`` under ``src/regions/``, ``src/authority/``,
    ``src/authorities/``, ``src/core/``. Skips test files (test
    fixtures legitimately call into helpers across the suite).

    Limitations (intentional false-negative bias):
      - Methods defined on a base class in a *different module* aren't
        seen — we only check the file's own classes. Some legitimate
        cross-module inheritance gets a free pass.
      - ``getattr(self, "name", default)`` patterns are skipped (not
        ``self.name`` syntactic form).
      - Methods added at runtime via setattr / mixin / metaclass are
        not seen. Caller expected to verify themselves.

    With those exceptions, this catches the dominant pattern that
    bit the project three times in different processors.
    """
    errors: List[str] = []
    scope_dirs = [
        "src/regions",
        "src/authority",
        "src/authorities",
        "src/core",
    ]

    # Dynamically harvest method + attribute names from common base
    # modules. This avoids the maintenance overhead of a hardcoded
    # allowlist that drifts when bases gain / lose methods.
    def _collect_class_members(module_path: Path) -> set:
        """All method + assigned-attr names from any class in module."""
        names: set = {
            # Always-present dunder + RegionSpec.__post_init__
            # attribute set
            "__init__",
            "__post_init__",
            "logger",
        }
        if not module_path.exists():
            return names
        try:
            mtree = ast.parse(module_path.read_text(encoding="utf-8"))
        except SyntaxError:
            return names
        for cls in [n for n in ast.walk(mtree) if isinstance(n, ast.ClassDef)]:
            for node in cls.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name):
                        names.add(node.target.id)
            # self.x = … inside methods
            for node in ast.walk(cls):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                        ):
                            names.add(target.attr)
                elif isinstance(node, ast.AnnAssign):
                    target = node.target
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        names.add(target.attr)
        return names

    INHERITED_ALLOWLIST: set = set()
    INHERITED_ALLOWLIST |= _collect_class_members(REPO / "src/regions/base.py")
    INHERITED_ALLOWLIST |= _collect_class_members(REPO / "src/regions/base_enhanced.py")
    INHERITED_ALLOWLIST |= _collect_class_members(REPO / "src/authorities/base.py")

    def _members_of(cls: ast.ClassDef) -> set:
        """Methods + self-attribute defs declared inside one class node."""
        m: set = set()
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                m.add(node.name)
        for node in ast.walk(cls):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        m.add(target.attr)
            elif isinstance(node, ast.AnnAssign):
                target = node.target
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    m.add(target.attr)
        return m

    # Stdlib / external bases whose method names we can't resolve via
    # local AST. Any class inheriting from one of these gets a free
    # pass on H3 — they're false positives, not the F3/E7-class bug.
    EXTERNAL_BASE_NAMES = frozenset(
        {
            # logging
            "Formatter",
            "Handler",
            "Logger",
            "Filter",
            "LogRecord",
            "Adapter",
            # threading
            "Thread",
            "RLock",
            "Lock",
            "Event",
            "Condition",
            "Timer",
            # asyncio
            "Protocol",
            "Transport",
            # dataclass / Generic
            "Generic",
            "Protocol",
            # exceptions
            "Exception",
            "ValueError",
            "RuntimeError",
            "KeyError",
            "TypeError",
            "OSError",
            # ABC
            "ABC",
            "ABCMeta",
            "Enum",
            "IntEnum",
            "Flag",
            # numeric / collections
            "dict",
            "list",
            "set",
            "tuple",
            "namedtuple",
            "OrderedDict",
            "defaultdict",
            "Counter",
            # pytest/unittest
            "TestCase",
        }
    )

    def _has_external_base(cls: ast.ClassDef) -> bool:
        """True if any direct base name suggests an external (stdlib /
        third-party) parent class we can't resolve by local AST."""
        for base in cls.bases:
            if isinstance(base, ast.Name) and base.id in EXTERNAL_BASE_NAMES:
                return True
            # Attribute-form bases (e.g. logging.Formatter) — assume
            # external unless prefix is `src.` (which we'd resolve in
            # principle, but we don't follow imports yet).
            if isinstance(base, ast.Attribute):
                return True
        return False

    for sub in scope_dirs:
        root = REPO / sub
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            # Build {class_name: members} for every class in this file
            # so subclasses can resolve methods declared on a same-
            # module base class (e.g. extreme_adapters.py has a
            # `_BaseAdapter` whose `_offline()` is called by every
            # Tier-2 / Tier-3 adapter in the same file).
            file_class_members: dict = {}
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                file_class_members[cls.name] = _members_of(cls)

            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                if _has_external_base(cls):
                    continue
                defined: set = set(INHERITED_ALLOWLIST)
                defined |= _members_of(cls)
                # Same-module base resolution: for every base named
                # by simple identifier, pull in that class's members.
                for base in cls.bases:
                    if isinstance(base, ast.Name):
                        bname = base.id
                        if bname in file_class_members:
                            defined |= file_class_members[bname]

                for node in ast.walk(cls):
                    if not isinstance(node, ast.Call):
                        continue
                    func = node.func
                    if not (
                        isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "self"
                    ):
                        continue
                    name = func.attr
                    if name not in defined:
                        rel = path.relative_to(REPO)
                        errors.append(
                            f"{rel}:{node.lineno} in class {cls.name}: "
                            f"calls self.{name}() but method/attribute is "
                            f"not defined on the class"
                        )

    return ("H3: no self.method() called without definition", errors)


def _check_no_dataclass_unknown_kwarg() -> Result:
    """Every keyword arg passed to a same-file ``@dataclass`` constructor
    must match a declared field on that dataclass.

    Round-14 caught ``ORCIDETDRecord(identifier=...)`` where the
    dataclass had renamed the field to ``orcid_id`` but a caller still
    used the old name. Python raises ``TypeError: __init__() got an
    unexpected keyword argument`` at call time — only if that branch
    is exercised. H4 catches the typo at audit time.

    Scope: every ``.py`` under ``src/``. For each file, harvest all
    ``@dataclass``-decorated classes and their fields (from
    ``AnnAssign`` targets, including those inherited from same-file
    dataclass bases). Then walk Call nodes whose ``func`` is a Name
    matching a known dataclass and check each ``keyword.arg`` against
    that class's field set.

    Limitations (intentional false-negative bias to keep noise low):
      - Cross-module inheritance: a dataclass whose base lives in a
        different file doesn't see the inherited fields. We allow
        unknown kwargs in that case rather than false-positive.
      - ``**kwargs`` expansion is not analyzed.
      - ``InitVar[...]`` annotations are accepted as kwargs (dataclass
        forwards them to ``__post_init__``).
      - ``ClassVar[...]`` annotations are *not* fields — excluded.
    """
    errors: List[str] = []

    # Collect all (path, dataclass_name) → field_set across src/, plus
    # inheritance chain restricted to the same file.
    file_dataclasses: Dict[Path, Dict[str, Tuple[Set[str], List[str]]]] = (
        {}
    )  # path → {classname: (own_fields, base_names)}

    def _is_dataclass_decorator(deco: ast.expr) -> bool:
        # @dataclass, @dataclass(...), @dataclasses.dataclass[(...)]
        if isinstance(deco, ast.Name):
            return deco.id == "dataclass"
        if isinstance(deco, ast.Attribute):
            return deco.attr == "dataclass"
        if isinstance(deco, ast.Call):
            return _is_dataclass_decorator(deco.func)
        return False

    def _is_classvar(node: ast.expr) -> bool:
        if isinstance(node, ast.Subscript):
            v = node.value
            if isinstance(v, ast.Name) and v.id == "ClassVar":
                return True
            if isinstance(v, ast.Attribute) and v.attr == "ClassVar":
                return True
        if isinstance(node, ast.Name) and node.id == "ClassVar":
            return True
        return False

    for path in (REPO / "src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # B1 catches parse errors

        per_file: Dict[str, Tuple[Set[str], List[str]]] = {}
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            if not any(_is_dataclass_decorator(d) for d in cls.decorator_list):
                continue
            own_fields: Set[str] = set()
            for item in cls.body:
                if isinstance(item, ast.AnnAssign):
                    if not isinstance(item.target, ast.Name):
                        continue
                    if _is_classvar(item.annotation):
                        continue
                    own_fields.add(item.target.id)
            base_names: List[str] = []
            for base in cls.bases:
                if isinstance(base, ast.Name):
                    base_names.append(base.id)
            per_file[cls.name] = (own_fields, base_names)
        if per_file:
            file_dataclasses[path] = per_file

    # Resolve same-file inheritance closure.
    def _resolve_fields(
        per_file: Dict[str, Tuple[Set[str], List[str]]], cls_name: str
    ) -> Set[str]:
        seen: Set[str] = set()
        out: Set[str] = set()
        stack = [cls_name]
        while stack:
            cur = stack.pop()
            if cur in seen or cur not in per_file:
                continue
            seen.add(cur)
            own, bases = per_file[cur]
            out |= own
            stack.extend(bases)
        return out

    # Walk Call sites and verify kwargs.
    for path, per_file in file_dataclasses.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = path.relative_to(REPO)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Name):
                continue
            cls_name = func.id
            if cls_name not in per_file:
                continue
            # Skip if the class has any base whose definition we cannot
            # see in this file — inherited fields could come from any-
            # where, so we'd produce false positives.
            _own, bases = per_file[cls_name]
            external_base = any(b not in per_file for b in bases)
            if external_base:
                continue
            allowed = _resolve_fields(per_file, cls_name)
            for kw in node.keywords:
                if kw.arg is None:  # **kwargs
                    break
                if kw.arg not in allowed:
                    errors.append(
                        f"{rel}:{node.lineno} {cls_name}({kw.arg}=...): "
                        f"unknown kwarg; declared fields are "
                        f"{sorted(allowed) or '(none)'}"
                    )

    return ("H4: no dataclass call with unknown kwarg", errors)


# Round-33 baseline: 38 class names with known duplicate definitions
# under ``src/``. Each is a real consolidation backlog item — collapse
# to one canonical definition + re-export from the others' historical
# locations. The audit ratchets *new* duplicates only; this set is
# the floor and shrinks as consolidations land. To remove an entry,
# fix the underlying duplication then delete the name from this set.
# Adding a name here without a justifying fix is a code smell — H5
# exists to prevent the next round-32-style class-of-bug.
_H5_KNOWN_BACKLOG: frozenset = frozenset()
# Round-36 phase 3 emptied the backlog. Trajectory: 38 → 31 → 21 → 0.
# Resolution strategy was per-location renaming with `as` aliases at
# consumer sites — the H5 audit's purpose is to prevent the round-32
# class-identity bug ("except SecurityError" catches wrong class), so
# every dup class got a distinct name and consumers updated their
# imports. Nothing was hoisted into a shared base class because the
# implementations were genuinely divergent; renaming preserves both
# semantics without ambiguity. Pure dead-orphan files (no production
# callers) were deleted outright (CacheManager, GraphCoherenceResult,
# GraphCoherenceScorer, PerformanceMonitor, SizedLRU, gates_fast_small).
#
# To add a new dup intentionally: rename one side and document why
# here, OR add the class name back to this set with a one-line
# justification. The empty default forces the conversation.


def _check_no_dual_class_definitions() -> Result:
    """Every public class name in ``src/`` should be defined in exactly
    one place.

    Round-32 caught ``RegionRuleError`` defined in *both*
    ``src/regions/base.py`` and ``src/regions/base_enhanced.py``.
    Production was fine because each importer pulled from one module
    consistently. Tests broke this: ``test_region_a1.py`` did
    ``from src.regions.base import RegionRuleError`` but the A1
    processor raised the *base_enhanced* class. ``pytest.raises``
    against the wrong class object silently missed real raises and
    reported "DID NOT RAISE" for tests that were assertion-correct.
    Six A1 tests were broken this way for ~30 rounds before round-32
    surfaced it.

    Scope: every ``.py`` under ``src/``. Build a name → list-of-paths
    map of class definitions, flag any name with > 1 distinct file
    that **isn't in the round-33 baseline backlog** (see
    ``_H5_KNOWN_BACKLOG`` above).

    The baseline + ratchet pattern: H5 doesn't gate on the existing
    backlog (~38 names as of round 33) because consolidating each
    requires care — a wrong move can break import chains. Instead it
    gates new duplicates: add a ``class FooBar`` to a second file
    while there's already one in ``src/``, audit fails, you either
    (a) fix the duplication or (b) consciously add ``FooBar`` to the
    backlog with a comment explaining why.

    Round-33's dead-cluster cleanup brought the count from 64 → 38;
    deletion of ``src/authority_tier2_3/``, ``src/authority_live/``,
    ``src/authorities/templates/src/``, the e4 backup directories,
    and 10 flat-shadowed region ``.py`` files. The remaining 38 are
    real consolidations that need their own rounds.

    Limitations:
      - Same-name classes in nested ``class`` blocks (e.g. test
        helpers inside test methods) are flagged. Acceptable
        false-positive: keeps the rule simple; src/ doesn't do this.
      - ``if TYPE_CHECKING: class X`` would be flagged. Fix by
        consolidating to a single canonical definition.
    """
    errors: List[str] = []
    classes: Dict[str, List[Path]] = {}
    for path in (REPO / "src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # B1 catches parse errors
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.setdefault(node.name, []).append(path)
    for name, paths in sorted(classes.items()):
        # De-dup paths in case a single file had multiple class blocks
        # with the same name (which would be a different bug worth
        # reporting separately, but rare; keep this signal noise-free).
        unique = sorted({p.relative_to(REPO).as_posix() for p in paths})
        if len(unique) <= 1:
            continue
        if name in _H5_KNOWN_BACKLOG:
            continue
        errors.append(
            f"class {name} defined in {len(unique)} files: "
            f"{', '.join(unique)} — collapse to one canonical "
            f"definition + re-export (or, if intentional, add to "
            f"_H5_KNOWN_BACKLOG with a justifying comment)"
        )
    return ("H5: no new dual class definitions in src/", errors)


# ─── I. Tool idempotency ───────────────────────────────────────────────


def _check_gen_api_reference_idempotent() -> Result:
    """Running tools/gen_api_reference.py must reproduce the committed
    openapi.json + api_reference.md byte-for-byte.

    NB: this check is non-mutating. It snapshots the committed files
    before regenerating, and restores them afterward regardless of
    whether the contents matched. That's important because
    ``tools/gen_api_reference.py`` writes to a fixed path — without
    save/restore, running this audit on a workstation with a
    different FastAPI/Pydantic version would silently corrupt the
    committed schema. (Found by hitting it on first run.)
    """
    errors: List[str] = []
    out_json = REPO / "docs" / "openapi.json"
    out_md = REPO / "docs" / "api_reference.md"
    if not out_json.exists():
        errors.append("docs/openapi.json missing — run `make api-docs`")
        return ("I1: gen_api_reference idempotent", errors)
    before_json = out_json.read_text()
    before_md = out_md.read_text() if out_md.exists() else None
    try:
        proc = subprocess.run(
            [sys.executable, "tools/gen_api_reference.py"],
            cwd=str(REPO),
            env={**os.environ, "PYTHONPATH": str(REPO)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            errors.append(f"re-run failed: {proc.stderr.strip()}")
            return ("I1: gen_api_reference idempotent", errors)
        after_json = out_json.read_text()
        after_md = out_md.read_text() if out_md.exists() else None
        if before_json != after_json or before_md != after_md:
            errors.append(
                "running tools/gen_api_reference.py produced different "
                "output than the committed docs/openapi.json + "
                "docs/api_reference.md. Either: (a) the committed files "
                "are stale — run `make api-docs` and commit the result, "
                "or (b) your local FastAPI/Pydantic versions differ "
                "from requirements.txt's pin (0.115.0/2.9.2) — install "
                "the pinned versions before regenerating."
            )
    finally:
        # Always restore — gen_api_reference.py writes to a fixed
        # path, so a version-skew run would otherwise leave the
        # committed schema corrupted.
        out_json.write_text(before_json)
        if before_md is not None:
            out_md.write_text(before_md)
    return ("I1: gen_api_reference idempotent", errors)


# ─── J. Doc cross-references ───────────────────────────────────────────


def _check_screenshots_exist() -> Result:
    """Every image referenced in DEMO.md must exist."""
    errors: List[str] = []
    demo = (REPO / "DEMO.md").read_text()
    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+\.png)\)", demo):
        path = REPO / m.group(1)
        if not path.exists():
            errors.append(f"DEMO.md → {m.group(1)} (image missing)")
    return ("J1: screenshots referenced in DEMO.md exist", errors)


def _check_api_reference_endpoint_count() -> Result:
    """docs/api_reference.md's claimed endpoint count must match the
    actual schema."""
    errors: List[str] = []
    md = (REPO / "docs" / "api_reference.md").read_text()
    j = json.loads((REPO / "docs" / "openapi.json").read_text())
    actual = len(j.get("paths") or {})
    m = re.search(r"Endpoints:\s*\*\*(\d+)\*\*", md)
    if not m:
        errors.append("docs/api_reference.md: no `Endpoints: **N**` claim")
    else:
        claimed = int(m.group(1))
        if claimed != actual:
            errors.append(
                f"docs/api_reference.md claims {claimed} endpoints, "
                f"openapi.json has {actual}"
            )
    return ("J2: api reference endpoint count", errors)


# ─── Runner ────────────────────────────────────────────────────────────


CHECKS: List[Callable[[], Result]] = [
    _check_referenced_files_exist,
    _check_no_stale_dead_module_refs,
    _check_python_files_parse,
    _check_production_imports,
    _check_json_files_parse,
    _check_yaml_files_parse,
    _check_calibration_doc_matches_json,
    _check_calibration_apply_matches_knots,
    _check_benchmark_split_sums,
    _check_genealogy_count_matches_docs,
    _check_memgraph_version_match,
    _check_lockfile_in_sync,
    _check_make_targets_resolve,
    _check_ci_test_files_exist,
    _check_ci_test_files_collect,
    _check_every_collected_test_runs_in_ci,
    _check_ci_test_files_contribute_tests,
    _check_no_test_module_shadowing,
    _check_no_test_bandaid_swallows,
    _check_no_self_method_called_but_not_defined,
    _check_no_dataclass_unknown_kwarg,
    _check_no_dual_class_definitions,
    _check_gen_api_reference_idempotent,
    _check_screenshots_exist,
    _check_api_reference_endpoint_count,
]

# Checks omitted from --fast mode (pre-commit hook). Each spawns a
# subprocess and noticeably slows the hook (B2: 8 imports ≈ 1.5 s;
# I1: 1 gen_api_reference run ≈ 1 s; G2/G3: one pytest --collect-only
# each, ≈ 5-15 s apiece). CI runs the full battery — G3 is gating
# there, which is the binding enforcement; the hook stays fast.
#
# G4 is NOT here: it is a pure AST read of the workflow-named files
# (see _defines_a_test), so it costs milliseconds and runs in the hook
# too.
_SLOW_CHECKS = {
    _check_production_imports,
    _check_gen_api_reference_idempotent,
    _check_ci_test_files_collect,
    _check_every_collected_test_runs_in_ci,
}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Skip slow subprocess-spawning checks (B2 production "
            "imports, I1 gen_api_reference idempotent). Suitable for "
            "pre-commit hooks; CI still runs the full battery."
        ),
    )
    args = parser.parse_args()

    selected = [c for c in CHECKS if not (args.fast and c in _SLOW_CHECKS)]
    skipped = len(CHECKS) - len(selected)

    label = f"{len(selected)} repository invariant checks"
    if skipped:
        label += f" (--fast: skipping {skipped} slow checks)"
    print(f"Running {label}...")
    print()
    total_errors = 0
    failed_checks: List[str] = []
    for check in selected:
        name, errors = check()
        if errors:
            print(f"  ✗ {name}")
            for e in errors:
                print(f"      {e}")
            total_errors += len(errors)
            failed_checks.append(name)
        else:
            print(f"  ✓ {name}")
    print()
    if total_errors:
        print(
            f"FAIL — {total_errors} error(s) across {len(failed_checks)} "
            f"failing check(s):"
        )
        for c in failed_checks:
            print(f"  - {c}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
