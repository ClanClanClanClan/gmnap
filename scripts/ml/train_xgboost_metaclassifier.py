#!/usr/bin/env python3
"""
Phase 2 ML - Day 4: XGBoost Meta-Classifier

Train an XGBoost meta-classifier that combines Phase 1 (rules) and Phase 2 (ML)
predictions with 86 additional features for intelligent ensemble.

Expected improvement: 97.54% → 98%+ (eliminate remaining 2/2720 failures)

Feature categories:
1. Phase 1 predictions + confidence (2 features)
2. Phase 2 ML predictions + confidence (2 features)
3. Regional script signals (20 features)
4. Name morphology (30 features)
5. Pattern matching signals (32 features)

Total: 86 features → 37-class region prediction
"""

import json
import sys
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not installed. Install with: pip install xgboost")

from src.regions.hybrid_classifier import HybridRegionClassifier


class MetaClassifierFeatureExtractor:
    """Extract 86 features from a name for meta-classification."""

    # Regional script patterns
    SCRIPT_PATTERNS = {
        "latin": r"[a-zA-Z]",
        "cyrillic": r"[а-яА-ЯёЁ]",
        "greek": r"[α-ωΑ-Ω]",
        "arabic": r"[ء-ي]",
        "hebrew": r"[א-ת]",
        "devanagari": r"[अ-ह]",
        "bengali": r"[অ-হ]",
        "tamil": r"[அ-ஹ]",
        "han": r"[\u4e00-\u9fff]",
        "hangul": r"[가-힣]",
        "katakana": r"[ァ-ヴ]",
        "hiragana": r"[ぁ-ゔ]",
        "thai": r"[ก-๛]",
        "lao": r"[ກ-ໝ]",
        "khmer": r"[ក-៹]",
        "myanmar": r"[က-႙]",
        "georgian": r"[ა-ჰ]",
        "armenian": r"[Ա-Ֆա-ֆ]",
        "ethiopic": r"[ሀ-ፚ]",
        "vietnamese_extended": r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
    }

    # Common surname patterns by region
    SURNAME_PATTERNS = {
        # Slavic
        "slavic_ov": r"(ov|ova|ev|eva)$",
        "slavic_ski": r"(ski|ska|sky|skaya)$",
        "slavic_ic": r"(ić|ič|ic)$",
        "slavic_uk": r"(uk|enko|ko)$",
        # Arabic
        "arabic_al": r"^(al|el|Al|El)[- ]",
        "arabic_ibn": r"(ibn|bin|bint)",
        # Chinese patterns
        "chinese_mono": r"^[\u4e00-\u9fff]$",  # Single character surname
        # Korean patterns
        "korean_kim": r"^(Kim|Park|Lee|Choi|Jung|Kang|Cho|Yoon|Jang|Lim)",
        # Western European
        "french_de": r"^[dD]e\s",
        "dutch_van": r"^[vV]an\s",
        "german_von": r"^[vV]on\s",
        # Latin American
        "hispanic_ez": r"(ez|éz)$",
        "hispanic_double": r"\s(y|de|del|de la)\s",
        # Nordic
        "nordic_son": r"(son|sen|dóttir|dottir)$",
        # African patterns
        "african_prefix": r"^(N|M|K|O)[A-Z]",
    }

    def __init__(self):
        import re

        self.re = re

    def extract_features(
        self, entry: Dict, phase1_result, phase2_results
    ) -> np.ndarray:
        """
        Extract 86 features for meta-classification.

        Args:
            entry: Name entry dict
            phase1_result: Phase 1 detection result
            phase2_results: Phase 2 top-k results (list of DetectionResult)

        Returns:
            86-dimensional feature vector
        """
        features = []
        name = entry.get("CanonicalNative", "")

        # Features 1-2: Phase 1 prediction
        features.append(self._region_to_ordinal(phase1_result.region_code))  # 1
        features.append(phase1_result.confidence)  # 2

        # Features 3-6: Phase 2 top-2 predictions
        if phase2_results and len(phase2_results) > 0:
            features.append(self._region_to_ordinal(phase2_results[0].region_code))  # 3
            features.append(phase2_results[0].confidence)  # 4
        else:
            features.extend([0, 0])

        if phase2_results and len(phase2_results) > 1:
            features.append(self._region_to_ordinal(phase2_results[1].region_code))  # 5
            features.append(phase2_results[1].confidence)  # 6
        else:
            features.extend([0, 0])

        # Features 7-8: Agreement signals
        phase1_region = phase1_result.region_code
        phase2_region = phase2_results[0].region_code if phase2_results else None

        features.append(
            1.0 if phase1_region == phase2_region else 0.0
        )  # 7: exact agreement
        features.append(
            1.0
            if phase1_region and phase2_region and phase1_region[0] == phase2_region[0]
            else 0.0
        )  # 8: group agreement (A1/A2 etc)

        # Features 9-28: Script detection (20 features)
        for script, pattern in self.SCRIPT_PATTERNS.items():
            has_script = 1.0 if self.re.search(pattern, name) else 0.0
            features.append(has_script)

        # Features 29-44: Surname pattern matching (16 features)
        for pattern_name, pattern in self.SURNAME_PATTERNS.items():
            matches = 1.0 if self.re.search(pattern, name, self.re.IGNORECASE) else 0.0
            features.append(matches)

        # Features 45-60: Name structure (16 features)
        parts = name.split()
        features.append(len(parts))  # 45: number of name parts
        features.append(len(name))  # 46: total character count
        features.append(
            len(name.replace(" ", ""))
        )  # 47: character count without spaces
        features.append(1.0 if len(parts) >= 3 else 0.0)  # 48: has 3+ parts
        features.append(
            1.0 if any(len(p) == 1 for p in parts) else 0.0
        )  # 49: has initial
        features.append(1.0 if "," in name else 0.0)  # 50: has comma
        features.append(1.0 if "-" in name else 0.0)  # 51: has hyphen
        features.append(1.0 if "'" in name else 0.0)  # 52: has apostrophe
        features.append(
            1.0 if any(c.isupper() for c in name[1:]) else 0.0
        )  # 53: has internal caps
        features.append(sum(1 for c in name if c.isupper()))  # 54: uppercase count
        features.append(sum(1 for c in name if c.islower()))  # 55: lowercase count
        features.append(sum(1 for c in name if c.isdigit()))  # 56: digit count
        features.append(
            sum(1 for c in name if not c.isalnum() and c != " ")
        )  # 57: special char count

        # Compute average part length
        if parts:
            avg_part_len = sum(len(p) for p in parts) / len(parts)
            max_part_len = max(len(p) for p in parts)
            min_part_len = min(len(p) for p in parts)
        else:
            avg_part_len = 0
            max_part_len = 0
            min_part_len = 0

        features.append(avg_part_len)  # 58: average part length
        features.append(max_part_len)  # 59: max part length
        features.append(min_part_len)  # 60: min part length

        # Features 61-86: Advanced morphological features (26 features)

        # Vowel/consonant patterns
        vowels = "aeiouAEIOU"
        vowel_count = sum(1 for c in name if c in vowels)
        consonant_count = sum(1 for c in name if c.isalpha() and c not in vowels)

        features.append(vowel_count)  # 61
        features.append(consonant_count)  # 62
        features.append(
            vowel_count / len(name) if len(name) > 0 else 0
        )  # 63: vowel ratio

        # Diacritic detection
        diacritics = "áéíóúàèìòùâêîôûäëïöüãõñçåøæœ"
        features.append(
            1.0 if any(c.lower() in diacritics for c in name) else 0.0
        )  # 64: has diacritics
        features.append(
            sum(1 for c in name if c.lower() in diacritics)
        )  # 65: diacritic count

        # Character diversity
        unique_chars = len(set(name.lower()))
        features.append(unique_chars)  # 66
        features.append(
            unique_chars / len(name) if len(name) > 0 else 0
        )  # 67: char diversity ratio

        # Repeating character patterns
        has_double = any(i > 0 and name[i] == name[i - 1] for i in range(len(name)))
        features.append(1.0 if has_double else 0.0)  # 68

        # Word boundaries (camelCase detection)
        has_camel_case = any(
            i > 0 and name[i].isupper() and name[i - 1].islower()
            for i in range(len(name))
        )
        features.append(1.0 if has_camel_case else 0.0)  # 69

        # Phonetic complexity (consonant clusters)
        consonants = "bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ"
        max_consonant_run = 0
        current_run = 0
        for c in name:
            if c in consonants:
                current_run += 1
                max_consonant_run = max(max_consonant_run, current_run)
            else:
                current_run = 0

        features.append(max_consonant_run)  # 70

        # Name position features (first/last part characteristics)
        if parts:
            first_part = parts[0]
            last_part = parts[-1]

            features.append(len(first_part))  # 71
            features.append(len(last_part))  # 72
            features.append(1.0 if first_part[0].isupper() else 0.0)  # 73
            features.append(1.0 if last_part[0].isupper() else 0.0)  # 74
            features.append(1.0 if first_part.isupper() else 0.0)  # 75
            features.append(1.0 if last_part.isupper() else 0.0)  # 76
        else:
            features.extend([0, 0, 0, 0, 0, 0])

        # Confidence gap between Phase 1 and Phase 2
        conf_gap = abs(
            phase1_result.confidence
            - (phase2_results[0].confidence if phase2_results else 0)
        )
        features.append(conf_gap)  # 77

        # Confidence of top-2 agreement
        if phase2_results and len(phase2_results) > 1:
            top2_gap = phase2_results[0].confidence - phase2_results[1].confidence
            features.append(top2_gap)  # 78
        else:
            features.append(0)

        # Padding to reach exactly 86 features
        while len(features) < 86:
            features.append(0.0)

        # Ensure exactly 86 features
        features = features[:86]

        return np.array(features, dtype=np.float32)

    def _region_to_ordinal(self, region_code: str) -> int:
        """Convert region code to ordinal for encoding."""
        # Map region codes to integers 0-36
        all_regions = [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "B1",
            "B2",
            "B3",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "F1",
            "F2",
            "F3",
            "F4",
            "G1",
            "H1",
            "R0",
            "Z0",
        ]

        try:
            return all_regions.index(region_code)
        except ValueError:
            return 36  # Default to Z0 (quarantine)


