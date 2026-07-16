"""R58: orthographic GROUP anchors for the same-group fastText gate.

A pure function over the name string: distinctive Latin-script diacritics
and patterns in the SURNAME token yield a group anchor (never a leaf), so
the existing same-group gate can let the fastText model refine to a leaf it
could not otherwise emit (fastText never emits without an anchor — see
docs/calibration.md R58).

Design provenance: the R58 adjudicated design round, with the adversarial
judge's four modifications applied:
  (a) đ is Tier-2 (not Tier-1) and ANY Vietnamese-specific codepoint in the
      full name suppresses Slavic anchoring ('Đinh, Tiến Cường' is E5, not
      B2 — VIETNAMESE is a real group).
  (b) token-initial Ç is Tier-2 (Albanian Çela must not get a veto-immune
      TURKIC anchor); ğ/ı/öz stay Tier-1 (no non-Turkic Latin orthography
      uses them).
  (c) Benaïm guard: Tier-2 GERMANIC_WESTERN marks license a LEAF only when
      the surname also matches the French/Italian/Catalan suffix whitelist;
      otherwise the anchor allows at most the model's same-group agreement
      to stand as a GROUP-level claim (kind='group_cap'). ft's documented
      A2-overprediction on Maghrebi/African names CORRELATES with these
      marks, so anchor+ft agreement is not independent evidence.
  (d) Tier-1 anchors override weak scorer hints; a Tier-2 anchor that
      conflicts with a weak hint yields no anchor at all.

Tables are frozen literals; the function is deterministic, OFFLINE, and
stdlib-only.
"""

from __future__ import annotations

import re
from typing import NamedTuple, Optional


class OrthoAnchor(NamedTuple):
    kind: str  # "group" | "permitted" | "group_cap"
    payload: object  # group name (str) or frozenset of group names
    tier: int  # 1 = signature (veto-immune), 2 = contextual (ft can veto)
    marks: str  # the evidence, for metadata/debugging


# --- Tier-1 signature marks: exclusive to one group's orthographies ------
_T1_SLAVIC = set("łąęśźżćřěůĺľŕ")
_T1_NORDIC = set("åøæþð")
_T1_GERMANIC = set("ß")
_T1_TURKIC = set("ğı")  # dotless ı U+0131; ğ U+011F — no other Latin use
_T1_BALTIC = set("ėųį")  # Lithuanian-unique; macrons deliberately EXCLUDED

# --- Tier-2 contextual marks ---------------------------------------------
_T2_FRENCHISH = set("èïœùàì")  # French/Italian/Dutch/Catalan — but also
#                                Maghrebi-French transliteration (Aïd)
_T2_SLAVIC_OR_BALTIC = set("ščžďťň")
_VIETNAMESE_MARKS = set("ơưạảấầẩẫậắằẳẵặẹẻẽếềểễệịỉĩọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ")
_HUNGARIAN_PAT = re.compile(r"(zs|gy|cs|sz|cz|ő|ű)")
_GERMANIC_SURNAME_PAT = re.compile(
    r"(sch|ck|tz|dt|mann$|berg$|burg$|wald$|feld$|stein$|bach$|hoff?$|dorf$|thal$|brück)"
)
_FRENCH_ITALIAN_SUFFIXES = (
    "eau",
    "eaux",
    "eux",
    "ier",
    "ière",
    "iere",
    "eur",
    "euse",
    "et",
    "ot",
    "ac",
    "ais",
    "ois",
    "ien",
    "on",
    "ont",
    "ard",
    "ault",
    "ette",
    "ià",  # Catalan (judge mod (c): Vitrià)
)
_SPANISH_SUFFIXES = ("ez", "es", "és")

# Group names must match LEAF_TO_GROUP values in manager_optimized.
G_SLAVIC = "SLAVIC_CENTRAL"
G_NORDIC = "NORDIC_BALTIC"
G_GERMANIC = "GERMANIC_WESTERN"
G_TURKIC = "TURKIC"
G_BALTIC = "BALTIC"


def _surname_tokens(canonical_latin: str) -> list:
    """Surname sub-tokens: text before the first comma if present, else the
    last whitespace token; hyphen-split, lowercased."""
    name = (canonical_latin or "").strip()
    if not name:
        return []
    if "," in name:
        surname = name.split(",", 1)[0].strip()
    else:
        parts = name.split()
        if len(parts) < 2:
            return []
        surname = parts[-1]
    return [t for t in surname.lower().split("-") if t]


def _french_suffix_ok(token: str) -> bool:
    if token.endswith(_SPANISH_SUFFIXES):
        return False
    if _HUNGARIAN_PAT.search(token):
        return False
    return token.endswith(_FRENCH_ITALIAN_SUFFIXES)


