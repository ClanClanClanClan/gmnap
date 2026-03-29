import pytest

#!/usr/bin/env python3
"""
Test language detection fix
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_language_detection_directly():
    """Test language detection on simple names."""

    print("🔧 TESTING LANGUAGE DETECTION FIX")
    print("=" * 50)

    manager = RegionManager()

    if not manager._lang_detector:
        print("FAIL No language detector loaded")
        return

    # Test names that should trigger language detection
    test_names = [
        "Jean Dupont",  # French
        "José García",  # Spanish
        "Maria Silva",  # Portuguese/Spanish
        "Hans Mueller",  # German
        "Antonio Rossi",  # Italian
        "Jan Kowalski",  # Polish
        "Ivan Petrov",  # Could be Russian (but in Latin script)
    ]

    print("Direct FastText Predictions:")
    for name in test_names:
        try:
            predictions = manager._lang_detector.predict(name, k=3)
            languages = [pred[0].replace("__label__", "") for pred in predictions[0]]
            scores = predictions[1]

            print(
                f"  {name:15} -> {languages[0]:3} ({scores[0]:.3f}), {languages[1]:3} ({scores[1]:.3f})"
            )
        except Exception as e:
            print(f"  {name:15} -> ERROR: {e}")

    # Test through region detection
    print("\nRegion Detection with Language:")
    for name in test_names:
        entry = {"name": name}
        result = manager.detect_region(entry, internal=True)

        print(
            f"  {name:15} -> {result.region_code} ({result.detection_method}, {result.confidence:.2f})"
        )


def check_fasttext_model():
    """Check what FastText model is loaded."""

    print("\n🔍 FASTTEXT MODEL INFO:")
    print("-" * 30)

    manager = RegionManager()

    if manager._lang_detector:
        # Try to get model info
        try:
            # Test with longer text to see if it works better
            long_texts = [
                "Bonjour monsieur, comment allez vous aujourd'hui?",  # French
                "Hola amigo, como estas tu hoy en el dia?",  # Spanish
                "Hello my friend, how are you doing today?",  # English
                "Guten Tag, wie geht es dir heute?",  # German
                "Ciao amico, come stai oggi?",  # Italian
            ]

            print("Longer text predictions:")
            for text in long_texts:
                predictions = manager._lang_detector.predict(text, k=2)
                lang = predictions[0][0][0].replace("__label__", "")
                conf = predictions[1][0]
                print(f"  {text[:30]}... -> {lang} ({conf:.3f})")

        except Exception as e:
            print(f"Error testing model: {e}")
    else:
        print("No FastText model loaded")


def main():
    """Run language detection tests."""

    test_language_detection_directly()
    check_fasttext_model()


if __name__ == "__main__":
    main()
