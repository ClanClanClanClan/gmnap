"""
Horn of Africa (F3) regional processor.

Implements Ethiopian and Eritrean naming patterns with Ethiopic script support.
Features: Patronymic system (no family surnames), Ge'ez/Ethiopic script,
multiple ethnic groups (Amhara, Tigray, Oromo, Afar, Somali), religious titles.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class F3_HornOfAfrica(RegionSpec):
    """Handler for F3 - Horn of Africa (Ethiopia, Eritrea)."""

    def __init__(self):
        super().__init__(
            code="F3",
            yaml_files=["f3_horn_of_africa.yaml"],
            scripts=["Ethiopic", "Latin"],
            mixed_scripts=True,
            # "Patronymic" matches the V7 spec's Literal[…] type for
            # Horn-of-Africa naming (Given Father Grandfather is the
            # specific shape; Patronymic is the family). Round-27
            # caught the test_processor_initialization assertion
            # expecting "Patronymic".
            canonical_order="Patronymic",
            romanisation_standards=["BGN/PCGN", "ALA-LC"],
        )

        # Ethiopic script ranges
        self.ethiopic_base = (0x1200, 0x137F)  # Basic Ethiopic
        self.ethiopic_supplement = (0x1380, 0x139F)  # Supplement
        self.ethiopic_extended = (0x2D80, 0x2DDF)  # Extended
        self.ethiopic_extended_a = (0xAB00, 0xAB2F)  # Extended-A

        # Titles and honorifics
        self.titles = {
            # Religious titles
            "abba",
            "aba",
            "abune",
            "qesis",
            "qes",
            "memhir",
            "diakon",
            "abbot",
            "bishop",
            "patriarch",
            "deacon",
            # Traditional titles
            "ato",
            "atto",
            "woizero",
            "woizerit",
            "woizrit",
            "emebeit",
            "ras",
            "dejazmach",
            "fitawrari",
            "grazmach",
            "kegnazmach",
            "balambaras",
            "lij",
            "negus",
            "nigus",
            # Academic
            "dr",
            "dr.",
            "doctor",
            "prof",
            "prof.",
            "professor",
            "engineer",
            "ing",
            "phd",
            "md",
            # Modern
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "ms",
            "ms.",
            "miss",
        }

        # Common Amharic given names
        self.amharic_names = {
            # Male
            "gebre",
            "tekle",
            "haile",
            "mulugeta",
            "mekonen",
            "tadesse",
            "abebe",
            "bekele",
            "getachew",
            "kebede",
            "tesfaye",
            "alemayehu",
            "yohannes",
            "dawit",
            "solomon",
            "abraham",
            "michael",
            "gabriel",
            # Female
            "marta",
            "selamawit",
            "tigist",
            "almaz",
            "meseret",
            "hirut",
            "bezawit",
            "azeb",
            "meron",
            "eden",
            "rahel",
            "sara",
            "hanna",
            "selam",
            "tsehay",
            "worknesh",
            "alem",
            "tsehaynesh",
        }

        # Tigrinya names (common in Tigray/Eritrea)
        self.tigrinya_names = {
            "amanuel",
            "berhe",
            "gebru",
            "hagos",
            "mehari",
            "yemane",
            "tsegay",
            "tesfay",
            "afewerki",
            "ghebremedhin",
            "kahsay",
            "senay",
            "semere",
            "tewolde",
            "zerai",
            "fesseha",
            "araya",
        }

        # Oromo names
        self.oromo_names = {
            "abdi",
            "adugna",
            "benti",
            "chala",
            "daba",
            "dechasa",
            "dejene",
            "dereje",
            "fikadu",
            "gadisa",
            "gemechu",
            "girma",
            "gutema",
            "jaleta",
            "kebede",
            "lemma",
            "tolera",
            "tolesa",
        }

        # Name components often indicating ethnicity
        self.ethnic_markers = {
            "amhara": ["haile", "gebre", "tekle", "selassie", "mariam"],
            "tigray": ["berhe", "gebru", "hagos", "aregawi", "gebremedhin"],
            "oromo": ["benti", "gutema", "gadisa", "tolera", "jaleta"],
            "afar": ["ahmed", "mohammed", "ali", "omar", "ibrahim"],
            "somali": ["abdi", "hassan", "mohamed", "farah", "jama"],
        }

        # Religious name elements
        self.religious_elements = {
            # Christian (Orthodox)
            "gebre": "servant of",
            "haile": "power of",
            "tekle": "plant of",
            "selassie": "trinity",
            "mariam": "mary",
            "giorgis": "george",
            "michael": "michael",
            "gabriel": "gabriel",
            # Islamic
            "abd": "servant of",
            "mohammed": "mohammed",
            "ahmed": "ahmed",
            "ali": "ali",
            "hassan": "hassan",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Apply V7 security validation and graceful edge case handling."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        # SECURITY: Check raw input for dangerous characters FIRST
        # Check both CanonicalLatin and CanonicalNative before any processing
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                raw_input = entry[field]
                # Normalize tabs/newlines BEFORE security check (V7 edge case)

                raw_input = raw_input.replace("\t", " ").replace("\n", " ")

                entry[field] = raw_input  # Update the entry with normalized value

                if self._has_security_risks(raw_input):
                    raise RegionRuleError(
                        f"Name contains dangerous characters: {raw_input[:50]}..."
                    )

        # More flexible: try to get any available name
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

        # Apply region-specific cleaning rules.
        # CanonicalLatin: strip titles (Dr., Professor, Ato, …) using
        # the existing _remove_titles helper.
        # CanonicalNative: strip Ethiopic-script titles (አባ, አቶ, …)
        # via _clean_ethiopic_name.
        if entry.get("CanonicalLatin"):
            entry["CanonicalLatin"] = self._clean_name(entry["CanonicalLatin"])
        if entry.get("CanonicalNative"):
            entry["CanonicalNative"] = self._clean_ethiopic_name(
                entry["CanonicalNative"]
            )

    def _clean_name(self, name: str) -> str:
        """Clean a single Horn of Africa name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", " ", name)  # No commas in patronymic system
        name = re.sub(r"\s*-\s*", "-", name)

        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Ethiopian/Eritrean titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            word_lower = word.lower().rstrip(".,")
            if word_lower not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with F3-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Detect scripts
        script_info = self._detect_scripts(entry)
        if script_info:
            components.update(script_info)

        # Analyze patronymic structure
        patronymic_info = self._analyze_patronymic(canonical)
        if patronymic_info:
            components.update(patronymic_info)

        # Detect ethnicity
        ethnicity = self._detect_ethnicity(canonical)
        if ethnicity:
            components["probable_ethnicity"] = ethnicity

        # Detect religious elements
        religious_info = self._detect_religious_elements(canonical)
        if religious_info:
            components.update(religious_info)

        # Detect country (Ethiopia vs Eritrea)
        country = self._detect_country(entry, components)
        if country:
            components["specific_country"] = country

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Round-27: also populate the structured keys F3 tests expect.
        # The processor's existing flat keys (`specific_country`,
        # `probable_ethnicity`, `has_patronymic`+`given_name`+…) are
        # kept for back-compat with any existing consumer; the
        # test-expected keys are added in parallel.
        entry["RegionalExtras"]["likely_country"] = self._determine_country(
            entry, components
        )
        entry["RegionalExtras"]["ethnic_background"] = self._analyze_ethnic_background(
            entry
        )
        entry["RegionalExtras"]["patronymic_structure"] = (
            self._analyze_patronymic_structure(entry)
        )

        # Synthesised variant generation (test-expected categories)
        ethnic = entry["RegionalExtras"]["ethnic_background"]
        patronymic = entry["RegionalExtras"]["patronymic_structure"]
        round27_variants = self._generate_variants(entry, ethnic, patronymic)
        # The existing Variants dict has `{Observed: [], Synthesised: []}`
        # shape; tests for the new variant types check the top-level
        # ``Variants`` key. Expose them at top level too.
        if isinstance(entry.get("Variants"), dict):
            existing = entry["Variants"].setdefault("Synthesised", [])
            for v in round27_variants:
                if v not in existing:
                    existing.append(v)
        else:
            entry["Variants"] = round27_variants

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate patronymic order variants
        patronymic_variants = self._generate_patronymic_variants(canonical, components)
        for variant in patronymic_variants:
            if variant != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": variant, "type": "patronymic-order"}
                )

        # Generate transliteration variants if Ethiopic
        if script_info.get("ethiopic_script_detected"):
            translit_variants = self._generate_transliteration_variants(entry)
            for variant in translit_variants:
                if variant not in [canonical, entry.get("CanonicalNative", "")]:
                    entry["Variants"]["Synthesised"].append(
                        {"str": variant, "type": "ethiopic-transliteration"}
                    )

    def _detect_scripts(self, entry: Dict[str, Any]) -> Dict[str, bool]:
        """Detect which scripts are used in the entry."""
        script_info = {}

        # Check CanonicalNative for Ethiopic script
        native = entry.get("CanonicalNative", "")
        if native:
            has_ethiopic = any(
                ord(c) in range(self.ethiopic_base[0], self.ethiopic_base[1] + 1)
                or ord(c)
                in range(self.ethiopic_supplement[0], self.ethiopic_supplement[1] + 1)
                or ord(c)
                in range(self.ethiopic_extended[0], self.ethiopic_extended[1] + 1)
                or ord(c)
                in range(self.ethiopic_extended_a[0], self.ethiopic_extended_a[1] + 1)
                for c in native
            )

            if has_ethiopic:
                script_info["ethiopic_script_detected"] = True

                # Detect specific Ethiopic script variant
                if any(ord(c) in range(0x1380, 0x139F) for c in native):
                    script_info["ethiopic_supplement_used"] = True
                if any(ord(c) in range(0x2D80, 0x2DDF) for c in native):
                    script_info["ethiopic_extended_used"] = True

        return script_info

    def _analyze_patronymic(self, name: str) -> Dict[str, Any]:
        """Analyze patronymic naming structure."""
        info = {}

        parts = name.split()
        if len(parts) >= 2:
            info["has_patronymic"] = True
            info["given_name"] = parts[0]
            info["father_name"] = parts[1]

            if len(parts) >= 3:
                info["grandfather_name"] = parts[2]
                info["full_patronymic"] = True
            else:
                info["full_patronymic"] = False

            if len(parts) > 3:
                # Sometimes great-grandfather or additional names
                info["extended_patronymic"] = True
                info["additional_names"] = parts[3:]
        else:
            # Single name only
            info["has_patronymic"] = False
            info["single_name"] = True

        return info

    def _analyze_patronymic_structure(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Entry-level analysis of Horn-of-Africa patronymic structure.

        Public-shape companion to ``_analyze_patronymic`` (which takes a
        bare string and returns the parse). This one takes an entry
        dict — pulling ``CanonicalLatin`` — and returns a categorical
        ``structure`` field plus the per-token breakdown. Used by
        downstream tests and any caller that wants the structural
        category without re-implementing token-counting.

        ``structure`` values:

          - ``"mononym"`` — single token (e.g., "Selassie")
          - ``"given_father"`` — two tokens (Given Father's-Given)
          - ``"given_father_grandfather"`` — three tokens, the
            canonical Horn-of-Africa pattern (Rule 30 / V7 §F3)
          - ``"extended_patronymic"`` — four+ tokens, including
            great-grandfather or composite religious / regional names

        Round-22 noted this method as called-but-not-defined; the
        F3 test file's 7+ ambient failures all stem from this.
        Round-27 fix implements it using the same token-counting as
        ``_analyze_patronymic`` but returning the entry-shape result
        the tests expect.
        """
        canonical = (entry.get("CanonicalLatin") or "").strip()
        if not canonical:
            return {"structure": "empty", "tokens": []}

        tokens = canonical.split()
        result: Dict[str, Any] = {"tokens": tokens}

        if len(tokens) == 1:
            result["structure"] = "mononym"
            result["given_name"] = tokens[0]
        elif len(tokens) == 2:
            result["structure"] = "given_father"
            result["given_name"] = tokens[0]
            result["father_name"] = tokens[1]
        elif len(tokens) == 3:
            result["structure"] = "given_father_grandfather"
            result["given_name"] = tokens[0]
            result["father_name"] = tokens[1]
            result["grandfather_name"] = tokens[2]
        else:
            result["structure"] = "extended_patronymic"
            result["given_name"] = tokens[0]
            result["father_name"] = tokens[1]
            result["grandfather_name"] = tokens[2]
            result["additional_names"] = tokens[3:]

        return result

    def _detect_ethnicity(self, name: str) -> Optional[str]:
        """Detect probable ethnicity from name patterns."""
        name_lower = name.lower()
        name_parts = name_lower.split()

        # Count ethnic markers
        ethnic_scores = {}

        for ethnicity, markers in self.ethnic_markers.items():
            score = 0
            for marker in markers:
                for part in name_parts:
                    if marker in part:
                        score += 1
            if score > 0:
                ethnic_scores[ethnicity] = score

        # Check specific name lists
        for part in name_parts:
            if part in self.amharic_names:
                ethnic_scores["amhara"] = ethnic_scores.get("amhara", 0) + 2
            if part in self.tigrinya_names:
                ethnic_scores["tigray"] = ethnic_scores.get("tigray", 0) + 2
            if part in self.oromo_names:
                ethnic_scores["oromo"] = ethnic_scores.get("oromo", 0) + 2

        # Return highest scoring ethnicity
        if ethnic_scores:
            return max(ethnic_scores.items(), key=lambda x: x[1])[0]

        return None

    def _detect_religious_elements(self, name: str) -> Dict[str, Any]:
        """Detect religious elements in names."""
        info = {}
        name_lower = name.lower()

        christian_elements = 0
        islamic_elements = 0

        for element, meaning in self.religious_elements.items():
            if element in name_lower:
                if element in [
                    "gebre",
                    "haile",
                    "tekle",
                    "selassie",
                    "mariam",
                    "giorgis",
                    "michael",
                    "gabriel",
                ]:
                    christian_elements += 1
                    info["has_christian_elements"] = True
                else:
                    islamic_elements += 1
                    info["has_islamic_elements"] = True

        if christian_elements > islamic_elements:
            info["probable_religion"] = "ethiopian_orthodox"
        elif islamic_elements > christian_elements:
            info["probable_religion"] = "islam"

        return info

    def _detect_country(
        self, entry: Dict[str, Any], components: Dict[str, Any]
    ) -> Optional[str]:
        """Detect whether name is more likely Ethiopian or Eritrean."""
        # Check email/affiliation
        email = entry.get("Email", "").lower()
        affiliation = entry.get("Affiliation", "").lower()

        if ".et" in email or "ethiopia" in affiliation:
            return "ethiopia"
        if ".er" in email or "eritrea" in affiliation:
            return "eritrea"

        # Check ethnicity
        ethnicity = components.get("probable_ethnicity")
        if ethnicity == "oromo":
            return "ethiopia"  # Oromo mainly in Ethiopia
        if ethnicity == "tigray" and (
            "asmara" in affiliation or "asmera" in affiliation
        ):
            return "eritrea"

        # Default based on population
        return "ethiopia"  # Ethiopia has larger population

    def _generate_patronymic_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[str]:
        """Generate patronymic order variants."""
        variants = []

        if not components.get("has_patronymic"):
            return variants

        given = components.get("given_name", "")
        father = components.get("father_name", "")
        grandfather = components.get("grandfather_name", "")

        # Standard format: Given Father Grandfather
        if given and father:
            # Two-name format
            variants.append(f"{given} {father}")

            if grandfather:
                # Three-name format
                variants.append(f"{given} {father} {grandfather}")

                # Academic citation format (sometimes used)
                variants.append(f"{given}, {father} {grandfather}")
                variants.append(f"{given} {father[0]}. {grandfather}")

                # Sometimes grandfather-father-given (rare but occurs)
                variants.append(f"{grandfather} {father} {given}")

        return sorted(set(variants))  # Remove duplicates

    def _generate_transliteration_variants(self, entry: Dict[str, Any]) -> List[str]:
        """Generate transliteration variants for Ethiopic names."""
        variants = []

        native = entry.get("CanonicalNative", "")
        if not native:
            return variants

        # Simple transliteration rules (subset)
        translit_map = {
            # Some common Ethiopic to Latin mappings
            "ገ": "ge",
            "ብ": "b",
            "ረ": "re",
            "ማ": "ma",
            "ር": "r",
            "ያ": "ya",
            "ም": "m",
            "ተ": "te",
            "ክ": "k",
            "ለ": "le",
            "ሃ": "ha",
            "ይ": "y",
            "ሰ": "se",
            "ላ": "la",
            "ሲ": "si",
            "አ": "a",
            "በ": "be",
            "ቤ": "be",
            "ከ": "ke",
            "ደ": "de",
        }

        # Generate basic transliteration
        translit = native
        for ethiopic, latin in translit_map.items():
            translit = translit.replace(ethiopic, latin)

        if translit != native and all(ord(c) < 128 for c in translit):
            variants.append(translit)

        return variants

    def validate(self, entry: Dict[str, Any]) -> None:
        """Apply V7 security validation with DoS protection."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # No name to validate - that's OK, just skip
            return

        # SECURITY: Check for dangerous characters first
        if self._has_security_risks(canonical):
            raise RegionRuleError(
                f"Name contains dangerous characters: {canonical[:50]}..."
            )

        # Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(
                f"Name too long: {len(canonical)} characters (max 150)"
            )

        # THEN handle legitimate edge cases
        if len(canonical.strip()) == 1:
            # Single character names are edge cases but valid
            self.logger.warning(f"Single character name: {canonical}")

        # Apply region-specific validation here
        pass

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for F3 names.

        Prefers the structured RegionalExtras.patronymic_structure
        when present (post-augment), falls back to splitting
        CanonicalLatin (pre-augment / no-extras path).
        """
        # Prefer post-augment structured form
        extras = entry.get("RegionalExtras") or {}
        ps = extras.get("patronymic_structure") or {}
        ordered_parts: list[str] = []
        for key in ("given_name", "father_name", "grandfather_name"):
            value = ps.get(key)
            if value:
                ordered_parts.append(value)

        if not ordered_parts:
            # Fallback: split CanonicalLatin
            canonical = entry.get("CanonicalLatin", "")
            ordered_parts = canonical.split()

        if not ordered_parts:
            return ""

        # Normalize each part: lowercase + strip diacritics
        normalized = []
        for part in ordered_parts:
            nfd = unicodedata.normalize("NFD", part.lower())
            cleaned = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
            normalized.append(cleaned)

        return " ".join(normalized)

    # ──────────────────────────────────────────────────────────────────
    # Round-27 missing methods. Test file calls these; the processor
    # was originally written without them. Each implementation uses
    # F3's existing data structures (titles, ethiopic_base / extended,
    # ethnic_markers, religious_elements, country_indicators, etc.)
    # — no new external data needed.
    # ──────────────────────────────────────────────────────────────────

    def _contains_ethiopic(self, text: str) -> bool:
        """True if any character lies in Ge'ez (Ethiopic) Unicode blocks."""
        if not text:
            return False
        for ch in text:
            cp = ord(ch)
            if (
                self.ethiopic_base[0] <= cp <= self.ethiopic_base[1]
                or self.ethiopic_supplement[0] <= cp <= self.ethiopic_supplement[1]
                or self.ethiopic_extended[0] <= cp <= self.ethiopic_extended[1]
                or self.ethiopic_extended_a[0] <= cp <= self.ethiopic_extended_a[1]
            ):
                return True
        return False

    def _is_valid_ethiopic_text(self, text: str) -> bool:
        """True if text contains Ge'ez characters AND no Latin letters
        outside ASCII whitespace / Ethiopic punctuation."""
        if not text:
            return False
        if not self._contains_ethiopic(text):
            return False
        # Reject if contains ASCII letters (mixed-script likely an error)
        for ch in text:
            if ch.isascii() and ch.isalpha():
                return False
        return True

    def _is_valid_latin_text(self, text: str) -> bool:
        """True if text is non-empty Latin (ASCII or Latin-1 with diacritics
        but NO Ge'ez characters)."""
        if not text:
            return False
        if self._contains_ethiopic(text):
            return False
        # At least one alphabetic character expected
        return any(ch.isalpha() for ch in text)

    # Title sets cached for clean_*_name
    _ETHIOPIC_TITLE_GLYPHS = frozenset({"አባ", "አቶ", "ወይዘሮ", "ወይዘሪት"})

    def _clean_latin_name(self, name: str) -> str:
        """Strip leading titles (Dr., Professor, Ato, …) and collapse
        whitespace. Uses the existing self.titles set."""
        if not name:
            return name
        # Remove titles. Token-by-token from the left, preserving order.
        tokens = name.replace(",", " ").split()
        keep: list[str] = []
        skipping_titles = True
        for token in tokens:
            normalized = token.lower().rstrip(".")
            if skipping_titles and normalized in self.titles:
                continue
            skipping_titles = False
            keep.append(token)
        return " ".join(keep)

    def _clean_ethiopic_name(self, name: str) -> str:
        """Strip Ethiopic-script titles and normalize whitespace +
        word-separator (U+1361 ETHIOPIC WORDSPACE)."""
        if not name:
            return name
        # Collapse multiple ASCII spaces; preserve U+1361 word separators
        # but cap consecutive ones.
        text = name.strip()
        # Replace runs of whitespace with single space
        import re

        text = re.sub(r"\s+", " ", text)
        # Strip Ethiopic titles when they appear as standalone leading
        # tokens.
        for title in self._ETHIOPIC_TITLE_GLYPHS:
            if text.startswith(title + " ") or text.startswith(title + "፡"):
                text = text[len(title) :].lstrip(" ፡")
                break
        # Collapse repeated word-separator characters
        text = re.sub("፡+", "፡", text)
        return text

    def _transliterate_ethiopic(self, text: str, mapping: Dict[str, str]) -> str:
        """Apply a character → romanization mapping. Unknown characters
        pass through unchanged."""
        if not text:
            return text
        out = []
        for ch in text:
            out.append(mapping.get(ch, ch))
        return "".join(out)

    def _has_religious_elements(self, entry: Dict[str, Any]) -> bool:
        """True if the entry's CanonicalLatin contains any element from
        ``self.religious_elements`` (Christian or Islamic markers)."""
        name = (entry.get("CanonicalLatin") or "").lower()
        if not name:
            return False
        tokens = name.replace(",", " ").split()
        for tok in tokens:
            tok_clean = tok.strip(".'\"")
            if tok_clean in self.religious_elements:
                return True
        return False

    def _analyze_ethnic_background(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Score the entry against each known ethnic group's name
        markers. Returns ``{ethnicity_scores: {group: score, …},
        primary_ethnicity: <group or None>}``.

        Walks both CanonicalLatin tokens and Affiliation hints
        (university names sometimes signal a region — e.g., Addis
        Ababa University → amhara, Mekelle University → tigray).
        """
        name = (entry.get("CanonicalLatin") or "").lower()
        affiliation = (entry.get("Affiliation") or "").lower()
        tokens = name.replace(",", " ").split()

        scores: Dict[str, int] = {}
        for ethnicity, markers in self.ethnic_markers.items():
            score = sum(1 for tok in tokens for m in markers if m in tok)
            if score:
                scores[ethnicity] = score

        # Curated names lists give an extra signal
        for tok in tokens:
            if tok in self.amharic_names:
                scores["amhara"] = scores.get("amhara", 0) + 2
            if tok in self.tigrinya_names:
                scores["tigray"] = scores.get("tigray", 0) + 2

        # Affiliation hints — coarse but helpful when token signal is
        # ambiguous. Addis Ababa, Mekelle, Jimma each signal a region.
        affiliation_signals = [
            ("addis", "amhara"),
            ("mekelle", "tigray"),
            ("jimma", "oromo"),
            ("dire", "oromo"),  # Dire Dawa
            ("hawassa", "sidama"),
        ]
        for needle, ethnicity in affiliation_signals:
            if needle in affiliation:
                scores[ethnicity] = scores.get(ethnicity, 0) + 1

        primary = max(scores, key=scores.get) if scores else None
        return {"ethnicity_scores": scores, "primary_ethnicity": primary}

    def _determine_country(self, entry: Dict[str, Any], _hints: Dict[str, Any]) -> str:
        """Determine likely Horn-of-Africa country from affiliation +
        email TLD signals.

        Returns ISO-3166 alpha-2: ET (Ethiopia), ER (Eritrea), SO
        (Somalia), DJ (Djibouti). Defaults to ``"ET"`` (most populous)
        when signals are ambiguous.
        """
        affiliation = (entry.get("Affiliation") or "").lower()
        email = (entry.get("Email") or "").lower()

        # Email TLD is the strongest signal
        for tld, cc in [
            (".et", "ET"),
            (".er", "ER"),
            (".so", "SO"),
            (".dj", "DJ"),
        ]:
            if email.endswith(tld) or tld + "/" in email or tld + "?" in email:
                return cc
            # Mid-string match (for educational subdomains)
            if tld in email.split("@")[-1]:
                return cc

        # Affiliation keyword match
        for keyword, cc in [
            ("asmara", "ER"),
            ("eritrea", "ER"),
            ("addis ababa", "ET"),
            ("ethiopia", "ET"),
            ("mekelle", "ET"),
            ("jimma", "ET"),
            ("hawassa", "ET"),
            ("mogadishu", "SO"),
            ("somalia", "SO"),
            ("djibouti", "DJ"),
        ]:
            if keyword in affiliation:
                return cc

        return "ET"

    def _generate_variants(
        self,
        entry: Dict[str, Any],
        ethnic_analysis: Dict[str, Any],
        patronymic_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate alternate name variants per Horn-of-Africa naming
        conventions: Given+Father shorthand, mononym (Given only),
        academic-initial form (G.M.T. for Gebre Mariam Tekle).

        Each variant is ``{type: <category>, str: <variant>}``. The
        test asserts presence of ``patronymic_given_father``,
        ``mononym_given``, and ``academic_initial`` types.
        """
        variants: List[Dict[str, Any]] = []
        given = patronymic_analysis.get("given_name")
        father = patronymic_analysis.get("father_name")
        grandfather = patronymic_analysis.get("grandfather_name")

        if given and father:
            variants.append(
                {"type": "patronymic_given_father", "str": f"{given} {father}"}
            )

        if given:
            variants.append({"type": "mononym_given", "str": given})

        # Academic initial form: G.M.T. (initials of all parts joined)
        initials_parts = [p for p in (given, father, grandfather) if p]
        if initials_parts:
            initials = ".".join(p[0].upper() for p in initials_parts) + "."
            variants.append({"type": "academic_initial", "str": initials})

        return variants

    def _has_security_risks(self, name: str) -> bool:
        """Check for dangerous characters that pose security risks."""
        if not name:
            return False
        for char in name:
            # Reject control characters (ASCII 0-31, 127)
            if ord(char) < 32 or ord(char) == 127:
                return True
            # Reject other potentially dangerous Unicode ranges
            if ord(char) in [0xFEFF, 0x200B, 0x200C, 0x200D]:  # Zero-width characters
                return True
        return False

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components for Horn of Africa names."""
        components = {}

        # Split into parts
        parts = name.split()

        if len(parts) == 0:
            return components

        # Patronymic system
        if len(parts) >= 1:
            components["given_name"] = parts[0]

        if len(parts) >= 2:
            components["father_name"] = parts[1]
            components["patronymic_structure"] = True

        if len(parts) >= 3:
            components["grandfather_name"] = parts[2]
            components["full_patronymic"] = True

        if len(parts) > 3:
            components["additional_ancestors"] = parts[3:]
            components["extended_genealogy"] = True

        # No family name in traditional system
        components["family_name"] = None
        components["uses_patronymic_system"] = True

        return components
