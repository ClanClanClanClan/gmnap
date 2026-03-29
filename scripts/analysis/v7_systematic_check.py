#!/usr/bin/env python3
"""
ULTRACAREFUL V7 Systematic Check and Fix
Triple-checking everything
"""

import os
import sys
import importlib.util
from pathlib import Path

# Silence warnings for cleaner output
import warnings

warnings.filterwarnings("ignore")


def check_file_exists(filepath):
    """Check if a file exists."""
    return Path(filepath).exists()


def try_import_module(module_path, item_name=None):
    """Try to import a module and optionally a specific item."""
    try:
        # Convert path to module name
        if module_path.endswith(".py"):
            module_path = module_path[:-3]
        module_name = module_path.replace("/", ".")

        # Try to import
        module = __import__(module_name, fromlist=[""])

        # If specific item requested, check it exists
        if item_name:
            if hasattr(module, item_name):
                return True, f"✓ Found {item_name}"
            else:
                return False, f"Module ok but missing {item_name}"
        return True, "✓ Module imports"
    except ImportError as e:
        return False, f"ImportError: {str(e)[:50]}"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"


def main():
    print("=" * 70)
    print("ULTRACAREFUL V7 SYSTEMATIC CHECK")
    print("Triple-checking every component")
    print("=" * 70)
    print()

    # Define what we need to check
    checks = {
        "CORE MODULES": [
            ("src/core/canonical_json.py", "to_canonical_bytes"),
            ("src/core/idempotency.py", "batch_hash"),
            ("src/core/schema_validator.py", "V7SchemaValidator"),
            ("src/core/db_pool.py", "BoltPool"),
            ("src/core/transaction_manager.py", "TransactionManager"),
        ],
        "PIPELINE STAGES": [
            ("src/pipeline/stage1b_llmextract_etd.py", "extract_from_text"),
            ("src/pipeline/stage2_detect_region.py", "detect_region"),
            ("src/pipeline/stage3_region_hooks.py", "apply_region_hooks"),
            ("src/pipeline/stage5_collision_analytics.py", "ensure_unique_global_ids"),
            ("src/pipeline/stage6_graph_consistency.py", "enforce_graph_coherence_gate"),
            ("src/pipeline/stage7_tag_short_forms.py", "tag_short_forms"),
            ("src/pipeline/stage8_global_validate.py", "global_validate"),
            ("src/pipeline/stage9_write_and_diff.py", "write_and_diff"),
            ("src/pipeline/stage10_report.py", "generate_report"),
            ("src/pipeline/stage11_idempotency_check.py", "enforce_idempotency_gate"),
        ],
        "SCHEMA FILES": [
            ("schemas/v7_entry.schema.json", None),
            ("schemas/etd.schema.json", None),
        ],
        "CRITICAL CONFIGS": [
            ("config/authorities.yaml", None),
            ("config/weights.yaml", None),
        ],
    }

    total_checks = 0
    passed_checks = 0
    failed_items = []

    for category, items in checks.items():
        print(f"\n{category}")
        print("-" * 40)

        for filepath, item_name in items:
            total_checks += 1

            # First check if file exists
            if not check_file_exists(filepath):
                print(f"✗ {filepath} - FILE NOT FOUND")
                failed_items.append((category, filepath, "File not found"))
                continue

            # For Python files, try to import
            if filepath.endswith(".py"):
                success, message = try_import_module(filepath, item_name)
                if success:
                    print(f"✓ {filepath} - {message}")
                    passed_checks += 1
                else:
                    print(f"✗ {filepath} - {message}")
                    failed_items.append((category, filepath, message))
            else:
                # Non-Python files just check existence
                print(f"✓ {filepath} - File exists")
                passed_checks += 1

    # Check patch files
    print("\n\nPATCH FILES")
    print("-" * 40)
    patch_dir = Path("reparation_plan")
    patch_count = 0
    if patch_dir.exists():
        for patch_file in patch_dir.rglob("*.patch"):
            patch_count += 1
            print(f"✓ Found patch: {patch_file.name}")
    print(f"Total patches found: {patch_count}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Checks passed: {passed_checks}/{total_checks} ({100*passed_checks/total_checks:.1f}%)")

    if failed_items:
        print("\nFAILED ITEMS THAT NEED FIXING:")
        for category, filepath, error in failed_items:
            print(f"  [{category}] {filepath}")
            print(f"    → {error}")

    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    if passed_checks < total_checks:
        print("1. Fix import errors by checking dependencies")
        print("2. Ensure all required files are copied from overlays/")
        print("3. Apply patches in order")
        print("4. Re-run this check after each fix")
    else:
        print("✓ All checks passed! Ready to apply patches.")

    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
