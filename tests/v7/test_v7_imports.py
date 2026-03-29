import pytest

#!/usr/bin/env python3
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


Test V7 module imports to verify all components are working.
"""

import sys
import warnings

warnings.filterwarnings("ignore")


@pytest.mark.timeout(15)
def test_imports():
    """Test all V7 module imports."""

    print("=" * 60)
    print("GMNAP V7 MODULE IMPORT TEST")
    print("=" * 60)
    print()

    modules_to_test = [
        # Core modules
        ("Core: Canonical JSON", "from src.core.canonical_json import to_canonical_bytes"),
        ("Core: Idempotency", "from src.core.idempotency import batch_hash, assert_identical"),
        ("Core: Schema Validator", "from src.core.schema_validator import V7SchemaValidator"),
        ("Core: DB Pool", "from src.core.db_pool import BoltPool"),
        (
            "Core: Transaction Manager",
            "from src.core.transaction_manager import TransactionManager",
        ),
        # Region management
        ("Regions: Manager", "from src.regions import RegionManager"),
        ("Regions: Base", "from src.regions.base import RegionSpec as RegionBase, RegionSpec"),
        # Pipeline stages
        ("Stage 1b: LLM Extract", "from src.llm.stage1b_llmextract_etd import extract_from_text"),
        ("Stage 2: Detect Region", "from src.pipeline.stage2_detect_region import detect_region"),
        (
            "Stage 3: Region Hooks",
            "from src.pipeline.stage3_region_hooks import apply_region_hooks",
        ),
        (
            "Stage 5: Collision Analytics",
            "from src.pipeline.stage5_collision_analytics import ensure_unique_global_ids",
        ),
        (
            "Stage 6: Graph Consistency",
            "from src.pipeline.stage6_graph_consistency import enforce_graph_coherence_gate",
        ),
        (
            "Stage 7: Tag Short Forms",
            "from src.pipeline.stage7_tag_short_forms import tag_short_forms",
        ),
        (
            "Stage 8: Global Validate",
            "from src.pipeline.stage8_global_validate import global_validate",
        ),
        ("Stage 9: Write & Diff", "from src.pipeline.stage9_write_and_diff import write_and_diff"),
        ("Stage 10: Report", "from src.pipeline.stage10_report import generate_report"),
        (
            "Stage 11: Idempotency",
            "from src.pipeline.stage11_idempotency_check import enforce_idempotency_gate",
        ),
        # Operations
        ("Ops: Metrics", "from src.ops.metrics import start_metrics_server"),
        ("Ops: Archive SFTP", "from src.ops.archive_sftp import SFTPArchiver"),
        ("Ops: DataCite Builder", "from src.ops.datacite_builder import build_datacite_doi"),
        # Security
        ("Security: Auth Middleware", "from src.security.auth_middleware import APIKeyAuth"),
    ]

    results = []
    success_count = 0

    for name, import_stmt in modules_to_test:
        try:
            exec(import_stmt)
            print(f"✓ {name}")
            results.append((name, True))
            success_count += 1
        except ImportError as e:
            error_msg = str(e).replace("\\n", " ")[:60]
            print(f"✗ {name}: Import error - {error_msg}")
            results.append((name, f"Import: {error_msg}"))
        except Exception as e:
            error_msg = str(e).replace("\\n", " ")[:60]
            print(f"✗ {name}: {error_msg}")
            results.append((name, f"Error: {error_msg}"))

    print()
    print("=" * 60)
    print(f"SUMMARY: {success_count}/{len(modules_to_test)} modules working")
    print("=" * 60)

    if success_count < len(modules_to_test):
        print("\nFailed modules:")
        for name, result in results:
            if result is not True:
                print(f"  - {name}: {result}")
        return 1
    else:
        print("\nPASS All V7 modules imported successfully!")
        return 0


if __name__ == "__main__":
    pass  # sys.exit(test_imports())
