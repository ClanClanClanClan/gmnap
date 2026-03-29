#!/usr/bin/env python3
"""
Phase 1.1: Download Open Corpora
Exact implementation from blueprint lines 72-84
"""

import os
from datasets import load_dataset

# Create data/corp directory (blueprint line 73)
os.makedirs("data/corp", exist_ok=True)

# Exact code from blueprint lines 76-83
from datasets import load_dataset

for name in ["lcw99/cc100-ko-only", "mc4", "aihub_korean_news"]:
    try:
        ds = load_dataset(name, "ko", split="train", cache_dir="data/corp")
        print(name, len(ds))
    except Exception as e:
        print("Skip", name, e)
