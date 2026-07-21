#!/usr/bin/env python3
"""De-bias the fastText training corpus (R59.5) — drop-only, never relabel.

The R59 forensics round PROVED the original corpus'
(``ft_name_training.geo-labeled.txt.retired``) labels are OpenAlex
*affiliation countries*, not name etymologies: 63.7 % of unique A1-class
surnames trace to an OpenAlex entry whose affiliation country is in
{US, GB, CA, AU, NZ, IE}; a seed-42 sample of 60 unique A1 surnames found
37 (62 %) clearly non-Anglo etymologies (kürkçüoğlu, aghamohammadi, giang,
nosrati, heilbronn, schmitz…); and the model trained on it memorized the
contamination (cetin → A1@1.000). Geo labeling concentrates the world's
diaspora into A1, and char-n-gram subwords then map arbitrary
"foreign-looking" unseen surnames to A1 at ~1.0 — the structural bias that
forced R58's same-group gate.

This script derives a cleaned corpus with DROP-ONLY rules. No model
predictions and no rule-tier *outputs* are used as labels (that would be
circular — the R59 design review explicitly rejected a relabeling step);
curated lexica only ever remove suspect lines:

  R1 junk        drop surname == 'anonymous', len < 2, any digit.
  R2 conflict    family-aware 0.75 rule: for each surname carrying >1
                 label, settle the GROUP FAMILY (leaf[0]) first — if the
                 top family's share is < 0.75 the surname is dropped
                 entirely (cross-family ambiguity is what the same-group
                 gate cannot survive); otherwise keep only the plurality
                 LEAF within the winning family. A flat per-leaf majority
                 was measured to be a trap (it deletes 'taylor', whose A1
                 lines split across leaf variants).
  R3 a1-veto     drop remaining A1 lines whose surname (a) is claimed by a
                 non-A1 config/regions/<code>.yaml surname_exact entry,
                 (b) carries a curated signature/medium suffix targeting a
                 non-A1 leaf (SIGNATURE_SUFFIXES + MEDIUM_SUFFIXES_TO_LEAF
                 imported LIVE from src.regions.detection.scorer — the
                 post-R59.3/R59.4 tables — with the runtime's
                 len > len(suffix)+1 guard), or (c) has A1 attestation
                 < 2 after R2 (the measured contamination lives almost
                 entirely in the singleton-A1 surnames).
  R3b forensics  drop A1 lines whose surname is on the R59 forensics list —
                 the seed-42 audit's 37 bearer-verified non-Anglo A1
                 surnames (+ cetina, the traced source of the cetin→A1
                 smoking gun). Matching is diacritic-fold-insensitive
                 because the corpus carries mojibake variants
                 (kürkçüog̃lu with combining tilde). Named negative
                 evidence, still drop-only: e.g. 'brauer' (Richard
                 Brauer, German etymology) survived R2 because its A1
                 lines have no cross-FAMILY competition (A1 vs A2 is
                 intra-family) and survived R3c at 2 attestations.
  R4 dedup cap   at most 3 identical (label, surname) lines — kills
                 census-frequency dominance (liu ×217, smith ×33).

The cleaned output is COMMITTED (reproducibility contract): the canonical
corpus is ``data/ml_training/ft_name_training_clean.txt`` as produced at
the commit that introduced it. Re-running against later rule tables may
drop more lines; that is a new curation decision, not a rebuild.

    PYTHONPATH=. python3 scripts/ml/clean_ft_corpus.py          # defaults
    PYTHONPATH=. python3 scripts/ml/clean_ft_corpus.py --cap 3 --a1-min 2
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.regions.detection.scorer import (  # noqa: E402
    MEDIUM_SUFFIXES_TO_LEAF,
    SIGNATURE_SUFFIXES,
)

DEFAULT_SRC = REPO / "data" / "ml_training" / "ft_name_training.geo-labeled.txt.retired"
DEFAULT_OUT = REPO / "data" / "ml_training" / "ft_name_training_clean.txt"

# R3b — the R59 forensics audit's bearer-verified non-Anglo A1 surnames
# (seed-42 sample of 60 unique A1-class surnames; 37 clearly non-Anglo,
# each with a named bearer/etymology in docs/calibration.md R59), plus
# 'cetina' (Marko Cetina, US/Duke — the traced training source of the old
# model's cetin→A1@1.000). A1 lines carrying these surnames are dropped.
FORENSICS_NON_ANGLO_A1 = {
    "chandra", "giang", "soh", "kurkcuoglu", "esin", "nosrati",
    "khoshnoud", "aghamohammadi", "younes", "sajjad", "shmoys",
    "morgenstern", "heilbronn", "asban", "giarmatzi", "buehler",
    "arens", "gerrits", "eisenhart", "kiess", "eberlein", "schmitz",
    "brauer", "vissers", "tempelaar", "otterbach", "tentrup",
    "colliander", "porto", "ferrus", "braccia", "spallitta", "arnault",
    "cognee", "ortega-taberner", "aspuru-guzik", "nori", "cetina",
}


def _fold(s: str) -> str:
    """Diacritic-fold for drop-list matching (corpus carries mojibake
    variants like kürkçüog̃lu with a combining tilde)."""
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def _load_non_a1_yaml_claims() -> set[str]:
    """Surnames claimed by any non-A1 surname_exact YAML supplement."""
    try:
        import yaml
    except ImportError:  # pragma: no cover - PyYAML is a hard project dep
        print("ERROR: PyYAML required", file=sys.stderr)
        raise
    claims: set[str] = set()
    for f in sorted(glob.glob(str(REPO / "config" / "regions" / "*.yaml"))):
        code = Path(f).stem.upper()
        if code == "A1":
            continue
        with open(f, encoding="utf-8") as fh:
            d = yaml.safe_load(fh) or {}
        se = d.get("surname_exact") or []
        keys = se.keys() if isinstance(se, dict) else se
        claims.update(
            unicodedata.normalize("NFC", str(k)).lower().strip() for k in keys
        )
    return claims


def _suffix_veto_table() -> dict[str, str]:
    """suffix -> curated target leaf ('' = signature, target implied non-A1).

    SIGNATURE_SUFFIXES is a flat set (every member's curated target is a
    non-A1 leaf — A1 has no signature suffixes); MEDIUM_SUFFIXES_TO_LEAF
    maps suffix -> leaf directly.
    """
    table = {suf: "" for suf in SIGNATURE_SUFFIXES}
    for suf, leaf in MEDIUM_SUFFIXES_TO_LEAF.items():
        if leaf != "A1":
            table.setdefault(suf, leaf)
    return table


def clean(
    src: Path, out: Path, cap: int, a1_min: int
) -> dict[str, object]:
    lines: list[tuple[str, str]] = []
    for line in src.open(encoding="utf-8"):
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        lab = parts[0].replace("__label__", "")
        name = parts[1].strip().lower()
        lines.append((lab, name))
    n0 = len(lines)

    # R1 — junk
    lines = [
        (l, s)
        for l, s in lines
        if s != "anonymous" and len(s) >= 2 and not any(c.isdigit() for c in s)
    ]
    n1 = len(lines)

    # R2 — family-aware conflict resolution (0.75 family share)
    by_sur: dict[str, Counter] = defaultdict(Counter)
    for l, s in lines:
        by_sur[s][l] += 1
    keep_label: dict[str, str | None] = {}
    for s, c in by_sur.items():
        if len(c) == 1:
            keep_label[s] = next(iter(c))
            continue
        fam = Counter()
        for l, k in c.items():
            fam[l[0]] += k
        ftop, fn = fam.most_common(1)[0]
        if fn / sum(fam.values()) < 0.75:
            keep_label[s] = None  # genuinely cross-family ambiguous
        else:
            infam = Counter({l: k for l, k in c.items() if l[0] == ftop})
            keep_label[s] = infam.most_common(1)[0][0]
    lines2 = [(l, s) for l, s in lines if keep_label[s] == l]
    n2 = len(lines2)

    # R3 — A1 de-contamination (drop-only)
    veto_exact = _load_non_a1_yaml_claims()
    suffix_table = _suffix_veto_table()

    def suffix_veto(s: str) -> bool:
        return any(
            s.endswith(suf) and len(s) > len(suf) + 1 for suf in suffix_table
        )

    a1_count = Counter(s for l, s in lines2 if l == "A1")
    lines3: list[tuple[str, str]] = []
    dropped_a1: list[str] = []
    for l, s in lines2:
        if l == "A1" and (
            s in veto_exact
            or suffix_veto(s)
            or a1_count[s] < a1_min
            or _fold(s) in FORENSICS_NON_ANGLO_A1  # R3b
        ):
            dropped_a1.append(s)
            continue
        lines3.append((l, s))
    n3 = len(lines3)

    # R4 — frequency cap
    seen: Counter = Counter()
    out_lines: list[tuple[str, str]] = []
    for l, s in lines3:
        seen[(l, s)] += 1
        if seen[(l, s)] <= cap:
            out_lines.append((l, s))
    n4 = len(out_lines)

    out.write_text(
        "".join(f"__label__{l} {s}\n" for l, s in out_lines), encoding="utf-8"
    )

    dist = Counter(l for l, _ in out_lines)
    return {
        "counts": (n0, n1, n2, n3, n4),
        "dropped_a1_sample": sorted(set(dropped_a1))[:12],
        "dist": dist,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--cap", type=int, default=3)
    ap.add_argument("--a1-min", type=int, default=2)
    args = ap.parse_args()

    src = args.input
    if not src.exists():
        # First run predates the retire-rename; fall back to the old name.
        legacy = REPO / "data" / "ml_training" / "ft_name_training.txt"
        if legacy.exists():
            src = legacy
        else:
            print(f"ERROR: corpus not found at {src} (nor {legacy})", file=sys.stderr)
            return 2

    stats = clean(src, args.output, args.cap, args.a1_min)
    n0, n1, n2, n3, n4 = stats["counts"]
    print(f"input:        {src.relative_to(REPO) if src.is_relative_to(REPO) else src}")
    print(f"R1 junk:      {n0} -> {n1}  (-{n0 - n1})")
    print(f"R2 conflict:  {n1} -> {n2}  (-{n1 - n2})")
    print(f"R3 a1-veto:   {n2} -> {n3}  (-{n2 - n3})  e.g. {stats['dropped_a1_sample']}")
    print(f"R4 cap:       {n3} -> {n4}  (-{n3 - n4})")
    dist = stats["dist"]
    tot = sum(dist.values())
    for l, c in dist.most_common(10):
        print(f"  {l}: {c} ({c / tot:.1%})")
    rel = args.output.relative_to(REPO) if args.output.is_relative_to(REPO) else args.output
    print(f"wrote {rel} ({tot} lines)")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("OFFLINE", "1")
    raise SystemExit(main())
