"""
GMNAP Security Module - Script Injection & Attack Prevention

This module provides system-wide security filtering to protect against:
- Script injections (HTML, JavaScript, SQL, etc.)
- Control character attacks
- Buffer overflow attempts
- Unicode normalization attacks
- Path traversal attempts
- Binary data injection

All regional processors should use these security functions to ensure
comprehensive protection against malicious input.
"""

import re
import unicodedata
import html
from typing import Any, Dict
from urllib.parse import unquote


class SecurityError(Exception):
    """Raised when malicious input is detected."""

    pass


class SecurityFilter:
    """
    Centralized security filtering for GMNAP.

    Provides comprehensive protection against various attack vectors
    while preserving legitimate name data across all writing systems.
    """

    def __init__(self):
        # Dangerous HTML/Script patterns
        self.script_patterns = [
            # JavaScript execution
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"vbscript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),  # onload=, onclick=, etc.
            # HTML injection
            re.compile(r"<iframe[^>]*>", re.IGNORECASE),
            re.compile(r"<object[^>]*>", re.IGNORECASE),
            re.compile(r"<embed[^>]*>", re.IGNORECASE),
            re.compile(r"<applet[^>]*>", re.IGNORECASE),
            re.compile(r"<meta[^>]*>", re.IGNORECASE),
            re.compile(r"<link[^>]*>", re.IGNORECASE),
            # Data URLs and other dangerous schemes
            re.compile(r"data:\s*text/html", re.IGNORECASE),
            re.compile(r"data:\s*application/", re.IGNORECASE),
            # SQL injection patterns
            re.compile(
                r"\b(union|select|insert|update|delete|drop|alter|create|exec|execute)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r'[\'";]\s*(or|and)\s+[\'"]?1[\'"]?\s*=\s*[\'"]?1', re.IGNORECASE
            ),
            re.compile(
                r'[\'";]\s*(or|and)\s+[\'"]?\w+[\'"]?\s*=\s*[\'"]?\w+', re.IGNORECASE
            ),
            # LDAP injection
            re.compile(r"[()=*&|!]+", re.IGNORECASE),
            # Command injection
            re.compile(r"[;&|`$(){}[\]\\]"),
            re.compile(r"\$\{[^}]*\}"),  # Variable expansion
            re.compile(
                r"%[0-9a-f]{2}", re.IGNORECASE
            ),  # URL encoding of dangerous chars
            # Path traversal
            re.compile(r"\.\.[\\/]"),
            re.compile(r"[\\/]\.\."),
            # Template/expression injection
            re.compile(r"\{\{.*?\}\}"),  # Django/Jinja2 templates
            re.compile(r"\$\{.*?\}"),  # Spring EL, etc.
            re.compile(r"#{.*?}"),  # Various expression languages
        ]

        # Dangerous control characters (except safe whitespace)
        self.dangerous_controls = set(range(0, 32)) - {
            9,
            10,
            13,
            32,
        }  # Exclude \t, \n, \r, space

        # Common attack strings
        self.attack_strings = {
            # XSS vectors
            "alert(",
            "prompt(",
            "confirm(",
            "document.",
            "window.",
            "eval(",
            "function(",
            "settimeout",
            "setinterval",
            # SQL injection
            "' or '",
            '" or "',
            "' union ",
            '" union ',
            "drop table",
            "select * from",
            "insert into",
            "update set",
            "delete from",
            # Command injection
            "/bin/",
            "/usr/bin/",
            "cmd.exe",
            "powershell",
            "bash",
            "rm -rf",
            "del /f",
            "format c:",
            "shutdown",
            # File inclusion
            "/etc/passwd",
            "/etc/shadow",
            "windows/system32",
            "boot.ini",
            "web.config",
            ".htaccess",
            # Common payloads
            "<svg/onload=",
            "<img/src=x/onerror=",
            "<?php",
            "<%=",
            "<%= %>",
            "eval(base64_decode",
            "system(",
            "shell_exec(",
            "passthru(",
        }

        # Maximum reasonable lengths for name components
        self.max_lengths = {
            "name_total": 500,  # Total name length
            "single_field": 200,  # Single field (family/given name)
            "variant": 300,  # Variant string
            "particle": 50,  # Name particle
            "title": 100,  # Title/honorific
        }

        # Unicode normalization attack patterns
        self.dangerous_unicode = [
            "\u200e",  # Left-to-right mark
            "\u200f",  # Right-to-left mark
            "\u202a",  # Left-to-right embedding
            "\u202b",  # Right-to-left embedding
            "\u202c",  # Pop directional formatting
            "\u202d",  # Left-to-right override
            "\u202e",  # Right-to-left override
            "\u2066",  # Left-to-right isolate
            "\u2067",  # Right-to-left isolate
            "\u2068",  # First strong isolate
            "\u2069",  # Pop directional isolate
            "\ufeff",  # Zero width no-break space (BOM)
            "\u00ad",  # Soft hyphen
        ]

    def scan_for_attacks(self, text: str, context: str = "unknown") -> None:
        """
        Scan text for malicious patterns and raise SecurityError if found.

        Args:
            text: Text to scan
            context: Context description for error reporting

        Raises:
            SecurityError: If malicious content is detected
        """
        if not isinstance(text, str):
            return  # Only scan strings

        # Check for dangerous control characters
        for char in text:
            if ord(char) in self.dangerous_controls:
                raise SecurityError(
                    f"Dangerous control character detected in {context}: "
                    f"U+{ord(char):04X} at position {text.index(char)}"
                )

        # Check for dangerous Unicode characters
        for char in self.dangerous_unicode:
            if char in text:
                raise SecurityError(
                    f"Dangerous Unicode character detected in {context}: "
                    f"U+{ord(char):04X} ({repr(char)})"
                )

        # Check text length
        if len(text) > self.max_lengths["name_total"]:
            raise SecurityError(
                f"Suspiciously long input in {context}: {len(text)} chars "
                f"(max {self.max_lengths['name_total']})"
            )

        # Normalize for consistent analysis
        normalized = text.lower()

        # Check for attack strings
        for attack_string in self.attack_strings:
            if attack_string in normalized:
                raise SecurityError(
                    f"Potential attack string detected in {context}: '{attack_string}'"
                )

        # Check for script injection patterns
        for pattern in self.script_patterns:
            if pattern.search(text):
                match = pattern.search(text)
                raise SecurityError(
                    f"Script injection pattern detected in {context}: "
                    f"'{match.group()[:50]}...'"
                )

        # Check for excessive special characters (potential obfuscation)
        special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if special_count > len(text) * 0.3:  # More than 30% special chars
            raise SecurityError(
                f"Excessive special characters in {context}: "
                f"{special_count}/{len(text)} ({special_count/len(text)*100:.1f}%)"
            )

        # Check for repeated identical characters (potential buffer overflow)
        for char in set(text):
            if text.count(char) > 50:  # More than 50 of same character
                raise SecurityError(
                    f"Excessive character repetition in {context}: "
                    f"'{char}' appears {text.count(char)} times"
                )

    def sanitize_string(self, text: str, preserve_unicode: bool = True) -> str:
        """
        Sanitize string while preserving legitimate name data.

        Args:
            text: Text to sanitize
            preserve_unicode: Whether to preserve Unicode name characters

        Returns:
            Sanitized text
        """
        if not isinstance(text, str):
            return str(text)

        # Remove dangerous Unicode directional/formatting characters
        for char in self.dangerous_unicode:
            text = text.replace(char, "")

        # Remove/escape HTML entities
        text = html.unescape(text)

        # URL decode any encoded content
        try:
            decoded = unquote(text)
            if decoded != text:
                # If URL decoding changed the string, scan the decoded version
                self.scan_for_attacks(decoded, "URL-decoded content")
                text = decoded
        except:
            pass  # Keep original if decoding fails

        # Normalize Unicode if preserving international characters
        if preserve_unicode:
            text = unicodedata.normalize("NFC", text)
        else:
            # Convert to ASCII, removing diacritics
            text = unicodedata.normalize("NFD", text)
            text = "".join(c for c in text if ord(c) < 128)

        # Remove null bytes and dangerous control characters
        text = "".join(c for c in text if ord(c) not in self.dangerous_controls)

        # Limit length
        if len(text) > self.max_lengths["name_total"]:
            text = text[: self.max_lengths["name_total"]]

        return text.strip()

    def validate_entry(
        self, entry: Dict[str, Any], region_code: str = "unknown"
    ) -> None:
        """
        Validate entire entry dictionary for security threats.

        Args:
            entry: Entry dictionary to validate
            region_code: Region code for context

        Raises:
            SecurityError: If malicious content is detected
        """

        def scan_recursive(obj: Any, path: str = "root"):
            """Recursively scan all string values in nested data structure."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Scan the key itself
                    if isinstance(key, str):
                        self.scan_for_attacks(key, f"{path}.key[{key}]")
                    # Scan the value
                    scan_recursive(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_recursive(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                self.scan_for_attacks(obj, f"{region_code}:{path}")

        # Scan entire entry structure
        try:
            scan_recursive(entry, f"entry")
        except SecurityError as e:
            # Add region context to error
            raise SecurityError(f"Security violation in region {region_code}: {e}")

    def secure_clean_name(self, name: str, field_name: str = "name") -> str:
        """
        Securely clean a name field with comprehensive protection.

        Args:
            name: Name string to clean
            field_name: Field name for error context

        Returns:
            Cleaned name string

        Raises:
            SecurityError: If malicious content is detected
        """
        if not isinstance(name, str):
            raise SecurityError(
                f"Name field {field_name} must be string, got {type(name).__name__}"
            )

        if not name:
            return name

        # Security scan first
        self.scan_for_attacks(name, field_name)

        # Sanitize the string
        cleaned = self.sanitize_string(name, preserve_unicode=True)

        # Final validation on cleaned string
        if cleaned != name:
            # If sanitization changed the string significantly, be suspicious
            similarity = len(set(cleaned) & set(name)) / max(
                len(set(cleaned)), len(set(name)), 1
            )
            if similarity < 0.7:  # Less than 70% character similarity
                raise SecurityError(
                    f"Suspicious content removed from {field_name}: "
                    f"similarity {similarity:.1%}"
                )

        return cleaned


# Global security filter instance
security_filter = SecurityFilter()


def secure_validate_entry(entry: Dict[str, Any], region_code: str = "unknown") -> None:
    """
    Convenience function to validate entry security.

    Args:
        entry: Entry to validate
        region_code: Region code for context

    Raises:
        SecurityError: If security threats detected
    """
    security_filter.validate_entry(entry, region_code)


def secure_clean_name(name: str, field_name: str = "name") -> str:
    """
    Convenience function to securely clean name strings.

    Args:
        name: Name to clean
        field_name: Field name for context

    Returns:
        Cleaned name string

    Raises:
        SecurityError: If security threats detected
    """
    return security_filter.secure_clean_name(name, field_name)


def scan_for_attacks(text: str, context: str = "unknown") -> None:
    """
    Convenience function to scan text for attacks.

    Args:
        text: Text to scan
        context: Context for error reporting

    Raises:
        SecurityError: If attacks detected
    """
    security_filter.scan_for_attacks(text, context)
