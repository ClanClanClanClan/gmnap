#!/usr/bin/env python3
"""
Download OSCAR-23.01 Korean corpus using multiple approaches.
"""

import os
import sys
import requests
from datasets import load_dataset
import gzip
import shutil

def download_oscar_direct():
    """Try multiple methods to download OSCAR Korean data"""
    
    os.makedirs("data/corp", exist_ok=True)
    
    # Method 1: Try OSCAR-2301 in Parquet format from HuggingFace
    print("Method 1: Trying OSCAR-2301 in Parquet format...")
    try:
        # OSCAR datasets are now available in Parquet format
        dataset = load_dataset(
            "oscar-corpus/OSCAR-2301", 
            "ko",  # Korean
            split="train",
            streaming=True,  # Use streaming to handle large dataset
            cache_dir="data/corp"
        )
        
        # Stream and save first 100MB of text
        output_file = "data/corp/oscar_ko_sample.txt"
        bytes_written = 0
        max_bytes = 100 * 1024 * 1024  # 100MB
        
        with open(output_file, "w", encoding="utf-8") as f:
            for i, example in enumerate(dataset):
                text = example.get("text", example.get("content", ""))
                if text:
                    f.write(text + "\n")
                    bytes_written += len(text.encode('utf-8'))
                    
                if bytes_written >= max_bytes:
                    break
                    
                if i % 1000 == 0:
                    print(f"  Processed {i} examples, {bytes_written / 1024 / 1024:.1f} MB")
        
        print(f"✓ Method 1 Success: Saved {bytes_written / 1024 / 1024:.1f} MB to {output_file}")
        return True
        
    except Exception as e:
        print(f"✗ Method 1 failed: {e}")
    
    # Method 2: Try the new OSCAR format with different naming
    print("\nMethod 2: Trying alternative OSCAR dataset names...")
    alternative_names = [
        ("oscar", "unshuffled_deduplicated_ko"),
        ("oscar-corpus/oscar", "ko"), 
        ("bigscience/oscar", "ko"),
    ]
    
    for dataset_name, config in alternative_names:
        try:
            print(f"  Trying {dataset_name} with config {config}...")
            dataset = load_dataset(
                dataset_name,
                config,
                split="train",
                streaming=True,
                cache_dir="data/corp"
            )
            
            # Save sample
            output_file = f"data/corp/{dataset_name.replace('/', '_')}_{config}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                for i, example in enumerate(dataset):
                    if i >= 10000:  # Sample size
                        break
                    text = example.get("text", example.get("content", ""))
                    if text:
                        f.write(text + "\n")
            
            print(f"✓ Method 2 Success with {dataset_name}: Saved to {output_file}")
            return True
            
        except Exception as e:
            print(f"  Failed: {e}")
            continue
    
    # Method 3: Try Common Crawl Korean data as alternative
    print("\nMethod 3: Trying Common Crawl Korean data...")
    try:
        dataset = load_dataset(
            "allenai/c4",
            "ko", 
            split="train",
            streaming=True,
            cache_dir="data/corp"
        )
        
        output_file = "data/corp/c4_ko_sample.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for i, example in enumerate(dataset):
                if i >= 50000:
                    break
                text = example.get("text", "")
                if text:
                    f.write(text + "\n")
                    
                if i % 5000 == 0:
                    print(f"  Processed {i} examples")
        
        print(f"✓ Method 3 Success: C4 Korean data saved to {output_file}")
        return True
        
    except Exception as e:
        print(f"✗ Method 3 failed: {e}")
    
    # Method 4: Download from direct URLs if available
    print("\nMethod 4: Trying direct download URLs...")
    direct_urls = [
        # Add any known direct download URLs for OSCAR Korean
        # These would be URLs to .txt.gz or similar files
    ]
    
    for url in direct_urls:
        try:
            print(f"  Downloading from {url}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            filename = url.split("/")[-1]
            filepath = f"data/corp/{filename}"
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # If it's a gzip file, decompress it
            if filepath.endswith(".gz"):
                with gzip.open(filepath, 'rb') as f_in:
                    with open(filepath[:-3], 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(filepath)
                filepath = filepath[:-3]
            
            print(f"✓ Method 4 Success: Downloaded to {filepath}")
            return True
            
        except Exception as e:
            print(f"  Failed: {e}")
            continue
    
    return False

def main():
    print("Attempting to download OSCAR Korean corpus...")
    print("=" * 60)
    
    success = download_oscar_direct()
    
    if success:
        print("\n✓ Successfully downloaded Korean corpus!")
        print("Next step: Run count_syllables.py to extract frequencies")
    else:
        print("\n✗ All download methods failed.")
        print("Alternative: Create synthetic Korean text from existing data")

if __name__ == "__main__":
    main()