def detect_ortho_group_anchor(canonical_latin: str) -> Optional[OrthoAnchor]:
    """Distinctive orthography in the surname -> group anchor, or None."""
    tokens = _surname_tokens(canonical_latin)
    if not tokens:
        return None
    full_lower = (canonical_latin or "").lower()
    # Judge mod (a): any Vietnamese-specific codepoint anywhere in the name
    # suppresses Slavic anchoring entirely (đ and the horn/hook vowels).
    vietnamese_context = any(ch in _VIETNAMESE_MARKS for ch in full_lower)

    anchors = []  # (kind, payload, tier, marks)
    for tok in tokens:
        chars = set(tok)

        # ---- Tier 1 ----
        if chars & _T1_SLAVIC and not vietnamese_context:
            anchors.append(("group", G_SLAVIC, 1, "".join(sorted(chars & _T1_SLAVIC))))
        if chars & _T1_NORDIC:
            anchors.append(("group", G_NORDIC, 1, "".join(sorted(chars & _T1_NORDIC))))
        if chars & _T1_GERMANIC:
            anchors.append(("group", G_GERMANIC, 1, "ß"))
        t1_turkic = chars & _T1_TURKIC
        if tok.startswith("öz"):
            t1_turkic = t1_turkic | {"öz"}
        if t1_turkic:
            anchors.append(("group", G_TURKIC, 1, "".join(sorted(t1_turkic))))
        if chars & _T1_BALTIC:
            anchors.append(("group", G_BALTIC, 1, "".join(sorted(chars & _T1_BALTIC))))

        # ---- Tier 2 ----
        # Umlaut/ş combination rules first (more specific).
        if (chars & set("öü")) and (chars & set("çşğı") or "ş" in chars):
            anchors.append(("group", G_TURKIC, 2, "umlaut+turkic-mark"))
        elif "ş" in chars and chars & set("çğıöü"):
            anchors.append(("group", G_TURKIC, 2, "ş+turkic-mark"))
        elif (
            "ü" in chars
            and _GERMANIC_SURNAME_PAT.search(tok)
            and not _HUNGARIAN_PAT.search(tok)
        ):
            anchors.append(("group", G_GERMANIC, 2, "ü+germanic-pattern"))
        elif (
            (chars & set("öä"))
            and _GERMANIC_SURNAME_PAT.search(tok)
            and not _HUNGARIAN_PAT.search(tok)
        ):
            anchors.append(
                (
                    "permitted",
                    frozenset({G_GERMANIC, G_NORDIC}),
                    2,
                    "ö/ä+germanic-pattern",
                )
            )

        # Token-initial ç (judge mod (b): Tier-2, Albanian trap).
        if tok.startswith("ç"):
            anchors.append(("group", G_TURKIC, 2, "ç-initial"))

        # French-ish marks (Tier-2; Benaïm guard decides leaf vs group cap).
        t2_fr = chars & _T2_FRENCHISH
        if t2_fr:
            kind = "group" if _french_suffix_ok(tok) else "group_cap"
            anchors.append((kind, G_GERMANIC, 2, "".join(sorted(t2_fr))))
        elif "é" in chars and _french_suffix_ok(tok):
            anchors.append(("group", G_GERMANIC, 2, "é+french-suffix"))

        # š/č/ž class: West/South Slavic vs Baltic not resolvable — permitted
        # set (judge mod (a): suppressed in Vietnamese context via đ above;
        # these marks themselves are not Vietnamese).
        if chars & _T2_SLAVIC_OR_BALTIC and not vietnamese_context:
            anchors.append(
                (
                    "permitted",
                    frozenset({G_SLAVIC, G_BALTIC}),
                    2,
                    "".join(sorted(chars & _T2_SLAVIC_OR_BALTIC)),
                )
            )

    if not anchors:
        return None
    # Prefer Tier-1; conflicts across DIFFERENT groups -> no anchor.
    tier1 = [a for a in anchors if a[2] == 1]
    pool = tier1 or anchors
    group_kinds = [a for a in pool if a[0] in ("group", "group_cap")]
    if group_kinds:
        groups = {a[1] for a in group_kinds}
        if len(groups) > 1:
            return None  # conflicting signature evidence
        kind = "group" if any(a[0] == "group" for a in group_kinds) else "group_cap"
        best = max(group_kinds, key=lambda a: (a[0] != "group_cap", len(a[3])))
        return OrthoAnchor(kind, best[1], min(a[2] for a in group_kinds), best[3])
    # only permitted-sets: intersect them
    sets = [a[1] for a in pool if a[0] == "permitted"]
    inter = frozenset.intersection(*sets) if sets else frozenset()
    if not inter:
        return None
    marks = "+".join(sorted({a[3] for a in pool if a[0] == "permitted"}))
    return OrthoAnchor("permitted", inter, 2, marks)
