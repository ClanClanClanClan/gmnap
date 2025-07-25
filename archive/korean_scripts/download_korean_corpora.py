#!/usr/bin/env python3
"""
Download available Korean corpora
Following blueprint Phase 1 requirements
"""

import os
from datasets import load_dataset

# Create data/corp directory
os.makedirs("data/corp", exist_ok=True)

# Try to download available Korean datasets
print("Downloading Korean corpora...")

# Alternative Korean datasets that are available
datasets_to_try = [
    ("wikipedia", "20220301.ko"),  # Korean Wikipedia
    ("oscar", "unshuffled_deduplicated_ko"),  # OSCAR Korean subset
]

for dataset_name, config in datasets_to_try:
    try:
        print(f"\nDownloading {dataset_name} ({config})...")
        
        # Download a subset for processing
        if dataset_name == "wikipedia":
            ds = load_dataset(dataset_name, config, split="train", cache_dir="data/corp")
        else:
            # For OSCAR, get a sample due to size
            ds = load_dataset(dataset_name, config, split="train[:1%]", cache_dir="data/corp")
        
        # Save text content
        output_file = f"data/corp/{dataset_name}_{config.replace('.', '_')}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            count = 0
            for item in ds:
                text = item.get("text", item.get("content", ""))
                if text and len(text.strip()) > 10:
                    f.write(text.strip() + "\n")
                    count += 1
                    if count % 10000 == 0:
                        print(f"  Processed {count} documents...")
        
        print(f"✓ Saved {count} documents to {output_file}")
        
    except Exception as e:
        print(f"✗ Failed to download {dataset_name} ({config}): {e}")
        continue

print("\nCorpus download complete.")