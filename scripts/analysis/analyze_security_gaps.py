#!/usr/bin/env python3
"""
Analyze Security Gaps - Find which attacks are passing through
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.regions.manager_optimized import RegionManager

print("🔍 ANALYZING SECURITY GAPS")
print("=" * 60)

manager = RegionManager()

# Comprehensive attack test cases (100 attacks from audit)
attack_cases = [
    # Path traversal attacks (20)
    ("../../../etc/passwd", "Path traversal unix"),
    ("..\\..\\..\\windows\\system32\\drivers\\etc\\hosts", "Path traversal windows"),
    ("/etc/shadow", "Direct path attack"),
    ("C:\\Windows\\System32\\config\\SAM", "Windows registry"),
    ("../../root/.ssh/id_rsa", "SSH key theft"),
    ("../../../var/log/auth.log", "Log file access"),
    ("/proc/self/environ", "Process environment"),
    ("file:///etc/passwd", "File protocol"),
    ("\\\\server\\share\\passwords.txt", "UNC path"),
    ("./../../etc/hosts", "Relative path"),
    ("~/../../etc/passwd", "Home relative"),
    ("/dev/null; cat /etc/passwd", "Command injection"),
    ("' OR 1=1 --", "SQL injection"),
    ("admin'--", "SQL comment injection"),
    ("1' UNION SELECT * FROM users--", "SQL union"),
    ('"; rm -rf /; "', "Command injection"),
    ("$(cat /etc/passwd)", "Command substitution"),
    ("`whoami`", "Command substitution backticks"),
    ("test && rm -rf /", "Command chaining"),
    ("test || cat /etc/passwd", "Command or"),
    # Script injection attacks (20)
    ("<script>alert('xss')</script>", "Basic XSS"),
    ("javascript:alert(1)", "JavaScript protocol"),
    ("data:text/html,<script>alert(1)</script>", "Data protocol XSS"),
    ("vbscript:msgbox(1)", "VBScript protocol"),
    ("<img src=x onerror=alert(1)>", "Image XSS"),
    ("<svg onload=alert(1)>", "SVG XSS"),
    ("'><script>alert(1)</script>", "Quote break XSS"),
    ('" onmouseover="alert(1)"', "Event handler XSS"),
    ("<iframe src=javascript:alert(1)>", "Iframe XSS"),
    ("<meta http-equiv=refresh content=0;url=javascript:alert(1)>", "Meta XSS"),
    ("alert(String.fromCharCode(88,83,83))", "Encoded XSS"),
    ("<script>eval(atob('YWxlcnQoMSk='))</script>", "Base64 XSS"),
    ("<script>window['al'+'ert'](1)</script>", "Concat XSS"),
    ("<object data=javascript:alert(1)>", "Object XSS"),
    ("<embed src=javascript:alert(1)>", "Embed XSS"),
    ("<%=7*7%>", "Server-side injection"),
    ("{{7*7}}", "Template injection"),
    ("{%print(7*7)%}", "Template injection"),
    ("${{7*7}}", "Expression injection"),
    ("#{7*7}", "Expression injection"),
    # Emoji/symbol attacks (15)
    ("😀😁😂🤣😃😄😅😆", "Pure emoji"),
    ("🔥💣💥⚡🌪️", "Dangerous emojis"),
    ("👤👥👫👬👭", "User emojis"),
    ("🏠🏡🏢🏣🏤", "Building emojis"),
    ("🚀🛸🛰️✈️🚁", "Vehicle emojis"),
    ("⚠️⛔🚫🚷🚯", "Warning symbols"),
    ("💀☠️⚰️🪦", "Death symbols"),
    ("🔞🔤🔡🔠", "Symbol blocks"),
    ("⌘⌥⇧⌃⌫", "Keyboard symbols"),
    ("∆∇∈∉∋∌", "Math symbols"),
    ("αβγδεζη", "Greek letters"),
    ("₀₁₂₃₄₅", "Subscripts"),
    ("⁰¹²³⁴⁵", "Superscripts"),
    ("※§¶†‡", "Typographic symbols"),
    ("❤️💛💚💙💜", "Heart emojis"),
    # Binary/hex attacks (10)
    ("\x00\x01\x02\x03", "Null bytes"),
    ("\xff\xfe\xfd\xfc", "High bytes"),
    ("\\x41\\x42\\x43", "Hex escape"),
    ("\\u0041\\u0042", "Unicode escape"),
    ("%41%42%43", "URL encoding"),
    ("&lt;script&gt;", "HTML entities"),
    ("&#60;script&#62;", "Numeric entities"),
    ("\\0\\1\\2\\3", "Octal escape"),
    ("\r\n\r\n", "CRLF injection"),
    ("\t\t\t\t", "Tab characters"),
    # Protocol attacks (10)
    ("ftp://evil.com/payload", "FTP protocol"),
    ("ldap://evil.com/payload", "LDAP protocol"),
    ("gopher://evil.com:70/", "Gopher protocol"),
    ("jar:http://evil.com!/", "JAR protocol"),
    ("mailto:test@evil.com", "Mail protocol"),
    ("news:comp.security", "News protocol"),
    ("nntp://evil.com/", "NNTP protocol"),
    ("telnet://evil.com:23/", "Telnet protocol"),
    ("ssh://evil.com:22/", "SSH protocol"),
    ("dict://evil.com:2628/", "Dict protocol"),
    # Length/DoS attacks (10)
    ("A" * 10000, "Buffer overflow"),
    ("X" * 100000, "Memory exhaustion"),
    ("🔥" * 1000, "Emoji bomb"),
    ("../../../" * 100, "Path bomb"),
    ("' UNION SELECT " * 50, "SQL bomb"),
    ("<script>" * 100, "Tag bomb"),
    ("alert(1);" * 100, "JS bomb"),
    ("\\x41" * 1000, "Escape bomb"),
    ("%%%%%%%%%%", "Format string"),
    ("{{{{{{{{", "Template bomb"),
    # Filename attacks (15)
    ("document.exe", "Executable filename"),
    ("payload.bat", "Batch file"),
    ("virus.com", "Com file"),
    ("trojan.scr", "Screensaver"),
    ("malware.pif", "Program info"),
    ("backdoor.cmd", "Command file"),
    ("rootkit.vbs", "VBScript"),
    ("worm.js", "JavaScript file"),
    ("keylogger.jar", "Java archive"),
    ("spyware.msi", "Windows installer"),
    ("ransomware.dll", "Dynamic library"),
    ("botnet.sys", "System file"),
    ("exploit.ps1", "PowerShell"),
    ("payload.sh", "Shell script"),
    ("hack.py", "Python script"),
]

# Analyze which attacks pass through
passed_attacks = []
blocked_attacks = []

for attack, description in attack_cases:
    try:
        result = manager.detect_region({"name": attack})

        # Check if attack was blocked (quarantined or blocked)
        is_blocked = result.region_code == "Z0" and (
            "quarantine" in result.detection_method
            or "security" in result.detection_method.lower()
            or "error" in result.detection_method.lower()
        )

        if is_blocked:
            blocked_attacks.append((attack, description))
        else:
            passed_attacks.append(
                (attack, description, result.region_code, result.detection_method)
            )

    except Exception as e:
        # If it crashes, that's also bad (but shouldn't happen)
        passed_attacks.append((attack, description, "CRASH", str(e)))

print(f"\n📊 SECURITY GAP ANALYSIS:")
print(f"  Total attacks: {len(attack_cases)}")
print(f"  Blocked: {len(blocked_attacks)}")
print(f"  PASSED THROUGH: {len(passed_attacks)}")
print(f"  Vulnerability rate: {len(passed_attacks)/len(attack_cases):.1%}")

if passed_attacks:
    print(f"\n🚨 ATTACKS THAT PASSED THROUGH ({len(passed_attacks)} total):")

    # Group by type
    by_type = {}
    for attack, desc, region, method in passed_attacks:
        attack_type = desc.split()[-1] if len(desc.split()) > 1 else desc
        if attack_type not in by_type:
            by_type[attack_type] = []
        by_type[attack_type].append((attack, desc, region, method))

    for attack_type, attacks in by_type.items():
        print(f"\n  📍 {attack_type.upper()} ({len(attacks)} attacks):")
        for attack, desc, region, method in attacks[:3]:  # Show first 3
            print(f"    • \"{attack[:50]}{'...' if len(attack) > 50 else ''}\"")
            print(f"      → {region} via {method}")
        if len(attacks) > 3:
            print(f"    ... and {len(attacks) - 3} more")

print(f"\n🔧 VULNERABILITY PATTERNS:")

# Analyze patterns in passed attacks
patterns = {
    "Protocol handlers": 0,
    "Script tags": 0,
    "Path traversal": 0,
    "File extensions": 0,
    "Command injection": 0,
    "Special characters": 0,
    "Long strings": 0,
    "Unicode attacks": 0,
}

for attack, desc, region, method in passed_attacks:
    if any(
        proto in attack.lower() for proto in ["http:", "ftp:", "javascript:", "data:"]
    ):
        patterns["Protocol handlers"] += 1
    if any(
        tag in attack.lower() for tag in ["<script", "<iframe", "<object", "<embed"]
    ):
        patterns["Script tags"] += 1
    if any(path in attack for path in ["../", "..\\", "/etc/", "c:\\"]):
        patterns["Path traversal"] += 1
    if any(ext in attack.lower() for ext in [".exe", ".bat", ".cmd", ".js", ".vbs"]):
        patterns["File extensions"] += 1
    if any(cmd in attack for cmd in ["$(", "`", "&&", "||", ";"]):
        patterns["Command injection"] += 1
    if any(char in attack for char in ["\x00", "\xff", "\\x", "\\u"]):
        patterns["Special characters"] += 1
    if len(attack) > 1000:
        patterns["Long strings"] += 1
    if any(ord(c) > 127 for c in attack if isinstance(c, str)):
        patterns["Unicode attacks"] += 1

for pattern, count in patterns.items():
    if count > 0:
        print(f"  • {pattern}: {count} attacks")

print(f"\n💡 RECOMMENDED SECURITY IMPROVEMENTS:")
print("  1. Add protocol handler detection")
print("  2. Strengthen HTML/script tag filtering")
print("  3. Improve path traversal detection")
print("  4. Add file extension blocking")
print("  5. Enhance command injection detection")
print("  6. Implement binary/unicode validation")
print("  7. Add length limits and DoS protection")
print("  8. Create multi-layer validation pipeline")
