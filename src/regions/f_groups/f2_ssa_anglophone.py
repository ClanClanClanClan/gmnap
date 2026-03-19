"""
F2 - Sub-Saharan Africa Anglophone regional processor.

Covers: Nigeria, Ghana, Kenya, Uganda, Tanzania, Zimbabwe, Zambia,
Malawi, Gambia, Liberia, Sierra Leone, Botswana, Lesotho, Namibia,
Rwanda, Swaziland/Eswatini, Mauritius, South Sudan.

Features: Yoruba prefixes (Ade-, Ola-, Olu-), Igbo prefixes (Nna-, Chi-),
hyphenated given names (Rule 23), Western-style Family-Given ordering.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class F2SSAAnglophone(RegionSpec):
    """
    Sub-Saharan Africa Anglophone region (F2).

    Handles Anglophone African naming conventions including:
    - Yoruba prefixes: Ade-, Ola-, Olu-, Ayo-, Oba-
    - Igbo prefixes: Nna-, Chi-, Eze-, Obi-, Nwa-
    - Akan day-names: Kwame, Kofi, Ama, Akua
    - East African patterns (Swahili, Bantu)
    - Hyphenated given names per Rule 23
    - Western-style Family, Given ordering
    """

    def __init__(self):
        super().__init__(
            code="F2",
            yaml_files=["f2_ssa_anglophone.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["English"]
        )

        # English titles to remove
        self.titles = {
            "Dr", "Dr.", "Doctor",
            "Prof", "Prof.", "Professor",
            "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.", "Miss",
            "Sir", "Chief", "Alhaji", "Alhaja",
            "Rev", "Rev.", "Reverend",
            "Hon", "Hon.", "Honourable",
            "Engr", "Engr.", "Barrister", "Barr.",
        }

        # Yoruba surname prefixes (must stay attached)
        self.yoruba_prefixes = [
            "Ade", "Ola", "Olu", "Ayo", "Oba",
            "Omo", "Ojo", "Ige", "Aina", "Oke",
            "Oso", "Akin", "Bam", "Odu", "Ogo",
        ]

        # Igbo surname prefixes (must stay attached)
        self.igbo_prefixes = [
            "Nna", "Chi", "Eze", "Obi", "Nwa",
            "Ike", "Udo", "Onu", "Agu", "Okw",
            "Nne", "Ama", "Ugo",
        ]

        # Akan day-names (Ghana) - these are given names
        self.akan_day_names = {
            "Kwame", "Kwasi", "Kwadwo", "Kwaku", "Yaw", "Kofi", "Kwabena",
            "Ama", "Akosua", "Adwoa", "Akua", "Yaa", "Afia", "Abena",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Anglophone African names in-place.

        - Remove English and African titles/honorifics
        - Normalize whitespace and punctuation
        - Preserve ethnic prefix patterns
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Remove titles
        titles_pattern = re.compile(
            r"\b(Dr\.?|Doctor|Prof\.?|Professor|Mr\.?|Mrs\.?|Ms\.?|Miss|"
            r"Sir|Chief|Alhaji|Alhaja|Rev\.?|Reverend|"
            r"Hon\.?|Honourable|Engr\.?|Barr\.?|Barrister)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", canonical)

        # Remove suffixes (degrees, etc.)
        suffixes_pattern = re.compile(
            r"\s+\b(Jr\.?|Sr\.?|Esq\.?|OFR|MFR|CON|GCON|PhD|Ph\.D\.|MBE|OBE)\b",
            re.IGNORECASE,
        )
        cleaned = suffixes_pattern.sub("", cleaned)

        # Normalize Unicode
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        entry["CanonicalLatin"] = cleaned

        # Clean variant strings
        if "Variants" in entry and "Observed" in entry["Variants"]:
            for variant in entry["Variants"]["Observed"]:
                if "str" in variant and variant["str"]:
                    v = titles_pattern.sub("", variant["str"])
                    v = suffixes_pattern.sub("", v)
                    v = re.sub(r"\s+", " ", v.strip())
                    variant["str"] = v

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with F2-specific data.

        - Extract family/given components
        - Detect Yoruba, Igbo, Akan name patterns
        - Generate hyphen-collapse and ASCII variants
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        extras = entry["RegionalExtras"]
        variants = entry["Variants"]["Synthesised"]

        # Extract name components
        family, given = self._split_canonical(canonical)
        extras["family_name"] = family
        extras["given_name"] = given

        # Detect ethnic origin from prefix patterns
        ethnicity = self._detect_ethnicity(family, given)
        if ethnicity:
            extras["ethnic_group_hint"] = ethnicity

        # Detect Yoruba prefix
        yoruba_prefix = self._detect_prefix(family, self.yoruba_prefixes)
        if yoruba_prefix:
            extras["yoruba_prefix"] = yoruba_prefix

        # Detect Igbo prefix
        igbo_prefix = self._detect_prefix(family, self.igbo_prefixes)
        if igbo_prefix:
            extras["igbo_prefix"] = igbo_prefix

        # Detect Akan day-name in given name
        if given:
            for day_name in self.akan_day_names:
                if day_name.lower() in given.lower().split():
                    extras["akan_day_name"] = day_name
                    break

        # Rule 23: Hyphenated given names collapse
        if given and "-" in given:
            extras["hyphenated_given"] = True
            first_part = given.split("-")[0]
            collapsed = f"{family}, {first_part}" if family else first_part
            if collapsed != canonical:
                variants.append({"str": collapsed, "type": "initial-collapse"})

        # ASCII-lossy variant
        ascii_variant = self._remove_diacritics(canonical)
        if ascii_variant != canonical:
            variants.append({"str": ascii_variant, "type": "ascii-lossy"})

        # Order-swap variant (Given Family)
        if family and given:
            variants.append({
                "str": f"{given} {family}",
                "type": "order-swap",
            })

        entry["RegionCode"] = self.code

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry per F2 rules.

        - CanonicalLatin must be present
        - Latin script characters only
        - Minimum length check
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        if len(canonical.strip()) < 2:
            raise RegionRuleError("Name too short for F2 region")

        # Latin script + common punctuation
        for ch in canonical:
            if ord(ch) > 0x024F and ch not in " ,-.'\u2019":
                raise RegionRuleError(
                    f"Non-Latin character U+{ord(ch):04X} in F2 name"
                )

        if len(canonical) > 120:
            raise RegionRuleError("Name exceeds 120 character limit")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key.

        Sorts by family name then given name, ASCII-folded.
        Pure function.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        if not family:
            canonical = entry.get("CanonicalLatin", "")
            family, given = self._split_canonical(canonical)

        sort_family = self._remove_diacritics(family).upper()
        sort_given = self._remove_diacritics(given).upper()

        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family}, {sort_given}".strip(", ")
        return " ".join(key.split())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_canonical(self, name: str) -> tuple:
        """Split canonical into (family, given)."""
        if ", " in name:
            parts = name.split(", ", 1)
            return parts[0].strip(), parts[1].strip()
        tokens = name.split()
        if len(tokens) >= 2:
            return tokens[-1], " ".join(tokens[:-1])
        return name.strip(), ""

    def _detect_prefix(self, surname: str, prefix_list: List[str]) -> Optional[str]:
        """Return ethnic prefix if surname starts with one."""
        for prefix in prefix_list:
            if surname.startswith(prefix) and len(surname) > len(prefix):
                return prefix
        return None

    def _detect_ethnicity(self, family: str, given: str) -> Optional[str]:
        """Heuristic to guess broad ethnic group from name patterns."""
        fl = family.lower()
        gl = given.lower() if given else ""

        # Yoruba indicators
        if any(fl.startswith(p.lower()) for p in self.yoruba_prefixes):
            return "Yoruba"

        # Igbo indicators
        if any(fl.startswith(p.lower()) for p in self.igbo_prefixes):
            return "Igbo"

        # Akan indicators
        if any(dn.lower() in gl.split() for dn in self.akan_day_names):
            return "Akan"

        return None

    def _remove_diacritics(self, text: str) -> str:
        """Strip diacritics, keeping base Latin letters."""
        nfd = unicodedata.normalize("NFD", text)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
