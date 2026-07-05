"""Security pattern tables for SecurityValidator (R46 split).

Moved verbatim (dedented) from ``security_validator.SecurityValidator.__init__``
— data, not logic. The validator builds per-instance copies, preserving the
previous mutability semantics. Keys in ``PATTERN_DESCRIPTIONS`` must match the
*exact* raw regex strings in the lists (dict-key dispatch).
"""

DANGEROUS_PATTERNS = [
    # SQL injection
    r"(?i)\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b",
    r"(?i)(/\*|\*/|;.*--|'.*or.*'|\".*or.*\"|^--|\s--\s|'.*--$)",  # Allow -- in names but not SQL comments
    r"(?i)'.*\s+OR\s+.*=",  # Catches: ' OR 1=1, ' OR 'a'='a'
    r"(?i)'.*\s+OR\s+\d+\s*=\s*\d+",  # Catches: ' OR 1=1
    r"#$",  # MySQL comment at end
    r"--$",  # SQL comment at end
    # XSS/HTML injection
    r"(?i)(<script|</script|<iframe|</iframe|<object|</object)",
    r"(?i)(<embed|<applet|<form|<input|<button)",
    r"(?i)(javascript:|vbscript:|data:|about:)",
    r"(?i)(onload|onclick|onerror|onmouseover)=",
    # Command injection
    r"(?i)([;|&].*rm\s|[;|&].*del\s|[;|&].*format|[;|&].*shutdown)",
    r"(&&|\|\||`[^`]*`|\$\([^)]+\))",  # Shell operators
    r";\s*(curl|wget|bash|sh|nc|netcat|python|perl|ruby|php)\s",  # Command chaining
    r"\|\s*(sh|bash|python|perl|ruby|php)\b",  # Pipe to interpreter
    # Path traversal
    r"\.\.[\\/]",
    r"(?i)(\/etc\/|\/proc\/|\/sys\/|c:\\\\windows|c:\\\\system)",
    # LDAP injection
    r"(?i)(\)\(|\*\)|=\*|=.*\*)",
    # XML/XXE
    r"(?i)(<!entity|<!doctype|<\?xml)",
    # Regex DoS (ReDoS) - excessive repetition (increased threshold for testing)
    r"(.)\1{5000,}",  # Same character repeated 5000+ times (clear DoS attempt)
    r"[a-z]{100,}[A-Z]",  # Long sequence followed by different char (ReDoS pattern)
    r"\(\w\+\)\+",  # Nested quantifiers like (a+)+
    r"\(\?\:\w\*\)\*",  # Catastrophic backtracking like (?:a*)*
    # Template injection patterns
    r"\{\{.*\}\}",  # Jinja2/Angular style {{expression}}
    r"\${.*}",  # ES6/JSP style ${expression}
    r"<%.*%>",  # ERB/ASP style <%expression%>
    r"#\{.*\}",  # Ruby style #{expression}
    r"\[%.*%\]",  # Perl Template Toolkit style [%expression%]
    r"@\(.*\)",  # Razor syntax @(expression)
    # NoSQL injection patterns
    r"(?i)(\$where|\$gt|\$lt|\$ne|\$eq|\$regex|\$exists|\$type|\$expr|\$nin|\$in|\$all)",
    r"'; return .* var .*=",  # JavaScript injection in NoSQL
    # Removed - was blocking legitimate JSON (moved to NoSQL operators above)
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

ADDITIONAL_PATTERNS = [
    # Timing attacks
    r"(?i)(sleep\s*\(\s*\d+\s*\)|WAITFOR\s+DELAY|BENCHMARK\s*\(|pg_sleep\s*\()",
    # Windows commands
    r"(?i)(powershell|cmd\.exe|rundll32|regsvr32)",
    # More SQL patterns
    r"(?i)\b(having|group\s+by|order\s+by|limit\s+\d+|offset\s+\d+)\b",
    # ReDoS patterns - only match when input looks like a regex
    r"^\((a\+)\+\)\$$",  # Literal (a+)+$ pattern
    r"^\((a\*)\*\)\$$",  # Literal (a*)*$ pattern
    r"^\((a\|a)\*\)\$$",  # Literal (a|a)*$ pattern
    r"^\((x\+x\+)\+y\$$",  # Literal (x+x+)+y pattern
]

EXTENDED_PATTERNS = [
    r"(?i)\b(exec|eval|compile|__import__)\s*\(",  # Python code execution
    r"(?i)\b(system|popen|subprocess)\s*\(",  # System commands
    r"(?i)(powershell|cmd\.exe|/bin/sh|/bin/bash)",  # Shell invocation
    r"sleep\s*\(\s*\d+\s*\)",  # Sleep timing attacks
    r"(?i)WAITFOR\s+DELAY",  # SQL timing
    r"(?i)BENCHMARK\s*\(",  # MySQL timing
    r"(?i)pg_sleep\s*\(",  # PostgreSQL timing
]
# NOTE: a `[f"pattern_{i}" for i in range(50)]` block used to be
# appended here as "dummy patterns for count". They were compiled
# as LIVE rules, so any input containing the literal substrings
# pattern_0..pattern_49 (e.g. a name/field with "pattern_5") was
# rejected as a dangerous pattern — a pure false-positive that
# padded the rule count with nothing real. Removed.

PATTERN_DESCRIPTIONS = {
    r"(?i)\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b": (
        "SQL injection"
    ),
    r"(?i)(<script|</script|<iframe|</iframe|<object|</object": "XSS/Script injection",
    r"(?i)([;|&].*rm\s|[;|&].*del\s|[;|&].*format|[;|&].*shutdown)": (
        "Command injection"
    ),
    r"(&&.*\||\|\|.*&&|`[^`]*`|\$\([^)]+\))": "Shell command injection",
    r"\.\.[\\\\]": "Path traversal",
    r"(?i)(__schema|__type|mutation|subscription)": "GraphQL introspection",
    r"(?i)(\$where|\$gt|\$lt|\$ne|\$eq|\$regex|\$exists|\$type|\$expr|\$nin|\$in|\$all)": (
        "NoSQL injection"
    ),
    r"'; return .* var .*=": "NoSQL JavaScript injection",
    r"\(\w\+\)\+": "ReDoS - nested quantifiers",
    r"\(\?\:\w\*\)\*": "ReDoS - catastrophic backtracking",
    r"[a-z]{100,}[A-Z]": "ReDoS - long sequence pattern",
    # Template-injection family — covers JNDI lookup syntax
    # (${jndi:ldap://…}, the Log4Shell vector), Jinja2 ({{…}}),
    # ERB / ASP (<%…%>), Ruby (#{…}), Razor (@(…)), Perl
    # Template Toolkit ([%…%]). Keys match the *exact* strings
    # in `self.dangerous_patterns` above — pattern lookup uses
    # the raw regex string as a dict key, so any escape-form
    # mismatch silently falls through to the auto-generated
    # "Pattern <regex>" description.
    r"\${.*}": "Template/JNDI injection",
    r"\{\{.*\}\}": "Template injection (Jinja2/Angular)",
    r"<%.*%>": "Template injection (ERB/ASP)",
    r"#\{.*\}": "Template injection (Ruby)",
    r"@\(.*\)": "Template injection (Razor)",
    r"\[%.*%\]": "Template injection (Perl TT)",
    # Path traversal — different patterns are flagged in the
    # main list; align the exact strings here so dispatch
    # produces "Path traversal detected" instead of opaque
    # "Pattern \\.\\.[\\\\/] detected".
    r"\.\.[\\/]": "Path traversal",
}
