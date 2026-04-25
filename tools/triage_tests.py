#!/usr/bin/env python3
"""Triage every ``tests/unit/`` Python file by collectibility.

For every test-shaped file under ``tests/unit/`` (excluding diagnostic
generator scripts), runs ``pytest --collect-only`` to learn:

- whether the module imports cleanly
- how many tests live in it
- whether it's tracked in git already
- whether it's listed in the CI core-tests step

The script then runs ``pytest <file> -q`` for every cleanly-collected
file to capture the actual pass/fail state, and writes a markdown
matrix to ``docs/test_triage.md``.

Output buckets:

- **GREEN**: collects + ≥ 1 test + zero failures.
- **GREEN-untracked**: same but file is `??` in `git status`.
- **YELLOW**: collects, 0 tests (utility / fixture / shared helper).
- **RED**: collection error or non-zero failures.

The matrix is the input to Phase 1.4 — files in GREEN buckets that
aren't already in CI's pytest invocation are the candidates to add.

Run::

    PYTHONPATH=. python3 tools/triage_tests.py

Idempotent and read-only. Writes only to ``docs/test_triage.md``.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO / "tests" / "unit"
CI_FILE = REPO / ".github" / "workflows" / "ci.yml"
OUTPUT = REPO / "docs" / "test_triage.md"

# Files we deliberately skip — diagnostics / generators, not real
# test modules. The plan calls these out explicitly.
SKIP_PATTERNS = (
    re.compile(r"_debug_"),
    re.compile(r"^generate_"),
    re.compile(r"hell_level"),
    re.compile(r"^verify_"),
    re.compile(r"^validation_"),
    re.compile(r"^debug_"),
)


@dataclass
class TestFile:
    path: Path  # absolute
    rel: str  # relative to repo root, forward-slash
    tracked: bool  # in git index
    in_ci: bool  # listed in CI core-tests step
    collected: int = 0  # number of tests collected
    collect_error: Optional[str] = None
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    xfailed: int = 0
    run_error: Optional[str] = None

    @property
    def bucket(self) -> str:
        if self.collect_error:
            return "RED"
        if self.run_error:
            return "RED"
        if self.collected == 0:
            return "YELLOW"
        if self.failed > 0:
            return "RED"
        if self.tracked:
            return "GREEN"
        return "GREEN-untracked"


# ---- helpers ---------------------------------------------------------


def _git_tracked() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "tests/unit/"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {ln for ln in out.splitlines() if ln.endswith(".py")}


def _ci_listed() -> set[str]:
    text = CI_FILE.read_text()
    return set(re.findall(r"tests/unit/[^\s\\]+\.py", text))


def _should_skip(rel: str) -> bool:
    name = Path(rel).name
    return any(p.search(name) for p in SKIP_PATTERNS)


def _discover() -> list[TestFile]:
    tracked = _git_tracked()
    in_ci = _ci_listed()
    out: list[TestFile] = []
    for p in sorted(TESTS_DIR.rglob("*.py")):
        if p.name == "__init__.py":
            continue
        rel = p.relative_to(REPO).as_posix()
        if _should_skip(rel):
            continue
        out.append(
            TestFile(
                path=p,
                rel=rel,
                tracked=rel in tracked,
                in_ci=rel in in_ci,
            )
        )
    return out


def _collect(tf: TestFile) -> None:
    """Run pytest --collect-only and parse the test count."""
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                tf.rel,
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PYTHONPATH": str(REPO)},
        )
    except subprocess.TimeoutExpired:
        tf.collect_error = "timeout > 60s"
        return

    out = (proc.stdout + proc.stderr).strip()
    # Look for collection errors / import errors
    m_err = re.search(r"^(ERROR|ImportError|ModuleNotFoundError)\b.*", out, re.M)
    if proc.returncode != 0 and m_err:
        # Compress to a single line
        line = m_err.group(0)[:120]
        tf.collect_error = line
        return
    # Parse "<N> tests collected" or "<N> tests collected in X.XXs"
    m = re.search(r"(\d+)\s+tests? collected", out)
    if m:
        tf.collected = int(m.group(1))
    else:
        # Some pytest variants emit a final line like "no tests ran"
        tf.collected = 0


def _run(tf: TestFile) -> None:
    """Run pytest <file> -q and parse pass/fail counts."""
    if tf.collected == 0 or tf.collect_error:
        return
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                tf.rel,
                "-q",
                "-p",
                "no:cacheprovider",
                "--tb=no",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PYTHONPATH": str(REPO)},
        )
    except subprocess.TimeoutExpired:
        tf.run_error = "timeout > 300s"
        return

    out = (proc.stdout + proc.stderr).strip()
    # Parse "X passed, Y failed, Z skipped, N xfailed in T.TTs"
    for kw, attr in (
        ("passed", "passed"),
        ("failed", "failed"),
        ("skipped", "skipped"),
        ("xfailed", "xfailed"),
    ):
        m = re.search(rf"(\d+)\s+{kw}", out)
        if m:
            setattr(tf, attr, int(m.group(1)))
    # Extract a minimal error summary if rc != 0 and we didn't classify
    if proc.returncode != 0 and tf.failed == 0 and tf.collect_error is None:
        # Could be runtime error during collection that pytest exits 2 on
        m = re.search(r"^(ERROR|FAILED)\b.*", out, re.M)
        if m:
            tf.run_error = m.group(0)[:120]


# ---- output ----------------------------------------------------------


def _emit(rows: list[TestFile]) -> str:
    lines: list[str] = [
        "# Test triage matrix",
        "",
        "Generated by `tools/triage_tests.py`. **Do not edit by hand.**",
        "",
        "Buckets:",
        "- **GREEN**: collects + ≥ 1 test + zero failures + tracked in git.",
        "- **GREEN-untracked**: same as GREEN but `git status` shows `??`.",
        "- **YELLOW**: collects, 0 tests (utility / fixture).",
        "- **RED**: collection error or non-zero failures.",
        "",
        "Files matching diagnostic / generator name patterns (`*_debug_*`, "
        "`generate_*`, `hell_level_*`, `verify_*`) are skipped.",
        "",
    ]

    # Summary by bucket
    buckets: dict[str, list[TestFile]] = {}
    for r in rows:
        buckets.setdefault(r.bucket, []).append(r)
    lines += [
        "## Summary",
        "",
        "| Bucket | Files | Tests |",
        "|---|---:|---:|",
    ]
    for b in ("GREEN", "GREEN-untracked", "YELLOW", "RED"):
        files = buckets.get(b, [])
        lines.append(f"| {b} | {len(files)} | " f"{sum(f.passed for f in files)} |")
    lines += [
        f"| **TOTAL** | {len(rows)} | {sum(f.passed for f in rows)} |",
        "",
    ]

    lines += [
        "## CI inclusion delta",
        "",
        "Files currently in CI's core-tests step are marked **CI**. "
        "Phase 1.4 adds every GREEN / GREEN-untracked file that isn't "
        "already there.",
        "",
        "| File | Bucket | CI? | Tracked | Tests | Notes |",
        "|---|---|---|---|---:|---|",
    ]
    for r in sorted(rows, key=lambda r: (r.bucket, r.rel)):
        ci = "✅" if r.in_ci else "—"
        tr = "✅" if r.tracked else "—"
        notes = (
            r.collect_error
            or r.run_error
            or (f"{r.failed} failing" if r.failed else "")
        )
        lines.append(
            f"| `{r.rel}` | {r.bucket} | {ci} | {tr} | " f"{r.passed} | {notes} |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the run-pytest step, only collect.",
    )
    args = parser.parse_args()

    files = _discover()
    print(f"discovered {len(files)} candidate test files", file=sys.stderr)

    for i, tf in enumerate(files, 1):
        print(f"[{i:>3}/{len(files)}] collect: {tf.rel}", file=sys.stderr)
        _collect(tf)
        if not args.dry_run and tf.collected > 0 and not tf.collect_error:
            print(
                f"           run: {tf.rel} ({tf.collected} tests)",
                file=sys.stderr,
            )
            _run(tf)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(_emit(files), encoding="utf-8")
    print(f"\nwrote {OUTPUT.relative_to(REPO)}", file=sys.stderr)

    # Print machine-readable summary so callers can chain
    by_bucket: dict[str, int] = {}
    for f in files:
        by_bucket[f.bucket] = by_bucket.get(f.bucket, 0) + 1
    for b, n in sorted(by_bucket.items()):
        print(f"{b}: {n}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
