"""
E7 - Maritime Southeast Asia region comprehensive implementation.

Covers: Indonesia, Malaysia, Philippines, Singapore
Features: Multi-script support (Latin, Arabic, Baybayin), colonial adaptation patterns,
         Islamic naming conventions, Chinese diaspora influences, Austronesian base languages
Scripts: Latin (primary), Arabic (Islamic names), Baybayin (historical Filipino)
Colonial Influences: Spanish, Dutch, English, Portuguese
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class E7MaritimeSEAProcessor(RegionSpec):
    """
    Maritime Southeast Asia region (E7) comprehensive processor.

    Handles naming conventions from Indonesia, Malaysia, Philippines, Singapore:
    - Indonesian/Malay naming (Bahasa Indonesia/Malaysia)
    - Filipino naming with Spanish colonial influence
    - Islamic naming patterns (patronymic systems)
    - Chinese diaspora influence (Hokkien, Teochew, Cantonese)
    - Colonial adaptations (Dutch, Spanish, English, Portuguese)
    - Multi-script support: Latin, Arabic, Baybayin
    """

    def __init__(self):
        super().__init__(
            code="E7",
            yaml_files=["e7_maritime_sea.yaml"],
            scripts=["Latin", "Arabic", "Baybayin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["EYD", "UNGEGN", "Filipino", "Jawi"],
        )

        # V7 Spec Compliance
        self.iso_territories = ["ID", "MY", "PH", "SG"]
        self.primary_scripts = ["Latin", "Arabic", "Baybayin"]
        self.distinct_features = "Diverse colonial influences; Islamic naming"

        # Arabic script Unicode ranges (for Islamic names)
        self.arabic_ranges = [
            (0x0600, 0x06FF),  # Arabic
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]

        # Baybayin Unicode ranges (historical Filipino script)
        self.baybayin_ranges = [
            (0x1700, 0x171F),  # Tagalog/Baybayin
        ]

        # Indonesian/Malay patronymic markers (Rule 28)
        self.malay_patronymics = {
            "bin": {"meaning": "son of", "gender": "male"},
            "binti": {"meaning": "daughter of", "gender": "female"},
            "bt": {"meaning": "daughter of", "gender": "female"},
            "b.": {"meaning": "child of", "gender": "ambiguous"},
            "ibn": {"meaning": "son of", "gender": "male"},  # Arabic variant
            "bint": {"meaning": "daughter of", "gender": "female"},  # Arabic variant
        }

        # Indonesian mononym indicators (Rule 14, 29)
        self.indonesian_mononym_patterns = {
            # Famous mononyms
            "suharto",
            "sukarno",
            "megawati",
            "jokowi",
            "prabowo",
            "wiranto",
            "habibie",
            "wahid",
            "susilo",
            "bambang",
            "soekarno",
            "soeharto",
            "abdurrahman",
            "kalla",
            "widodo",
            "jonan",
            "luhut",
            "rizal",
            # Javanese patterns
            "suryo",
            "wibowo",
            "sutomo",
            "kartono",
            "sumarto",
            "hartono",
            # Common endings indicating mononyms
            "harto",
            "karno",
            "wati",
            "joko",
            "bowo",
            "tanto",
            "noto",
            # Batak patterns (North Sumatra)
            "siregar",
            "situmorang",
            "hutabarat",
            "simanungkalit",
        }

        # Filipino naming patterns (Rule 30)
        self.filipino_patterns = {
            "spanish_surnames": {
                "santos",
                "cruz",
                "reyes",
                "ramos",
                "mendoza",
                "garcia",
                "rodriguez",
                "fernandez",
                "lopez",
                "gonzales",
                "hernandez",
                "perez",
                "sanchez",
                "ramirez",
                "torres",
                "flores",
                "rivera",
                "gomez",
                "diaz",
                "morales",
                "castro",
                "vargas",
                "jimenez",
                "herrera",
                "medina",
                "aguilar",
                "valencia",
                "salvador",
                "villanueva",
                "martinez",
                "francisco",
                "dela cruz",
                "delos santos",
                "de leon",
                "del rosario",
            },
            "indigenous_surnames": {
                "bagong",
                "malaya",
                "tapat",
                "mabini",
                "katipunan",
                "bayani",
                "lakas",
                "buhay",
                "puso",
                "diwa",
                "tagumpay",
                "kamatayan",
            },
            "maternal_indicators": {
                # Words that often indicate maternal lineage
                "y",
                "de",
                "del",
                "dela",
                "delos",
                "ng",
                "na",
            },
        }

        # Chinese diaspora patterns (Singapore, Malaysia)
        self.chinese_diaspora_patterns = {
            "hokkien": {
                "surnames": [
                    "tan",
                    "lim",
                    "wong",
                    "ong",
                    "teo",
                    "goh",
                    "ng",
                    "yeo",
                    "koh",
                    "sim",
                ],
                "given_patterns": [
                    "ah",
                    "beng",
                    "seng",
                    "hock",
                    "chuan",
                    "keng",
                    "huat",
                    "swee",
                ],
            },
            "teochew": {
                "surnames": [
                    "li",
                    "chen",
                    "huang",
                    "lin",
                    "zheng",
                    "xu",
                    "hong",
                    "zhuang",
                ],
                "given_patterns": [
                    "wei",
                    "ming",
                    "qiang",
                    "jun",
                    "hui",
                    "jie",
                    "bin",
                    "hao",
                ],
            },
            "cantonese": {
                "surnames": [
                    "chan",
                    "leung",
                    "cheung",
                    "li",
                    "ho",
                    "ma",
                    "yip",
                    "fung",
                ],
                "given_patterns": [
                    "wai",
                    "ming",
                    "fai",
                    "kit",
                    "chung",
                    "yuen",
                    "kin",
                    "ho",
                ],
            },
            "common_patterns": {
                "double_names": ["li li", "mei mei", "jin jin", "wei wei"],
                "generational": ["ah", "xiao", "da", "lao"],
            },
        }

        # Islamic naming patterns (Malaysia, Indonesia)
        self.islamic_patterns = {
            "arabic_names": {
                "muhammad",
                "ahmad",
                "ali",
                "hassan",
                "hussain",
                "omar",
                "abdul",
                "abdullah",
                "ibrahim",
                "ismail",
                "yusuf",
                "musa",
                "isa",
                "adam",
                "noor",
                "nur",
                "siti",
                "aishah",
                "fatimah",
                "khadijah",
                "maryam",
                "zainab",
                "aminah",
                "hafsah",
                "ruqayyah",
                "umm",
                "abu",
            },
            "malay_islamic": {
                "mohamed",
                "mohamad",
                "mohd",
                "ahmad",
                "hassan",
                "hussein",
                "halim",
                "rahman",
                "rahim",
                "karim",
                "hakim",
                "rashid",
                "said",
                "salim",
                "farid",
                "faisal",
                "amin",
                "aziz",
                "latif",
                "majid",
                "nasir",
            },
            "compound_patterns": {
                "abdul": ["rahman", "aziz", "malik", "karim", "latif", "majid"],
                "abu": ["bakar", "hassan", "said", "talib", "yusuf"],
                "siti": ["aishah", "fatimah", "khadijah", "maryam", "zainab"],
            },
        }

        # Colonial influence patterns
        self.colonial_patterns = {
            "dutch": {
                "surnames": ["van", "de", "der", "ten", "ter", "tot", "op", "aan"],
                "adaptations": {"ij": "y", "oe": "u", "ch": "k"},
            },
            "spanish": {
                "particles": ["de", "del", "dela", "delos", "y", "san", "santa"],
                "endings": ["ez", "es", "os", "as", "illo", "ito", "ita"],
            },
            "portuguese": {
                "surnames": ["dos", "das", "da", "do", "pereira", "silva", "santos"],
                "patterns": ["ão", "ões", "al", "el"],
            },
            "english": {
                "adaptations": {"ph": "f", "th": "t", "ght": "t"},
                "colonial_surnames": [
                    "smith",
                    "brown",
                    "wilson",
                    "johnson",
                    "williams",
                ],
            },
        }

        # Major cities and institutions for regional detection
        self.regional_indicators = {
            "indonesia": {
                "cities": [
                    "jakarta",
                    "surabaya",
                    "bandung",
                    "medan",
                    "semarang",
                    "makassar",
                    "palembang",
                    "tangerang",
                    "depok",
                    "bekasi",
                    "batam",
                    "denpasar",
                ],
                "universities": [
                    "ui",
                    "ugm",
                    "itb",
                    "its",
                    "unpad",
                    "undip",
                    "unair",
                    "upi",
                ],
                "institutions": ["bppt", "lipi", "batan", "lapan", "bmkg"],
            },
            "malaysia": {
                "cities": [
                    "kuala lumpur",
                    "george town",
                    "ipoh",
                    "shah alam",
                    "petaling jaya",
                    "johor bahru",
                    "malacca",
                    "kota kinabalu",
                    "kuching",
                    "seremban",
                ],
                "universities": [
                    "um",
                    "upm",
                    "ukm",
                    "usm",
                    "utm",
                    "utp",
                    "mmu",
                    "sunway",
                ],
                "institutions": ["mosti", "might", "mida", "mdec", "sirim"],
            },
            "philippines": {
                "cities": [
                    "manila",
                    "quezon city",
                    "caloocan",
                    "davao",
                    "cebu",
                    "zamboanga",
                    "taguig",
                    "antipolo",
                    "cavite",
                    "bacoor",
                    "iloilo",
                    "marikina",
                ],
                "universities": [
                    "up",
                    "ateneo",
                    "dlsu",
                    "ust",
                    "admu",
                    "mapua",
                    "feu",
                    "pup",
                ],
                "institutions": ["dost", "nast", "pnri", "itdi", "fnri"],
            },
            "singapore": {
                "cities": ["singapore", "jurong", "tampines", "woodlands", "sengkang"],
                "universities": ["nus", "ntu", "smu", "sutd", "sit", "sims"],
                "institutions": ["a*star", "dsta", "ida", "spring", "sedb"],
            },
        }

        # Common titles and honorifics
        self.titles_honorifics = {
            "malay_indonesian": {
                "dato",
                "datuk",
                "tan sri",
                "tun",
                "datuk seri",
                "dato seri",
                "haji",
                "hajjah",
                "encik",
                "puan",
                "cik",
                "tuan",
                "wan",
                "prof",
                "dr",
                "ir",
                "drs",
                "drg",
                "apt",
            },
            "filipino": {
                "don",
                "doña",
                "ginoo",
                "ginang",
                "binibini",
                "bb",
                "g",
                "atty",
                "engr",
                "arch",
                "prof",
                "dr",
                "dra",
            },
            "chinese": {
                "mr",
                "mrs",
                "ms",
                "sir",
                "madam",
                "ah",
                "uncle",
                "auntie",
                "shifu",
                "laoshi",
                "prof",
                "dr",
            },
            "islamic": {
                "imam",
                "ustaz",
                "ustazah",
                "sheikh",
                "syeikh",
                "haji",
                "hajjah",
                "sayid",
                "sayyid",
                "sharif",
                "syarif",
            },
            "colonial": {
                "mr",
                "mrs",
                "ms",
                "sir",
                "madam",
                "prof",
                "dr",
                "professor",
                "captain",
                "major",
                "colonel",
                "general",
            },
        }

        # Diacritic mappings for Malay/Indonesian
        self.malay_diacritics = {
            "â": "a",
            "ê": "e",
            "î": "i",
            "ô": "o",
            "û": "u",
            "ç": "c",
            "ñ": "ny",
            "é": "e",
            "è": "e",
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

        # Apply region-specific cleaning rules here
        # This is a stub implementation - region-specific logic should be added
        pass

    def _clean_name(self, name: str) -> str:
        """Clean and normalize Maritime SEA name."""
        if not name:
            return name

        # Remove titles and honorifics
        name = self._remove_titles_honorifics(name)

        # Normalize Unicode (important for multi-script support)
        name = unicodedata.normalize("NFC", name)

        # Handle colonial spelling variations
        name = self._normalize_colonial_variations(name)

        # Normalize whitespace and punctuation
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"\s*,\s*", ", ", name)

        # Handle common abbreviations
        name = self._expand_abbreviations(name)

        return name.strip()

    def _remove_titles_honorifics(self, text: str) -> str:
        """Remove Maritime SEA titles and honorifics from text."""
        if not text:
            return text

        # Collect all titles
        all_titles = set()
        for category in self.titles_honorifics.values():
            if isinstance(category, set):
                all_titles.update(category)
            elif isinstance(category, (list, tuple)):
                all_titles.update(category)

        words = text.split()
        cleaned = []

        i = 0
        while i < len(words):
            word = words[i]
            # Remove periods and check against titles
            clean_word = word.rstrip(".,").lower()

            # Check for compound titles (e.g., "Tan Sri", "Dato Seri")
            if i < len(words) - 1:
                compound = f"{clean_word} {words[i+1].rstrip('.,').lower()}"
                if compound in all_titles:
                    i += 2  # Skip both words
                    continue

            if clean_word not in all_titles:
                cleaned.append(word)

            i += 1

        return " ".join(cleaned)

    def _normalize_colonial_variations(self, name: str) -> str:
        """Normalize colonial spelling variations."""
        # Dutch adaptations
        for old, new in self.colonial_patterns["dutch"]["adaptations"].items():
            name = name.replace(old, new)

        # Handle Dutch particles (keep as separate words)
        dutch_particles = self.colonial_patterns["dutch"]["surnames"]
        words = name.split()
        normalized_words = []

        for word in words:
            word_lower = word.lower()
            if word_lower in dutch_particles:
                normalized_words.append(word_lower)
            else:
                normalized_words.append(word)

        return " ".join(normalized_words)

    def _expand_abbreviations(self, name: str) -> str:
        """Expand common Maritime SEA abbreviations."""
        abbreviations = {
            "mohd": "mohamed",
            "md": "mohamed",
            "m.": "mohamed",
            "siti": "siti",
            "st": "siti",
            "abd": "abdul",
            "a.": "abdul",
        }

        words = name.split()
        expanded_words = []

        for word in words:
            word_clean = word.rstrip(".,").lower()
            if word_clean in abbreviations:
                # Preserve original capitalization pattern
                if word[0].isupper():
                    expanded_words.append(abbreviations[word_clean].capitalize())
                else:
                    expanded_words.append(abbreviations[word_clean])
            else:
                expanded_words.append(word)

        return " ".join(expanded_words)

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with E7-specific data and regional rules."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract comprehensive components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Apply specific regional rules
        self._apply_regional_rules(entry, canonical, components)

        # Generate romanization variants if needed
        self._generate_romanization_variants(entry, canonical, components)

        # Generate cultural variants
        self._generate_cultural_variants(entry, canonical, components)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract comprehensive name components with multi-cultural analysis."""
        components = {}

        # Detect script and cultural background
        script_info = self._detect_script_and_culture(name)
        components.update(script_info)

        # Parse name structure based on detected culture
        name_structure = self._parse_name_structure(
            name, script_info.get("cultural_background", "unknown")
        )
        components.update(name_structure)

        # Detect specific patterns
        components.update(self._detect_specific_patterns(name))

        return components

    def _detect_script_and_culture(self, name: str) -> Dict[str, Any]:
        """Detect script and cultural background of the name."""
        script_counts = {
            "latin": sum(1 for c in name if c.isalpha() and ord(c) < 256),
            "arabic": sum(1 for c in name if self._is_arabic_char(c)),
            "baybayin": sum(1 for c in name if self._is_baybayin_char(c)),
        }

        # Determine primary script
        primary_script = max(script_counts.keys(), key=lambda x: script_counts[x])

        # Detect cultural background
        cultural_background = self._detect_cultural_background(name)

        return {
            "primary_script": primary_script,
            "script_counts": script_counts,
            "cultural_background": cultural_background,
            "is_mixed_script": sum(1 for count in script_counts.values() if count > 0)
            > 1,
        }

    def _detect_cultural_background(self, name: str) -> str:
        """Detect the cultural background based on name patterns."""
        name_lower = name.lower()

        # Check for Indonesian mononym patterns
        if self._is_indonesian_mononym(name):
            return "indonesian_mononym"

        # Check for Malay/Islamic patterns
        if self._has_malay_patronymic(name) or self._has_islamic_patterns(name_lower):
            return "malay_islamic"
            return "malay_islamic"

        # Check for Filipino patterns
        if self._has_filipino_patterns(name_lower):
            return "filipino"

        # Check for Chinese patterns
        if self._has_chinese_patterns(name_lower):
            return "chinese_diaspora"

        # Check for colonial patterns
        colonial_type = self._detect_colonial_influence(name_lower)
        if colonial_type:
            return f"colonial_{colonial_type}"

        return "mixed_maritime_sea"

    def _parse_name_structure(
        self, name: str, cultural_background: str
    ) -> Dict[str, Any]:
        """Parse name structure based on cultural background."""
        structure = {}

        if cultural_background == "indonesian_mononym":
            structure.update(self._parse_indonesian_mononym(name))
        elif cultural_background == "malay_islamic":
            structure.update(self._parse_malay_islamic_name(name))
        elif cultural_background == "filipino":
            structure.update(self._parse_filipino_name(name))
        elif cultural_background == "chinese_diaspora":
            structure.update(self._parse_chinese_diaspora_name(name))
        else:
            structure.update(self._parse_general_maritime_name(name))

        return structure

    def _parse_indonesian_mononym(self, name: str) -> Dict[str, Any]:
        """Parse Indonesian mononym (Rule 14, 29)."""
        normalized_mononym = self._normalize_indonesian_mononym(name)

        return {
            "is_mononym": True,
            "mononym_type": "indonesian",
            "normalized_form": normalized_mononym,
            "family_name": normalized_mononym,
            "given_name": "",
            "initials_clustering_skipped": True,
        }

    def _parse_malay_islamic_name(self, name: str) -> Dict[str, Any]:
        """Parse Malay/Islamic name with patronymic (Rule 28)."""
        components = {}

        # Find patronymic
        patronymic_info = self._find_malay_patronymic(name)
        if patronymic_info:
            components["malay_patronymic"] = patronymic_info["patronymic"]
            components["patronymic_meaning"] = patronymic_info["meaning"]
            components["patronymic_gender"] = patronymic_info["gender"]

            # Parse around patronymic
            parts = self._split_around_patronymic(name, patronymic_info)
            components.update(parts)
        else:
            # Standard parsing
            components.update(self._parse_general_maritime_name(name))

        # Check for Islamic compound names
        islamic_compounds = self._detect_islamic_compounds(name)
        if islamic_compounds:
            components["islamic_compounds"] = islamic_compounds

        return components

    def _detect_islamic_compounds(self, name: str) -> List[Dict[str, str]]:
        """Detect Islamic compound naming patterns in a Maritime SEA name.

        Looks for the canonical compound forms documented in
        ``self.islamic_patterns['compound_patterns']`` — primarily:

          - ``abdul`` + (rahman | aziz | malik | karim | latif | majid)
          - ``abu``   + (bakar  | hassan | said | talib | yusuf)
          - ``siti``  + (aishah | fatimah | khadijah | maryam | zainab)

        Returns a list of ``{"prefix": …, "suffix": …}`` dicts (one
        per detected compound, in left-to-right order). Empty list if
        no compound pattern fires.

        This method was referenced by ``_parse_malaysian_name`` /
        ``_parse_indonesian_name`` but never defined — caller crashed
        with ``AttributeError``. The band-aid ``try/except: pass`` in
        ``test_region_processors_full.py`` was hiding the regression
        until round 20 strengthened the assertions.
        """
        compounds: List[Dict[str, str]] = []
        tokens = [t.lower().strip(",") for t in name.split() if t]
        compound_map = self.islamic_patterns.get("compound_patterns", {})
        for i, tok in enumerate(tokens[:-1]):
            suffixes = compound_map.get(tok)
            if not suffixes:
                continue
            next_tok = tokens[i + 1]
            if next_tok in suffixes:
                compounds.append({"prefix": tok, "suffix": next_tok})
        return compounds

    def _parse_filipino_name(self, name: str) -> Dict[str, Any]:
        """Parse Filipino name (Rule 30 - maternal middle name)."""
        components = {}

        # Handle comma format first
        if ", " in name:
            family_part, given_part = name.split(", ", 1)
            components["family_name"] = family_part.strip()
            components["given_name"] = given_part.strip()

            # Check if given part has maternal middle name
            given_words = given_part.split()
            if len(given_words) > 1:
                components["maternal_middle_name"] = " ".join(given_words[1:])
                components["given_name"] = given_words[0]
        else:
            # Space-separated format
            words = name.split()

            if len(words) == 3:
                # Likely: Given Maternal Paternal
                components["given_name"] = words[0]
                components["maternal_middle_name"] = words[1]
                components["family_name"] = words[2]
            elif len(words) == 2:
                components["given_name"] = words[0]
                components["family_name"] = words[1]
            elif len(words) > 3:
                # Complex case: try to identify maternal component
                components["given_name"] = words[0]
                components["family_name"] = words[-1]
                components["maternal_middle_name"] = " ".join(words[1:-1])
            else:
                components["family_name"] = name
                components["given_name"] = ""

        # Check for Spanish colonial indicators
        if self._has_spanish_colonial_patterns(name):
            components["spanish_colonial_influence"] = True

        return components

    def _parse_chinese_diaspora_name(self, name: str) -> Dict[str, Any]:
        """Parse Chinese diaspora name patterns."""
        components = {}

        # Detect dialect group
        dialect_group = self._detect_chinese_dialect_group(name.lower())
        if dialect_group:
            components["chinese_dialect_group"] = dialect_group

        # Standard Chinese order: Family Given
        if ", " in name:
            family_part, given_part = name.split(", ", 1)
            components["family_name"] = family_part.strip()
            components["given_name"] = given_part.strip()
        else:
            words = name.split()
            if len(words) >= 2:
                # Chinese names typically: Family Given
                # But in Maritime SEA, might be adapted to Given Family
                if self._is_likely_chinese_surname(words[0].lower()):
                    components["family_name"] = words[0]
                    components["given_name"] = " ".join(words[1:])
                    components["chinese_name_order"] = "family_given"
                else:
                    components["given_name"] = words[0]
                    components["family_name"] = " ".join(words[1:])
                    components["chinese_name_order"] = "given_family"
            else:
                components["family_name"] = name
                components["given_name"] = ""

        return components

    def _parse_general_maritime_name(self, name: str) -> Dict[str, Any]:
        """Parse general Maritime SEA name."""
        components = {}

        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
            components["name_format"] = "family_given"
        else:
            # Space-separated (Given Family order common in Maritime SEA)
            parts = name.split(None, 1)
            if len(parts) >= 2:
                components["given_name"] = parts[0].strip()
                components["family_name"] = parts[1].strip()
                components["name_format"] = "given_family"
            else:
                components["family_name"] = name.strip()
                components["given_name"] = ""
                components["name_format"] = "family_only"

        return components

    def _detect_specific_patterns(self, name: str) -> Dict[str, Any]:
        """Detect specific Maritime SEA naming patterns."""
        patterns = {}

        # Regional detection
        region = self._detect_likely_region(name)
        if region:
            patterns["likely_region"] = region

        # Language detection
        language = self._detect_primary_language(name)
        if language:
            patterns["primary_language"] = language

        # Colonial influence
        colonial = self._detect_colonial_influence(name.lower())
        if colonial:
            patterns["colonial_influence"] = colonial

        return patterns

    def _apply_regional_rules(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Apply specific regional processing rules."""
        # Rule 14: Indonesian Mononyms
        if components.get("is_mononym"):
            entry["FamilyNameType"] = "mononym"
            # Ensure canonical is single token
            normalized = components.get("normalized_form", canonical)
            if normalized != canonical:
                entry["CanonicalLatin"] = normalized

        # Rule 28: Malay bin/binti patronymic handling
        if components.get("malay_patronymic"):
            self._handle_malay_patronymic(entry, canonical, components)

        # Rule 30: Filipino maternal middle name
        if components.get("maternal_middle_name"):
            entry["RegionalExtras"]["secondary_surname"] = components[
                "maternal_middle_name"
            ]

    def _generate_romanization_variants(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Generate romanization variants for different scripts."""
        script = components.get("primary_script", "latin")

        if script == "arabic":
            # Generate Latin romanization from Arabic
            romanized = self._romanize_arabic_to_latin(canonical)
            if romanized and romanized != canonical:
                entry["CanonicalLatin"] = romanized
                entry["Variants"]["Synthesised"].append(
                    {"str": romanized, "type": "arabic-latin-romanization"}
                )

        elif script == "baybayin":
            # Generate Latin romanization from Baybayin
            romanized = self._romanize_baybayin_to_latin(canonical)
            if romanized and romanized != canonical:
                entry["CanonicalLatin"] = romanized
                entry["Variants"]["Synthesised"].append(
                    {"str": romanized, "type": "baybayin-latin-romanization"}
                )

        # Generate diacritic-free variants for Latin names with diacritics
        if script == "latin" and self._has_diacritics(canonical):
            ascii_variant = self._remove_diacritics(canonical)
            if ascii_variant != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": ascii_variant, "type": "latin-ascii"}
                )

    def _generate_cultural_variants(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Generate cultural and linguistic variants."""
        cultural_bg = components.get("cultural_background", "")

        # Generate name order variants
        if not components.get("is_mononym"):
            self._generate_name_order_variants(entry, canonical, components)

        # Generate patronymic variants (Malay)
        if components.get("malay_patronymic"):
            self._generate_patronymic_variants(entry, canonical, components)

        # Generate Chinese dialect variants
        if cultural_bg == "chinese_diaspora":
            self._generate_chinese_variants(entry, canonical, components)

        # Generate colonial spelling variants
        if components.get("colonial_influence"):
            self._generate_colonial_variants(entry, canonical, components)

    def _handle_malay_patronymic(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Handle Malay patronymic processing (Rule 28)."""
        # Generate variant without patronymic
        no_patronymic = self._remove_patronymic_from_name(canonical, components)
        if no_patronymic and no_patronymic != canonical:
            entry["Variants"]["Synthesised"].append(
                {"str": no_patronymic, "type": "no-patronymic"}
            )

    def _generate_name_order_variants(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Generate name order variants."""
        given = components.get("given_name", "")
        family = components.get("family_name", "")

        if given and family:
            current_format = components.get("name_format", "")

            if current_format == "given_family":
                # Generate Family, Given variant
                family_given = f"{family}, {given}"
                if family_given != canonical:
                    entry["Variants"]["Synthesised"].append(
                        {"str": family_given, "type": "order-swap-comma"}
                    )
            elif current_format == "family_given" and ", " in canonical:
                # Generate Given Family variant
                given_family = f"{given} {family}"
                if given_family != canonical:
                    entry["Variants"]["Synthesised"].append(
                        {"str": given_family, "type": "order-swap-space"}
                    )

    def _generate_patronymic_variants(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Generate Malay patronymic variants."""
        # Already handled in _handle_malay_patronymic

    def _generate_chinese_variants(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Generate Chinese diaspora variants."""
        dialect_group = components.get("chinese_dialect_group")
        if dialect_group and dialect_group in self.chinese_diaspora_patterns:
            # Could generate dialect-specific romanization variants
            # This would require more extensive dialect mapping data
            pass  # Placeholder for future dialect variant generation

    def _generate_colonial_variants(
        self, entry: Dict[str, Any], canonical: str, components: Dict[str, Any]
    ) -> None:
        """Generate colonial spelling variants."""
        colonial_type = components.get("colonial_influence")
        if colonial_type in self.colonial_patterns:
            adaptations = self.colonial_patterns[colonial_type].get("adaptations", {})

            variant = canonical
            for old, new in adaptations.items():
                variant = variant.replace(new, old)  # Reverse mapping for variant

            if variant != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": variant, "type": f"{colonial_type}-colonial-spelling"}
                )

    # Helper methods for pattern detection

    def _is_arabic_char(self, char: str) -> bool:
        """Check if character is Arabic."""
        char_code = ord(char)
        return any(start <= char_code <= end for start, end in self.arabic_ranges)

    def _is_baybayin_char(self, char: str) -> bool:
        """Check if character is Baybayin."""
        char_code = ord(char)
        return any(start <= char_code <= end for start, end in self.baybayin_ranges)

    def _is_indonesian_mononym(self, name: str) -> bool:
        """Check if name is likely an Indonesian mononym."""
        name_clean = name.replace(", ", " ").strip().lower()
        words = name_clean.split()

        if len(words) == 1:
            return words[0] in self.indonesian_mononym_patterns or any(
                words[0].endswith(pattern)
                for pattern in [
                    "harto",
                    "karno",
                    "wati",
                    "joko",
                    "bowo",
                    "tanto",
                    "noto",
                ]
            )
        return False

    def _has_malay_patronymic(self, name: str) -> bool:
        """Check if name has Malay patronymic markers."""
        words = [word.lower().rstrip(".,") for word in name.split()]
        return any(word in self.malay_patronymics for word in words)

    def _has_islamic_patterns(self, name_lower: str) -> bool:
        """Check for Islamic naming patterns."""
        words = name_lower.split()
        islamic_names = (
            self.islamic_patterns["arabic_names"]
            | self.islamic_patterns["malay_islamic"]
        )
        return any(word in islamic_names for word in words)

    def _has_filipino_patterns(self, name_lower: str) -> bool:
        """Check for Filipino naming patterns."""
        filipino_surnames = self.filipino_patterns["spanish_surnames"]
        words = name_lower.split()
        return any(word in filipino_surnames for word in words)

    def _has_chinese_patterns(self, name_lower: str) -> bool:
        """Check for Chinese diaspora patterns."""
        words = name_lower.split()
        for dialect_data in self.chinese_diaspora_patterns.values():
            if isinstance(dialect_data, dict) and "surnames" in dialect_data:
                if any(word in dialect_data["surnames"] for word in words):
                    return True
        return False

    def _detect_colonial_influence(self, name_lower: str) -> Optional[str]:
        """Detect colonial influence in the name."""
        # Check Dutch patterns
        if any(
            particle in name_lower
            for particle in self.colonial_patterns["dutch"]["surnames"]
        ):
            return "dutch"

        # Check Spanish patterns
        spanish_particles = self.colonial_patterns["spanish"]["particles"]
        if any(particle in name_lower for particle in spanish_particles):
            return "spanish"

        # Check Portuguese patterns
        portuguese_surnames = self.colonial_patterns["portuguese"]["surnames"]
        if any(surname in name_lower for surname in portuguese_surnames):
            return "portuguese"

        # Check English adaptations
        english_surnames = self.colonial_patterns["english"]["colonial_surnames"]
        if any(surname in name_lower for surname in english_surnames):
            return "english"

        return None

    def _detect_likely_region(self, name: str) -> Optional[str]:
        """Detect likely country/region based on name patterns."""
        name_lower = name.lower()

        # Indonesian patterns
        if self._is_indonesian_mononym(name) or any(
            pattern in name_lower for pattern in ["sari", "putra", "dewi", "indra"]
        ):
            return "indonesia"

        # Malaysian patterns
        if self._has_malay_patronymic(name):
            return "malaysia"

        # Filipino patterns
        if self._has_filipino_patterns(name_lower):
            return "philippines"

        # Singapore (mixed patterns, Chinese influence)
        if self._has_chinese_patterns(name_lower):
            return "singapore"

        return None

    def _detect_primary_language(self, name: str) -> Optional[str]:
        """Detect primary language of the name."""
        name_lower = name.lower()

        if self._has_islamic_patterns(name_lower):
            return "arabic_malay"
        elif self._has_chinese_patterns(name_lower):
            return "chinese"
        elif self._has_filipino_patterns(name_lower):
            return "filipino"
        elif self._is_indonesian_mononym(name):
            return "bahasa_indonesia"
        else:
            return "malay"

    def _detect_chinese_dialect_group(self, name_lower: str) -> Optional[str]:
        """Detect Chinese dialect group."""
        words = name_lower.split()

        for dialect, data in self.chinese_diaspora_patterns.items():
            if isinstance(data, dict) and "surnames" in data:
                if any(word in data["surnames"] for word in words):
                    return dialect

        return None

    def _is_likely_chinese_surname(self, word: str) -> bool:
        """Check if word is likely a Chinese surname."""
        for dialect_data in self.chinese_diaspora_patterns.values():
            if isinstance(dialect_data, dict) and "surnames" in dialect_data:
                if word in dialect_data["surnames"]:
                    return True
        return False

    def _has_spanish_colonial_patterns(self, name: str) -> bool:
        """Check for Spanish colonial patterns in Filipino names."""
        name_lower = name.lower()
        spanish_indicators = self.filipino_patterns["spanish_surnames"] | set(
            self.colonial_patterns["spanish"]["particles"]
        )
        return any(indicator in name_lower for indicator in spanish_indicators)

    def _normalize_indonesian_mononym(self, name: str) -> str:
        """Normalize Indonesian mononym to single token form."""
        words = name.split()
        if len(words) == 1:
            return name

        # Remove generational suffixes
        suffixes_to_remove = {
            "jr",
            "jr.",
            "senior",
            "sr",
            "sr.",
            "ii",
            "iii",
            "iv",
            "muda",
            "tua",
            "besar",
            "kecil",
        }

        filtered_words = [
            word
            for word in words
            if word.lower().rstrip(".,") not in suffixes_to_remove
        ]

        if len(filtered_words) == 1:
            return filtered_words[0]
        elif len(filtered_words) > 1:
            # Try to combine into known mononym
            combined = "".join(filtered_words).lower()
            for known in self.indonesian_mononym_patterns:
                if combined == known:
                    return known.capitalize()

        # Fallback: take first significant word
        return words[0] if words else name

    def _find_malay_patronymic(self, name: str) -> Optional[Dict[str, Any]]:
        """Find Malay patronymic in name."""
        words = name.split()

        for i, word in enumerate(words):
            word_clean = word.lower().rstrip(",.")
            if word_clean in self.malay_patronymics:
                patronymic_data = self.malay_patronymics[word_clean]
                return {
                    "patronymic": word,
                    "meaning": patronymic_data["meaning"],
                    "gender": patronymic_data["gender"],
                    "index": i,
                }

        return None

    def _split_around_patronymic(
        self, name: str, patronymic_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Split name around patronymic marker."""
        words = name.split()
        patronymic_index = patronymic_info["index"]

        # Before patronymic = given name
        given_parts = words[:patronymic_index]

        # After patronymic = father's name (not family name for sorting)
        father_parts = words[patronymic_index + 1 :]

        return {
            "given_name": " ".join(given_parts).strip(),
            "fathers_name": " ".join(father_parts).strip(),
            "family_name": " ".join(given_parts).strip(),  # Use given name for sorting
            "has_patronymic": True,
        }

    def _remove_patronymic_from_name(
        self, name: str, components: Dict[str, Any]
    ) -> Optional[str]:
        """Remove patronymic from name to create variant."""
        patronymic_info = self._find_malay_patronymic(name)
        if not patronymic_info:
            return None

        words = name.split()
        patronymic_index = patronymic_info["index"]

        # Remove patronymic and father's name
        filtered_words = []
        i = 0
        while i < len(words):
            if i == patronymic_index:
                # Skip patronymic and next word (father's name)
                i += 2 if i + 1 < len(words) else 1
            else:
                filtered_words.append(words[i])
                i += 1

        return " ".join(filtered_words) if filtered_words else None

    def _romanize_arabic_to_latin(self, arabic_text: str) -> str:
        """Basic Arabic to Latin romanization for Maritime SEA context."""
        # This is a simplified romanization - would need comprehensive mapping
        # for production use
        romanized = arabic_text  # Placeholder - would implement proper romanization
        return romanized

    def _romanize_baybayin_to_latin(self, baybayin_text: str) -> str:
        """Basic Baybayin to Latin romanization."""
        # This is a simplified romanization - would need comprehensive mapping
        # for production use
        romanized = baybayin_text  # Placeholder - would implement proper romanization
        return romanized

    def _has_diacritics(self, text: str) -> bool:
        """Check if text contains diacritics."""
        return any(c in self.malay_diacritics for c in text)

    def _remove_diacritics(self, text: str) -> str:
        """Remove diacritics from text."""
        result = text
        for diacritic, replacement in self.malay_diacritics.items():
            result = result.replace(diacritic, replacement)

        # Also handle general diacritic removal
        normalized = unicodedata.normalize("NFD", result)
        ascii_text = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

        return ascii_text

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

    def _is_valid_maritime_sea_name(self, name: str) -> bool:
        """Check if name contains valid Maritime SEA characters."""
        for char in name:
            # Allow spaces, hyphens, apostrophes, commas, periods
            if char in " -',.":
                continue
            # Check Maritime SEA scripts
            if self._is_arabic_char(char) or self._is_baybayin_char(char):
                continue
            # Allow Latin characters and diacritics
            if char.isalpha() or ord(char) < 256:
                continue
            # Allow common diacritics
            if char in self.malay_diacritics:
                continue
            # Invalid character found

    def _validate_script_consistency(self, native: str, latin: str) -> bool:
        """Validate consistency between native and latin script forms."""
        # Basic validation - both should represent the same name
        # This would need more sophisticated validation in production
        return len(native.replace(" ", "")) > 0 and len(latin.replace(" ", "")) > 0

        for char in name:
            # Reject control characters (ASCII 0-31, 127)
            if ord(char) < 32 or ord(char) == 127:
                return True
            # Reject other potentially dangerous Unicode ranges
            if ord(char) in [0xFEFF, 0x200B, 0x200C, 0x200D]:  # Zero-width characters
                return True
        return False

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for Maritime SEA names."""
        components = entry.get("RegionalExtras", {})

        # Handle mononyms
        if components.get("is_mononym"):
            mononym = components.get("normalized_form", "")
            if mononym:
                return mononym.upper().strip()

        # Handle Malay names with patronymic (use given name for sorting)
        if components.get("has_patronymic"):
            given = components.get("given_name", "")
            if given:
                return given.upper().strip()

        # Standard family-given sorting
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Romanize non-Latin scripts for sorting
        script = components.get("primary_script", "latin")
        if script == "arabic" and family:
            family = self._remove_diacritics(family)
        elif script == "baybayin" and family:
            family = self._remove_diacritics(family)

        # Generate sort key
        if family and given:
            sort_key = f"{family} {given}"
        elif family:
            sort_key = family
        elif given:
            sort_key = given
        else:
            # Fallback to canonical
            canonical = entry.get("CanonicalLatin", "") or entry.get(
                "CanonicalNative", ""
            )
            sort_key = canonical

        # Normalize for sorting
        sort_key = sort_key.upper()
        sort_key = re.sub(r"[^\w\s]", "", sort_key)
        sort_key = self._remove_diacritics(sort_key)

        return sort_key.strip()