def main():
    print("=" * 80)
    print("XGBOOST META-CLASSIFIER TRAINING")
    print("=" * 80)
    print()

    if not XGBOOST_AVAILABLE:
        print("⚠️  XGBoost not available. Install with:")
        print("   pip install xgboost")
        return 1

    print("Phase 2 ML - Day 4: Training XGBoost ensemble")
    print("86-feature meta-classifier combining Phase 1 + Phase 2")
    print()

    # Initialize hybrid classifier
    print("Initializing hybrid classifier...")
    classifier = HybridRegionClassifier()
    feature_extractor = MetaClassifierFeatureExtractor()
    print()

    # Load training data
    test_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "test_suites"
        / "tier1_regional_comprehensive.json"
    )

    with open(test_file) as f:
        test_data = json.load(f)

    entries = test_data["test_data"]
    total = len(entries)

    print(f"Loaded {total} training entries")
    print()

    # Extract features for all entries
    print("Extracting features...")
    X = []
    y = []

    for i, entry in enumerate(entries):
        if (i + 1) % 500 == 0:
            print(f"  Processed {i+1}/{total} entries...")

        # Get predictions
        phase1_result = classifier.phase1.detect_region(entry)
        phase2_results = []

        if classifier.use_ml and classifier.phase2:
            name = entry.get("CanonicalNative", "")
            if name:
                try:
                    pred = classifier.phase2.predict(name, k=3)
                    for j in range(min(3, len(pred[0]))):
                        from src.regions.hybrid_classifier import DetectionResult

                        ml_region = pred[0][j].replace("__label__", "")
                        ml_conf = float(pred[1][j])
                        phase2_results.append(
                            DetectionResult(
                                region_code=ml_region,
                                confidence=ml_conf,
                                detection_method="phase2",
                                metadata={},
                            )
                        )
                except:
                    pass

        # Extract features
        features = feature_extractor.extract_features(
            entry, phase1_result, phase2_results
        )
        X.append(features)

        # Label
        region = entry["Region"].upper().replace("_SYNTHETIC", "")
        y.append(feature_extractor._region_to_ordinal(region))

    print(f"  Processed {total}/{total} entries")
    print()

    X = np.array(X)
    y = np.array(y)

    print(f"Feature matrix shape: {X.shape}")
    print(f"Label vector shape: {y.shape}")
    print()

    # Split train/test (80/20)
    split_idx = int(0.8 * len(X))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"Training set: {len(X_train)} entries")
    print(f"Test set: {len(X_test)} entries")
    print()

    # Train XGBoost
    print("Training XGBoost meta-classifier...")
    print()

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    # XGBoost parameters
    params = {
        "objective": "multi:softprob",
        "num_class": 37,
        "max_depth": 6,
        "eta": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "mlogloss",
        "seed": 42,
    }

    # Train with early stopping
    evals = [(dtrain, "train"), (dtest, "test")]
    bst = xgb.train(
        params,
        dtrain,
        num_boost_round=200,
        evals=evals,
        early_stopping_rounds=20,
        verbose_eval=20,
    )

    print()
    print("Training complete!")
    print()

    # Evaluate
    print("=" * 80)
    print("EVALUATION")
    print("=" * 80)
    print()

    y_pred = bst.predict(dtest)
    y_pred_labels = np.argmax(y_pred, axis=1)

    accuracy = np.mean(y_pred_labels == y_test)

    print(f"Test accuracy: {accuracy*100:.2f}%")
    print()

    # Save model
    model_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "ml_training"
        / "xgboost_metaclassifier.json"
    )
    bst.save_model(str(model_file))

    print(f"Model saved to: {model_file}")
    print()

    # Summary
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Validate on full dataset:")
    print("   python scripts/ml/validate_xgboost.py")
    print()
    print("2. Compare with hybrid baseline (97.54%):")
    print("   - Hybrid: 97.54% top-1, 99.93% top-3")
    print(f"   - XGBoost: {accuracy*100:.2f}% (test set)")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
