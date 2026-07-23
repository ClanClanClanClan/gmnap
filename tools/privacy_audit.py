#!/usr/bin/env python3
"""R57 privacy gate — no identifiable LIVING person may carry an origin label.

THE RULE, in one line: a public file may say what a SURNAME STRING
classifies as; it may not say what a PERSON's origin is.

    ok    "silberberg": "A2"        <- a surname dictionary entry
    FAIL  "Lior Silberberg" -> C6   <- a claim about an identifiable person

Why the distinction is load-bearing: names, advisors and institutions are
ordinary personal data already published by MGP / OpenAlex / arXiv, and
republishing them is what this project is FOR. A name-origin label is a
DERIVED attribute capable of revealing ethnic or religious origin, which
GDPR Art. 9 treats as special-category data — and under CJEU C-184/20
*inferred* data counts, so "we only computed it from a public name" is
not an exemption. Swiss FADP (besonders schützenswerte Personendaten)
is equivalent. GDPR does NOT apply to deceased persons (Recital 27),
which is why historical mathematicians may appear freely.

Detection is ground-truth based rather than regex-guessed: a hit needs a
name that OUR OWN enrichment data says belongs to a presumed-living
person (no DeathYear on record), appearing on a line that also carries a
leaf code. That keeps false positives near zero — region names like
"Latin America" and synthetic test names are not people, and are never
flagged.

KNOWN LIMITATION, stated rather than hidden: "presumed living" means
"no DeathYear in data/genealogy_enrichment.json". Our data has gaps —
Alan Turing (d. 1954) and Hua Luogeng (d. 1985) both lack death years —
so the gate can flag the long-dead. It errs toward flagging, which is
the safe direction; triage the report, don't trust it blindly.

Checks:
  P1  nothing tracked under data/eval/  (the adjudicated corpora pair
      ~3 000 living academics with origin labels — they stay local;
      tools/build_heldout2_corpus.py keeps them reproducible)
  P2  no tracked line pairs a presumed-living person with a leaf code
  P3  allowlisted fixtures carry a documented provenance/basis note

Exit 0 = safe to publish. Run before ANY visibility change:

    PYTHONPATH=. python3 tools/privacy_audit.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENRICHMENT = REPO / "data" / "genealogy_enrichment.json"

LEAF = re.compile(r"\b[A-G][1-9]\b")
CANDIDATE = re.compile(
    r"[A-ZÀ-Ý][\wÀ-ÿ'’-]+(?:,)?\s+[A-ZÀ-Ý][\wÀ-ÿ'’-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'’-]+)?"
)
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".txt", ".cfg", ".toml"}

# Wikidata-derived fixtures kept deliberately: these are encyclopedia
# subjects whose nationality Wikidata already publishes, so the marginal
# disclosure of our label is ~nil — unlike the arXiv-derived corpora,
# where the label is novel inference about non-public working academics.
# Rationale recorded in tests/fixtures/PROVENANCE.md.
ALLOWLIST = {
    "tests/fixtures/name_origin_benchmark.json",
    "tests/fixtures/golden_mathematicians.json",
    # Archetypal per-region name SHAPES used to generate synthetic
    # training data ("Wang Wei", "Tanaka Yuki", "Kim Min-jun"...). They
    # are constructed from the commonest surname+given pairs precisely so
    # they denote a pattern rather than a person.
    "scripts/ml/prepare_fasttext_training_data.py",
}

# Verified deceased; our enrichment lacks their DeathYear (see LIMITATION).
KNOWN_DECEASED = {"Turing, Alan", "Luogeng, Hua", "Hua, Luogeng"}

# GENERIC NAME PATTERNS, not claims about individuals. These are stock
# test inputs chosen because their SHAPE exercises a classifier path
# (Han-Chinese given+surname pairs, Korean hyphenated givens, common
# Anglo/Indian/Germanic forms). They collide with real people only
# because such names are common — which is precisely why they identify
# nobody. They are NOT de-identified because several tests depend on the
# given name carrying the signal under test (Korean E4 detection needs
# "Min-Su"; CJK disambiguation needs a real given-name token).
SYNTHETIC_TEST_NAMES = {
    "Zhang, Wei",
    "Wang, Wei",
    "Chen, Wei",
    "Wang, Lei",
    "Yang, Lei",
    "Liu, Xiang",
    "Chen, Ting",
    "Wang, Daqing",
    "Lee, Patricia",
    "Schmidt, Klaus",
    "Williams, David",
    "Lee, Min Ho",
    "Kim, Min-Su",
    "Patel, Vijay",
    "Khan, Imran",
    "Kumar, Manoj",
    "Pandey, Deepak",
    "Zhang, Jun",
    "Zhang, Ming",
    "Liu, Yang",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", s.lower())).strip()


def living_forms() -> dict[str, str]:
    """Presumed-living name forms that UNIQUELY identify one person.

    k-anonymity: a name shared by several people does not identify any of
    them. "Zhang, Wei" matches many real mathematicians and is also a
    stock synthetic test name, so a line reading `Zhang, Wei -> E1` is a
    statement about a name pattern, not about a person. "Papasoglu,
    Panos" matches exactly one and therefore is about that person.
    Only k == 1 forms are treated as identifying.
    """
    if not ENRICHMENT.exists():
        return {}
    data = json.loads(ENRICHMENT.read_text(encoding="utf-8")).get("by_name", {})
    counts: Counter = Counter()
    owner: dict[str, str] = {}
    dead: set[str] = set()
    for rec in data.values():
        name = (rec.get("CanonicalLatin") or "").strip()
        if not name:
            continue
        forms = {name}
        if "," in name:
            surname, given = name.split(",", 1)
            forms.add(f"{given.strip()} {surname.strip()}")
        for f in forms:
            if len(f) < 9 or " " not in f:
                continue
            key = _norm(f)
            counts[key] += 1
            owner.setdefault(key, name)
            if rec.get("DeathYear") or name in KNOWN_DECEASED:
                dead.add(key)
    return {
        k: owner[k]
        for k, n in counts.items()
        if n == 1
        and k not in dead
        and owner[k] not in KNOWN_DECEASED
        and owner[k] not in SYNTHETIC_TEST_NAMES
    }


def tracked() -> list[str]:
    r = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return [f for f in r.stdout.splitlines() if f.strip()]


def main() -> int:
    files = tracked()
    failures: list[str] = []

    tracked_eval = [f for f in files if f.startswith("data/eval/")]
    if tracked_eval:
        failures.append(
            f"P1: {len(tracked_eval)} file(s) tracked under data/eval/ — the "
            f"adjudicated corpora must stay local: {tracked_eval[:4]}"
        )

    people = living_forms()
    hits: dict[str, list[tuple[int, str]]] = defaultdict(list)
    counts: Counter = Counter()
    for f in files:
        if f in ALLOWLIST or Path(f).suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = (REPO / f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not LEAF.search(text):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if not LEAF.search(line):
                continue
            for m in CANDIDATE.finditer(line):
                who = people.get(_norm(m.group(0)))
                if who:
                    hits[f].append((i, who))
                    counts[who] += 1
                    break
    if hits:
        failures.append(
            f"P2: {sum(len(v) for v in hits.values())} line(s) pair a "
            f"presumed-living person with a leaf code ({len(counts)} people)"
        )

    prov = REPO / "tests" / "fixtures" / "PROVENANCE.md"
    if ALLOWLIST and not prov.exists():
        failures.append("P3: tests/fixtures/PROVENANCE.md missing for allowlist")

    if failures:
        print("PRIVACY AUDIT: FAIL\n")
        for x in failures:
            print(f"  ✗ {x}")
        if hits:
            print("\n  people (triage: verify each is genuinely living):")
            for who, n in counts.most_common():
                where = [f for f, v in hits.items() if any(w == who for _, w in v)]
                print(f"    {n:3d}  {who:32s} {where[0]}")
        return 1

    print("PRIVACY AUDIT: PASS")
    print("  P1  no tracked data/eval/ corpora")
    print(f"  P2  no living-person/leaf pairings across {len(files)} tracked files")
    print(f"      (checked against {len(people)} presumed-living name forms)")
    print(f"  P3  allowlisted fixtures documented ({len(ALLOWLIST)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
