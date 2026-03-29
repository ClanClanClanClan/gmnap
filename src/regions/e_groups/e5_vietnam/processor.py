"""
Vietnam (E5) regional processor.

Implements Vietnamese with tone marks and numeric tone variants (Rule 4).
Features: 6-tone system, full/ASCII/numeric variants, Vietnamese name order.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional
from ...base_enhanced import EnhancedRegionSpec as RegionSpec, RegionRuleError


class E5_Vietnam(RegionSpec):
    """Handler for E5 - Vietnam."""

    def __init__(self):
        super().__init__(
            code="E5",
            yaml_files=["e5_vietnam.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family Given",  # Vietnamese order
            romanisation_standards=["Vietnamese orthography"],
        )

        # Vietnamese tone mark mappings for Rule 4
        # Maps tone-marked characters to (base_char, tone_number)
        self.tone_mappings = {
            # Vowel 'a'
            "a": ("a", 1),
            "á": ("a", 2),
            "à": ("a", 3),
            "ả": ("a", 4),
            "ã": ("a", 5),
            "ạ": ("a", 6),
            "A": ("A", 1),
            "Á": ("A", 2),
            "À": ("A", 3),
            "Ả": ("A", 4),
            "Ã": ("A", 5),
            "Ạ": ("A", 6),
            # Vowel 'e'
            "e": ("e", 1),
            "é": ("e", 2),
            "è": ("e", 3),
            "ẻ": ("e", 4),
            "ẽ": ("e", 5),
            "ẹ": ("e", 6),
            "E": ("E", 1),
            "É": ("E", 2),
            "È": ("E", 3),
            "Ẻ": ("E", 4),
            "Ẽ": ("E", 5),
            "Ẹ": ("E", 6),
            # Vowel 'i'
            "i": ("i", 1),
            "í": ("i", 2),
            "ì": ("i", 3),
            "ỉ": ("i", 4),
            "ĩ": ("i", 5),
            "ị": ("i", 6),
            "I": ("I", 1),
            "Í": ("I", 2),
            "Ì": ("I", 3),
            "Ỉ": ("I", 4),
            "Ĩ": ("I", 5),
            "Ị": ("I", 6),
            # Vowel 'o'
            "o": ("o", 1),
            "ó": ("o", 2),
            "ò": ("o", 3),
            "ỏ": ("o", 4),
            "õ": ("o", 5),
            "ọ": ("o", 6),
            "O": ("O", 1),
            "Ó": ("O", 2),
            "Ò": ("O", 3),
            "Ỏ": ("O", 4),
            "Õ": ("O", 5),
            "Ọ": ("O", 6),
            # Vowel 'u'
            "u": ("u", 1),
            "ú": ("u", 2),
            "ù": ("u", 3),
            "ủ": ("u", 4),
            "ũ": ("u", 5),
            "ụ": ("u", 6),
            "U": ("U", 1),
            "Ú": ("U", 2),
            "Ù": ("U", 3),
            "Ủ": ("U", 4),
            "Ũ": ("U", 5),
            "Ụ": ("U", 6),
            # Vowel 'y'
            "y": ("y", 1),
            "ý": ("y", 2),
            "ỳ": ("y", 3),
            "ỷ": ("y", 4),
            "ỹ": ("y", 5),
            "ỵ": ("y", 6),
            "Y": ("Y", 1),
            "Ý": ("Y", 2),
            "Ỳ": ("Y", 3),
            "Ỷ": ("Y", 4),
            "Ỹ": ("Y", 5),
            "Ỵ": ("Y", 6),
            # Compound vowels - ô
            "ô": ("ô", 1),
            "ố": ("ô", 2),
            "ồ": ("ô", 3),
            "ổ": ("ô", 4),
            "ỗ": ("ô", 5),
            "ộ": ("ô", 6),
            "Ô": ("Ô", 1),
            "Ố": ("Ô", 2),
            "Ồ": ("Ô", 3),
            "Ổ": ("Ô", 4),
            "Ỗ": ("Ô", 5),
            "Ộ": ("Ô", 6),
            # Compound vowels - ơ
            "ơ": ("ơ", 1),
            "ớ": ("ơ", 2),
            "ờ": ("ơ", 3),
            "ở": ("ơ", 4),
            "ỡ": ("ơ", 5),
            "ợ": ("ơ", 6),
            "Ơ": ("Ơ", 1),
            "Ớ": ("Ơ", 2),
            "Ờ": ("Ơ", 3),
            "Ở": ("Ơ", 4),
            "Ỡ": ("Ơ", 5),
            "Ợ": ("Ơ", 6),
            # Compound vowels - ư
            "ư": ("ư", 1),
            "ứ": ("ư", 2),
            "ừ": ("ư", 3),
            "ử": ("ư", 4),
            "ữ": ("ư", 5),
            "ự": ("ư", 6),
            "Ư": ("Ư", 1),
            "Ứ": ("Ư", 2),
            "Ừ": ("Ư", 3),
            "Ử": ("Ư", 4),
            "Ữ": ("Ư", 5),
            "Ự": ("Ư", 6),
        }

        # Reverse mapping for generating tone variants
        self.base_to_tones = {}
        for char, (base, tone) in self.tone_mappings.items():
            if base not in self.base_to_tones:
                self.base_to_tones[base] = {}
            self.base_to_tones[base][tone] = char

        # Common Vietnamese family names
        self.common_family_names = {
            "Nguyễn",
            "Trần",
            "Lê",
            "Phạm",
            "Hoàng",
            "Huỳnh",
            "Phan",
            "Vũ",
            "Võ",
            "Đặng",
            "Bùi",
            "Đỗ",
            "Hồ",
            "Ngô",
            "Dương",
            "Lý",
            "Lâm",
            "Lương",
            "Trương",
            "Đinh",
        }

        # Common Vietnamese titles to remove
        self.titles = {
            "Ông",
            "Bà",
            "Cô",
            "Chú",
            "Anh",
            "Chị",
            "Em",  # Family terms
            "Tiến sĩ",
            "Tiến sỹ",
            "Bác sĩ",
            "Giáo sư",
            "Thầy",
            "Cô",  # Professional
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",  # English
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Apply V7 security validation and graceful edge case handling."""
        # Use comprehensive V7 security validation from base class
        # This includes all 7 required security checks:
        # 1. Dangerous characters, 2. DoS protection (length limits)
        # 3. SQL injection patterns, 4. XSS patterns
        # 5. Command injection patterns, 6. Path traversal patterns
        # 7. Native field validation
        self.apply_security_and_validation_checks(entry)

        # Handle legitimate edge cases gracefully
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

        # Apply region-specific cleaning rules here
        # This is a stub implementation - region-specific logic should be added
        pass

    def _clean_name(self, name: str) -> str:
        """Clean a single Vietnamese name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize Unicode (NFC form for Vietnamese)
        name = unicodedata.normalize("NFC", name)

        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Vietnamese titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            # Remove periods and check against titles
            clean_word = word.rstrip(".,")
            if clean_word not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with E5-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
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

        # Rule 4: Vietnamese Tone Handling – full, ASCII and numeric-tone variants
        tone_variants = self._generate_vietnamese_tone_variants(canonical)
        for variant in tone_variants:
            if variant["str"] != canonical:
                entry["Variants"]["Synthesised"].append(variant)

        # Add order swap variant (Given Family)
        if components.get("family_name") and components.get("given_name"):
            given_family = f"{components['given_name']} {components['family_name']}"
            if given_family != canonical:
                self.add_variant(entry, {"str": given_family, "type": "order-swap"})

    def _generate_vietnamese_tone_variants(self, name: str) -> List[Dict[str, str]]:
        """
        Rule 4: Vietnamese Tone Handling – full, ASCII and numeric-tone variants.

        Generates three types of variants:
        1. Full tone variant (with all diacritics): "Nguyễn Văn Anh"
        2. ASCII variant (no tones): "Nguyen Van Anh"
        3. Numeric tone variant: "Nguyen5 Van Anh"

        Examples:
        - "Nguyễn" (tone 5) → "Nguyen" (ASCII), "Nguyen5" (numeric)
        - "Trần" (tone 1) → "Tran" (ASCII), "Tran1" (numeric)
        """
        variants = []

        # Check if name has Vietnamese tones
        has_tones = any(char in self.tone_mappings for char in name)

        if has_tones:
            # Generate ASCII variant (remove all tone marks)
            ascii_variant = self._remove_tones(name)
            if ascii_variant != name:
                variants.append({"str": ascii_variant, "type": "ascii-lossy"})

            # Generate numeric tone variant
            numeric_variant = self._generate_numeric_tone_variant(name)
            if numeric_variant and numeric_variant != name and numeric_variant != ascii_variant:
                variants.append({"str": numeric_variant, "type": "tone-number"})
        else:
            # If ASCII input, try to generate toned variant if we can identify it
            toned_variant = self._restore_common_tones(name)
            if toned_variant and toned_variant != name:
                variants.append({"str": toned_variant, "type": "tone-restored"})

        return variants

    def _remove_tones(self, text: str) -> str:
        """Remove all tone marks from Vietnamese text."""
        result = []
        for char in text:
            if char in self.tone_mappings:
                base, _ = self.tone_mappings[char]
                # Remove compound vowel markers for ASCII
                if base in ["ô", "Ô"]:
                    result.append("o" if char.islower() else "O")
                elif base in ["ơ", "Ơ"]:
                    result.append("o" if char.islower() else "O")
                elif base in ["ư", "Ư"]:
                    result.append("u" if char.islower() else "U")
                else:
                    result.append(base)
            else:
                result.append(char)
        return "".join(result)

    def _generate_numeric_tone_variant(self, text: str) -> str:
        """Generate numeric tone variant (e.g., Nguyen5)."""
        words = text.split()
        result_words = []

        for word in words:
            word_result = []
            tone_found = None

            # Find the tone in this word
            for char in word:
                if char in self.tone_mappings:
                    base, tone = self.tone_mappings[char]
                    if tone != 1:  # Don't add number for tone 1 (no mark)
                        tone_found = tone
                    # Add base character without tone
                    if base in ["ô", "Ô"]:
                        word_result.append("o" if char.islower() else "O")
                    elif base in ["ơ", "Ơ"]:
                        word_result.append("o" if char.islower() else "O")
                    elif base in ["ư", "Ư"]:
                        word_result.append("u" if char.islower() else "U")
                    else:
                        word_result.append(base)
                else:
                    word_result.append(char)

            # Append tone number at end of word if found
            word_str = "".join(word_result)
            if tone_found and tone_found != 1:
                word_str += str(tone_found)

            result_words.append(word_str)

        return " ".join(result_words)

    def _restore_common_tones(self, text: str) -> Optional[str]:
        """Try to restore tones for common Vietnamese names."""
        # Simple restoration for very common names
        common_restorations = {
            "Nguyen": "Nguyễn",
            "Tran": "Trần",
            "Le": "Lê",
            "Pham": "Phạm",
            "Hoang": "Hoàng",
            "Huynh": "Huỳnh",
            "Vu": "Vũ",
            "Vo": "Võ",
            "Dang": "Đặng",
            "Bui": "Bùi",
            "Do": "Đỗ",
            "Ho": "Hồ",
            "Ngo": "Ngô",
            "Duong": "Dương",
            "Ly": "Lý",
            "Lam": "Lâm",
            "Luong": "Lương",
            "Truong": "Trương",
            "Dinh": "Đinh",
        }

        words = text.split()
        restored_words = []
        found_restoration = False

        for word in words:
            if word in common_restorations:
                restored_words.append(common_restorations[word])
                found_restoration = True
            else:
                restored_words.append(word)

        return " ".join(restored_words) if found_restoration else None

    def validate(self, entry: Dict[str, Any]) -> None:
        """Apply V7 security validation with DoS protection."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # No name to validate - that's OK, just skip
            return

        # SECURITY: Check for dangerous characters first
        if self._has_security_risks(canonical):
            raise RegionRuleError(f"Name contains dangerous characters: {canonical[:50]}...")

        # Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(f"Name too long: {len(canonical)} characters (max 150)")

        # THEN handle legitimate edge cases
        if len(canonical.strip()) == 1:
            # Single character names are edge cases but valid
            self.logger.warning(f"Single character name: {canonical}")

        # Apply region-specific validation here
        pass

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for E5 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Simple sort by family name
        if ", " in canonical:
            family = canonical.split(", ")[0]
            return family.lower()

        return canonical.lower()

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated
            parts = name.split(None, 1)
            if len(parts) >= 2:
                components["given_name"] = parts[0].strip()
                components["family_name"] = parts[1].strip()
            else:
                components["family_name"] = name.strip()
                components["given_name"] = ""

        return components
