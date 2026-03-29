#!/usr/bin/env python3
"""
Phase 3.2: Enhanced Surname Pattern Detection

This module implements morphological surname pattern matching for Latin-script names.
Addresses the critical gap in Phase 3 where Latin-script names (A1, A2, G1) fail
due to lack of pattern recognition.

Root Cause (from Phase 3 plan):
- A1 (Anglo): 37.0% → Need English patterns
- A2 (Western Europe): 18.9% → Need German/French patterns
- G1 (Latin America): 18.6% → Need Spanish patterns

Expected Impact: +15-20pp accuracy boost on Latin-script names
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SurnamePattern:
    """A surname pattern with its associated region and confidence."""

    pattern: str
    region_code: str
    confidence: float
    pattern_type: str  # 'suffix', 'prefix', 'contains'
    description: str


class SurnamePatternDetector:
    """
    Detects regional patterns in surnames for Latin-script names.

    This is the CRITICAL missing component from Phase 3 that caused
    71% accuracy instead of 90%+.
    """

    def __init__(self):
        """Initialize surname pattern database."""
        self.patterns = self._build_pattern_database()

    def _build_pattern_database(self) -> List[SurnamePattern]:
        """
        Build comprehensive surname pattern database.

        Based on Phase 3 plan specification for Enhanced Rules.
        """
        patterns = []

        # ===================================================================
        # A1: ANGLO-SPHERE (English surname patterns)
        # ===================================================================

        # English locative surnames (-ton = "town")
        english_ton = [
            "Newton",
            "Washington",
            "Hamilton",
            "Wellington",
            "Carleton",
            "Middleton",
            "Livingston",
            "Clinton",
            "Allington",
            "Barton",
        ]
        patterns.append(
            SurnamePattern(
                pattern=r"ton$",
                region_code="A1",
                confidence=0.90,
                pattern_type="suffix",
                description="English locative -ton (town)",
            )
        )

        # English patronymic (-son)
        patterns.append(
            SurnamePattern(
                pattern=r"son$",
                region_code="A1",
                confidence=0.85,
                pattern_type="suffix",
                description="English patronymic -son",
            )
        )

        # English -ing surnames
        patterns.append(
            SurnamePattern(
                pattern=r"ing$",
                region_code="A1",
                confidence=0.80,
                pattern_type="suffix",
                description="English -ing surnames (Turing, Browning)",
            )
        )

        # English locative -ford
        patterns.append(
            SurnamePattern(
                pattern=r"ford$",
                region_code="A1",
                confidence=0.85,
                pattern_type="suffix",
                description="English locative -ford (river crossing)",
            )
        )

        # English locative -ham
        patterns.append(
            SurnamePattern(
                pattern=r"ham$",
                region_code="A1",
                confidence=0.90,
                pattern_type="suffix",
                description="English locative -ham (homestead)",
            )
        )

        # English locative -ley/-ly
        patterns.append(
            SurnamePattern(
                pattern=r"l[e]?y$",
                region_code="A1",
                confidence=0.75,
                pattern_type="suffix",
                description="English locative -ley (clearing)",
            )
        )

        # English -worth
        patterns.append(
            SurnamePattern(
                pattern=r"worth$",
                region_code="A1",
                confidence=0.85,
                pattern_type="suffix",
                description="English locative -worth (enclosure)",
            )
        )

        # ===================================================================
        # A2: WESTERN EUROPE (German surname patterns)
        # ===================================================================

        # German -mann (very strong signal)
        patterns.append(
            SurnamePattern(
                pattern=r"mann$",
                region_code="A2",
                confidence=0.95,
                pattern_type="suffix",
                description="German -mann (Riemann, Grassmann, Boltzmann)",
            )
        )

        # German -stein (very strong signal)
        patterns.append(
            SurnamePattern(
                pattern=r"stein$",
                region_code="A2",
                confidence=0.95,
                pattern_type="suffix",
                description="German -stein (Einstein, Bernstein, Goldstein)",
            )
        )

        # German -berg
        patterns.append(
            SurnamePattern(
                pattern=r"berg$",
                region_code="A2",
                confidence=0.90,
                pattern_type="suffix",
                description="German -berg (Goldberg, Heisenberg)",
            )
        )

        # German -feld
        patterns.append(
            SurnamePattern(
                pattern=r"feld$",
                region_code="A2",
                confidence=0.90,
                pattern_type="suffix",
                description="German -feld (Sommerfeld)",
            )
        )

        # German -haus/-hausen
        patterns.append(
            SurnamePattern(
                pattern=r"haus(en)?$",
                region_code="A2",
                confidence=0.85,
                pattern_type="suffix",
                description="German -haus/-hausen (house)",
            )
        )

        # German -bauer
        patterns.append(
            SurnamePattern(
                pattern=r"bauer$",
                region_code="A2",
                confidence=0.90,
                pattern_type="suffix",
                description="German -bauer (farmer)",
            )
        )

        # German -schmidt/-schmitt
        patterns.append(
            SurnamePattern(
                pattern=r"schmidt$|schmitt$",
                region_code="A2",
                confidence=0.85,
                pattern_type="suffix",
                description="German Schmidt/Schmitt (smith)",
            )
        )

        # German umlauts (strong signal)
        patterns.append(
            SurnamePattern(
                pattern=r"[äöüÄÖÜß]",
                region_code="A2",
                confidence=0.90,
                pattern_type="contains",
                description="German umlauts (Müller, März, Schrödinger)",
            )
        )

        # ===================================================================
        # A2: WESTERN EUROPE (French surname patterns)
        # ===================================================================

        # French nobility 'De ' prefix
        patterns.append(
            SurnamePattern(
                pattern=r"^De\s",
                region_code="A2",
                confidence=0.95,
                pattern_type="prefix",
                description="French nobility De (Descartes, De Moivre)",
            )
        )

        # French 'Du ' prefix
        patterns.append(
            SurnamePattern(
                pattern=r"^Du\s",
                region_code="A2",
                confidence=0.95,
                pattern_type="prefix",
                description="French Du (Dubois, Dupont)",
            )
        )

        # French 'Le ' prefix
        patterns.append(
            SurnamePattern(
                pattern=r"^Le\s",
                region_code="A2",
                confidence=0.90,
                pattern_type="prefix",
                description="French Le (Leblanc, Leroy)",
            )
        )

        # French 'La ' prefix
        patterns.append(
            SurnamePattern(
                pattern=r"^La\s",
                region_code="A2",
                confidence=0.90,
                pattern_type="prefix",
                description="French La (Lagrange)",
            )
        )

        # French -eau
        patterns.append(
            SurnamePattern(
                pattern=r"eau$",
                region_code="A2",
                confidence=0.80,
                pattern_type="suffix",
                description="French -eau",
            )
        )

        # French accents (moderate signal, could also be G1)
        patterns.append(
            SurnamePattern(
                pattern=r"[àâäéèêëîïôùûü]",
                region_code="A2",
                confidence=0.70,
                pattern_type="contains",
                description="French accents",
            )
        )

        # ===================================================================
        # A2: WESTERN EUROPE (Italian surname patterns)
        # ===================================================================

        # Italian 'Di ' prefix
        patterns.append(
            SurnamePattern(
                pattern=r"^Di\s",
                region_code="A2",
                confidence=0.90,
                pattern_type="prefix",
                description="Italian Di (Di Lavore)",
            )
        )

        # Italian -ini
        patterns.append(
            SurnamePattern(
                pattern=r"ini$",
                region_code="A2",
                confidence=0.85,
                pattern_type="suffix",
                description="Italian -ini (Bellini, Rossini)",
            )
        )

        # Italian -elli
        patterns.append(
            SurnamePattern(
                pattern=r"elli$",
                region_code="A2",
                confidence=0.85,
                pattern_type="suffix",
                description="Italian -elli (Gabrielli, Morelli)",
            )
        )

        # Italian -etti
        patterns.append(
            SurnamePattern(
                pattern=r"etti$",
                region_code="A2",
                confidence=0.80,
                pattern_type="suffix",
                description="Italian -etti (Rossetti)",
            )
        )

        # Italian -ino/-ina
        patterns.append(
            SurnamePattern(
                pattern=r"ino$|ina$",
                region_code="A2",
                confidence=0.75,
                pattern_type="suffix",
                description="Italian -ino/-ina",
            )
        )

        # Italian double consonants
        patterns.append(
            SurnamePattern(
                pattern=r"(cc|ff|ll|mm|nn|pp|rr|ss|tt|zz)",
                region_code="A2",
                confidence=0.65,
                pattern_type="contains",
                description="Italian double consonants",
            )
        )

        # ===================================================================
        # G1: LATIN AMERICA (Spanish surname patterns)
        # ===================================================================

        # Spanish -ez (very common patronymic)
        patterns.append(
            SurnamePattern(
                pattern=r"ez$",
                region_code="G1",
                confidence=0.85,
                pattern_type="suffix",
                description="Spanish patronymic -ez (Rodriguez, Martinez, Gonzalez)",
            )
        )

        # Spanish -es
        patterns.append(
            SurnamePattern(
                pattern=r"es$",
                region_code="G1",
                confidence=0.75,
                pattern_type="suffix",
                description="Spanish -es (Torres, Flores)",
            )
        )

        # Spanish -az
        patterns.append(
            SurnamePattern(
                pattern=r"az$",
                region_code="G1",
                confidence=0.80,
                pattern_type="suffix",
                description="Spanish -az (Diaz)",
            )
        )

        # Spanish -iz
        patterns.append(
            SurnamePattern(
                pattern=r"iz$",
                region_code="G1",
                confidence=0.80,
                pattern_type="suffix",
                description="Spanish -iz (Ruiz, Ortiz)",
            )
        )

        # Spanish ñ (unique to Spanish)
        patterns.append(
            SurnamePattern(
                pattern=r"ñ",
                region_code="G1",
                confidence=0.95,
                pattern_type="contains",
                description="Spanish ñ (Peña, Muñoz)",
            )
        )

        # Spanish 'De la ' prefix
        patterns.append(
            SurnamePattern(
                pattern=r"^De\sla\s",
                region_code="G1",
                confidence=0.85,
                pattern_type="prefix",
                description="Spanish De la",
            )
        )

        # Portuguese -es (Brazil/Portugal)
        patterns.append(
            SurnamePattern(
                pattern=r"es$",
                region_code="G1",
                confidence=0.70,
                pattern_type="suffix",
                description="Portuguese -es (Gomes, Lopes)",
            )
        )

        # ===================================================================
        # A3: NORDIC-BALTIC (Scandinavian patterns)
        # ===================================================================

        # Scandinavian -sen
        patterns.append(
            SurnamePattern(
                pattern=r"sen$",
                region_code="A3",
                confidence=0.85,
                pattern_type="suffix",
                description="Scandinavian patronymic -sen (Andersen, Jensen)",
            )
        )

        # Scandinavian -sson
        patterns.append(
            SurnamePattern(
                pattern=r"sson$",
                region_code="A3",
                confidence=0.90,
                pattern_type="suffix",
                description="Swedish/Icelandic -sson (Andersson, Svensson)",
            )
        )

        # Scandinavian -dottir
        patterns.append(
            SurnamePattern(
                pattern=r"dottir$",
                region_code="A3",
                confidence=0.95,
                pattern_type="suffix",
                description="Icelandic matronymic -dottir",
            )
        )

        # Scandinavian -lund
        patterns.append(
            SurnamePattern(
                pattern=r"lund$",
                region_code="A3",
                confidence=0.80,
                pattern_type="suffix",
                description="Scandinavian -lund (grove)",
            )
        )

        # Scandinavian -quist/-qvist
        patterns.append(
            SurnamePattern(
                pattern=r"q(ui|vi)st$",
                region_code="A3",
                confidence=0.85,
                pattern_type="suffix",
                description="Swedish -quist/-qvist (Lundqvist)",
            )
        )

        # Scandinavian ø/å/æ
        patterns.append(
            SurnamePattern(
                pattern=r"[øåæØÅÆ]",
                region_code="A3",
                confidence=0.90,
                pattern_type="contains",
                description="Scandinavian special characters",
            )
        )

        # ===================================================================
        # B2: SOUTH SLAVIC-CENTRAL (Polish/Czech patterns)
        # ===================================================================

        # Polish -ski/-ska
        patterns.append(
            SurnamePattern(
                pattern=r"ski$|ska$",
                region_code="B2",
                confidence=0.85,
                pattern_type="suffix",
                description="Polish -ski/-ska (Kowalski)",
            )
        )

        # Polish -wicz
        patterns.append(
            SurnamePattern(
                pattern=r"wicz$",
                region_code="B2",
                confidence=0.90,
                pattern_type="suffix",
                description="Polish patronymic -wicz",
            )
        )

        # Czech -ová (feminine)
        patterns.append(
            SurnamePattern(
                pattern=r"ová$",
                region_code="B2",
                confidence=0.90,
                pattern_type="suffix",
                description="Czech feminine -ová",
            )
        )

        # Polish special characters
        patterns.append(
            SurnamePattern(
                pattern=r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]",
                region_code="B2",
                confidence=0.85,
                pattern_type="contains",
                description="Polish special characters",
            )
        )

        # Czech special characters
        patterns.append(
            SurnamePattern(
                pattern=r"[čďěňřšťůžČĎĚŇŘŠŤŮŽ]",
                region_code="B2",
                confidence=0.85,
                pattern_type="contains",
                description="Czech special characters",
            )
        )

        return patterns

    def detect_surname_patterns(self, name: str) -> List[Tuple[str, float, str]]:
        """
        Detect surname patterns in a name.

        Args:
            name: Full name (e.g., "Albert Einstein", "Isaac Newton")

        Returns:
            List of (region_code, confidence, description) tuples
        """
        # Extract likely surname (last token)
        tokens = name.strip().split()
        if not tokens:
            return []

        surname = tokens[-1]

        # Check all patterns
        matches = []
        for pattern_obj in self.patterns:
            if self._matches_pattern(surname, pattern_obj):
                matches.append(
                    (pattern_obj.region_code, pattern_obj.confidence, pattern_obj.description)
                )

        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def _matches_pattern(self, surname: str, pattern_obj: SurnamePattern) -> bool:
        """Check if surname matches a pattern."""
        if pattern_obj.pattern_type == "suffix":
            return re.search(pattern_obj.pattern, surname, re.IGNORECASE) is not None
        elif pattern_obj.pattern_type == "prefix":
            # For prefix, check full name with space
            return re.search(pattern_obj.pattern, surname, re.IGNORECASE) is not None
        elif pattern_obj.pattern_type == "contains":
            return re.search(pattern_obj.pattern, surname, re.IGNORECASE | re.UNICODE) is not None
        return False

    def get_best_match(self, name: str) -> Optional[Tuple[str, float, str]]:
        """
        Get the highest-confidence surname pattern match.

        Args:
            name: Full name

        Returns:
            (region_code, confidence, description) or None if no match
        """
        matches = self.detect_surname_patterns(name)
        return matches[0] if matches else None


# Singleton instance
_detector = None


def get_surname_detector() -> SurnamePatternDetector:
    """Get singleton surname pattern detector."""
    global _detector
    if _detector is None:
        _detector = SurnamePatternDetector()
    return _detector


if __name__ == "__main__":
    # Test the detector
    detector = SurnamePatternDetector()

    test_names = [
        "Isaac Newton",  # English -ton → A1
        "Albert Einstein",  # German -stein → A2
        "Bernhard Riemann",  # German -mann → A2
        "Alan Turing",  # English -ing → A1
        "José Rodriguez",  # Spanish -ez → G1
        "Pierre Dubois",  # French Du- → A2
        "Giovanni Bellini",  # Italian -ini → A2
        "Anders Andersen",  # Scandinavian -sen → A3
        "Jan Kowalski",  # Polish -ski → B2
    ]

    print("Surname Pattern Detection Test")
    print("=" * 70)
    print()

    for name in test_names:
        matches = detector.detect_surname_patterns(name)
        print(f"{name:25s} → ", end="")
        if matches:
            region, conf, desc = matches[0]
            print(f"{region} ({conf:.2f}) - {desc}")
        else:
            print("No match")

    print()
    print(f"Total patterns loaded: {len(detector.patterns)}")
