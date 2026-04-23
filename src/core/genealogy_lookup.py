"""Singleton lookup for curated genealogy enrichment data.

Loads data/genealogy_enrichment.json (built by tools/build_genealogy_enrichment.py)
and exposes two operations:

- `enrich(entry)`: decorate an entry dict with BirthYear / Institution / Advisors
  when a matching record exists. Idempotent; never overwrites non-null values.
- `traverse_lineage(start, depth)`: build advisor edges for the lineage endpoint.

`start` accepts either a GlobalID or a canonical name (case-insensitive). The
name form supports an optional `name:` prefix used by the API route.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _strip_diacritics(text: str) -> str:
    """'Erdős' → 'Erdos', 'Poincaré' → 'Poincare'.

    Decompose to NFD then drop combining marks. Keeps ordinary letters
    and hyphens/apostrophes/punctuation intact so the result is still
    readable ASCII.
    """
    if not text:
        return text
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


# Lowercase name particles that may appear either stuck to the surname
# ('von Neumann') or trailing the given name ('Neumann, John von').
# Normalizing these to the second form collapses both variants onto the
# same key.
_NAME_PARTICLES = frozenset(
    (
        "von",
        "van",
        "de",
        "del",
        "della",
        "di",
        "du",
        "da",
        "den",
        "der",
        "le",
        "la",
        "ten",
        "ter",
        "af",
        "av",
        "zu",
        "zum",
        "zur",
    )
)


def _fold_particles(key: str) -> str:
    """Move leading particles off the surname side onto the given side.

    'von neumann, john' → 'neumann, john von'
    'de witt, jan' → 'witt, jan de'
    Idempotent; leaves keys without particles unchanged.
    """
    if "," not in key:
        return key
    surname, given = key.split(",", 1)
    surname_tokens = surname.strip().split()
    particles: list[str] = []
    while surname_tokens and surname_tokens[0] in _NAME_PARTICLES:
        particles.append(surname_tokens.pop(0))
    if not particles or not surname_tokens:
        return key
    new_surname = " ".join(surname_tokens)
    new_given = (given.strip() + " " + " ".join(particles)).strip()
    return f"{new_surname}, {new_given}"


_ENRICHMENT_FIELDS = (
    "BirthYear",
    "DeathYear",
    "Institution",
    "Country",
    "Thesis",
    "ThesisYear",
    "Advisors",
)


def _normalize_key(name: str) -> str:
    """Match the normalization used when the enrichment file was built.

    Lowercase, strip diacritics (so 'Erdős' ↔ 'Erdos' and 'Poincaré' ↔
    'Poincare' collapse), collapse whitespace, strip parenthetical
    aliases (e.g. 'G. H. (Godfrey Harold) Hardy' → 'hardy, g. h.'), and
    reorder 'First Last' to 'last, first'.
    """
    if not name:
        return ""
    # Drop parenthetical aliases before any other processing
    name = re.sub(r"\s*\([^)]*\)", "", name)
    # Strip diacritics BEFORE lowercasing so the category filter sees Mn
    name = _strip_diacritics(name)
    name = re.sub(r"\s+", " ", name.strip().lower())
    if "," not in name:
        parts = name.split()
        if len(parts) >= 2:
            name = f"{parts[-1]}, {' '.join(parts[:-1])}"
    # Trim any trailing stray punctuation left after paren removal
    name = re.sub(r"\s+,", ",", name).strip(" ,")
    # Normalize particle placement (Dutch/German cataloging convention)
    name = _fold_particles(name)
    return name


def _split_given_tokens(given_part: str) -> set[str]:
    """Split a given-name string on whitespace AND hyphens.

    Used by token-set matching so 'Joseph-Louis' contains 'joseph' and
    'louis' as separate matchable tokens. Also drops single-character
    tokens (initials like 'c.', 'l.') to avoid spurious matches.
    """
    tokens = re.split(r"[\s\-]+", given_part.strip())
    return {t for t in tokens if len(t) > 1}


def _short_key(full_key: str) -> str:
    """Return 'surname, first-given' short form of a full key.

    Used as a secondary index so abbreviated forms like 'Tao, T.'
    still resolve to 'tao, terence chi-shen'.
    """
    if not full_key or "," not in full_key:
        return full_key
    surname, given = full_key.split(",", 1)
    given_tokens = given.strip().split()
    if not given_tokens:
        return full_key
    return f"{surname.strip()}, {given_tokens[0]}"


class GenealogyLookup:
    """Process-wide singleton. Instantiate cheaply; data is loaded once."""

    _instance: Optional["GenealogyLookup"] = None

    def __new__(cls) -> "GenealogyLookup":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        self._by_name: Dict[str, Dict[str, Any]] = {}
        self._by_gid: Dict[str, str] = {}
        # Secondary index: "surname, first-given" -> full key. Allows
        # short input forms ("Tao, T.") to match full entries
        # ("tao, terence chi-shen"). Ambiguous short keys (multiple
        # full entries share a short form) are dropped from the index.
        self._by_short: Dict[str, str] = {}
        path = Path("data/genealogy_enrichment.json")
        if not path.exists():
            logger.info(
                "genealogy_enrichment.json not found; "
                "genealogy fields will not be populated"
            )
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._by_name = data.get("by_name") or {}
            self._by_gid = data.get("by_global_id") or {}
            self._build_short_index()
            logger.info(
                "Loaded genealogy enrichment: %d names, %d global-ids, "
                "%d short-keys",
                len(self._by_name),
                len(self._by_gid),
                len(self._by_short),
            )
        except Exception as exc:
            logger.warning("Failed to load genealogy enrichment: %s", exc)

    def _build_short_index(self) -> None:
        """Build the short-key → full-key index, dropping ambiguous keys."""
        counts: Dict[str, int] = {}
        first_hit: Dict[str, str] = {}
        for full_key in self._by_name:
            short = _short_key(full_key)
            if short == full_key:
                continue
            counts[short] = counts.get(short, 0) + 1
            first_hit.setdefault(short, full_key)
        self._by_short = {
            short: full for short, full in first_hit.items() if counts[short] == 1
        }

    # ---- Lookup helpers -------------------------------------------------

    def _resolve(self, identifier: str) -> Optional[str]:
        """Resolve a GlobalID or name to the internal key.

        Tries in order:
          1. GlobalID exact match
          2. Normalized-name exact match
          3. Short-key index ('tao, terence' → 'tao, terence chi-shen')
          4. Token-set match (same surname + overlapping given-name tokens,
             when unambiguous)
        """
        if not identifier:
            return None
        if identifier.startswith("name:"):
            identifier = identifier[5:]
        # Try as GlobalID first
        if identifier in self._by_gid:
            return self._by_gid[identifier]
        # Try as canonical name (exact, then short-form, then token-set)
        key = _normalize_key(identifier)
        if key in self._by_name:
            return key
        if key in self._by_short:
            return self._by_short[key]
        short = _short_key(key)
        if short in self._by_short:
            return self._by_short[short]
        return self._token_set_match(key)

    def _token_set_match(self, key: str) -> Optional[str]:
        """Match on same surname + overlapping given-name tokens.

        Handles stored aliases like 'Lindemann, C. L. Ferdinand' being
        queried as 'Lindemann, Ferdinand', and hyphenated forms like
        'Lagrange, Joseph-Louis' matching 'Lagrange, Joseph'. Only returns
        a hit when exactly one stored entry matches, so an ambiguous query
        stays a miss.
        """
        if "," not in key:
            return None
        q_surname, q_given = key.split(",", 1)
        q_surname = q_surname.strip()
        q_tokens = _split_given_tokens(q_given)
        if not q_tokens:
            return None
        matches = []
        for full_key in self._by_name:
            if "," not in full_key:
                continue
            f_surname, f_given = full_key.split(",", 1)
            if f_surname.strip() != q_surname:
                continue
            f_tokens = _split_given_tokens(f_given)
            if not f_tokens:
                continue
            # Accept when one set is a subset of the other (shared tokens
            # with no contradicting extras on the shorter side).
            if f_tokens <= q_tokens or q_tokens <= f_tokens:
                matches.append(full_key)
        if len(matches) == 1:
            return matches[0]
        return None

    def lookup_by_gid(self, gid: str) -> Optional[Dict[str, Any]]:
        key = self._by_gid.get(gid)
        return self._by_name.get(key) if key else None

    def lookup_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        key = self._resolve(name)
        return self._by_name.get(key) if key else None

    # ---- Public API -----------------------------------------------------

    def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Decorate an entry with curated genealogy fields.

        Looks up by CanonicalLatin first (exact, then short-form), then by
        GlobalID. Never overwrites fields that are already populated
        (truthy).
        """
        record: Optional[Dict[str, Any]] = None
        canonical = entry.get("CanonicalLatin") or entry.get("name")
        if canonical:
            record = self.lookup_by_name(canonical)
        if record is None:
            gid = entry.get("GlobalID") or entry.get("global_id")
            if gid:
                record = self.lookup_by_gid(gid)
        if record is None:
            return entry
        for field in _ENRICHMENT_FIELDS:
            if field in record and not entry.get(field):
                entry[field] = record[field]
        return entry

    def traverse_lineage(self, start: str, depth: int) -> List[Dict[str, str]]:
        """Build advisor edges starting from `start` (GlobalID or name).

        Returns a list of ``{from, to, relation}`` edges. Each hop
        represents a 'doctoralAdvisor' relation. Stops at ``depth``
        levels, or when a node has no advisors, or when a cycle would
        form.

        Edge endpoints are the canonical display names of each person
        (e.g. ``"Bernoulli, Johann"``) rather than opaque internal
        GlobalIDs — the web UI renders these verbatim. The root uses
        the caller's input, stripped of any ``name:`` prefix, so the
        response's ``root`` field matches the query.
        """
        edges: List[Dict[str, str]] = []
        visited: set[str] = set()
        root_key = self._resolve(start)
        if root_key is None:
            return edges

        root_label = start[5:] if start.startswith("name:") else start
        # If the caller passed an opaque GlobalID, substitute the record's
        # CanonicalLatin so the root node is readable instead of a hash.
        if root_key in self._by_name:
            root_record = self._by_name[root_key]
            root_label = root_record.get("CanonicalLatin") or root_label

        queue: List[tuple[str, str, int]] = [(root_key, root_label, depth)]
        while queue:
            key, from_label, remaining = queue.pop(0)
            if remaining <= 0 or key in visited:
                continue
            visited.add(key)
            record = self._by_name.get(key)
            if not record:
                continue
            for adv in record.get("Advisors", []) or []:
                adv_name = adv.get("name") if isinstance(adv, dict) else adv
                if not adv_name:
                    continue
                adv_key = _normalize_key(adv_name)
                # Prefer the stored canonical casing over the inbound string
                # (advisor name is sometimes a short form while the stored
                # record has the full one).
                adv_record = self._by_name.get(adv_key, {})
                adv_label = adv_record.get("CanonicalLatin") or adv_name
                edges.append(
                    {"from": from_label, "to": adv_label, "relation": "doctoralAdvisor"}
                )
                if adv_key in self._by_name:
                    queue.append((adv_key, adv_label, remaining - 1))
        return edges
