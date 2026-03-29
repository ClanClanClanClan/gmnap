import pytest

#!/usr/bin/env python3
"""
Test the new FastText language identification model
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Force reload FastText model by resetting globals
import src.regions.manager_optimized as mgr_module

mgr_module._fasttext_model = None
mgr_module._fasttext_load_attempted = False

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_new_fasttext_model():
    """Test the new FastText model."""

    print("🔥 TESTING NEW FASTTEXT LANGUAGE MODEL")
    print("=" * 50)

    # Force new manager instance
    manager = RegionManager()

    if not manager._lang_detector:
        print("FAIL Still no language detector loaded")
        return

    print("PASS Language detector loaded")

    # Test with longer texts that should work better
    test_texts = [
        ("Bonjour monsieur, comment allez-vous?", "French", "A2"),
        ("Hola amigo, cómo estás hoy?", "Spanish", "G1"),
        ("Hello friend, how are you today?", "English", "A1"),
        ("Guten Tag, wie geht es dir?", "German", "A2"),
        ("Ciao amico, come stai oggi?", "Italian", "A2"),
        ("Olá meu amigo, como está você?", "Portuguese", "G1"),
    ]

    print("\nDirect FastText Language Detection:")
    for text, expected_lang, expected_region in test_texts:
        try:
            predictions = manager._lang_detector.predict(text, k=3)
            languages = [pred[0].replace("__label__", "") for pred in predictions[0]]
            scores = predictions[1]

            print(f"  {text[:30]:32} -> {languages[0]:3} ({scores[0]:.3f})")
        except Exception as e:
            print(f"  {text[:30]:32} -> ERROR: {e}")

    # Test with actual names
    print("\nName-based Detection:")
    test_names = [
        ("Jean Dupont", "A2"),
        ("José García", "G1"),
        ("Maria Silva", "G1"),
        ("Hans Mueller", "A2"),
        ("Antonio Rossi", "A2"),
    ]

    for name, expected_region in test_names:
        entry = {"name": name}
        result = manager.detect_region(entry, internal=True)

        status = "PASS" if result.region_code == expected_region else "FAIL"
        print(
            f"  {status} {name:15} -> {result.region_code} (expected {expected_region}, method: {result.detection_method})"
        )


def main():
    """Run FastText model test."""
    test_new_fasttext_model()


if __name__ == "__main__":
    main()
