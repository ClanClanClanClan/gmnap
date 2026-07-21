#!/usr/bin/env python3
"""Rebuild the fastText name-origin classifier from committed training data.

R54: the model the pipeline loads first —
``data/ml_training/ft_name_classifier.ftz`` — is gitignored (50 MB), so a
fresh clone silently ran region detection in rules-only mode. This script
regenerates it from the COMMITTED corpus, so the model is reproducible from
data in the repo — not a mystery binary.

R59.5: the corpus is now ``data/ml_training/ft_name_training_clean.txt``
(13 429 lines), derived drop-only from the retired geo-labeled original by
``scripts/ml/clean_ft_corpus.py`` — R59 forensics proved the original's
labels were OpenAlex *affiliation countries*, not name etymologies (63.7 %
of unique A1 surnames trace to Anglosphere affiliations; the old model
memorized the contamination, e.g. cetin → A1@1.000). See
``docs/calibration.md`` (R59) for the audit numbers and gate results.

    python3 scripts/ml/build_name_classifier.py      # or: make model

DETERMINISM (R59.5): with ``thread=1`` the build is byte-deterministic —
two consecutive builds (including ``quantize(retrain=True)``) produce
md5-identical ``.ftz`` artifacts on the pinned fasttext wheel. The earlier
"not bit-deterministic" caveat applied to the old ``thread=4`` setting.
Verify a rebuild with the smoke probes below and, before citing detection
KPIs, the 843-entry benchmark (CLAUDE.md fidelity rule).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "data" / "ml_training" / "ft_name_training_clean.txt"
OUT_DIR = REPO / "data" / "ml_training"
FTZ = OUT_DIR / "ft_name_classifier.ftz"
BIN = OUT_DIR / "ft_name_classifier.bin"

# Reference hyperparameters (scripts/ml/train_custom_models.py), except
# thread=1 — required for byte-determinism (R59.5), verified md5-identical
# across consecutive builds.
PARAMS = dict(epoch=50, lr=0.5, wordNgrams=2, minn=2, maxn=5, dim=100, thread=1)

# Informational probes: [??] flags a drifted build without failing it.
SMOKE_EXPECT = [
    ("smith", "A1"),
    ("taylor", "A1"),  # the R2 family-aware rule keeps taylor (flat majority drops it)
    ("zhang", "E1"),
    ("schur", "A2"),
    ("touzi", "C5"),
    ("cvitanic", "B2"),
]

# Hard gates: the de-contamination's whole point. A build where these
# surnames score A1 at >= 0.5 is REJECTED (exit 1). The predicate is the
# R59 design-review judge's (A1 probability < 0.5), NOT top-1: measured
# on this corpus scale, cetin's top-1 sits knife-edge near-uniform
# (B1@0.42 vs A1@0.31 across a 2-line corpus perturbation), so a top-1
# gate would be noise. The absolute emission guarantee lives in the
# runtime anchor gate (tests/unit/test_ft_adversarial_pins.py).
MUST_NOT_BE_A1_CONFIDENT = ["hazra", "cetin"]


def main() -> int:
    try:
        import fasttext
    except ImportError:
        print(
            "ERROR: the `fasttext` Python package is required.\n"
            "  pip install fasttext   (or: make install-fasttext)",
            file=sys.stderr,
        )
        return 2

    if not CORPUS.exists():
        print(
            f"ERROR: training corpus not found at {CORPUS}\n"
            "  It is committed to the repo; regenerate with\n"
            "  PYTHONPATH=. python3 scripts/ml/clean_ft_corpus.py",
            file=sys.stderr,
        )
        return 2

    n_lines = sum(1 for _ in CORPUS.open(encoding="utf-8"))
    print(f"Training on {n_lines:,} lines from {CORPUS.relative_to(REPO)}")
    print(f"  params: {PARAMS}")

    model = fasttext.train_supervised(input=str(CORPUS), **PARAMS)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(BIN))
    print(f"  wrote {BIN.relative_to(REPO)} ({BIN.stat().st_size / 1e6:.0f} MB)")

    # Quantize for the compact model the pipeline loads first.
    model.quantize(input=str(CORPUS), retrain=True)
    model.save_model(str(FTZ))
    print(f"  wrote {FTZ.relative_to(REPO)} ({FTZ.stat().st_size / 1e6:.0f} MB)")

    # NumPy-2-safe low-level predict (R58: the high-level API raises under
    # NumPy >= 2 on this wheel).
    def top1(text: str) -> tuple[str, float]:
        pairs = model.f.predict(text, 1, 0.0, "strict")
        if not pairs:
            return "", 0.0
        p, lab = pairs[0]
        return str(lab).replace("__label__", ""), float(p)

    def a1_prob(text: str) -> float:
        pairs = model.f.predict(text, 40, 0.0, "strict")
        for p, lab in pairs:
            if str(lab).replace("__label__", "") == "A1":
                return float(p)
        return 0.0

    ok = True
    for name, expect in SMOKE_EXPECT:
        got, p = top1(name)
        flag = "ok" if got == expect else "??"
        print(f"  [{flag}] {name!r} -> {got} ({p:.2f}); expected {expect}")
    for name in MUST_NOT_BE_A1_CONFIDENT:
        pa1 = a1_prob(name)
        if pa1 >= 0.5:
            ok = False
            print(f"  [FAIL] {name!r} -> A1@{pa1:.2f} — contamination gate (>= 0.5)")
        else:
            print(f"  [ok] {name!r} A1@{pa1:.2f}; gate: A1 < 0.5")

    if not ok:
        print(
            "\nBUILD REJECTED: the de-contamination gate failed — the model "
            "still maps known non-Anglo surnames to A1. Do not deploy.",
            file=sys.stderr,
        )
        return 1

    print(
        "\nDone. Region detection will now use the ML tiebreaker. If your "
        "rebuild's accuracy matters, validate it against the 843-entry "
        "benchmark before citing the documented KPIs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
