#!/usr/bin/env python3
"""
Systematic import issue finder and fixer
"""

import os
import sys
import time
import ast

os.environ["GMNAP_TEST_MODE"] = "true"
sys.path.insert(0, ".")


def test_import(module_path, timeout=2):
    """Test if a module can be imported within timeout"""
    import_str = f"from {module_path} import *"
    start = time.time()
    try:
        exec(import_str)
        elapsed = time.time() - start
        return True, elapsed
    except Exception as e:
        elapsed = time.time() - start
        return False, elapsed


def find_module_level_code(filepath):
    """Find module-level code that might block"""
    problematic = []

    try:
        with open(filepath, "r") as f:
            content = f.read()
            tree = ast.parse(content)

        for node in ast.walk(tree):
            # Check for module-level function calls
            if isinstance(node, ast.Call) and not isinstance(node.func, ast.Attribute):
                # This is too broad, need context
                pass

            # Check for module-level assignments with function calls
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    line_no = node.lineno
                    problematic.append(f"Line {line_no}: Assignment with function call")

        # Simple grep for common patterns
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Skip comments and function definitions
            if (
                line.strip().startswith("#")
                or line.strip().startswith("def ")
                or line.strip().startswith("class ")
            ):
                continue

            # Look for problematic patterns
            if "Client()" in line and "def " not in line and "    " not in line:
                problematic.append(f"Line {i}: Module-level Client instantiation")
            if ".connect(" in line and "def " not in line and "    " not in line:
                problematic.append(f"Line {i}: Module-level connect call")
            if "register_check(" in line and "def " not in line and "#" not in line:
                problematic.append(f"Line {i}: Module-level registration")

    except Exception as e:
        problematic.append(f"Error parsing: {e}")

    return problematic


print("=" * 60)
print("SYSTEMATIC MODULE-LEVEL CODE DETECTION")
print("=" * 60)

# Check core modules
core_modules = [
    "src/core/memgraph_client.py",
    "src/core/memgraph_integration.py",
    "src/core/monitoring.py",
    "src/core/pipeline.py",
    "src/core/pipeline_v7.py",
]

print("\n1. CORE MODULES:")
for module in core_modules:
    if os.path.exists(module):
        issues = find_module_level_code(module)
        if issues:
            print(f"\n{module}:")
            for issue in issues:
                print(f"  - {issue}")
    else:
        print(f"  {module}: NOT FOUND")

# Check authority modules
authority_modules = [
    "src/authorities/crossref.py",
    "src/authorities/openalex.py",
    "src/authorities/orcid.py",
    "src/authorities/arxiv.py",
    "src/authorities/mathgenealogy.py",
    "src/authorities/manager.py",
]

print("\n2. AUTHORITY MODULES:")
for module in authority_modules:
    if os.path.exists(module):
        issues = find_module_level_code(module)
        if issues:
            print(f"\n{module}:")
            for issue in issues:
                print(f"  - {issue}")
    else:
        print(f"  {module}: NOT FOUND")

# Check imports
print("\n3. TESTING IMPORTS:")
test_imports = [
    ("src.pipeline.stage11_idempotency_gate", "_canonical_bytes"),
    ("src.authorities.arxiv", "ArXivAPI"),
    ("src.authorities.crossref", "CrossrefAPI"),
    ("src.authorities.openalex", "OpenAlexAPI"),
    ("src.authorities.orcid", "ORCIDAPI"),
    ("src.core.memgraph_integration", "MemgraphClient"),
]

for module, item in test_imports:
    try:
        start = time.time()
        exec(f"from {module} import {item}")
        elapsed = time.time() - start
        print(f"  ✓ {module}: {elapsed:.2f}s")
    except Exception as e:
        elapsed = time.time() - start
        if elapsed > 1:
            print(f"  ✗ {module}: TIMEOUT ({elapsed:.2f}s)")
        else:
            print(f"  ✗ {module}: {str(e)[:50]}")
