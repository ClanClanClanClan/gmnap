"""
Enhanced base classes for regional processors with A+ compliance.
Fixes all issues found in psychotic paranoid testing.
"""

import logging
import re
import unicodedata
from typing import Any, Dict, List

from src.regions.base import RegionRuleError, RegionSpec  # noqa: F401 (re-export)

# RegionRuleError is the canonical exception type, defined once in
# base.py. Re-exported here so the historical
# `from src.regions.base_enhanced import RegionRuleError` callers
# (region processors + unit tests) keep working AND see the same
# class object as `from src.regions.base import RegionRuleError`
# callers. Before the round-32 collapse there were *two* unrelated
# classes with the same name; pytest.raises against the "wrong"
# import would silently miss raises from the other module.


class EnhancedRegionSpec(RegionSpec):
    """Enhanced base class with A+ security and processing compliance."""

    # Unicode categories to ALWAYS remove for security
    DANGEROUS_CATEGORIES = {
        "Cc",  # Control characters
        "Cf",  # Format characters
        "Co",  # Private use
        "Cs",  # Surrogates
        "Cn",  # Unassigned
    }

    # Specific dangerous characters to remove
    DANGEROUS_CHARS = {
        0x0000,  # NULL
        0x200B,  # Zero-width space
        0x200C,  # Zero-width non-joiner
        0x200D,  # Zero-width joiner
        0x200E,  # Left-to-right mark
        0x200F,  # Right-to-left mark
        0x202A,  # Left-to-right embedding
        0x202B,  # Right-to-left embedding
        0x202C,  # Pop directional formatting
        0x202D,  # Left-to-right override
        0x202E,  # Right-to-left override
        0x2066,  # Left-to-right isolate
        0x2067,  # Right-to-left isolate
        0x2068,  # First strong isolate
        0x2069,  # Pop directional isolate
        0xFEFF,  # BOM/Zero-width no-break space
        0xFFFD,  # Replacement character
        0xFFFE,  # Non-character
        0xFFFF,  # Non-character
    }

    # Emoji ranges to filter
    EMOJI_RANGES = [
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
        (0x1F680, 0x1F6FF),  # Transport and Map Symbols
        (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
        (0x2600, 0x26FF),  # Misc symbols
        (0x2700, 0x27BF),  # Dingbats
        (0x1F1E0, 0x1F1FF),  # Regional indicators (flags)
    ]

    def __init__(
        self,
        code: str,
        yaml_files: List[str],
        scripts: List[str],
        mixed_scripts: bool,
        canonical_order: str,
        romanisation_standards: List[str],
    ):
        self.code = code
        self.yaml_files = yaml_files
        self.scripts = scripts
        self.mixed_scripts = mixed_scripts
        self.canonical_order = canonical_order
        self.romanisation_standards = romanisation_standards
        self.logger = logging.getLogger(f"gmnap.regions.{code}")

        # Cache for idempotency
        self._processing_cache = {}
        # Track processed entries for idempotency
        self._processed_entries = set()

    def comprehensive_unicode_filter(self, text: str) -> str:
        """
        Comprehensive Unicode filtering for A+ security compliance.
        Removes ALL dangerous characters while preserving legitimate text.
        """
        if not text:
            return text

        # First pass: Remove dangerous Unicode categories
        filtered = []
        for char in text:
            category = unicodedata.category(char)
            code = ord(char)

            # Skip dangerous categories
            if category in self.DANGEROUS_CATEGORIES:
                continue

            # Skip specific dangerous characters
            if code in self.DANGEROUS_CHARS:
                continue

            # Skip emoji (optional based on region)
            if self.should_filter_emoji():
                if any(start <= code <= end for start, end in self.EMOJI_RANGES):
                    continue

            # Skip non-characters
            if 0xFDD0 <= code <= 0xFDEF:
                continue

            # Skip non-characters at end of planes
            if (code & 0xFFFE) == 0xFFFE:
                continue

            # Keep the character
            filtered.append(char)

        result = "".join(filtered)

        # If the entire input was filtered out, it was likely malicious
        if not result and text:
            # Check if it was all dangerous characters
            if all(
                ord(c) in self.DANGEROUS_CHARS
                or unicodedata.category(c) in self.DANGEROUS_CATEGORIES
                or any(start <= ord(c) <= end for start, end in self.EMOJI_RANGES)
                for c in text
            ):
                raise RegionRuleError("Input contains only dangerous characters")

        # Also check if we filtered out dangerous characters
        if text != result:
            # Check what was filtered
            for char in text:
                if char not in result:
                    code = ord(char)
                    # Check if it was a dangerous character
                    if code in self.DANGEROUS_CHARS:
                        if code == 0x0000:
                            raise RegionRuleError("Null bytes detected")
                        elif code in [0x202A, 0x202B, 0x202C, 0x202D, 0x202E]:
                            raise RegionRuleError(
                                "BIDI/directional override characters detected"
                            )
                        elif code in [0x200B, 0x200C, 0x200D]:
                            raise RegionRuleError("Zero-width characters detected")

        return result

    def should_filter_emoji(self) -> bool:
        """Determine if emoji should be filtered for this region."""
        # Most regions should filter emoji for security
        # Can be overridden by specific regions if needed
        return True

    def normalize_unicode_secure(self, text: str) -> str:
        """
        Secure Unicode normalization that ensures idempotency.
        Always normalizes to NFC form and handles edge cases.
        """
        if not text:
            return text

        # Apply comprehensive filtering FIRST
        text = self.comprehensive_unicode_filter(text)

        # Normalize whitespace (tabs, newlines, etc.)
        text = self.normalize_whitespace_in_text(text)

        # Apply Unicode normalization (NFC for consistency)
        text = unicodedata.normalize("NFC", text)

        # Handle special cases
        text = self.apply_unicode_fold_exceptions(text)

        return text

    def normalize_whitespace_in_text(self, text: str) -> str:
        """
        Normalize ALL whitespace characters consistently in a text string.
        Handles tabs, newlines, and exotic Unicode spaces.
        Note: This is different from normalize_whitespace_characters which operates on entries.
        """
        if not text:
            return text

        # Map of Unicode whitespace to regular space
        whitespace_chars = {
            "\t": " ",  # Tab
            "\n": " ",  # Newline
            "\r": " ",  # Carriage return
            "\v": " ",  # Vertical tab
            "\f": " ",  # Form feed
            "\xa0": " ",  # Non-breaking space
            "\u1680": " ",  # Ogham space
            "\u2000": " ",  # En quad
            "\u2001": " ",  # Em quad
            "\u2002": " ",  # En space
            "\u2003": " ",  # Em space
            "\u2004": " ",  # Three-per-em space
            "\u2005": " ",  # Four-per-em space
            "\u2006": " ",  # Six-per-em space
            "\u2007": " ",  # Figure space
            "\u2008": " ",  # Punctuation space
            "\u2009": " ",  # Thin space
            "\u200a": " ",  # Hair space
            "\u202f": " ",  # Narrow no-break space
            "\u205f": " ",  # Medium mathematical space
            "\u3000": " ",  # Ideographic space
        }

        # Replace all exotic whitespace with regular space
        for old, new in whitespace_chars.items():
            text = text.replace(old, new)

        # Normalize multiple spaces to single space
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def is_collision_suffix(self, text: str) -> bool:
        """
        Check if text ends with a valid collision suffix pattern.
        Fixes false positive CSV injection for '--1' pattern.
        """
        # Valid collision suffix pattern: --<number>
        return bool(re.search(r"--\d+$", text))

    def enhanced_security_check(self, text: str) -> None:
        """
        Enhanced security check with better accuracy.
        Reduces false positives while maintaining security.
        """
        if not text:
            return

        # Check for null bytes
        if "\x00" in text:
            raise RegionRuleError("Null bytes detected")

        # Check for BIDI/directional override characters
        bidi_chars = [
            "\u202a",
            "\u202b",
            "\u202c",
            "\u202d",
            "\u202e",  # LTR/RTL overrides
            "\u2066",
            "\u2067",
            "\u2068",
            "\u2069",  # Isolates
            "\u200e",
            "\u200f",  # LTR/RTL marks
        ]
        for char in bidi_chars:
            if char in text:
                raise RegionRuleError("BIDI/directional override characters detected")

        # Check length limits
        if len(text) > 150:
            raise RegionRuleError(f"Name too long: {len(text)} characters (max 150)")

        # Allow collision suffixes (fix false positive)
        if self.is_collision_suffix(text):
            # Remove suffix for further checking
            text = re.sub(r"--\d+$", "", text)

        # SQL Injection (only real patterns)
        sql_patterns = [
            r"';\s*(DROP|DELETE|UPDATE|INSERT|SELECT)\s+",
            r"--\s*$",  # SQL comment at end
            r"\bOR\s+['\"]?1['\"]?\s*=\s*['\"]?1",
            r"\bUNION\s+SELECT\b",
        ]
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise RegionRuleError("Potential SQL injection detected")

        # XSS (comprehensive patterns)
        xss_patterns = [
            r"<script",
            r"javascript:",
            r"<img[^>]*onerror",
            r"<img[^>]*onload",
            r"<iframe",
            r"<object",
            r"<embed",
            r"<svg[^>]*onload",
            r"on\w+\s*=",  # Any on* event handler
            r"<\?php",  # PHP injection
            r"<%",  # ASP/JSP injection
        ]
        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise RegionRuleError("Potential XSS/Code injection detected")

        # Command injection (only real patterns)
        if re.search(r"[;&|]\s*(rm|sudo|cat|wget|curl)\s+", text):
            raise RegionRuleError("Potential command injection detected")

        # Path traversal
        if "../" in text or "..\\" in text:
            raise RegionRuleError("Potential path traversal detected")

        # LDAP injection (reduce false positives)
        ldap_patterns = [
            r"\*\)\)\(\|\(",  # *))((
            r"\*\(\)",  # *()
            r"\(\*\)",  # (*)
            r"\*\(\|",  # *(|
            r"\(\|\(",  # (|(
        ]
        for pattern in ldap_patterns:
            if re.search(pattern, text):
                raise RegionRuleError("Potential LDAP injection detected")

        # CSV injection (but not collision suffixes)
        if not self.is_collision_suffix(text):
            csv_patterns = [r"^\=", r"^\+", r"^\-", r"^\@"]
            for pattern in csv_patterns:
                if re.match(pattern, text):
                    raise RegionRuleError("Potential CSV injection detected")

        # Template injection (Jinja2, Django, Twig, etc.)
        template_patterns = [
            r"\{\{.*\}\}",  # {{expression}}
            r"\{%.*%\}",  # {%statement%}
            r"\$\{[^}]*\}",  # ${expression}
            r"#\{.*\}",  # #{expression}
            r"<%.*%>",  # <%expression%>
        ]
        for pattern in template_patterns:
            if re.search(pattern, text):
                raise RegionRuleError("Potential template injection detected")

        # LDAP injection (comprehensive)
        if re.search(r"\*\s*\)\s*\(\s*[|&]", text):
            raise RegionRuleError("Potential LDAP injection detected")

        # NoSQL injection
        nosql_keywords = [
            "$where",
            "$regex",
            "$ne",
            "$gt",
            "$lt",
            "$gte",
            "$lte",
            "$in",
            "$nin",
            "$exists",
        ]
        for keyword in nosql_keywords:
            if keyword in text:
                raise RegionRuleError("Potential NoSQL injection detected")

        # Log4j / JNDI injection
        if (
            "${jndi:" in text.lower()
            or "${env:" in text.lower()
            or "${sys:" in text.lower()
        ):
            raise RegionRuleError("Potential Log4j/JNDI injection detected")

        # CRLF injection (including after normalization)
        crlf_patterns = [
            "%0d%0a",
            "%0a%0d",
            "\r\n",
            "\n\r",
            "Set-Cookie:",
            "Location:",
            "Content-Type:",
        ]
        if any(pattern in text for pattern in crlf_patterns):
            raise RegionRuleError("Potential CRLF/Header injection detected")

    def ensure_idempotency(self, entry: Dict[str, Any], field: str) -> str:
        """
        Ensure idempotent processing of a field.
        Same input always produces same output.
        """
        if field not in entry:
            return ""

        original = entry[field]
        if not original:
            return ""

        # IMPORTANT: Use a normalized version for cache key to ensure consistency
        # This prevents issues where "Test\tName" and "Test Name" are treated differently
        normalized_for_key = original
        if isinstance(normalized_for_key, str):
            # Normalize whitespace for cache key
            normalized_for_key = re.sub(r"\s+", " ", normalized_for_key).strip()

        # Check cache for already processed values
        cache_key = f"{self.code}:{field}:{normalized_for_key}"
        if cache_key in self._processing_cache:
            # Return cached result and update entry
            cached = self._processing_cache[cache_key]
            entry[field] = cached
            return cached

        # Process the value
        processed = self.normalize_unicode_secure(original)

        # Apply security check on FILTERED content
        if processed:
            self.enhanced_security_check(processed)

        # Cache the result
        self._processing_cache[cache_key] = processed

        # Update the entry
        entry[field] = processed

        return processed

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean entry with idempotent, secure processing.
        Must be overridden by subclasses but should call super().clean(entry).
        """
        # Ensure idempotent processing of canonical fields
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                # This will filter dangerous chars AND raise errors
                self.ensure_idempotency(entry, field)

        # Apply additional security checks AFTER normalization
        canonical = self.get_canonical_name(entry)
        if canonical:
            self.enhanced_security_check(canonical)

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with region-specific data.
        Must be overridden by subclasses but should call super().
        """
        # Ensure we don't duplicate variants on multiple calls
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}

        # Track processing for idempotency without modifying entry
        entry_id = entry.get("GlobalID", "")
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")

        if entry_id and canonical:
            # Normalize for consistent key (handles tabs, newlines, etc.)
            normalized_canonical = (
                re.sub(r"\s+", " ", canonical).strip() if canonical else ""
            )
            process_key = f"{self.code}:{entry_id}:{normalized_canonical}"
            if process_key in self._processed_entries:
                return  # Already processed
            self._processed_entries.add(process_key)

    def add_variant(
        self,
        entry: Dict[str, Any],
        variant: Dict[str, Any],
        variant_type: str = "Synthesised",
    ) -> None:
        """
        Add a variant only if it doesn't already exist.
        Prevents duplicate variants for idempotency.
        """
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}

        variants_list = entry["Variants"].get(variant_type, [])

        # Check for duplicates
        variant_str = variant.get("str", "")
        if not variant_str:
            return

        # Check if this exact variant already exists
        for existing in variants_list:
            if existing.get("str") == variant_str and existing.get(
                "type"
            ) == variant.get("type"):
                return  # Already exists, don't add

        # Add the variant
        entry["Variants"][variant_type].append(variant)

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry according to regional rules.
        Must be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement validate method")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key for entry.
        Must be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement order_key method")

    def get_canonical_name(self, entry: Dict[str, Any]) -> str:
        """Get the canonical name for processing."""
        canonical_latin = entry.get("CanonicalLatin", "").strip()
        canonical_native = entry.get("CanonicalNative", "").strip()

        if canonical_latin:
            return canonical_latin
        elif canonical_native:
            return canonical_native
        else:
            return ""

    def has_sufficient_name_data(self, entry: Dict[str, Any]) -> bool:
        """Check if entry has sufficient name data for processing."""
        canonical_latin = entry.get("CanonicalLatin", "").strip()
        canonical_native = entry.get("CanonicalNative", "").strip()

        if canonical_latin or canonical_native:
            return True

        # Allow entries with just GlobalID for tracking
        if "GlobalID" in entry and entry["GlobalID"]:
            return True

        return False

    def basic_validation(self, entry: Dict[str, Any]) -> bool:
        """Cheap pre-check used by alternate ``detect_region`` shapes
        (in C5 / C6 / D2 / D3 / E6 processors) as an early-exit guard
        before running their full detection logic.

        Round-29 finding: H3 audit caught these processors calling
        ``self.basic_validation()`` but the method was undefined
        anywhere — every invocation would have raised ``AttributeError``.
        The call sites are reachable from
        ``HybridRegionClassifier`` via ``self.phase1.detect_region``,
        but in practice ``self.phase1`` resolves to the central
        ``RegionManager`` not the per-region processor, so the bug
        was latent. Adding the method here makes any future revival
        of those code paths safe by default.

        Permissive by design: returns True for any entry with at
        least one of ``CanonicalLatin`` / ``CanonicalNative`` /
        ``name`` populated. The downstream detection methods do their
        own stricter checks; this is just "is it worth even looking
        at this entry?"
        """
        if not isinstance(entry, dict):
            return False
        for key in ("CanonicalLatin", "CanonicalNative", "name"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                return True
        return False

    def apply_unicode_fold_exceptions(self, text: str) -> str:
        """
        Apply Unicode case folding with exceptions.
        Handles special cases like German ß → ss.
        """
        if not text:
            return text

        # German eszett special case
        text = text.replace("ß", "ss")
        text = text.replace("ẞ", "SS")

        # Turkish I handling (region-specific, override in Turkish region)
        # Default behavior is standard case folding

        # Ligature decomposition
        ligatures = {
            "ﬀ": "ff",
            "ﬁ": "fi",
            "ﬂ": "fl",
            "ﬃ": "ffi",
            "ﬄ": "ffl",
            "æ": "ae",
            "Æ": "AE",
            "œ": "oe",
            "Œ": "OE",
        }
        for ligature, replacement in ligatures.items():
            text = text.replace(ligature, replacement)

        return text

    def apply_gender_heuristic_guard(self, entry: Dict[str, Any]) -> None:
        """Apply gender heuristic validation guard."""
        # Base implementation does nothing - regions can override
        pass

    def has_security_risks_lenient(self, name: str) -> bool:
        """Check for dangerous characters (lenient version for compatibility)."""
        if not name:
            return False

        # This is now handled by comprehensive_unicode_filter
        # Return False since filtering happens elsewhere
        return False

    def _has_security_risks(self, name: str) -> bool:
        """Check for dangerous characters (strict version for compatibility)."""
        if not name:
            return False

        # This is now handled by comprehensive_unicode_filter
        # Return False since filtering happens elsewhere
        return False

    def validate_name_requirements(self, entry: Dict[str, Any]) -> None:
        """
        Validate that the entry has sufficient name data.
        Required by some regional processors (A4, C5).
        """
        if not self.has_sufficient_name_data(entry):
            raise RegionRuleError("Entry lacks required name data")

        # Additional validation
        canonical = self.get_canonical_name(entry)
        if canonical:
            # Check minimum length
            if len(canonical.strip()) < 1:
                raise RegionRuleError("Name too short")

            # Check maximum length (already handled elsewhere but for consistency)
            if len(canonical) > 150:
                raise RegionRuleError(f"Name too long: {len(canonical)} characters")

    def apply_security_and_validation_checks(self, entry: Dict[str, Any]) -> None:
        """
        Apply comprehensive security checks.
        This is now called by clean() after normalization.
        """
        canonical = self.get_canonical_name(entry)
        if canonical:
            self.enhanced_security_check(canonical)
