import yaml
import argparse
from tqdm import tqdm
import json
import sys
sys.path.append('.')

from scripts.dice_coefficient_impl import roundtrip_score

def evaluate_dataset(yaml_path, threshold=0.97):
    """Evaluate round-trip accuracy on full dataset"""
    data = yaml.safe_load(open(yaml_path))
    
    results = []
    for entry_id, entry in tqdm(data.items()):
        canonical = entry.get("CanonicalLatin", "")
        if canonical:
            score = roundtrip_score(canonical)
            results.append({
                "id": entry_id,
                "name": canonical,
                "score": score,
                "pass": score >= threshold
            })
    
    # Summary statistics
    passing = sum(1 for r in results if r["pass"])
    total = len(results)
    accuracy = passing / total
    
    print(f"Overall accuracy: {accuracy:.1%} ({passing}/{total})")
    
    # Save detailed results
    with open("validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return accuracy >= threshold

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-t", "--threshold", type=float, default=0.97)
    args = parser.parse_args()
    
    success = evaluate_dataset(args.input, args.threshold)
    exit(0 if success else 1)