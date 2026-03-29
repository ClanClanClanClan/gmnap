#!/usr/bin/env python3
"""
Prepare fastText Training Data from Real Mathematicians

Creates fastText training file combining:
- 70% real mathematician data (6,913 profiles with country-mapped regions)
- 30% synthetic data (for rare region coverage)

Output format: __label__<region> <name>

This addresses the critical issue: System was trained on 100% synthetic data,
now we train on real naming patterns with actual affiliation data.
"""

import sys
import json
import random
from pathlib import Path
from collections import Counter

# Simple synthetic name generator for rare regions
SYNTHETIC_NAMES = {
    "A1": ["John Smith", "Mary Johnson", "David Williams", "Sarah Brown", "Michael Davis"],
    "A2": ["Hans Mueller", "Jean Dubois", "Marco Rossi", "Pedro Garcia", "Jan de Vries"],
    "A3": ["Lars Andersson", "Erik Nielsen", "Mikko Virtanen", "Ole Hansen", "Sven Johansson"],
    "B1": ["Ivan Petrov", "Dmitri Ivanov", "Olga Sokolova", "Andrei Volkov", "Natalia Popova"],
    "B2": ["Jan Kowalski", "Petr Novak", "Istvan Nagy", "Wojciech Wisniewski", "Anna Nowak"],
    "B3": ["Georgios Papadopoulos", "Maria Konstantinou", "Dimitrios Georgiou", "Andreas Ioannou"],
    "C1": ["Mehmet Yilmaz", "Ayse Demir", "Mustafa Kaya", "Fatma Celik", "Ali Sahin"],
    "C2": ["Mohammad Rezai", "Fatemeh Ahmadi", "Ali Hosseini", "Zahra Karimi", "Hassan Moradi"],
    "C3": ["Ahmed Hassan", "Fatima Ali", "Mohamed Ibrahim", "Sara Mahmoud", "Omar Khalil"],
    "C4": ["Abdullah Al-Rashid", "Fatima Al-Masri", "Mohammed Al-Khalifa", "Aisha Al-Saud"],
    "C5": ["Mohamed Benali", "Fatima Bouzid", "Ahmed Mansour", "Yasmine El-Fassi"],
    "C6": ["David Cohen", "Rachel Levy", "Yosef Katz", "Sarah Friedman", "Michael Goldberg"],
    "D1": ["Raj Kumar", "Priya Sharma", "Amit Patel", "Anita Singh", "Rahul Gupta"],
    "D3": ["Rahim Ahmed", "Fatima Begum", "Karim Rahman", "Nasrin Akter", "Habib Chowdhury"],
    "D4": ["Muhammad Khan", "Fatima Malik", "Ahmed Ali", "Ayesha Hassan", "Omar Hussain"],
    "E1": ["Wang Wei", "Li Na", "Zhang Ming", "Liu Yang", "Chen Jing"],
    "E2": ["Lin Mei-ling", "Chen Chih-wei", "Wu Hsiao-fen", "Huang Ming-chuan", "Lee Shu-chen"],
    "E3": ["Tanaka Yuki", "Suzuki Aiko", "Sato Takeshi", "Yamamoto Keiko", "Watanabe Hiroshi"],
    "E4": ["Kim Min-jun", "Lee Seo-yeon", "Park Ji-hoon", "Choi Soo-jin", "Jung Hyun-woo"],
    "E5": ["Nguyen Van An", "Tran Thi Lan", "Le Van Hai", "Pham Thi Mai", "Hoang Van Duc"],
    "E6": ["Somchai Srisuk", "Thida Phongsavanh", "Aung Win", "Bopha Sok", "Phimmasone Kham"],
    "E7": ["Ahmad Bin Hassan", "Siti Nurhaliza", "Jose Rizal", "Maria Santos", "Budi Santoso"],
    "F1": ["Mamadou Diallo", "Fatou Sow", "Ibrahim Traore", "Aminata Toure", "Ousmane Kone"],
    "F2": ["Chukwuemeka Okafor", "Amara Mensah", "Kwame Nkrumah", "Nia Kamau", "Abebe Bekele"],
    "F3": ["Abebe Gebre", "Fatuma Mohamed", "Yohannes Tesfaye", "Hawa Ahmed", "Dawit Haile"],
    "G1": ["Juan Rodriguez", "Maria Garcia", "Carlos Hernandez", "Ana Martinez", "Jose Lopez"],
}


