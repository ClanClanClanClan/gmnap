#!/usr/bin/env python3
"""Rebuild the fastText name-origin classifier from committed training data.

R54: the model the pipeline loads first —
``data/ml_training/ft_name_classifier.ftz`` — is gitignored (50 MB), so a
fresh clone silently ran region detection in rules-only mode. This script
regenerates it from the COMMITTED corpus
``data/ml_training/ft_name_training.txt`` (23 470 ``__label__<region> <name>``
lines), so the model is reproducible from data in the repo — not a mystery
binary.

    python3 scripts/ml/build_name_classifier.py      # or: make model

Hyperparameters mirror the reference build (scripts/ml/train_custom_models.py):
character n-grams minn=2/maxn=5 (names classify on sub-word shape), then
``quantize(retrain=True)`` for the compact ``.ftz``.

NOTE ON FIDELITY: fastText training is not bit-deterministic (threaded, random
init), so a rebuild is *comparable to* — not byte-identical to — the reference
artifact, and its accuracy may differ by a point or two from the documented
detection KPIs. Validate a rebuild before trusting the exact KPI numbers:
``python3 scripts/ml/validate_on_name_origin.py`` (if present) or the 843-entry
benchmark. To get the EXACT validated model instead, ``git lfs pull`` (when the
maintainer has LFS-committed it).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "data" / "ml_training" / "ft_name_training.txt"
OUT_DIR = REPO / "data" / "ml_training"
FTZ = OUT_DIR / "ft_name_classifier.ftz"
BIN = OUT_DIR / "ft_name_classifier.bin"

# Reference hyperparameters (scripts/ml/train_custom_models.py).
PARAMS = dict(epoch=50, lr=0.5, wordNgrams=2, minn=2, maxn=5, dim=100, thread=4)


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
            "  It is committed to the repo; did `git lfs pull` / a full "
            "checkout run?",
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

    # Quick smoke prediction so a bad build is obvious.
    for name, expect in [("schur", "A2"), ("zhang", "E1"), ("smith", "A1")]:
        labels, probs = model.predict(name, k=1)
        got = labels[0].replace("__label__", "")
        flag = "ok" if got == expect else "??"
        print(f"  [{flag}] {name!r} -> {got} ({probs[0]:.2f}); expected {expect}")

    print(
        "\nDone. Region detection will now use the ML tiebreaker. If your "
        "rebuild's accuracy matters, validate it against the 843-entry "
        "benchmark before citing the documented KPIs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
