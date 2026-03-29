#!/usr/bin/env python3
"""
Validate Phase 2 on REAL Collected Mathematician Data

Uses 1414 real mathematician names collected from:
- OpenAlex (997 with country codes)
- arXiv (417 names)

Maps country codes to expected regions and validates HybridRegionManager accuracy.

This is the REAL test - not synthetic, not simulated, but actual mathematician names
from production academic databases.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_region_manager import HybridRegionManager

# Country code to region mapping (ISO 3166-1 alpha-2)
COUNTRY_TO_REGION = {
    # A1 - Anglo-Sphere
    "US": "A1",
    "GB": "A1",
    "CA": "A1",
    "AU": "A1",
    "NZ": "A1",
    "IE": "A1",
    # A2 - Western Europe
    "DE": "A2",
    "FR": "A2",
    "IT": "A2",
    "ES": "A2",
    "PT": "A2",
    "BE": "A2",
    "NL": "A2",
    "CH": "A2",
    "AT": "A2",
    "LU": "A2",
    # A3 - Nordic/Baltic
    "SE": "A3",
    "NO": "A3",
    "DK": "A3",
    "FI": "A3",
    "IS": "A3",
    "EE": "A3",
    "LV": "A3",
    "LT": "A3",
    # A4 - Oceania
    # (AU, NZ already in A1)
    # A5 - Caribbean
    "JM": "A5",
    "TT": "A5",
    "BB": "A5",
    # B1 - East Slavic
    "RU": "B1",
    "UA": "B1",
    "BY": "B1",
    # B2 - South Slavic/Central Europe
    "PL": "B2",
    "CZ": "B2",
    "SK": "B2",
    "HU": "B2",
    "SI": "B2",
    "HR": "B2",
    "RS": "B2",
    "BA": "B2",
    "MK": "B2",
    "BG": "B2",
    "RO": "B2",
    # B3 - Greek
    "GR": "B3",
    "CY": "B3",
    # C1 - Turkic
    "TR": "C1",
    "AZ": "C1",
    "KZ": "C1",
    "UZ": "C1",
    "TM": "C1",
    "KG": "C1",
    # C2 - Persian/Tajik
    "IR": "C2",
    "AF": "C2",
    "TJ": "C2",
    # C3 - Arabic Levant/Nile
    "EG": "C3",
    "IQ": "C3",
    "SY": "C3",
    "LB": "C3",
    "JO": "C3",
    "PS": "C3",
    # C4 - Arabic Gulf
    "SA": "C4",
    "AE": "C4",
    "QA": "C4",
    "KW": "C4",
    "BH": "C4",
    "OM": "C4",
    "YE": "C4",
    # C5 - Arabic Maghreb
    "MA": "C5",
    "DZ": "C5",
    "TN": "C5",
    "LY": "C5",
    # C6 - Hebrew/Diaspora
    "IL": "C6",
    # C7 - Armenian
    "AM": "C7",
    # C8 - Georgian
    "GE": "C8",
    # D1 - South Asia Hindi Belt
    "IN": "D1",  # Note: India is complex, we'll use D1 as default
    # D3 - South Asia Bengali
    "BD": "D3",
    # D4 - Pakistan/Urdu
    "PK": "D4",
    # D5 - Sinhala
    "LK": "D5",
    # E1 - Sinophone Mainland
    "CN": "E1",
    # E2 - Traditional Chinese
    "TW": "E2",
    "HK": "E2",
    "MO": "E2",
    # E3 - Japan
    "JP": "E3",
    # E4 - Korea
    "KR": "E4",
    "KP": "E4",
    # E5 - Vietnam
    "VN": "E5",
    # E6 - Mainland SEA
    "TH": "E6",
    "MM": "E6",
    "LA": "E6",
    "KH": "E6",
    # E7 - Maritime SEA
    "MY": "E7",
    "SG": "E7",
    "ID": "E7",
    "PH": "E7",
    "BN": "E7",
    # F1 - SSA Francophone
    "SN": "F1",
    "CI": "F1",
    "ML": "F1",
    "BF": "F1",
    "NE": "F1",
    "TD": "F1",
    "CM": "F1",
    "CG": "F1",
    "CD": "F1",
    "GA": "F1",
    "BJ": "F1",
    "TG": "F1",
    # F2 - SSA Anglophone
    "NG": "F2",
    "GH": "F2",
    "KE": "F2",
    "UG": "F2",
    "TZ": "F2",
    "ZA": "F2",
    "ZW": "F2",
    "ZM": "F2",
    "MW": "F2",
    "BW": "F2",
    "LS": "F2",
    "SZ": "F2",
    # F3 - Horn of Africa
    "ET": "F3",
    "ER": "F3",
    "SO": "F3",
    "DJ": "F3",
    # F4 - Lusophone Africa
    "AO": "F4",
    "MZ": "F4",
    "GW": "F4",
    "CV": "F4",
    "ST": "F4",
    # G1 - Latin America
    "MX": "G1",
    "BR": "G1",
    "AR": "G1",
    "CL": "G1",
    "CO": "G1",
    "VE": "G1",
    "PE": "G1",
    "EC": "G1",
    "BO": "G1",
    "PY": "G1",
    "UY": "G1",
    "GT": "G1",
    "HN": "G1",
    "SV": "G1",
    "NI": "G1",
    "CR": "G1",
    "PA": "G1",
    "CU": "G1",
    "DO": "G1",
    "PR": "G1",
    "HT": "G1",
}


def load_collected_data():
    """Load the 1414 real mathematician names."""
    data_path = Path("data/real_world_collection/real_mathematicians_combined.json")

    with open(data_path) as f:
        data = json.load(f)

    return data["profiles"]


def map_to_regions(profiles):
    """
    Map country codes to expected regions.

    Returns:
        List of profiles with expected_region field
    """
    mapped = []
    unmapped_countries = set()

    for profile in profiles:
        country_code = profile.get("country_code")

        if country_code:
            expected_region = COUNTRY_TO_REGION.get(country_code)

            if expected_region:
                profile["expected_region"] = expected_region
                mapped.append(profile)
            else:
                unmapped_countries.add(country_code)
        # Skip profiles without country codes

    if unmapped_countries:
        print(f"⚠️  Unmapped country codes: {sorted(unmapped_countries)}\n")

    return mapped


def validate_on_real_data(profiles):
    """
    Validate HybridRegionManager on real mathematician data.

    Args:
        profiles: List of profiles with name, expected_region

    Returns:
        dict with accuracy metrics
    """
    print(f"Validating on {len(profiles)} real mathematician names...")
    print()

    manager = HybridRegionManager(use_security=False)

    results = {
        "total": len(profiles),
        "correct": 0,
        "failures": [],
        "regional_stats": defaultdict(lambda: {"total": 0, "correct": 0}),
        "confidence_stats": [],
    }

    for i, profile in enumerate(profiles):
        # Detect region
        entry = {"CanonicalNative": profile["name"]}
        detection = manager.detect_region(entry)

        expected = profile["expected_region"]
        detected = detection.region_code

        # Normalize (remove underscores, take prefix)
        expected_prefix = expected.split("_")[0] if "_" in expected else expected[:2]
        detected_prefix = detected.split("_")[0] if "_" in detected else detected[:2]

        # Track regional performance
        results["regional_stats"][expected_prefix]["total"] += 1

        # Check correctness
        is_correct = expected_prefix == detected_prefix

        if is_correct:
            results["correct"] += 1
            results["regional_stats"][expected_prefix]["correct"] += 1
        else:
            results["failures"].append(
                {
                    "name": profile["name"],
                    "expected": expected_prefix,
                    "detected": detected_prefix,
                    "confidence": detection.confidence,
                    "method": detection.detection_method,
                    "country": profile.get("country_code", "Unknown"),
                    "source": profile.get("source", "Unknown"),
                }
            )

        # Track confidence
        results["confidence_stats"].append(
            {"confidence": detection.confidence, "correct": is_correct}
        )

        # Progress
        if (i + 1) % 100 == 0 or (i + 1) == len(profiles):
            acc = results["correct"] / (i + 1) * 100
            print(f"  Progress: {i+1}/{len(profiles)} ({acc:.2f}% accurate)")

    # Calculate accuracy
    results["accuracy"] = (
        results["correct"] / results["total"] * 100 if results["total"] > 0 else 0
    )

    return results


def print_results(results):
    """Print detailed validation results."""
    print(f"\n{'='*80}")
    print("VALIDATION RESULTS ON REAL MATHEMATICIAN DATA")
    print(f"{'='*80}\n")

    print(
        f"Overall Accuracy: {results['correct']}/{results['total']} = {results['accuracy']:.2f}%"
    )
    print()

    # Regional breakdown
    print("Regional Performance:")
    sorted_regions = sorted(
        results["regional_stats"].items(), key=lambda x: x[1]["total"], reverse=True
    )

    for region, stats in sorted_regions:
        acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✅" if acc >= 90 else "⚠️" if acc >= 70 else "❌"
        print(f"  {status} {region}: {stats['correct']}/{stats['total']} = {acc:.1f}%")

    # Confidence analysis
    avg_conf = sum(s["confidence"] for s in results["confidence_stats"]) / len(
        results["confidence_stats"]
    )
    correct_conf = [
        s["confidence"] for s in results["confidence_stats"] if s["correct"]
    ]
    incorrect_conf = [
        s["confidence"] for s in results["confidence_stats"] if not s["correct"]
    ]

    print()
    print("Confidence Analysis:")
    print(f"  Average: {avg_conf:.3f}")
    if correct_conf:
        print(f"  Correct predictions: {sum(correct_conf)/len(correct_conf):.3f}")
    if incorrect_conf:
        print(f"  Incorrect predictions: {sum(incorrect_conf)/len(incorrect_conf):.3f}")

    # Top failures
    if results["failures"]:
        print()
        print(f"Top 10 Failures (of {len(results['failures'])} total):")
        for i, failure in enumerate(results["failures"][:10], 1):
            print(f"  {i}. {failure['name']}")
            print(f"     Expected: {failure['expected']}, Got: {failure['detected']}")
            print(
                f"     Confidence: {failure['confidence']:.3f}, Method: {failure['method']}"
            )
            print(f"     Country: {failure['country']}, Source: {failure['source']}")


def main():
    """Main validation on real collected data."""
    print("=" * 80)
    print("REAL-WORLD VALIDATION: COLLECTED MATHEMATICIAN DATA")
    print("=" * 80)
    print()
    print("Data sources:")
    print("  - OpenAlex: 997 profiles with country codes")
    print("  - arXiv: 417 author names")
    print("  - Total: 1414 REAL mathematician names")
    print()

    # Load data
    print("Loading collected data...")
    profiles = load_collected_data()
    print(f"✅ Loaded {len(profiles)} profiles\n")

    # Map to regions
    print("Mapping country codes to regions...")
    mapped_profiles = map_to_regions(profiles)
    print(f"✅ Mapped {len(mapped_profiles)} profiles to regions\n")

    # Validate
    results = validate_on_real_data(mapped_profiles)

    # Print results
    print_results(results)

    # Verdict
    print(f"\n{'='*80}")
    print("VERDICT")
    print(f"{'='*80}\n")

    accuracy = results["accuracy"]

    if accuracy >= 95:
        print("✅ EXCELLENT: Phase 2 achieves ≥95% on REAL mathematician data!")
        print("   Phase 3 may not be needed.")
    elif accuracy >= 90:
        print("✅ GOOD: Phase 2 achieves 90%+ on REAL data")
        print("   Phase 3 could provide marginal improvement.")
    elif accuracy >= 85:
        print("⚠️  ACCEPTABLE: Phase 2 achieves 85%+ on REAL data")
        print("   Phase 3 recommended for production.")
    else:
        print("❌ NEEDS IMPROVEMENT: Phase 2 <85% on REAL data")
        print("   Phase 3 REQUIRED before production.")

    print()
    print(f"**Real-world accuracy: {accuracy:.2f}%**")
    print(f"Synthetic test accuracy: 97.54%")
    print(f"**Gap: {97.54 - accuracy:.2f}pp**")

    return 0 if accuracy >= 90 else 1


if __name__ == "__main__":
    sys.exit(main())
