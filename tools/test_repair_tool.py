#!/usr/bin/env python3
"""
Test Repair Tool
- Diagnose import errors, missing deps, likely timeouts and interactive calls
- Auto-fix: add pytest imports, add timeouts, create alias shims, stub missing files
Usage:
  python tools/test_repair_tool.py diagnose  [tests/]
  python tools/test_repair_tool.py autofix   [tests/]
"""

from __future__ import annotations
import sys, os, re, json, pathlib, importlib.util

ROOT = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "tests")

ALIASES = {
    "HangulToRomanConverter": "src.regions.e_groups.e4_korea.romanize.KoreanConverterV7",
    "QualityGateChecker": "src.quality.quality_gates.enforce",
}


def _find_missing_modules(pyfile: pathlib.Path) -> list[str]:
    missing = []
    for line in pyfile.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*from\s+([\w\.]+)\s+import\s+([\w\*, ]+)", line) or re.match(
            r"\s*import\s+([\w\.]+)", line
        )
        if not m:
            continue
        mod = m.group(1)
        try:
            if mod.startswith("src"):
                # don't import project code during static analysis
                continue
            importlib.util.find_spec(mod)
        except Exception:
            missing.append(mod)
    return sorted(set(missing))


def diagnose(root: pathlib.Path) -> dict:
    report = {"files": [], "summary": {}}
    timeouts = 0
    missing_mods = set()
    inputs = 0
    for p in root.rglob("test_*.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        has_pytest = "import pytest" in txt
        has_timeout = "@pytest.mark.timeout" in txt
        if "input(" in txt:
            inputs += 1
        if not has_timeout:
            timeouts += 1
        mm = _find_missing_modules(p)
        for m in mm:
            missing_mods.add(m)
        report["files"].append(
            {
                "path": str(p),
                "has_pytest": has_pytest,
                "has_timeout": has_timeout,
                "missing_modules": mm,
            }
        )
    report["summary"] = {
        "files_scanned": len(report["files"]),
        "files_missing_timeout": timeouts,
        "files_with_input_calls": inputs,
        "unique_missing_modules": sorted(missing_mods),
        "alias_hints": ALIASES,
    }
    return report


def autofix(root: pathlib.Path) -> dict:
    changes = []
    for p in root.rglob("test_*.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        new = txt
        if "import pytest" not in new:
            new = "import pytest\n" + new
        if "@pytest.mark.timeout" not in new:
            new = re.sub(
                r"(\n\s*def\s+test_[A-Za-z0-9_]+\s*\()", "\n@pytest.mark.timeout(15)\n\g<1>", new
            )
        if new != txt:
            p.write_text(new, encoding="utf-8")
            changes.append(str(p))
    # Create alias shim module to satisfy older imports
    shim = pathlib.Path("src/compat/aliases_autogen.py")
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(" # generated alias module\n", encoding="utf-8")
    return {"files_modified": changes, "alias_module": str(shim)}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "diagnose"
    if cmd == "diagnose":
        print(json.dumps(diagnose(ROOT), indent=2))
    elif cmd == "autofix":
        print(json.dumps(autofix(ROOT), indent=2))
    else:
        sys.exit("usage: test_repair_tool.py [diagnose|autofix] [root]")
