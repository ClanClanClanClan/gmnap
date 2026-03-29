import pytest

pytest.skip("Test needs major refactoring", allow_module_level=True)
import pytest

#!/usr/bin/env python3
"""Debug numeric name handling"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

manager = RegionManager()

# Test numeric name
print("Testing numeric name...")
result = manager.detect_region({"name": 123})
print(f"Result: region_code={result.region_code}, confidence={result.confidence}")
print(f"Metadata: {result.metadata}")
print(f"Expected: Z0 with error metadata")
print(f"Test passes: {result.region_code == 'Z0' and 'error' in result.metadata}")

# Let's see what happens with string "123"
print("\nTesting string '123'...")
result2 = manager.detect_region({"name": "123"})
print(f"Result: region_code={result2.region_code}, confidence={result2.confidence}")
print(f"Metadata: {result2.metadata}")