def load_train_split():
    """Load the real training data (6,913 profiles)."""
    train_path = Path("data/ml_training/train_split.json")

    with open(train_path) as f:
        data = json.load(f)

    return data["profiles"]


def generate_synthetic_samples(n_samples=3000):
    """
    Generate synthetic samples for rare regions.

    Uses simple combinations to ensure coverage of underrepresented regions.
    """
    samples = []

    # Get region distribution from synthetic names
    regions = list(SYNTHETIC_NAMES.keys())

    # Generate n_samples
    for _ in range(n_samples):
        region = random.choice(regions)
        name = random.choice(SYNTHETIC_NAMES[region])

        samples.append({"name": name, "region": region, "source": "synthetic"})

    return samples


def prepare_fasttext_data(real_profiles, synthetic_profiles):
    """
    Prepare data in fastText format.

    Format: __label__<region> <name>
    """
    combined = real_profiles + synthetic_profiles

    # Shuffle to mix real and synthetic
    random.seed(42)
    random.shuffle(combined)

    lines = []
    for profile in combined:
        region = profile["region"]
        name = profile["name"]

        # fastText format
        line = f"__label__{region} {name}"
        lines.append(line)

    return lines


def save_training_data(lines):
    """Save training data in fastText format."""
    output_path = Path("data/ml_training/real_mathematicians_train.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    return output_path


def print_stats(real_profiles, synthetic_profiles, lines):
    """Print statistics about the training data."""
    print(f"\n{'='*80}")
    print("TRAINING DATA STATISTICS")
    print(f"{'='*80}\n")

    print(
        f"Real mathematician data: {len(real_profiles)} ({len(real_profiles)/(len(real_profiles)+len(synthetic_profiles))*100:.1f}%)"
    )
    print(
        f"Synthetic data: {len(synthetic_profiles)} ({len(synthetic_profiles)/(len(real_profiles)+len(synthetic_profiles))*100:.1f}%)"
    )
    print(f"Total: {len(lines)}")
    print()

    # Regional distribution
    print("Regional distribution in training data:")

    real_regions = Counter(p["region"] for p in real_profiles)
    synthetic_regions = Counter(p["region"] for p in synthetic_profiles)
    all_regions = set(real_regions.keys()) | set(synthetic_regions.keys())

    for region in sorted(all_regions):
        real_count = real_regions.get(region, 0)
        synthetic_count = synthetic_regions.get(region, 0)
        total = real_count + synthetic_count
        print(f"  {region}: {total} total ({real_count} real, {synthetic_count} synthetic)")

    print()
    print(f"Coverage: {len(all_regions)} regions")


def main():
    """Prepare fastText training data."""
    print("=" * 80)
    print("PREPARING FASTTEXT TRAINING DATA")
    print("=" * 80)
    print()

    # Load real data
    print("Loading real mathematician data (train split)...")
    real_profiles = load_train_split()
    print(f"✅ Loaded {len(real_profiles)} real profiles\n")

    # Generate synthetic data for coverage
    print("Generating synthetic data for rare regions...")
    synthetic_profiles = generate_synthetic_samples(n_samples=3000)
    print(f"✅ Generated {len(synthetic_profiles)} synthetic samples\n")

    # Prepare in fastText format
    print("Preparing fastText format...")
    lines = prepare_fasttext_data(real_profiles, synthetic_profiles)
    print(f"✅ Prepared {len(lines)} training examples\n")

    # Save
    print("Saving training data...")
    output_path = save_training_data(lines)
    print(f"✅ Saved to {output_path}\n")

    # Stats
    print_stats(real_profiles, synthetic_profiles, lines)

    print(f"\n{'='*80}")
    print("✅ TRAINING DATA PREPARED")
    print(f"{'='*80}\n")
    print(f"Next step: Train fastText model with:")
    print(f"  python3 scripts/ml/train_fasttext_on_real_data.py\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
