"""
B3 - Greek World region implementation.

Covers: GR (Greece), CY (Cyprus)
Features: Greek script detection, ELOT 743 & ISO 843 romanisation,
          Ancient vs modern Greek handling, Χατζη- variants.
"""

import re
from typing import Any, Dict, List, Optional

from ...base import RegionRuleError, RegionSpec


class B3GreekProcessor(RegionSpec):
    """
    Greek World region (B3).

    Handles Greek naming conventions:
    - Greek script (Ελληνικά) detection and validation
    - ELOT 743 & ISO 843 romanisation standards
    - Ancient vs modern Greek distinction (rule #25)
    - Χατζη- (Chatzi-/Hatzi-) variants (rule #19)
    - Common Greek prefixes (Παπα-, Χατζη-, Καρα-)
    - Genitive case endings (-ου, -η, -ά)
    - Cypriot-specific patterns
    """

    def __init__(self):
        super().__init__(
            code="B3",
            yaml_files=["b3_greek.yaml"],
            scripts=["Greek", "Latin"],
            mixed_scripts=True,  # Can have both Greek and Latin
            canonical_order="Family, Given",
            romanisation_standards=["ELOT 743", "ISO 843"],
        )

        # Greek alphabet
        self.greek_chars = set("ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψω")

        # Greek diacritics
        self.greek_diacritics = set("άέήίόύώΆΈΉΊΌΎΏΐΰϊϋΐΰ")

        # Final sigma
        self.final_sigma = "ς"

        self.allowed_greek_chars = self.greek_chars | self.greek_diacritics | {self.final_sigma}

        # Latin characters used in romanisation
        self.latin_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

        # Common Greek prefixes (with translations)
        self.greek_prefixes = {
            "Παπα": "Papa",  # Priest
            "Χατζη": "Chatzi",  # Hajji (pilgrimage)
            "Χατζι": "Chatzi",  # Alternative spelling
            "Καρα": "Kara",  # Black/Dark
            "Μαστρο": "Mastro",  # Master
            "Κυρ": "Kyr",  # Lord/Sir
            "Γερο": "Gero",  # Elder
            "Μακρο": "Makro",  # Long/Tall
            "Μικρο": "Mikro",  # Small/Little
        }

        # Romanisation of prefixes (various standards)
        self.romanised_prefixes = {
            # Chatzi- variants (rule #19)
            "Chatzi",
            "Hatzi",
            "Chatzi-",
            "Hatzi-",
            "Hadji",
            "Haji",
            # Papa- variants
            "Papa",
            "Papas",
            "Papa-",
            # Others
            "Kara",
            "Kara-",
            "Mastro",
            "Mastro-",
            "Kyria",
            "Kyr",
            "Gero",
            "Makro",
            "Mikro",
        }

        # Common Greek surnames (for pattern detection)
        self.common_greek_surnames = {
            # Most common
            "Παπαδόπουλος",
            "Papadopoulos",
            "Παπαδοπούλου",
            "Παναγιωτόπουλος",
            "Panagiotopoulos",
            "Γιαννόπουλος",
            "Giannopoulos",
            "Yannopoulos",
            "Νικολάου",
            "Nicolaou",
            "Nikolaou",
            "Κωνσταντίνου",
            "Constantinou",
            "Konstantinou",
            # Cypriot common
            "Χριστοδούλου",
            "Christodoulou",
            "Γεωργίου",
            "Georgiou",
            "Μιχαήλ",
            "Michael",
            "Michail",
            # With prefixes
            "Χατζηδάκης",
            "Hadjidakis",
            "Chatzidakis",
            "Παπαγεωργίου",
            "Papageorgiou",
        }

        # Genitive endings (common in surnames)
        self.genitive_endings = {
            # Male genitive
            "-ου",
            "-όπουλος",
            "-άκης",
            "-ίδης",
            "-άδης",
            # Female forms
            "-ού",
            "-οπούλου",
            "-άκη",
            "-ίδου",
            "-άδου",
        }

        # Ancient Greek indicators (for rule #25)
        self.ancient_indicators = {
            # Names
            "Αριστοτέλης",
            "Aristotle",
            "Πλάτων",
            "Plato",
            "Σωκράτης",
            "Socrates",
            "Ευκλείδης",
            "Euclid",
            "Αρχιμήδης",
            "Archimedes",
            "Πυθαγόρας",
            "Pythagoras",
            # Patterns
            "-κλής",
            "-kles",
            "-μένης",
            "-menes",
            "-φάνης",
            "-phanes",
            "-γένης",
            "-genes",
        }

        # Titles to remove
        self.titles = {
            # Greek
            "Κύριος",
            "Κυρία",
            "Δρ",
            "Δρ.",
            "Καθ",
            "Καθ.",
            # English (common in Cyprus)
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Professor",
            # Academic
            "Καθηγητής",
            "Καθηγήτρια",
            "Δόκτωρ",
        }

    def is_applicable(self, entry: Dict[str, Any]) -> bool:
        """Check if this processor should handle the entry."""
        # Check for region hint first
        detected_region = entry.get("DetectedRegion", "")
        if detected_region == "B3":
            return True

        # Check canonical forms for Greek script
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")

        # Check if text contains Greek script
        for canonical in [canonical_native, canonical_latin]:
            if canonical and self._is_likely_greek_name(canonical):
                return True

        return False

    def _is_likely_greek_name(self, name: str) -> bool:
        """Check if name is likely from Greek region."""
        if not name:
            return False

        # Check for Greek script characters
        if self._has_greek_script(name):
            return True

        # Check for romanised Greek patterns
        # 1. Greek prefixes
        for prefix in self.romanised_prefixes:
            if name.lower().startswith(prefix.lower()):
                return True

        # 2. Greek surnames (common patterns)
        name_lower = name.lower()
        greek_patterns = ["poulos", "opoulos", "akis", "idis", "iadis", "ou"]
        if any(pattern in name_lower for pattern in greek_patterns):
            return True

        # 3. Known Greek names
        if name in self.common_greek_surnames:
            return True

        # 4. Greek-style family/given format with Greek endings
        if "," in name:
            family = name.split(",")[0].strip().lower()
            # Check for typical Greek family name endings
            if any(family.endswith(ending) for ending in ["os", "is", "as", "ou"]):
                return True

        return False

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to B3 rules."""
        # Clean canonical forms
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])

        # Clean variants
        if "Variants" in entry:
            if "Observed" in entry["Variants"]:
                for variant in entry["Variants"]["Observed"]:
                    if "str" in variant:
                        variant["str"] = self._clean_name(variant["str"])

    def _clean_name(self, name: str) -> str:
        """Clean a single name string."""
        # Input validation - ensure it's a string
        if not isinstance(name, str):
            raise RegionRuleError(f"Name must be string, not {type(name).__name__}")

        if not name:
            return name

        # Security: filter out dangerous control characters (except safe whitespace)
        if any(ord(c) < 32 and c not in "\t\n\r " for c in name):
            raise RegionRuleError("Name contains dangerous control characters")

        # Remove titles
        name = self._remove_titles(name)

        # Normalize final sigma (σ at end of word → ς)
        name = self._normalize_final_sigma(name)

        # Normalize whitespace
        name = " ".join(name.split())

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        # Handle hyphenation in prefixes consistently
        name = self._normalize_prefix_hyphens(name)

        return name.strip()

    def _normalize_final_sigma(self, text: str) -> str:
        """Ensure σ at end of words becomes ς."""
        # Only for Greek script portions
        if not any(c in self.greek_chars for c in text):
            return text

        # Replace σ with ς at word boundaries
        text = re.sub(r"σ\b", "ς", text)

        return text

    def _normalize_prefix_hyphens(self, text: str) -> str:
        """Normalize hyphenation in prefixes (Chatzi- vs Chatzi)."""
        # For romanised text
        for prefix in ["Chatzi", "Hatzi", "Papa", "Kara", "Mastro"]:
            # Ensure consistent hyphenation
            text = re.sub(f"{prefix}\\s+", f"{prefix}-", text)
            text = re.sub(f"{prefix}(?=[A-Z])", f"{prefix}-", text)

        # For Greek text
        for gr_prefix in ["Χατζη", "Χατζι", "Παπα", "Καρα", "Μαστρο"]:
            text = re.sub(f"{gr_prefix}\\s+", f"{gr_prefix}", text)

        return text

    def _remove_titles(self, text: str) -> str:
        """Remove titles from beginning of name."""
        if not text:
            return text

        words = text.split()

        # Remove titles from beginning
        while words and words[0] in self.titles:
            words.pop(0)

        return " ".join(words)

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with B3-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")

        if not canonical and not native:
            return

        # Detect script
        has_greek = self._has_greek_script(native) if native else False

        # Extract components
        components = self._extract_components(canonical, native)

        # Add script info
        components["has_greek_script"] = has_greek
        components["script"] = "Greek" if has_greek else "Latin"

        # Rule 25: Greek Ancient Names – Latinised canonical; excluded from modern collisions
        if self._is_ancient_greek(canonical, native):
            components["is_ancient"] = True
            entry["NameType"] = "ancient"

            # Ensure Latinised canonical form (Rule 25 requirement)
            if native and self._has_greek_script(native):
                # If we have Greek native form, ensure canonical is Latinised
                latinised = self._get_latinised_ancient_form(native, canonical)
                if latinised:
                    entry["CanonicalLatin"] = latinised
                    components["latinised_canonical"] = latinised

            # Mark for collision exclusion (Rule 25 requirement)
            components["excluded_from_modern_collisions"] = True
            entry["RegionalExtras"]["ancient_greek_rule_25"] = True

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate synthesized variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Add Chatzi/Hatzi variants (rule #19)
        if components.get("has_chatzi_prefix"):
            chatzi_variants = self._generate_chatzi_variants(canonical)
            for variant in chatzi_variants:
                if variant != canonical:
                    entry["Variants"]["Synthesised"].append(
                        {"str": variant, "type": "chatzi-variant"}
                    )

        # Add transliteration variants if Greek script
        if has_greek and native:
            # ELOT 743 transliteration
            elot_variant = self._transliterate_elot743(native)
            if elot_variant and elot_variant != canonical:
                entry["Variants"]["Synthesised"].append({"str": elot_variant, "type": "elot-743"})

            # ISO 843 transliteration
            iso_variant = self._transliterate_iso843(native)
            if iso_variant and iso_variant != canonical and iso_variant != elot_variant:
                entry["Variants"]["Synthesised"].append({"str": iso_variant, "type": "iso-843"})

        # Add genitive variants if applicable
        if components.get("has_genitive"):
            nominative = self._generate_nominative_variant(canonical)
            if nominative and nominative != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": nominative, "type": "nominative-form"}
                )

    def _has_greek_script(self, text: str) -> bool:
        """Check if text contains Greek script."""
        return any(c in self.allowed_greek_chars for c in text)

    def _is_ancient_greek(self, latin: str, greek: str) -> bool:
        """Detect if name is ancient Greek (rule #25)."""
        # Check against known ancient names
        for indicator in self.ancient_indicators:
            if indicator in latin or indicator in greek:
                return True

        # Check for ancient patterns (simplified)
        ancient_patterns = [
            "-kles",
            "-menes",
            "-phanes",
            "-genes",
            "-κλής",
            "-μένης",
            "-φάνης",
            "-γένης",
        ]

        for pattern in ancient_patterns:
            if pattern in latin.lower() or pattern in greek:
                return True

        # Check if explicitly marked or in historical context
        # (would need additional metadata in real implementation)

        return False

    def _get_latinised_ancient_form(self, greek_native: str, current_latin: str) -> Optional[str]:
        """
        Rule 25: Get Latinised canonical form for ancient Greek names.

        Ancient Greek names should use traditional Latinised forms (e.g., "Aristotle"
        not "Aristoteles"), as these are the established scholarly conventions.
        """
        # Standard Latinised forms of ancient Greek names
        ancient_latinised_forms = {
            # Philosophers
            "Αριστοτέλης": "Aristotle",
            "Πλάτων": "Plato",
            "Σωκράτης": "Socrates",
            "Επίκουρος": "Epicurus",
            "Διογένης": "Diogenes",
            "Ηράκλειτος": "Heraclitus",
            "Παρμενίδης": "Parmenides",
            "Δημόκριτος": "Democritus",
            # Mathematicians/Scientists
            "Ευκλείδης": "Euclid",
            "Αρχιμήδης": "Archimedes",
            "Πυθαγόρας": "Pythagoras",
            "Θαλής": "Thales",
            "Ανάξιμανδρος": "Anaximander",
            "Ερατοσθένης": "Eratosthenes",
            "Απολλώνιος": "Apollonius",
            "Ιππάρχος": "Hipparchus",
            # Historians
            "Ηρόδοτος": "Herodotus",
            "Θουκυδίδης": "Thucydides",
            "Ξενοφών": "Xenophon",
            "Πλούταρχος": "Plutarch",
            # Poets/Dramatists
            "Όμηρος": "Homer",
            "Ησίοδος": "Hesiod",
            "Αισχύλος": "Aeschylus",
            "Σοφοκλής": "Sophocles",
            "Ευριπίδης": "Euripides",
            "Αριστοφάνης": "Aristophanes",
            "Πίνδαρος": "Pindar",
            # Other notables
            "Αλέξανδρος": "Alexander",
            "Περικλής": "Pericles",
            "Δημοσθένης": "Demosthenes",
            "Λυκούργος": "Lycurgus",
        }

        # Check if the Greek name matches a known ancient form
        for greek_form, latin_form in ancient_latinised_forms.items():
            if greek_form in greek_native:
                return latin_form

        # If we already have a good Latin form, use it
        if current_latin and not self._has_greek_script(current_latin):
            return current_latin

        # Fallback to ELOT 743 transliteration but apply ancient conventions
        transliterated = self._transliterate_elot743(greek_native)

        # Apply ancient naming conventions
        ancient_conventions = {
            # Common ancient name endings
            "kles": "cles",  # -κλής → -cles (e.g., Pericles)
            "genes": "genes",  # -γένης → -genes
            "menes": "menes",  # -μένης → -menes
            "phanes": "phanes",  # -φάνης → -phanes
            # Common transformations
            "os": "us",  # Greek -ος → Latin -us (sometimes)
        }

        result = transliterated
        for greek_ending, latin_ending in ancient_conventions.items():
            if result.lower().endswith(greek_ending):
                result = result[: -len(greek_ending)] + latin_ending
                break

        return result.title()  # Proper case

    def _extract_components(self, latin: str, greek: str) -> Dict[str, Any]:
        """Extract name components with Greek-specific handling."""
        components = {}

        # Use Latin version for parsing (more reliable)
        name = latin if latin else greek

        # Check for Chatzi- prefix (rule #19)
        has_chatzi = False
        chatzi_variant = None

        for prefix in ["Chatzi", "Hatzi", "Hadji", "Haji", "Χατζη", "Χατζι"]:
            if name.startswith(prefix):
                has_chatzi = True
                chatzi_variant = prefix
                break

        if has_chatzi:
            components["has_chatzi_prefix"] = True
            components["chatzi_variant"] = chatzi_variant

        # Check for other prefixes
        prefix_found = None
        for gr_prefix, lat_prefix in self.greek_prefixes.items():
            if greek and greek.startswith(gr_prefix):
                prefix_found = gr_prefix
                break
            if latin and latin.startswith(lat_prefix):
                prefix_found = lat_prefix
                break

        if prefix_found:
            components["has_prefix"] = True
            components["prefix"] = prefix_found

        # Parse structure
        if "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        else:
            words = name.split()
            if len(words) >= 2:
                # Assume Given Family for modern Greek
                given = " ".join(words[:-1])
                family = words[-1]
            else:
                given = ""
                family = name

        components["family_name"] = family
        components["given_name"] = given

        # Check for genitive endings
        for ending in self.genitive_endings:
            if family.endswith(ending.replace("-", "")):
                components["has_genitive"] = True
                components["genitive_ending"] = ending
                break

        # Detect Cypriot patterns (often end in -ου)
        if family.endswith("ου") or family.endswith("ou"):
            components["likely_cypriot"] = True

        return components

    def _generate_chatzi_variants(self, name: str) -> List[str]:
        """Generate Chatzi/Hatzi variants (rule #19)."""
        variants = []

        # Common Chatzi- variations
        chatzi_forms = ["Chatzi", "Hatzi", "Hadji", "Haji", "Chatzi-", "Hatzi-"]

        for form1 in chatzi_forms:
            if name.startswith(form1):
                # Generate variants with other forms
                for form2 in chatzi_forms:
                    if form1 != form2:
                        variant = name.replace(form1, form2, 1)
                        if variant not in variants:
                            variants.append(variant)
                break

        return variants

    def _transliterate_elot743(self, greek_text: str) -> str:
        """Transliterate Greek to Latin using ELOT 743 standard."""
        # Simplified ELOT 743 mapping
        elot_map = {
            "Α": "A",
            "α": "a",
            "Ά": "A",
            "ά": "a",
            "Β": "V",
            "β": "v",
            "Γ": "G",
            "γ": "g",
            "Δ": "D",
            "δ": "d",
            "Ε": "E",
            "ε": "e",
            "Έ": "E",
            "έ": "e",
            "Ζ": "Z",
            "ζ": "z",
            "Η": "I",
            "η": "i",
            "Ή": "I",
            "ή": "i",
            "Θ": "Th",
            "θ": "th",
            "Ι": "I",
            "ι": "i",
            "Ί": "I",
            "ί": "i",
            "Κ": "K",
            "κ": "k",
            "Λ": "L",
            "λ": "l",
            "Μ": "M",
            "μ": "m",
            "Ν": "N",
            "ν": "n",
            "Ξ": "X",
            "ξ": "x",
            "Ο": "O",
            "ο": "o",
            "Ό": "O",
            "ό": "o",
            "Π": "P",
            "π": "p",
            "Ρ": "R",
            "ρ": "r",
            "Σ": "S",
            "σ": "s",
            "ς": "s",
            "Τ": "T",
            "τ": "t",
            "Υ": "Y",
            "υ": "y",
            "Ύ": "Y",
            "ύ": "y",
            "Φ": "F",
            "φ": "f",
            "Χ": "Ch",
            "χ": "ch",
            "Ψ": "Ps",
            "ψ": "ps",
            "Ω": "O",
            "ω": "o",
            "Ώ": "O",
            "ώ": "o",
        }

        result = ""
        i = 0
        while i < len(greek_text):
            char = greek_text[i]

            # Handle digraphs
            if i < len(greek_text) - 1:
                digraph = greek_text[i : i + 2]
                # Check for specific combinations
                if digraph in ["Μπ", "μπ"]:
                    result += "B" if digraph[0].isupper() else "b"
                    i += 2
                    continue
                elif digraph in ["Ντ", "ντ"]:
                    result += "D" if digraph[0].isupper() else "d"
                    i += 2
                    continue
                elif digraph in ["Γγ", "γγ"]:
                    result += "Ng" if digraph[0].isupper() else "ng"
                    i += 2
                    continue
                elif digraph in ["Γκ", "γκ"]:
                    result += "G" if digraph[0].isupper() else "g"
                    i += 2
                    continue

            # Single character mapping
            if char in elot_map:
                result += elot_map[char]
            else:
                result += char

            i += 1

        return result

    def _transliterate_iso843(self, greek_text: str) -> str:
        """Transliterate Greek to Latin using ISO 843 standard."""
        # ISO 843 is similar to ELOT but with some differences
        # This is a simplified version
        iso_map = {
            "Α": "A",
            "α": "a",
            "Ά": "Á",
            "ά": "á",
            "Β": "V",
            "β": "v",
            "Γ": "G",
            "γ": "g",
            "Δ": "D",
            "δ": "d",
            "Ε": "E",
            "ε": "e",
            "Έ": "É",
            "έ": "é",
            "Ζ": "Z",
            "ζ": "z",
            "Η": "Ī",
            "η": "ī",
            "Ή": "Ī́",
            "ή": "ī́",
            "Θ": "Th",
            "θ": "th",
            "Ι": "I",
            "ι": "i",
            "Ί": "Í",
            "ί": "í",
            "Κ": "K",
            "κ": "k",
            "Λ": "L",
            "λ": "l",
            "Μ": "M",
            "μ": "m",
            "Ν": "N",
            "ν": "n",
            "Ξ": "X",
            "ξ": "x",
            "Ο": "O",
            "ο": "o",
            "Ό": "Ó",
            "ό": "ó",
            "Π": "P",
            "π": "p",
            "Ρ": "R",
            "ρ": "r",
            "Σ": "S",
            "σ": "s",
            "ς": "s",
            "Τ": "T",
            "τ": "t",
            "Υ": "Y",
            "υ": "y",
            "Ύ": "Ý",
            "ύ": "ý",
            "Φ": "F",
            "φ": "f",
            "Χ": "Ch",
            "χ": "ch",
            "Ψ": "Ps",
            "ψ": "ps",
            "Ω": "Ō",
            "ω": "ō",
            "Ώ": "Ṓ",
            "ώ": "ṓ",
        }

        # Similar logic to ELOT but with ISO differences
        result = self._transliterate_elot743(greek_text)

        # Apply ISO-specific diacritic handling
        # (simplified - full implementation would be more complex)

        return result

    def _generate_nominative_variant(self, name: str) -> Optional[str]:
        """Generate nominative form from genitive."""
        # Simplified - only handle common cases

        # Common genitive → nominative transformations
        transformations = {
            "όπουλος": "όπουλος",  # Already nominative
            "οπούλου": "όπουλος",  # Female → male nominative
            "ίδης": "ίδης",  # Already nominative
            "ίδου": "ίδης",  # Female → male nominative
            "άκης": "άκης",  # Already nominative
            "άκη": "άκης",  # Female → male nominative
            # Cypriot/genitive
            "ου": "ος",  # -ου → -ος
            "iou": "ios",  # Romanised version
        }

        for gen_ending, nom_ending in transformations.items():
            if name.endswith(gen_ending):
                return name[: -len(gen_ending)] + nom_ending

        return None

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to B3 rules."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")

        if not canonical and not native:
            raise RegionRuleError("Missing both CanonicalLatin and CanonicalNative")

        # Check script consistency
        if native and self._has_greek_script(native):
            # Native should be in Greek script
            if not all(c in self.allowed_greek_chars or c in " ,.-" for c in native):
                invalid_chars = set(native) - self.allowed_greek_chars - set(" ,.-")
                raise RegionRuleError(f"Invalid characters in Greek native form: {invalid_chars}")

        if canonical:
            # Canonical Latin should not have Greek characters
            if any(c in self.greek_chars for c in canonical):
                raise RegionRuleError("Greek characters found in CanonicalLatin")

            # Should be valid Latin romanisation
            allowed_latin = self.latin_chars | set(" ,.-'0123456789")
            if not all(c in allowed_latin for c in canonical):
                invalid_chars = set(canonical) - allowed_latin
                raise RegionRuleError(f"Invalid characters in Latin form: {invalid_chars}")

        # Validate structure
        if canonical and "," in canonical:
            parts = canonical.split(",")
            if len(parts) != 2:
                raise RegionRuleError(f"Invalid comma usage: {canonical}")
            if not parts[0].strip() or not parts[1].strip():
                raise RegionRuleError(f"Empty name component: {canonical}")

        # Check ancient Greek marking
        extras = entry.get("RegionalExtras", {})
        if extras.get("is_ancient") and entry.get("NameType") != "ancient":
            raise RegionRuleError("Ancient Greek name not properly marked")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Use family, given order
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        if family:
            sort_key = f"{family}, {given}".strip(", ")
        else:
            # Fallback to canonical
            sort_key = entry.get("CanonicalLatin", "")
            if not sort_key:
                sort_key = entry.get("CanonicalNative", "")

        # Remove prefixes for sorting (optional - depends on convention)
        # For now, keep prefixes as they're often integral

        # Normalize for sorting
        sort_key = self._normalize_for_sorting(sort_key)

        # Convert to uppercase
        sort_key = sort_key.upper()

        # Normalize whitespace
        sort_key = " ".join(sort_key.split())

        return sort_key

    def _normalize_for_sorting(self, text: str) -> str:
        """Normalize text for sorting."""
        # Remove diacritics for sorting
        replacements = {
            "Ά": "Α",
            "ά": "α",
            "Έ": "Ε",
            "έ": "ε",
            "Ή": "Η",
            "ή": "η",
            "Ί": "Ι",
            "ί": "ι",
            "Ό": "Ο",
            "ό": "ο",
            "Ύ": "Υ",
            "ύ": "υ",
            "Ώ": "Ω",
            "ώ": "ω",
            # Latin diacritics
            "Á": "A",
            "á": "a",
            "É": "E",
            "é": "e",
            "Í": "I",
            "í": "i",
            "Ó": "O",
            "ó": "o",
            "Ú": "U",
            "ú": "u",
            "Ý": "Y",
            "ý": "y",
            "Ī": "I",
            "ī": "i",
            "Ō": "O",
            "ō": "o",
        }

        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        return result
