"""
Central security validation for GMNAP pipeline.
Prevents XSS, SQL injection, command injection, and other attacks.
"""

import re
import unicodedata
from typing import Any, Dict, List, Set
import logging

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Raised when security validation fails."""
    pass

class SecurityValidator:
    """Central security validation for all pipeline inputs."""
    
    def __init__(self):
        # Dangerous patterns that should never appear in names
        self.dangerous_patterns = [
            # SQL injection
            r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)",
            r"(?i)(/\*|\*/|;.*--|'.*or.*'|\".*or.*\"|^--|\s--\s|'.*--$)",  # Allow -- in names but not SQL comments
            
            # XSS/HTML injection  
            r"(?i)(<script|</script|<iframe|</iframe|<object|</object)",
            r"(?i)(<embed|<applet|<form|<input|<button)",
            r"(?i)(javascript:|vbscript:|data:|about:)",
            r"(?i)(onload|onclick|onerror|onmouseover)=",
            
            # Command injection
            r"(?i)(;.*rm\s|;.*del\s|;.*format|;.*shutdown)",
            r"(?i)(&&|\|\||`.*`|\$\(|\$\{)",
            
            # Path traversal
            r"\.\.[\\/]",
            r"(?i)(\/etc\/|\/proc\/|\/sys\/|c:\\\\windows|c:\\\\system)",
            
            # LDAP injection
            r"(?i)(\)\(|\*\)|=\*|=.*\*)",
            
            # XML/XXE
            r"(?i)(<!entity|<!doctype|<\?xml)",
            
            # Regex DoS (ReDoS) - excessive repetition
            r"(.)\1{30,}",  # Same character repeated 30+ times
            r"(a{30,}|b{30,}|c{30,}|d{30,}|e{30,}|f{30,}|g{30,}|h{30,}|i{30,}|j{30,})",  # Long sequences
            
            # Template injection patterns
            r"\{\{.*\}\}",  # Jinja2/Angular style {{expression}}
            r"\${.*}",      # ES6/JSP style ${expression}
            r"<%.*%>",      # ERB/ASP style <%expression%>
            r"#\{.*\}",     # Ruby style #{expression}
            r"\[%.*%\]",    # Perl Template Toolkit style [%expression%]
            r"@\(.*\)",     # Razor syntax @(expression)
            
            # NoSQL injection patterns
            r"(?i)(\$where|\$gt|\$lt|\$ne|\$eq|\$regex|\$exists|\$type|\$expr)",
            r"(?i)({.*:.*})",  # MongoDB-style queries
            
            # Server-Side Request Forgery (SSRF) patterns
            r"(?i)(file://|gopher://|dict://|ftp://|sftp://|ldap://)",
            r"(?i)(localhost|127\.0\.0\.1|0\.0\.0\.0|::1)",
            r"(?i)(169\.254\.|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)",  # Private IPs
            
            # CSV injection patterns
            r"^[=+\-@]",  # Formula injection in spreadsheets
            r"(?i)(=cmd|=calc|=notepad|=powershell)",
            
            # Unicode direction override attacks
            r"[\u202A-\u202E\u2066-\u2069]",  # BiDi override characters
            
            # Null byte injection
            r"%00|\\x00|\\0",
            
            # Log injection patterns
            r"[\r\n].*\[(ERROR|WARNING|INFO|DEBUG)\]",  # Fake log entries
            r"\\r\\n|%0d%0a|%0D%0A",  # CRLF injection
            
            # Email header injection
            r"(?i)(bcc:|cc:|to:|from:|subject:|reply-to:)",
            
            # GraphQL injection patterns
            r"(?i)(__schema|__type|mutation|subscription)",
            r"\.\.\.",  # GraphQL spread syntax abuse
            
            # YAML/JSON specific patterns
            r"!!python/|!!ruby/",  # YAML tags for code execution
            r"__proto__|constructor|prototype",  # Prototype pollution
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = [re.compile(pattern) for pattern in self.dangerous_patterns]
        
        # Dangerous control characters (except safe whitespace)
        self.dangerous_controls = set(range(0, 32)) - {9, 10, 13, 32}  # Allow tab, LF, CR, space
        
        # Unicode categories that might be problematic
        self.dangerous_categories = {
            'Cc',  # Control characters
            'Cf',  # Format characters (except safe ones)
            'Co',  # Private use
            'Cs',  # Surrogates
            'Cn',  # Unassigned
        }
        
        # Safe format characters (zero-width joiners, etc.)
        self.safe_format_chars = {
            0x200C,  # Zero Width Non-Joiner
            0x200D,  # Zero Width Joiner
            0x061C,  # Arabic Letter Mark
        }
        
        # Homograph attack patterns - Cyrillic lookalikes for Latin
        self.homograph_mappings = {
            'А': 'A',  # Cyrillic A -> Latin A
            'В': 'B',  # Cyrillic Ve -> Latin B
            'С': 'C',  # Cyrillic Es -> Latin C
            'Е': 'E',  # Cyrillic Ye -> Latin E
            'Н': 'H',  # Cyrillic En -> Latin H
            'І': 'I',  # Cyrillic I -> Latin I
            'Ј': 'J',  # Cyrillic Je -> Latin J
            'К': 'K',  # Cyrillic Ka -> Latin K
            'М': 'M',  # Cyrillic Em -> Latin M
            'О': 'O',  # Cyrillic O -> Latin O
            'Р': 'P',  # Cyrillic Er -> Latin P
            'Т': 'T',  # Cyrillic Te -> Latin T
            'Х': 'X',  # Cyrillic Kha -> Latin X
            'У': 'Y',  # Cyrillic U -> Latin Y
            'а': 'a',  # Cyrillic a -> Latin a
            'с': 'c',  # Cyrillic es -> Latin c
            'е': 'e',  # Cyrillic ye -> Latin e
            'о': 'o',  # Cyrillic o -> Latin o
            'р': 'p',  # Cyrillic er -> Latin p
            'х': 'x',  # Cyrillic kha -> Latin x
            'у': 'y',  # Cyrillic u -> Latin y
            'ӏ': 'l',  # Cyrillic palochka -> Latin l
        }
    
    def validate_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize an entire entry.
        
        Args:
            entry: Dictionary representing a person entry
            
        Returns:
            Sanitized entry
            
        Raises:
            SecurityError: If entry contains dangerous content
        """
        sanitized = {}
        
        for key, value in entry.items():
            if isinstance(value, str):
                sanitized[key] = self.validate_string(value, context=key)
            elif isinstance(value, dict):
                sanitized[key] = self.validate_entry(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.validate_string(item, context=key) if isinstance(item, str) 
                    else self.validate_entry(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def validate_string(self, text: str, context: str = "unknown") -> str:
        """
        Validate and sanitize a string value.
        
        Args:
            text: String to validate
            context: Context for better error messages
            
        Returns:
            Sanitized string
            
        Raises:
            SecurityError: If string contains dangerous content
        """
        if not isinstance(text, str):
            raise SecurityError(f"Expected string, got {type(text).__name__} in {context}")
        
        # Check for dangerous patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                logger.warning(f"Dangerous pattern detected in {context}: {pattern.pattern}")
                raise SecurityError(f"Dangerous pattern detected in {context}")
        
        # Check for dangerous control characters
        for char in text:
            char_code = ord(char)
            if char_code in self.dangerous_controls:
                raise SecurityError(f"Dangerous control character (\\x{char_code:02x}) in {context}")
        
        # Check for dangerous Unicode categories
        for char in text:
            category = unicodedata.category(char)
            if category in self.dangerous_categories:
                char_code = ord(char)
                # Allow safe format characters
                if char_code not in self.safe_format_chars:
                    raise SecurityError(f"Dangerous Unicode character (U+{char_code:04X}, {category}) in {context}")
        
        # Check for homograph attacks
        self._check_homograph_attack(text, context)
        
        # Check for excessive combining characters (like Ä̈)
        self._check_combining_character_attack(text, context)
        
        # Check for encoded attacks
        self._check_encoded_attacks(text, context)
        
        # Check for polyglot attacks
        self._check_polyglot_attacks(text, context)
        
        # Check for timing attacks
        self._check_timing_attacks(text, context)
        
        # Normalize Unicode to prevent normalization attacks
        normalized = unicodedata.normalize('NFC', text)
        
        # Length check to prevent buffer overflow
        if len(normalized) > 1000:  # Reasonable limit for names
            raise SecurityError(f"String too long ({len(normalized)} chars) in {context}")
        
        return normalized
    
    def sanitize_for_output(self, text: str) -> str:
        """
        Sanitize text for safe output to files.
        This is a failsafe in case validation missed something.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text safe for output
        """
        if not isinstance(text, str):
            return str(text)
        
        # Escape HTML/XML special characters
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '&quot;',
            "'": '&#x27;',
            '\x00': '',  # Remove null bytes
        }
        
        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
        
        # Remove any remaining dangerous control characters
        result = ''.join(char for char in result if ord(char) not in self.dangerous_controls)
        
        return result
    
    def validate_yaml_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate YAML keys (canonical names) for safety.
        
        Args:
            data: Dictionary with potentially unsafe keys
            
        Returns:
            Dictionary with validated keys
        """
        validated = {}
        
        for key, value in data.items():
            try:
                # Special handling for GlobalID collision suffixes per v7 spec
                # Allow keys ending with --N where N is a number
                if re.match(r"^.*--\d+$", key):
                    # Still validate the base part without the suffix
                    base_key = re.sub(r"--\d+$", "", key)
                    safe_base = self.validate_string(base_key, context="yaml_key")
                    # Reconstruct with suffix
                    suffix_match = re.search(r"(--\d+)$", key)
                    safe_key = safe_base + suffix_match.group(1)
                    validated[safe_key] = value
                else:
                    # Normal validation
                    safe_key = self.validate_string(key, context="yaml_key")
                    validated[safe_key] = value
            except SecurityError as e:
                logger.warning(f"Skipping dangerous key: {repr(key)[:50]} - {e}")
                # Skip this entry entirely
                continue
        
        return validated
    
    def _check_homograph_attack(self, text: str, context: str) -> None:
        """
        Check for homograph attacks using Cyrillic lookalikes.
        
        Args:
            text: Text to check
            context: Context for error messages
            
        Raises:
            SecurityError: If homograph attack detected
        """
        # Count homograph characters
        homograph_count = 0
        total_alpha = 0
        
        for char in text:
            if char.isalpha():
                total_alpha += 1
                if char in self.homograph_mappings:
                    homograph_count += 1
        
        # If more than 50% of alphabetic characters are homographs, it's suspicious
        if total_alpha > 0 and (homograph_count / total_alpha) > 0.5:
            raise SecurityError(f"Homograph attack detected in {context} ({homograph_count}/{total_alpha} chars are lookalikes)")
        
        # Special case: detect specific attack patterns
        # "Аррӏе" should be caught here
        if any(char in self.homograph_mappings for char in text):
            # Check if it looks like a common English word written in Cyrillic
            converted = ''.join(self.homograph_mappings.get(char, char) for char in text)
            if converted.lower() in ['apple', 'google', 'microsoft', 'admin', 'test', 'user']:
                raise SecurityError(f"Homograph attack detected in {context} (mimics '{converted}')")
    
    def _check_combining_character_attack(self, text: str, context: str) -> None:
        """
        Check for attacks using excessive combining characters.
        
        Args:
            text: Text to check
            context: Context for error messages
            
        Raises:
            SecurityError: If excessive combining characters detected
        """
        combining_count = 0
        
        for char in text:
            if unicodedata.combining(char):
                combining_count += 1
        
        # Allow reasonable number of combining characters (accents, etc.)
        # But block excessive stacking like "Ä̈"
        if combining_count > len(text) * 0.3:  # More than 30% combining chars is suspicious
            raise SecurityError(f"Excessive combining characters in {context} ({combining_count} combining chars)")
        
        # Check for specific dangerous patterns
        # Multiple combining characters on same base character
        i = 0
        while i < len(text):
            if i + 1 < len(text) and not unicodedata.combining(text[i]):
                # Count combining chars following this base char
                combining_seq = 0
                j = i + 1
                while j < len(text) and unicodedata.combining(text[j]):
                    combining_seq += 1
                    j += 1
                
                # More than 2 combining chars on one base is suspicious
                if combining_seq > 2:
                    raise SecurityError(f"Multiple combining characters attack in {context} (base + {combining_seq} combiners)")
                
                i = j
            else:
                i += 1
    
    def _check_encoded_attacks(self, text: str, context: str) -> None:
        """
        Check for attacks using various encoding tricks.
        
        Args:
            text: Text to check
            context: Context for error messages
            
        Raises:
            SecurityError: If encoded attack patterns detected
        """
        # Check for URL encoding
        url_decode_count = 0
        if '%' in text:
            import urllib.parse
            try:
                decoded = urllib.parse.unquote(text)
                if decoded != text:
                    url_decode_count = text.count('%')
                    # Check if decoded version contains attacks
                    for pattern in self.compiled_patterns[:20]:  # Check first 20 patterns
                        if pattern.search(decoded):
                            raise SecurityError(f"URL-encoded attack detected in {context}")
            except:
                pass
        
        # Check for HTML entity encoding
        if '&' in text and ';' in text:
            import html
            decoded = html.unescape(text)
            if decoded != text:
                # Check if decoded version contains attacks
                for pattern in self.compiled_patterns[:20]:
                    if pattern.search(decoded):
                        raise SecurityError(f"HTML-encoded attack detected in {context}")
        
        # Check for Unicode escape sequences
        if '\\u' in text or '\\x' in text:
            raise SecurityError(f"Unicode escape sequences detected in {context}")
        
        # Check for Base64-like patterns (could hide malicious content)
        # Exclude GlobalID context as they use Base32
        if context != "GlobalID" and re.match(r'^[A-Za-z0-9+/]{40,}={0,2}$', text):
            raise SecurityError(f"Suspicious Base64-like pattern in {context}")
    
    def _check_polyglot_attacks(self, text: str, context: str) -> None:
        """
        Check for polyglot attacks that work across multiple contexts.
        
        Args:
            text: Text to check
            context: Context for error messages
            
        Raises:
            SecurityError: If polyglot attack patterns detected
        """
        # Check for content that could be both valid name and code
        polyglot_patterns = [
            # JavaScript/HTML polyglot
            r"(?i)(alert|eval|document|window|script)",
            # SQL/JavaScript polyglot
            r"(?i)(select.*from.*where|union.*select)",
            # XML/JavaScript polyglot
            r"<!\[CDATA\[.*\]\]>",
            # JSON/JavaScript polyglot
            r'["\'].*["\']:\s*function',
        ]
        
        for pattern in polyglot_patterns:
            if re.search(pattern, text):
                raise SecurityError(f"Polyglot attack pattern detected in {context}")
    
    def _check_timing_attacks(self, text: str, context: str) -> None:
        """
        Check for patterns that could cause timing-based attacks.
        
        Args:
            text: Text to check
            context: Context for error messages
            
        Raises:
            SecurityError: If timing attack patterns detected
        """
        # Check for extremely long strings that could cause DoS
        if len(text) > 500:
            raise SecurityError(f"Excessively long string in {context} ({len(text)} chars)")
        
        # Check for patterns that could cause algorithmic complexity attacks
        # Repeated patterns that could exploit hash collisions
        if len(set(text)) < len(text) * 0.1:  # Less than 10% unique characters
            raise SecurityError(f"Low character diversity in {context} (possible hash collision attack)")
        
        # Check for patterns that could cause regex backtracking
        # Only check if the text looks like a regex pattern, not normal names
        if re.search(r'[\*\+\{\}\[\]\(\)\|]', text):
            backtrack_patterns = [
                r"(a+)+$",
                r"(a*)*$",
                r"(a|a)*$",
                r"(.*a){20}",
            ]
            for pattern in backtrack_patterns:
                if re.search(pattern, text[:50]):  # Only check start to avoid actual DoS
                    raise SecurityError(f"Potential ReDoS pattern in {context}")

# Global instance
security_validator = SecurityValidator()