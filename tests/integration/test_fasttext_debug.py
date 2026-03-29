#!/usr/bin/env python3
"""Debug FastText language detection"""
import sys
from pathlib import Path
import pytest

pytest.skip("Test needs major refactoring", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

manager = RegionManager()

# Test language detection directly
test_names = [
    "Marie Curie",  # French
    "Vladimir Putin",  # Russian
    "Ahmed Al-Rashid",  # Arabic
    "Raj Patel",  # Hindi
]

print("🔍 Testing FastText language detection...")
print("=" * 60)

if manager._language_model is None:
    print("FAIL FastText model not loaded!")
else:
    print("PASS FastText model loaded")

    for name in test_names:
        try:
            # Test language detection
            predictions = manager._language_model.predict(name, k=3)
            languages = predictions[0]
            confidences = predictions[1]

            print(f"\nName: {name}")
            print("Top 3 language predictions:")
            for i, (lang, conf) in enumerate(zip(languages, confidences)):
                lang_code = lang.replace("__label__", "")
                print(f"  {i+1}. {lang_code}: {conf:.3f}")
        except Exception as e:
            print(f"Error detecting language for '{name}': {e}")

# Check the model path
print("\n" + "=" * 60)
model_path = Path("config/models/lid.176.ftz")
print(f"Model path exists: {model_path.exists()}")
if model_path.exists():
    print(f"Model size: {model_path.stat().st_size / 1024 / 1024:.1f} MB")
