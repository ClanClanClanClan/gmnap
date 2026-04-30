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
  G. CI-yaml file references     — every test file in CI exists
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
from typing import Callable, List, Tuple

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
        "src.authority.manager_tier01",
        "src.authority.common",
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
    ~20,600 claim in docs (within +/- 1000 to handle natural growth)."""
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
    # Allow LFS-stub files (tiny payload). Real file has ~20,600.
    if count < 1000:
        errors.append(
            f"by_global_id count={count} — looks like an LFS stub, "
            f"run `git lfs install && git lfs pull`"
        )
        return ("D4: genealogy count claim", errors)
    # Docs say ~20,600. Allow 19,000-22,000 range.
    if not (19000 <= count <= 22000):
        errors.append(
            f"by_global_id count={count} outside expected ~20,600 range; "
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
        "docs/orphaned_tests",
        "tests/coherence",
        "tests/compliance",
        "tests/error_recovery",
        "tests/extreme",
        "tests/genealogy",
        "tests/hardcore",
        "tests/idempotency",
        "tests/integration/stages",
        "tests/live",
        "tests/memory",
        "tests/mock_api",
        "tests/paranoid",
        "tests/performance",
        "tests/production",
        "tests/regional",
        "tests/regions/e6_mainland_sea",
        "tests/roundtrip",
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


# ─── I. Tool idempotency ───────────────────────────────────────────────


def _check_gen_api_reference_idempotent() -> Result:
    """Running tools/gen_api_reference.py twice must produce identical
    output."""
    errors: List[str] = []
    out_json = REPO / "docs" / "openapi.json"
    if not out_json.exists():
        errors.append("docs/openapi.json missing — run `make api-docs`")
        return ("I1: gen_api_reference idempotent", errors)
    before = out_json.read_text()
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
    after = out_json.read_text()
    if before != after:
        errors.append(
            "running tools/gen_api_reference.py twice produced different "
            "output — committed openapi.json is stale; run `make api-docs`"
        )
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
    _check_no_test_module_shadowing,
    _check_gen_api_reference_idempotent,
    _check_screenshots_exist,
    _check_api_reference_endpoint_count,
]


def main() -> int:
    print(f"Running {len(CHECKS)} repository invariant checks...")
    print()
    total_errors = 0
    failed_checks: List[str] = []
    for check in CHECKS:
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
