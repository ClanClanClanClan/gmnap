"""
Context-aware security validation for GMNAP
ULTRAFIX Phase 8: Prevents path patterns and emoji-only names in name fields
"""

import re
import unicodedata


class ContextAwareSecurityValidator:
    """Security validator that understands context of different fields"""

    def __init__(self):
        # Path-like patterns that should NEVER appear in names
        self.path_patterns = [
            r"^[A-Za-z]:[/\\]",  # Windows absolute paths (C:\, D:/, etc)
            r"^/[a-zA-Z]",  # Unix absolute paths starting with /
            r"[/\\]{2,}",  # Multiple slashes/backslashes
            r"\.\.[/\\]",  # Directory traversal
            r"[/\\]etc[/\\]",  # Unix system paths
            r"[/\\]windows[/\\]",  # Windows system paths
            r"[/\\]system32[/\\]",  # Windows system paths
            r"[/\\]Users[/\\]",  # User directories
            r"[/\\]home[/\\]",  # Unix home directories
            r"[/\\]var[/\\]",  # Unix var directories
            r"[/\\]tmp[/\\]",  # Temp directories
        ]
        self.compiled_path_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.path_patterns
        ]

    def validate_name_field(self, value: str, field: str = "name") -> tuple[bool, str]:
        """
        Validate that a name field doesn't contain suspicious patterns.

        Returns:
            (is_valid, reason) - True if valid, False with reason if not
        """
        if not isinstance(value, str):
            return True, "Not a string, handled elsewhere"

        # 1. Check for path-like patterns
        for pattern in self.compiled_path_patterns:
            if pattern.search(value):
                return False, f"Path pattern detected in {field}"

        # 2. Check for file extensions
        if re.search(
            r"\.(exe|bat|sh|cmd|com|scr|vbs|js|jar|pdf|doc|xls)$", value, re.IGNORECASE
        ):
            return False, f"File extension detected in {field}"

        # 3. Check for emoji/symbol-only names
        # Count actual letters vs symbols/emojis
        letters = 0
        symbols = 0

        for char in value:
            category = unicodedata.category(char)
            if category[0] == "L":  # Letter
                letters += 1
            elif category in ["So", "Sm", "Sk", "Sc"]:  # Symbols
                symbols += 1

        # If it's all symbols/emojis (no letters), reject it
        if symbols > 0 and letters == 0:
            return False, f"Symbol-only {field} not allowed"

        # If symbols heavily outweigh letters (more than 50% symbols), reject
        total_chars = letters + symbols
        if total_chars > 0 and symbols / total_chars > 0.5:
            return False, f"Too many symbols in {field}"

        # 4. Check for protocol handlers
        if re.match(
            r"^(https?|ftp|file|javascript|data|vbscript):", value, re.IGNORECASE
        ):
            return False, f"Protocol handler in {field}"

        # 5. Check for HTML/script tags (even partial)
        if re.search(
            r"<[^>]+>|<script|</script|javascript:|onerror=", value, re.IGNORECASE
        ):
            return False, f"HTML/script pattern in {field}"

        return True, "Valid"

    def sanitize_for_name_context(self, value: str) -> str:
        """
        Sanitize a value specifically for name context.
        More aggressive than general sanitization.
        """
        if not isinstance(value, str):
            return str(value)

        # Remove any path separators
        value = re.sub(r"[/\\]", "", value)

        # Remove any protocol handlers
        value = re.sub(
            r"^(https?|ftp|file|javascript|data|vbscript):",
            "",
            value,
            flags=re.IGNORECASE,
        )

        # Remove file extensions
        value = re.sub(
            r"\.(exe|bat|sh|cmd|com|scr|vbs|js|jar)$", "", value, flags=re.IGNORECASE
        )

        # Remove excessive symbols (keep max 1 symbol between letters)
        value = re.sub(r"[^\w\s-]{2,}", "", value)

        return value.strip()


# Global instance
context_security = ContextAwareSecurityValidator()
