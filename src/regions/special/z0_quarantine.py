"""
Z0 - Quarantine regional processor.

Handles entries with confidence < 50% that could not be reliably
assigned to any region.  Flags for human review with maximum
preservation of original data and minimal processing.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class Z0Quarantine(RegionSpec):
    """
    Quarantine region (Z0).

    Handles low-confidence entries that could not be reliably assigned
    to any regional processor.  Design principles:

    - Maximum preservation of original data
    - Minimal transformation (only safety-critical cleaning)
    - Comprehensive flagging for human review
    - Record why the entry was quarantined
    """

    def __init__(self):
        super().__init__(
            code="Z0",
            yaml_files=["z0_quarantine.yaml"],
            scripts=["Latin"],
            mixed_scripts=True,  # Accept any script
            canonical_order="Family, Given",
            romanisation_standards=[]
        )

        # Quarantine thresholds
        self.confidence_threshold = 0.50

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Minimal safety-critical cleaning in-place.

        Z0 deliberately performs the absolute minimum transformation
        to preserve the original data for human review:
        - Normalize Unicode to NFC (safety)
        - Strip leading/trailing whitespace
        - Collapse internal runs of whitespace
        - Remove control characters
        """
        canonical = entry.get("CanonicalLatin", "")
        if canonical:
            cleaned = self._safety_clean(canonical)
            entry["CanonicalLatin"] = cleaned

        native = entry.get("CanonicalNative", "")
        if native:
            entry["CanonicalNative"] = self._safety_clean(native)

        # Clean observed variants with same minimal approach
        if "Variants" in entry and "Observed" in entry["Variants"]:
            for variant in entry["Variants"]["Observed"]:
                if "str" in variant and variant["str"]:
                    variant["str"] = self._safety_clean(variant["str"])

    def _safety_clean(self, text: str) -> str:
        """Apply safety-critical-only cleaning to a string."""
        # NFC normalization
        text = unicodedata.normalize("NFC", text)
        # Remove control characters (except newline, tab)
        text = "".join(
            c for c in text
            if not unicodedata.category(c).startswith("C") or c in "\t\n"
        )
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text.strip())
        return text

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment quarantined entry with review metadata.

        - Extract basic components (best-effort)
        - Flag for human review with reason
        - Preserve original confidence score
        - Record quarantine metadata
        """
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not canonical:
            return

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        extras = entry["RegionalExtras"]

        # Best-effort component extraction
        family, given = self._split_canonical(canonical)
        extras["family_name"] = family
        extras["given_name"] = given

        # Quarantine metadata
        extras["quarantined"] = True
        extras["needs_human_review"] = True
        extras["confidence"] = entry.get("DetectionConfidence", 0.0)

        # Record quarantine reasons
        reasons: List[str] = []
        detection_conf = entry.get("DetectionConfidence", 0.0)
        if detection_conf < self.confidence_threshold:
            reasons.append(
                f"low-confidence ({detection_conf:.2f} < {self.confidence_threshold})"
            )

        # Check for mixed scripts (possible ambiguity)
        scripts_detected = self._detect_scripts(canonical)
        if len(scripts_detected) > 1:
            reasons.append(f"mixed-scripts ({', '.join(scripts_detected)})")
            extras["scripts_detected"] = scripts_detected

        # Check for unusual length
        if len(canonical) > 100:
            reasons.append("unusually-long-name")
        if len(canonical.strip()) < 3:
            reasons.append("unusually-short-name")

        if not reasons:
            reasons.append("unspecified-quarantine-trigger")

        extras["quarantine_reasons"] = reasons

        # No synthesised variants -- preserve original data only
        entry["RegionCode"] = self.code

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Permissive validation for quarantined entries.

        Z0 only rejects entries that are completely empty.
        Everything else is accepted and flagged for review.
        """
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")

        if not canonical and not native:
            raise RegionRuleError(
                "Quarantine entry must have CanonicalLatin or CanonicalNative"
            )

        # Accept anything with content -- the point of quarantine is to
        # preserve data that other processors could not handle.

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key.

        Quarantined entries sort by whatever canonical text is available,
        ASCII-folded.  Pure function.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        if not family and not given:
            canonical = (
                entry.get("CanonicalLatin", "")
                or entry.get("CanonicalNative", "")
                or ""
            )
            family, given = self._split_canonical(canonical)

        sort_family = self._ascii_fold(family).upper()
        sort_given = self._ascii_fold(given).upper()

        # Remove non-alphanumeric for consistent sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family}, {sort_given}".strip(", ")
        return " ".join(key.split()) if key.strip() else "ZZZZ_QUARANTINE"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_canonical(self, name: str) -> tuple:
        """Best-effort split into (family, given)."""
        if ", " in name:
            parts = name.split(", ", 1)
            return parts[0].strip(), parts[1].strip()
        tokens = name.split()
        if len(tokens) >= 2:
            return tokens[-1], " ".join(tokens[:-1])
        return name.strip(), ""

    def _detect_scripts(self, text: str) -> List[str]:
        """Detect which Unicode script blocks are present in the text."""
        scripts = set()
        for ch in text:
            if ch.isspace() or not ch.isalpha():
                continue
            cp = ord(ch)
            if cp <= 0x024F:
                scripts.add("Latin")
            elif 0x0400 <= cp <= 0x04FF:
                scripts.add("Cyrillic")
            elif 0x0600 <= cp <= 0x06FF:
                scripts.add("Arabic")
            elif 0x0900 <= cp <= 0x097F:
                scripts.add("Devanagari")
            elif 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
                scripts.add("CJK")
            elif 0xAC00 <= cp <= 0xD7AF:
                scripts.add("Hangul")
            elif 0x3040 <= cp <= 0x30FF:
                scripts.add("Japanese")
            elif 0x0E00 <= cp <= 0x0E7F:
                scripts.add("Thai")
            elif 0x1200 <= cp <= 0x139F:
                scripts.add("Ge'ez")
            elif 0x0370 <= cp <= 0x03FF:
                scripts.add("Greek")
            elif 0x0530 <= cp <= 0x058F:
                scripts.add("Armenian")
            elif 0x10A0 <= cp <= 0x10FF:
                scripts.add("Georgian")
            else:
                scripts.add("Other")
        return sorted(scripts)

    def _ascii_fold(self, text: str) -> str:
        """Fold to ASCII for sorting, best-effort."""
        try:
            nfd = unicodedata.normalize("NFD", text)
            return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        except (TypeError, ValueError):
            return str(text)
