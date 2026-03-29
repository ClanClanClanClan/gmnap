"""
D1 - South Asia Hindi Belt region implementation.

Covers: Hindi-speaking states of India, parts of Nepal
Features: Devanagari script, patronymic patterns, caste/community indicators, honorifics
"""

import re
from typing import Any, Dict, List, Optional

from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class D1_SouthAsiaHindiBelt(RegionSpec):
    """
    South Asia Hindi Belt region (D1).

    Handles names from Hindi-speaking regions:
    - Devanagari script support
    - Complex name patterns (given + father + family/caste)
    - Honorific titles (Shri, Pandit, etc.)
    - Caste and community indicators
    - Romanization support (IAST/ISO 15919)
    """

    def __init__(self):
        super().__init__(
            code="D1",
            yaml_files=["d1_south_asia_hindi_belt.yaml"],
            scripts=["Devanagari"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["IAST", "ISO 15919", "Hunterian"],
        )

        # Common honorific titles
        self.honorifics = {
            # Hindi honorifics
            "श्री",
            "श्रीमती",
            "श्रीमान",
            "सुश्री",
            "कुमारी",
            "कुमार",
            "Shri",
            "Shree",
            "Sri",
            "Smt",
            "Smt.",
            "Shrimati",
            "Kumari",
            "Kumar",
            # Religious/professional titles
            "पंडित",
            "पं.",
            "Pandit",
            "Pt",
            "Pt.",
            "डॉ.",
            "डॉक्टर",
            "Dr",
            "Dr.",
            "Doctor",
            "प्रो.",
            "प्रोफेसर",
            "Prof",
            "Prof.",
            "Professor",
            "इंजीनियर",
            "Er",
            "Er.",
            "Engineer",
            "गुरु",
            "Guru",
            "स्वामी",
            "Swami",
            "महात्मा",
            "Mahatma",
            "बाबू",
            "Babu",
            "मास्टर",
            "Master",
            "जी",
            "Ji",
            # Caste/community titles
            "ठाकुर",
            "Thakur",
            "चौधरी",
            "Chaudhary",
            "Chaudhuri",
            "राय",
            "राव",
            "Rai",
            "Rao",
            "Roy",
            "सिंह",
            "Singh",  # Often used as title
            "वर्मा",
            "Verma",
            "शर्मा",
            "Sharma",  # Brahmin indicators
            # Sikh titles
            "सरदार",
            "Sardar",
            "S.",
            "गुरबचन",
            "Gurbachan",
            "भाई",
            "Bhai",
            # Muslim titles (in Hindi belt)
            "हाजी",
            "Haji",
            "मौलवी",
            "Maulvi",
            "मौलाना",
            "Maulana",
            "खान",
            "Khan",
            "बेगम",
            "Begum",
            "बीबी",
            "Bibi",
        }

        # Name suffixes that might be caste/community indicators
        self.caste_indicators = {
            # Brahmin
            "शर्मा",
            "Sharma",
            "पांडे",
            "Pandey",
            "मिश्र",
            "Mishra",
            "मिश्रा",
            "Misra",
            "त्रिपाठी",
            "Tripathi",
            "द्विवेदी",
            "Dwivedi",
            "चतुर्वेदी",
            "Chaturvedi",
            "शुक्ल",
            "Shukla",
            "शुक्ला",
            "Shukla",
            "अग्निहोत्री",
            "Agnihotri",
            # Kshatriya
            "सिंह",
            "Singh",
            "राणा",
            "Rana",
            "राज",
            "Raj",
            "ठाकुर",
            "Thakur",
            "चौहान",
            "Chauhan",
            "तोमर",
            "Tomar",
            "राठौर",
            "Rathore",
            # Vaishya
            "गुप्ता",
            "Gupta",
            "अग्रवाल",
            "Agrawal",
            "अग्रवाल",
            "Agarwal",
            "बंसल",
            "Bansal",
            "गोयल",
            "Goyal",
            "जैन",
            "Jain",
            # Other communities
            "यादव",
            "Yadav",
            "पटेल",
            "Patel",
            "कुमार",
            "Kumar",
            "वर्मा",
            "Verma",
            "जायसवाल",
            "Jaiswal",
            "सिन्हा",
            "Sinha",
            "प्रसाद",
            "Prasad",
            "राम",
            "Ram",
            "लाल",
            "Lal",
        }

        # Common name patterns
        self.name_particles = {
            "कुमार",
            "Kumar",  # Often middle name
            "चंद",
            "Chand",
            "चन्द",
            "Chandra",
            "प्रसाद",
            "Prasad",
            "प्रकाश",
            "Prakash",
            "देव",
            "Dev",
            "देवी",
            "Devi",
            "लाल",
            "Lal",
            "राम",
            "Ram",
            "नाथ",
            "Nath",
            "दास",
            "Das",
            "पाल",
            "Pal",
            "बहादुर",
            "Bahadur",
        }

        # Devanagari character ranges
        self.devanagari_ranges = [
            (0x0900, 0x097F),  # Devanagari
            (0xA8E0, 0xA8FF),  # Devanagari Extended
            (0x1CD0, 0x1CFF),  # Vedic Extensions
        ]

        # Common Hindi given names (for validation)
        self.common_given_names = {
            # Male names
            "राम",
            "Ram",
            "श्याम",
            "Shyam",
            "कृष्ण",
            "Krishna",
            "अजय",
            "Ajay",
            "विजय",
            "Vijay",
            "संजय",
            "Sanjay",
            "राज",
            "Raj",
            "राजेश",
            "Rajesh",
            "सुरेश",
            "Suresh",
            "मोहन",
            "Mohan",
            "सोहन",
            "Sohan",
            "रोहन",
            "Rohan",
            "अमित",
            "Amit",
            "सुमित",
            "Sumit",
            "अनिल",
            "Anil",
            # Female names
            "सीता",
            "Sita",
            "गीता",
            "Gita",
            "राधा",
            "Radha",
            "प्रिया",
            "Priya",
            "पूजा",
            "Pooja",
            "अनीता",
            "Anita",
            "सुनीता",
            "Sunita",
            "कविता",
            "Kavita",
            "ममता",
            "Mamta",
            "रेखा",
            "Rekha",
            "सुधा",
            "Sudha",
            "आशा",
            "Asha",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean entry according to D1 rules."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        # SECURITY: Check raw input for dangerous characters FIRST
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                raw_input = entry[field]
                # Check for dangerous control characters
                # Normalize tabs and newlines (V7 edge case)
                if "\t" in raw_input:
                    raw_input = raw_input.replace("\t", " ")
                    entry[field] = raw_input
                if "\n" in raw_input:
                    raw_input = raw_input.replace("\n", " ")
                    entry[field] = raw_input
                # Check remaining dangerous chars
                if any(
                    ord(c) < 32 and c not in (" ", "\t", "\n") or ord(c) == 127 for c in raw_input
                ):
                    raise RegionRuleError(
                        f"Name contains dangerous characters: {raw_input[:50]}..."
                    )
                # Check for zero-width characters
                if any(ord(c) in [0xFEFF, 0x200B, 0x200C, 0x200D] for c in raw_input):
                    raise RegionRuleError(
                        f"Name contains zero-width characters: {raw_input[:50]}..."
                    )

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
        if not name:
            return name

        # Remove honorifics and titles
        name = self._remove_honorifics(name)

        # Normalize whitespace
        name = " ".join(name.split())

        # Normalize punctuation
        name = self._normalize_punctuation(name)

        # Handle special Hindi punctuation
        name = self._normalize_devanagari_punctuation(name)

        return name

    def _remove_honorifics(self, text: str) -> str:
        """Remove honorific titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            # Remove periods and check against honorifics
            clean_word = word.rstrip(".,।")
            if clean_word not in self.honorifics:
                cleaned.append(word)

        # Handle Ji suffix (e.g., "Gandhiji" -> "Gandhi")
        result = " ".join(cleaned)
        result = re.sub(r"([a-zA-Z\u0900-\u097F]+)[jJ]i\b", r"\1", result)
        result = re.sub(r"([a-zA-Z\u0900-\u097F]+)जी\b", r"\1", result)

        return result

    def _normalize_punctuation(self, name: str) -> str:
        """Normalize punctuation in names."""
        # Remove extra spaces
        name = re.sub(r"\s+", " ", name)

        # Normalize dashes
        name = re.sub(r"[-—–]", "-", name)

        # Remove trailing punctuation
        name = re.sub(r"[,;:]$", "", name)

        return name.strip()

    def _normalize_devanagari_punctuation(self, name: str) -> str:
        """Normalize Devanagari-specific punctuation."""
        # Devanagari danda (।) and double danda (॥)
        name = name.replace("।", ".")
        name = name.replace("॥", "..")

        # Remove Devanagari abbreviation sign (॰)
        name = name.replace("॰", "")

        return name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with D1-specific data."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Check if already processed for idempotency
        entry_id = entry.get("GlobalID", "")
        process_key = f"{self.code}:{entry_id}:{canonical}"
        if process_key in self._processed_entries:
            return  # Already processed, skip to avoid duplicates

        # Extract components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Add region code
        entry["RegionCode"] = self.code

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Add romanized variant if original is Devanagari
        if self._is_devanagari(canonical):
            romanized = self._romanize_name(canonical)
            if romanized != canonical:
                # Update CanonicalLatin to be romanized
                entry["CanonicalLatin"] = romanized
                # Use add_variant for idempotency
                if hasattr(self, "add_variant"):
                    self.add_variant(entry, {"str": romanized, "type": "romanization"})
                else:
                    entry["Variants"]["Synthesised"].append(
                        {"str": romanized, "type": "romanization"}
                    )

        # Add initials variant
        initials_variant = self._generate_initials_variant(canonical, components)
        if initials_variant and initials_variant != canonical:
            # Use add_variant for idempotency
            if hasattr(self, "add_variant"):
                self.add_variant(entry, {"str": initials_variant, "type": "initials"})
            else:
                entry["Variants"]["Synthesised"].append(
                    {"str": initials_variant, "type": "initials"}
                )

        # Add variant without middle/father name
        short_variant = self._generate_short_variant(canonical, components)
        if short_variant and short_variant != canonical:
            # Use add_variant for idempotency
            if hasattr(self, "add_variant"):
                self.add_variant(entry, {"str": short_variant, "type": "short-form"})
            else:
                entry["Variants"]["Synthesised"].append(
                    {"str": short_variant, "type": "short-form"}
                )

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        # Split into words
        words = name.split()

        # Identify caste/community indicator
        caste_info = self._identify_caste_indicator(words)
        if caste_info:
            components.update(caste_info)

        # Common patterns in Hindi names:
        # 1. Given Family (2 words)
        # 2. Given Father Family (3 words)
        # 3. Given Middle Family (3 words)
        # 4. Given Father's-Given Family (3+ words)

        if len(words) == 2:
            # Simple: Given Family
            components["given_name"] = words[0]
            components["family_name"] = words[1]

        elif len(words) == 3:
            # Could be: Given Father Family or Given Middle Family
            components["given_name"] = words[0]

            # Check if middle word is a common particle/father name
            if words[1] in self.name_particles or self._is_common_middle_name(words[1]):
                components["middle_name"] = words[1]
                components["family_name"] = words[2]
            else:
                components["father_name"] = words[1]
                components["family_name"] = words[2]

        elif len(words) > 3:
            # Complex pattern
            components["given_name"] = words[0]

            # Last word is usually family name
            components["family_name"] = words[-1]

            # Everything in between
            middle_parts = words[1:-1]
            if len(middle_parts) == 1:
                components["middle_name"] = middle_parts[0]
            else:
                components["middle_name"] = " ".join(middle_parts)

        else:
            # Single word name
            components["given_name"] = name

        return components

    def _identify_caste_indicator(self, words: List[str]) -> Optional[Dict[str, Any]]:
        """Identify caste/community indicators in name."""
        result = {}

        # Check last word (family name) for caste indicator
        if words:
            last_word = words[-1]
            if last_word in self.caste_indicators:
                result["has_caste_indicator"] = True
                result["caste_indicator"] = last_word

                # Determine probable community
                if last_word in ["शर्मा", "Sharma", "पांडे", "Pandey", "मिश्र", "Mishra"]:
                    result["probable_community"] = "Brahmin"
                elif last_word in ["सिंह", "Singh", "राणा", "Rana", "ठाकुर", "Thakur"]:
                    result["probable_community"] = "Kshatriya"
                elif last_word in ["गुप्ता", "Gupta", "अग्रवाल", "Agrawal", "जैन", "Jain"]:
                    result["probable_community"] = "Vaishya"

        return result if result else None

    def _is_common_middle_name(self, word: str) -> bool:
        """Check if word is a common middle name pattern."""
        return word in self.name_particles or word in [
            "Kumar",
            "कुमार",
            "Chand",
            "चंद",
            "Prasad",
            "प्रसाद",
        ]

    def _is_devanagari(self, text: str) -> bool:
        """Check if text contains Devanagari characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.devanagari_ranges):
                return True
        return False

    def _romanize_name(self, name: str) -> str:
        """Romanize Devanagari name using IAST standard."""
        # Basic Devanagari to IAST mapping
        romanization_map = {
            # Vowels
            "अ": "a",
            "आ": "ā",
            "इ": "i",
            "ई": "ī",
            "उ": "u",
            "ऊ": "ū",
            "ऋ": "ṛ",
            "ॠ": "ṝ",
            "ऌ": "ḷ",
            "ॡ": "ḹ",
            "ए": "e",
            "ऐ": "ai",
            "ओ": "o",
            "औ": "au",
            # Consonants
            "क": "k",
            "ख": "kh",
            "ग": "g",
            "घ": "gh",
            "ङ": "ṅ",
            "च": "c",
            "छ": "ch",
            "ज": "j",
            "झ": "jh",
            "ञ": "ñ",
            "ट": "ṭ",
            "ठ": "ṭh",
            "ड": "ḍ",
            "ढ": "ḍh",
            "ण": "ṇ",
            "त": "t",
            "थ": "th",
            "द": "d",
            "ध": "dh",
            "न": "n",
            "प": "p",
            "फ": "ph",
            "ब": "b",
            "भ": "bh",
            "म": "m",
            "य": "y",
            "र": "r",
            "ल": "l",
            "व": "v",
            "श": "ś",
            "ष": "ṣ",
            "स": "s",
            "ह": "h",
            # Additional consonants
            "क्ष": "kṣ",
            "त्र": "tr",
            "ज्ञ": "jñ",
            "श्र": "śr",
            # Vowel marks
            "ा": "ā",
            "ि": "i",
            "ी": "ī",
            "ु": "u",
            "ू": "ū",
            "ृ": "ṛ",
            "ॄ": "ṝ",
            "ॢ": "ḷ",
            "ॣ": "ḹ",
            "े": "e",
            "ै": "ai",
            "ो": "o",
            "ौ": "au",
            # Nasalization and other marks
            "ं": "ṃ",
            "ः": "ḥ",
            "़": "",
            "ँ": "m̐",
            "्": "",  # Virama (halant)
            # Numbers
            "०": "0",
            "१": "1",
            "२": "2",
            "३": "3",
            "४": "4",
            "५": "5",
            "६": "6",
            "७": "7",
            "८": "8",
            "९": "9",
        }

        # For common names, use simplified romanization
        common_names_map = {
            "राम": "Ram",
            "श्याम": "Shyam",
            "कृष्ण": "Krishna",
            "सिंह": "Singh",
            "शर्मा": "Sharma",
            "गुप्ता": "Gupta",
            "कुमार": "Kumar",
            "प्रसाद": "Prasad",
            "वर्मा": "Verma",
        }

        # Check if it's a common name first
        for hindi, roman in common_names_map.items():
            if hindi in name:
                name = name.replace(hindi, roman)

        # Apply character-by-character romanization
        result = []
        i = 0
        while i < len(name):
            # Check for multi-character combinations first
            found = False
            for length in [3, 2]:
                if i + length <= len(name):
                    substr = name[i : i + length]
                    if substr in romanization_map:
                        result.append(romanization_map[substr])
                        i += length
                        found = True
                        break

            if not found:
                char = name[i]
                if char in romanization_map:
                    result.append(romanization_map[char])
                else:
                    result.append(char)
                i += 1

        romanized = "".join(result)

        # Post-process: remove diacritics for common usage
        # This is a simplified version - full IAST would keep diacritics
        simplified = romanized.replace("ā", "a").replace("ī", "i").replace("ū", "u")
        simplified = simplified.replace("ṛ", "ri").replace("ṝ", "ri")
        simplified = simplified.replace("ñ", "n").replace("ṅ", "n").replace("ṇ", "n")
        simplified = simplified.replace("ś", "sh").replace("ṣ", "sh")
        simplified = simplified.replace("ṭ", "t").replace("ḍ", "d")
        simplified = simplified.replace("ṃ", "m").replace("ḥ", "h")

        # Clean up and capitalize
        simplified = " ".join(simplified.split())
        return simplified.title()

    def _generate_initials_variant(self, name: str, components: Dict[str, Any]) -> Optional[str]:
        """Generate variant with initials."""
        given = components.get("given_name", "")
        middle = components.get("middle_name", "") or components.get("father_name", "")
        family = components.get("family_name", "")

        if given and family:
            if middle:
                # Use initials for given and middle
                return f"{given[0]}. {middle[0]}. {family}"
            else:
                # Use initial for given
                return f"{given[0]}. {family}"

        return None

    def _generate_short_variant(self, name: str, components: Dict[str, Any]) -> Optional[str]:
        """Generate short form without middle/father name."""
        given = components.get("given_name", "")
        family = components.get("family_name", "")

        if given and family:
            return f"{given} {family}"

        return None

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to D1 rules - MORE LENIENT."""
        # Use the base class helper for graceful handling
        canonical = self.get_canonical_name(entry)
        if not canonical:
            if not self.has_sufficient_name_data(entry):
                raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")
            else:
                # Has sufficient data but no processable name - skip strict validation
                return

        # SECURITY: Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(f"Name too long: {len(canonical)} characters (max 150)")

        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")

        # RELAXED: If CanonicalNative exists and is not empty, prefer Devanagari but don't require it
        if canonical_native and len(canonical_native.strip()) > 0:
            if not self._is_devanagari(canonical_native) and not self._is_mixed_script(
                canonical_native
            ):
                # Just warn, don't fail - D1 region can process romanized names too
                self.logger.warning(
                    f"CanonicalNative in D1 region is not Devanagari: {canonical_native}"
                )
                # Continue processing instead of failing

        # If CanonicalLatin exists and is pure Devanagari, that's unusual but acceptable
        if canonical_latin:
            if self._is_devanagari(canonical_latin) and not self._is_mixed_script(canonical_latin):
                self.logger.warning(
                    f"CanonicalLatin contains Devanagari (unusual): {canonical_latin}"
                )
                # Continue processing instead of failing

        # Check name structure (more lenient)
        for canonical in [canonical_native, canonical_latin]:
            if canonical and len(canonical.strip()) > 0:
                # Allow single character names for edge cases
                if len(canonical.strip()) == 1:
                    self.logger.warning(f"Single character name accepted: {canonical}")
                    continue

                # Check for invalid characters (but be lenient)
                if not self._has_valid_characters(canonical):
                    # Only reject if truly problematic
                    self.logger.warning(f"Potentially invalid characters in name: {canonical}")
                    # Continue processing instead of failing

    def _is_mixed_script(self, text: str) -> bool:
        """Check if text contains both Devanagari and Latin scripts."""
        has_devanagari = False
        has_latin = False

        for char in text:
            if any(start <= ord(char) <= end for start, end in self.devanagari_ranges):
                has_devanagari = True
            elif char.isalpha() and ord(char) < 256:
                has_latin = True

        return has_devanagari and has_latin

    def _has_valid_characters(self, name: str) -> bool:
        """Check if name contains valid characters."""
        for char in name:
            # Allow Latin, Devanagari, spaces, hyphens, apostrophes, dots, commas
            if char.isalpha() or char in " -'.,":
                continue
            # Check if it's valid Devanagari
            if any(start <= ord(char) <= end for start, end in self.devanagari_ranges):
                continue
            # Allow digits in some contexts
            if char.isdigit():
                continue
            # Invalid character found
            return False
        return True

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        middle = components.get("middle_name", "") or components.get("father_name", "")

        # Use romanized form for sorting if available
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")

        # If we have Devanagari, romanize for sorting
        if self._is_devanagari(canonical):
            canonical = self._romanize_name(canonical)

        # Normalize for sorting
        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""
        sort_middle = middle.upper() if middle else ""

        # If no family name extracted, use the whole canonical name
        if not sort_family and canonical:
            # Use the canonical form directly
            return canonical.upper().replace(",", "").strip()

        # Remove punctuation for sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)
        sort_middle = re.sub(r"[^\w\s]", "", sort_middle)

        # Generate key: Family, Given Middle
        key_parts = []
        if sort_family:
            key_parts.append(sort_family)
        if sort_given:
            key_parts.append(sort_given)
        if sort_middle:
            key_parts.append(sort_middle)

        key = " ".join(key_parts) if key_parts else canonical.upper()

        # Ensure determinism
        key = " ".join(key.split())

        return key

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
