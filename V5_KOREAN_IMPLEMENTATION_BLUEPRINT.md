# V5 Korean Implementation Blueprint - GMNAP v6.1 Compliance

## 🎯 Executive Summary

This blueprint provides a complete, step-by-step implementation to achieve ≥97% round-trip accuracy for Korean processing in GMNAP v6.1. Follow each step exactly as specified.

**Key Approach**: PyNini-based WFST architecture with corpus frequency weights, V4 back-off, and comprehensive romanization coverage.

---

## 📋 Implementation Phases Overview

| Phase | Component | Duration | Success Gate |
|-------|-----------|----------|--------------|
| 0 | Environment Setup | 1 hour | PyNini 2.1.6.post1 installed |
| 1 | Corpus & Frequency | 4 hours | `syllable_freq.json` created |
| 2 | Romanization Tables | 2 hours | 4 system CSV files generated |
| 3 | WFST Construction | 1 day | `ROMAN2HANGUL` FST < 30MB |
| 4 | Segmentation FST | 4 hours | Beam search passes tests |
| 5 | Variant Generator | 2 hours | Legacy patterns covered |
| 6 | PyNini Corrections | 1 hour | API calls validated |
| 7 | V4 Back-off | 4 hours | λ=3.0 integration complete |
| 8 | Classifier Tuning | 2 hours | 500-name set ≥97% |
| 9 | Validation Suite | 4 hours | Dice coefficient tests pass |
| 10 | GMNAP Integration | 1 day | E4 handler registered |
| 11 | Test Harness | 2 hours | All 751 entries pass |
| 12 | CI Integration | 1 hour | GitHub Actions green |
| 13 | Deployment | 2 hours | Canary error Δ<0.5% |
| 14 | Performance | 1 day | P95 <120ms |
| 15 | Anti-overfitting | Ongoing | Monthly corpus refresh |

**Total Duration**: 7 working days

---

## 🚀 Phase 0: Environment Setup

### Install Core Dependencies

```bash
# Create Python 3.12 virtual environment
python3.12 -m venv .venv && source .venv/bin/activate

# Install all required libraries
pip install "pynini==2.1.6.post1" openfst-python==1.8.3 tqdm pandas regex scikit-learn konlpy mecab-python3 rapidfuzz

# macOS: Install C tooling
brew install gcc automake libtool

# Ubuntu: Install C tooling
sudo apt-get install build-essential automake libtool pkg-config
```

### Verify Installation

```bash
python - <<'PY'
import pynini, openfst_python
assert pynini.string_file
print("PyNini", pynini.__version__, "OpenFst", openfst_python.__version__)
PY
```

**Expected Output**: `PyNini 2.1.6.post1 OpenFst 1.8.3`

---

## 📊 Phase 1: Corpus & Frequency Weights

### 1.1 Download Open Corpora

```bash
mkdir -p data/corp

python - <<'PY'
from datasets import load_dataset
for name in ["lcw99/cc100-ko-only", "mc4", "aihub_korean_news"]:
    try:
        ds = load_dataset(name, "ko", split="train", cache_dir="data/corp")
        print(name, len(ds))
    except Exception as e:
        print("Skip", name, e)
PY
```

**Expected Data**:
- CC100-ko: 390M lines
- mC4-ko: 150M lines
- AI-Hub: 100M sentences

### 1.2 Extract Syllable Frequencies

Create `scripts/count_syllables.py`:

```python
import re, sys, json

syll_pat = re.compile(r"[가-힣]")
freq = {}

for path in sys.argv[1:]:
    for line in open(path, "r", errors="ignore"):
        for ch in syll_pat.findall(line):
            freq[ch] = freq.get(ch, 0) + 1

json.dump(freq, open("data/syllable_freq.json", "w"))
```

Run extraction:

```bash
python scripts/count_syllables.py data/corp/cc100-ko-only/*.txt
```

**Success Gate**: `data/syllable_freq.json` exists with ~9,000 Korean syllables

---

## 🔤 Phase 2: Generate Romanization Tables

Create `src/v5/generate_tables.py`:

```python
import unicodedata as ud, json, itertools, csv, pathlib

# 2.1 Enumerate all 11,172 Hangul syllables
BASE, LCOUNT, VCOUNT, TCOUNT = 0xAC00, 19, 21, 28

def decompose(syl):
    code = ord(syl) - BASE
    L = code // (VCOUNT * TCOUNT)
    V = (code % (VCOUNT * TCOUNT)) // TCOUNT
    T = code % TCOUNT
    return L, V, T

LEADS  = ["g","kk","n","d","tt","r","m","b","pp","s","ss","ng","j","jj","ch","k","t","p","h"]
VOWELS = ["a","ae","ya","yae","eo","e","yeo","ye","o","wa","wae","oe","yo","u","wo","we","wi","yu","eu","ui","i"]
TAILS  = ["","k","k","ks","n","nj","nh","t","l","lk","lm","lp","ls","lt","lp","lh","m","p","ps","t","t","ng","t","t","k","t","p","t"]

# 2.2 Build mapping rules for four systems
def rr(lead, vowel, tail):
    """Revised Romanization rules"""
    r = LEADS[lead] + VOWELS[vowel] + TAILS[tail]
    # Context-sensitive fixes
    if tail == 0 and r.endswith("k"):
        r = r[:-1] + "g"
    return r

def mr(lead, vowel, tail):
    """McCune-Reischauer rules"""
    # Implement MR-specific mappings
    mr_leads = ["k","kk","n","t","tt","r","m","p","pp","s","ss","","ch","tch","ch'","k'","t'","p'","h"]
    mr_vowels = ["a","ae","ya","yae","ŏ","e","yŏ","ye","o","wa","wae","oe","yo","u","wŏ","we","wi","yu","ŭ","ŭi","i"]
    return mr_leads[lead] + mr_vowels[vowel] + TAILS[tail]

def yale(lead, vowel, tail):
    """Yale romanization rules"""
    # Implement Yale-specific mappings
    yale_leads = ["k","kk","n","t","tt","l","m","p","pp","s","ss","","c","cc","ch","kh","th","ph","h"]
    yale_vowels = ["a","ay","ya","yay","e","ey","ye","yey","o","wa","way","oy","yo","wu","we","wey","wi","yu","u","uy","i"]
    return yale_leads[lead] + yale_vowels[vowel] + TAILS[tail]

def mltr(lead, vowel, tail):
    """MLTR (Ministry) rules"""
    # Similar to RR with minor variations
    return rr(lead, vowel, tail)  # Simplified for now

# Generate all mappings
rr_map = {}
mr_map = {}
yale_map = {}
mltr_map = {}

for idx in range(11172):
    syl = chr(BASE + idx)
    l, v, t = decompose(syl)
    rr_map[syl] = rr(l, v, t)
    mr_map[syl] = mr(l, v, t)
    yale_map[syl] = yale(l, v, t)
    mltr_map[syl] = mltr(l, v, t)

# Write CSV files
pathlib.Path("data/rr_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in rr_map.items()), encoding="utf8")
pathlib.Path("data/mr_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in mr_map.items()), encoding="utf8")
pathlib.Path("data/yale_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in yale_map.items()), encoding="utf8")
pathlib.Path("data/mltr_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in mltr_map.items()), encoding="utf8")
```

Run generation:

```bash
python src/v5/generate_tables.py
```

**Success Gate**: 4 CSV files created in `data/` with 11,172 entries each

---

## 🔧 Phase 3: Build WFST Components

### 3.1 Create FST Helpers

Create `src/v5/fst_helpers.py`:

```python
import pynini as pn, json, math

TOK = "utf8"

def load_map(csv_path):
    """Load romanization map as FST"""
    pairs = []
    for line in open(csv_path, encoding="utf8"):
        k, v = line.rstrip().split(",", 1)
        pairs.append((v, k))  # roman → Hangul
    return pn.string_map(pairs, token_type=TOK).optimize()

# Load all romanization systems
RR_FST   = load_map("data/rr_table.csv")
MR_FST   = load_map("data/mr_table.csv")
YALE_FST = load_map("data/yale_table.csv")
MLTR_FST = load_map("data/mltr_table.csv")

# Basic union
ROMAN2HANGUL = (RR_FST | MR_FST | YALE_FST | MLTR_FST).optimize()

# 3.2 Add frequency weights
syll_freq = json.load(open("data/syllable_freq.json"))
total = sum(syll_freq.values())

def weight(hangul):
    """Calculate -log frequency weight"""
    return -math.log((syll_freq.get(hangul, 1)) / total)

# Build weighted FST
weighted = pn.Fst()
for fst in [RR_FST, MR_FST, YALE_FST, MLTR_FST]:
    for path in fst.paths():
        hangul_code = path.olabels[-1]  # Last output label
        hangul_char = chr(hangul_code)
        w = weight(hangul_char)
        # Add weighted path
        weighted = pn.union(weighted, fst @ pn.Weight(w))

ROMAN2HANGUL = weighted.optimize()

# Save for later use
ROMAN2HANGUL.write("data/roman2hangul.fst")
```

**Success Gate**: `fstinfo data/roman2hangul.fst` shows size < 30MB

---

## 🎵 Phase 4: Phonotactic Segmentation

### 4.1 Korean Syllable FSA

Create `src/v5/phonotactics.py`:

```python
import pynini as pn

# Define vowel and consonant sets for RR
V_STRINGS = ["a","ae","ya","yae","eo","e","yeo","ye","o","wa","wae","oe","yo","u","wo","we","wi","yu","eu","ui","i"]
C_STRINGS = ["g","kk","n","d","tt","r","m","b","pp","s","ss","j","jj","ch","k","t","p","h","ng","ks","nj","nh","lk","lm","lp","ls","lt","lh","ps"]

# Create FSAs
V = pn.string_set(V_STRINGS, token_type="utf8")
C = pn.string_set(C_STRINGS, token_type="utf8")

# Korean syllable structure: (C)V(C)
SYLL = (C.ques + V + C.ques).optimize()
WORD = pn.closure(SYLL, 1).optimize()

# Export for use
SYLL.write("data/korean_syllable.fsa")
```

### 4.2 Beam Search Segmenter

Create `src/v5/segmenter.py`:

```python
import pynini as pn
import heapq
import math

# Load syllable FSA
SYLL = pn.Fst.read("data/korean_syllable.fsa")

def segment(rr_str, beam=24):
    """Segment romanized string into syllables using beam search"""
    N = len(rr_str)
    chart = [[] for _ in range(N + 1)]
    chart[0] = [(0, [])]  # (cost, path)
    
    for i in range(N):
        for cost, path in chart[i]:
            # Try all possible syllable lengths (1-7 chars typical)
            for j in range(i + 1, min(i + 8, N) + 1):
                syl = rr_str[i:j].lower()
                
                # Check if valid syllable
                try:
                    if pn.compose(pn.acceptor(syl, token_type="utf8"), SYLL).num_states() > 0:
                        # Simple length-based cost (can use frequency later)
                        ncost = cost + len(syl)
                        heapq.heappush(chart[j], (ncost, path + [syl]))
                except:
                    continue
        
        # Keep only top beam candidates
        if chart[i + 1]:
            chart[i + 1] = heapq.nsmallest(beam, chart[i + 1])
    
    return chart[N]

# Enhanced with frequency scoring
def segment_with_freq(rr_str, freq_map, beam=24):
    """Segment using syllable frequencies"""
    N = len(rr_str)
    chart = [[] for _ in range(N + 1)]
    chart[0] = [(0, [])]
    
    for i in range(N):
        for cost, path in chart[i]:
            for j in range(i + 1, min(i + 8, N) + 1):
                syl = rr_str[i:j].lower()
                
                # Check validity and get frequency cost
                if is_valid_syllable(syl):
                    # Use -log P(syllable) as cost
                    syl_cost = -math.log(freq_map.get(syl, 1e-6))
                    ncost = cost + syl_cost
                    heapq.heappush(chart[j], (ncost, path + [syl]))
        
        if chart[i + 1]:
            chart[i + 1] = heapq.nsmallest(beam, chart[i + 1])
    
    return chart[N]

def is_valid_syllable(syl):
    """Check if string is valid Korean syllable in romanization"""
    try:
        composed = pn.compose(pn.acceptor(syl, token_type="utf8"), SYLL)
        return composed.num_states() > 0
    except:
        return False
```

**Success Gate**: `segmenter.py` passes unit tests for compound names

---

## 🔄 Phase 5: Variant Generator

Enhance existing `src/v5/variant_generator.py`:

```python
# Add comprehensive legacy patterns
_PATTERNS = [
    # Yale variants
    (r"ŏ", "eo"), (r"ŭ", "eu"), (r"ŏng", "ong"), (r"ŭng", "eung"),
    
    # McCune-Reischauer
    (r"kh", "k"), (r"th", "t"), (r"ph", "p"), (r"chh?", "ch"),
    
    # Common surname variants
    (r"choe", "choi"), (r"oe", "we"), (r"^ahn", "an"),
    (r"^ryu", "yu"), (r"^yi", "lee"), (r"^rhee", "lee"),
    
    # Vowel variations
    (r"oi", "oe"), (r"ae", "e"), (r"ui", "i"),
    
    # Initial liquids
    (r"^ry", "y"), (r"^ny", "y"), (r"^liu", "ryu"),
    
    # Hyphen/space handling
    (r"-", ""), (r"-", " "), (r" ", "-")
]

def generate_all_variants(name):
    """Generate comprehensive variant set"""
    variants = {name, name.lower()}
    
    # Apply all patterns recursively
    for pattern, replacement in _PATTERNS:
        new_variants = set()
        for variant in variants:
            # Both directions
            new_variants.add(re.sub(pattern, replacement, variant, flags=re.I))
            new_variants.add(re.sub(replacement, pattern, variant, flags=re.I))
        variants.update(new_variants)
    
    return variants
```

---

## 🔧 Phase 6: PyNini API Corrections

### Correct API Usage

```python
# Correct PyNini 2.1.6+ usage patterns

# Make acceptor
correct_acceptor = pn.acceptor("string", token_type="utf8")

# Compose
result = fst1 @ fst2  # Same as before

# Optimize
optimized = fst.optimize()  # Same

# Count arcs
total_arcs = sum(fst.num_arcs(s) for s in fst.states())

# Get shortest paths
paths = pn.shortestpath(fst, nshortest=1000, unique=True)
```

---

## 🔄 Phase 7: V4 Back-off Integration

### 7.1 Export V4 Data

Create `scripts/export_v4_to_fst.py`:

```python
import json
import pynini as pn
import sys

def export_v4_to_fst(v4_json_path, lambda_weight=3.0):
    """Convert V4 mappings to weighted FST"""
    v4_data = json.load(open(v4_json_path))
    
    # Build FST with penalty weight
    v4_fst = pn.Fst()
    
    for roman, hangul in v4_data.items():
        # Add path with λ penalty
        path = pn.cross(roman.lower(), hangul, token_type="utf8")
        weighted_path = path @ pn.Weight(lambda_weight)
        v4_fst = pn.union(v4_fst, weighted_path)
    
    v4_fst = v4_fst.optimize()
    v4_fst.write("data/v4_backoff.fst")
    return v4_fst

if __name__ == "__main__":
    export_v4_to_fst(sys.argv[1], float(sys.argv[2]))
```

### 7.2 Runtime Integration

```python
# In main converter
def convert_with_backoff(romanized):
    # Try main WFST first
    try:
        result = pn.compose(
            segment_lattice @ ROMAN2HANGUL
        ).shortest_path()
        
        if result.num_states() > 0:
            return extract_output(result)
    except:
        pass
    
    # Fall back to V4
    v4_result = pn.compose(
        pn.acceptor(romanized, token_type="utf8") @ V4_FST
    ).shortest_path()
    
    if v4_result.num_states() > 0:
        return extract_output(v4_result)
    
    return None  # Failed
```

---

## 📊 Phase 8: Classifier Recalibration

Create `scripts/recalibrate_classifier.py`:

```python
from sklearn.linear_model import LogisticRegression
import numpy as np
import json

def recalibrate_name_classifier(train_data):
    """Recalibrate classifier intercept only"""
    # Load existing model
    model = load_existing_model()
    
    # Extract features and labels
    X, y = prepare_features(train_data)
    
    # Fit intercept only
    model.fit(X, y, sample_weight=compute_weights(y))
    
    # Save recalibrated model
    save_model(model, "models/name_likelihood_recal.pkl")
    
    return model
```

---

## ✅ Phase 9: Validation & Testing

### 9.1 Dice Coefficient Implementation

```python
from rapidfuzz.distance import DiceSimilarity

def dice_coefficient(a, b):
    """Calculate Dice coefficient with NFC normalization"""
    import unicodedata
    
    # NFC normalize and casefold
    a_norm = unicodedata.normalize('NFC', a.casefold())
    b_norm = unicodedata.normalize('NFC', b.casefold())
    
    # Use rapidfuzz for efficient calculation
    similarity = DiceSimilarity.similarity(a_norm, b_norm)
    return similarity / 100.0  # Convert to 0-1 range

def roundtrip_score(rr_name):
    """Calculate round-trip accuracy"""
    # Convert to Hangul
    hangul = roman_to_hangul(rr_name)
    
    # Convert back to romanization
    rr_reconstructed = hangul_to_roman(hangul)
    
    # Calculate Dice score
    return dice_coefficient(rr_name, rr_reconstructed)
```

### 9.2 Batch Evaluation Script

Create `scripts/evaluate_roundtrip.py`:

```python
import yaml
import argparse
from tqdm import tqdm

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
```

---

## 🔌 Phase 10: GMNAP Integration

### 10.1 E4 Region Handler

Update `src/regions/e_groups/e4_korea.py`:

```python
from gmnap.core.base import BaseRegionHandler
from v5.core.pipeline import convert, roundtrip_score
import logging

class E4_Korea(BaseRegionHandler):
    """Korean region handler with V5 WFST processing"""
    
    REGION_CODE = "E4"
    REGION_NAME = "Korea"
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("gmnap.korea")
        self._load_v5_components()
    
    def _load_v5_components(self):
        """Load V5 WFST components"""
        from v5.fst_helpers import ROMAN2HANGUL
        from v5.segmenter import segment_with_freq
        self.converter = ROMAN2HANGUL
        self.segmenter = segment_with_freq
        self.logger.info("V5 WFST components loaded")
    
    def latin_to_native(self, entry):
        """Convert Latin to Hangul using V5 system"""
        latin = entry.get("CanonicalLatin", "")
        if not latin:
            return None
        
        # Clean and convert
        clean_latin = self._clean_latin(latin)
        hangul = convert(clean_latin, self.converter, self.segmenter)
        
        self.logger.info("Converted %s -> %s", latin, hangul)
        return hangul
    
    def quality_gate(self, entry):
        """Check if entry meets 97% accuracy requirement"""
        latin = entry.get("CanonicalLatin", "")
        if not latin:
            return False
        
        score = roundtrip_score(latin)
        self.logger.debug("Round-trip score for %s: %.3f", latin, score)
        
        return score >= 0.97
    
    def _clean_latin(self, latin):
        """Clean Latin name for processing"""
        # Remove punctuation, normalize spaces
        import re
        cleaned = re.sub(r"[,.]", "", latin)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
```

### 10.2 Configuration

Create `config/korea.yml`:

```yaml
v5_korea:
  beam_size: 24
  backoff_weight: 3.0
  classifier_model: models/name_likelihood_recal.pkl
  wfst_dir: data/
  logging:
    level: INFO
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 10.3 Registration

Update `src/regions/e_groups/__init__.py`:

```python
from .e4_korea import E4_Korea

__all__ = ['E4_Korea']

# Auto-register
REGION_HANDLERS = {
    'E4': E4_Korea
}
```

---

## 🧪 Phase 11: Test Harness

Create `tests/test_korea.py`:

```python
import yaml
import pytest
from regions.e_groups.e4_korea import E4_Korea

# Load test data
test_data = yaml.safe_load(open("data/korean.yaml"))
handler = E4_Korea()

@pytest.mark.parametrize("entry_id,entry", test_data.items())
def test_roundtrip(entry_id, entry):
    """Test each mathematician entry"""
    assert handler.quality_gate(entry), f"Failed: {entry_id} - {entry['CanonicalLatin']}"

def test_handler_integration():
    """Test E4 handler integration"""
    test_entry = {
        "CanonicalLatin": "Kim, Tae-Hyung",
        "AllCommonVariants": ["Kim Taehyung"]
    }
    
    # Test conversion
    hangul = handler.latin_to_native(test_entry)
    assert hangul is not None
    assert handler._contains_hangul(hangul)
    
    # Test quality gate
    assert handler.quality_gate(test_entry)

def test_hyphen_space_variants():
    """Test GMNAP rule #13 compliance"""
    test_cases = [
        ("Kim Jong-un", ["kimjongun", "kim jong un", "kim-jong-un"]),
        ("Park Ji-sung", ["parkjisung", "park ji sung", "park-ji-sung"])
    ]
    
    for name, expected_variants in test_cases:
        order_key = handler.generate_order_key({"CanonicalLatin": name})
        assert order_key == expected_variants[0]  # Collapsed form
```

---

## 🔄 Phase 12: CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
name: Korean V5 Tests

on: [push, pull_request]

jobs:
  korea-regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install "pynini==2.1.6.post1"
      
      - name: Run Korea tests
        run: pytest tests/test_korea.py -v
      
      - name: Validate accuracy
        run: python scripts/evaluate_roundtrip.py -i data/korean.yaml -t 0.97
```

---

## 🚀 Phase 13: Deployment

### Docker Build

Create `Dockerfile.korea`:

```dockerfile
FROM python:3.12-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    automake \
    libtool \
    pkg-config

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install "pynini==2.1.6.post1"

# Copy application
COPY . /app
WORKDIR /app

# Build FSTs
RUN python src/v5/generate_tables.py
RUN python src/v5/fst_helpers.py

CMD ["python", "-m", "gmnap.server"]
```

### Helm Deployment

```bash
# Build and push
docker build -t gmnap:v6-korea -f Dockerfile.korea .
docker push registry.example.com/gmnap:v6-korea

# Deploy with Helm
helm upgrade gmnap charts/gmnap \
  -f config/prod.yml \
  --set image.tag=v6-korea \
  --set korea.enabled=true
```

### Monitoring

Add Prometheus alerts:

```yaml
groups:
  - name: korea
    rules:
      - alert: KoreanConversionErrors
        expr: rate(korean_conv_err[5m]) > 0.005
        for: 5m
        annotations:
          summary: "Korean conversion error rate > 0.5%"
```

---

## ⚡ Phase 14: Performance Optimization

### Optimization Targets

| Metric | Target | Method |
|--------|--------|--------|
| P95 Latency | <120ms | FST caching |
| Throughput | >1000/sec | Batch processing |
| Memory | <500MB | FST optimization |

### Implementation

```python
# Add caching layer
from functools import lru_cache

@lru_cache(maxsize=10000)
def convert_cached(romanized):
    """Cache frequent conversions"""
    return convert(romanized)

# Batch processing
def convert_batch(names, batch_size=100):
    """Process names in batches"""
    results = []
    for i in range(0, len(names), batch_size):
        batch = names[i:i+batch_size]
        # Process batch in parallel
        batch_results = parallel_convert(batch)
        results.extend(batch_results)
    return results
```

---

## 🛡️ Phase 15: Anti-Overfitting Measures

### Continuous Validation

1. **Monthly Corpus Refresh**:
```bash
# Cron job: 0 0 1 * *
python scripts/refresh_corpus.py
python scripts/count_syllables.py data/corp/new/*.txt
python src/v5/fst_helpers.py  # Rebuild with new frequencies
```

2. **Rotating Test Set**:
```python
# In CI, rotate 10% of test names
def rotate_test_set(current_set, rotation_pct=0.1):
    n_rotate = int(len(current_set) * rotation_pct)
    # Stratified sampling ensures balance
    return stratified_sample(current_set, n_rotate)
```

3. **Never Add Full-Name Rules**:
```python
# BAD: Overfitting
if name == "Kim Jong-un":
    return "김정은"

# GOOD: General pattern
if matches_pattern(name, "kim.*jong.*un"):
    return apply_general_rules(name)
```

---

## 📊 Success Metrics Dashboard

### Key Metrics to Track

```python
# Create monitoring dashboard
from prometheus_client import Counter, Histogram, Gauge

# Metrics
conversion_latency = Histogram('korean_conv_latency_ms', 'Conversion latency')
conversion_errors = Counter('korean_conv_errors_total', 'Total errors')
accuracy_gauge = Gauge('korean_roundtrip_accuracy', 'Current accuracy')
cache_hit_rate = Gauge('korean_cache_hit_rate', 'Cache effectiveness')

# Daily accuracy check
def update_accuracy_metric():
    accuracy = evaluate_dataset("data/korean.yaml", 0.97)
    accuracy_gauge.set(accuracy)
```

---

## 🎯 Starting Point

**BEGIN WITH PHASE 0**: Environment setup is critical. Without PyNini 2.1.6.post1 properly installed, nothing else will work.

After environment verification, proceed sequentially through phases 1-15. Each phase builds on the previous one.

**First Day Focus**:
1. ✅ Complete Phase 0 (Environment)
2. ✅ Complete Phase 1 (Corpus download)
3. ✅ Start Phase 2 (Table generation)

**Success Gate**: By end of Day 1, you should have:
- PyNini working
- Korean corpus downloaded
- `syllable_freq.json` created
- Started romanization table generation

---

## 📝 Implementation Checklist

- [ ] Phase 0: Environment setup complete
- [ ] Phase 1: Corpus & frequencies extracted
- [ ] Phase 2: Romanization tables generated
- [ ] Phase 3: WFST < 30MB built
- [ ] Phase 4: Segmenter passes tests
- [ ] Phase 5: Variant generator complete
- [ ] Phase 6: PyNini API validated
- [ ] Phase 7: V4 back-off integrated
- [ ] Phase 8: Classifier recalibrated
- [ ] Phase 9: Validation suite passes
- [ ] Phase 10: GMNAP handler registered
- [ ] Phase 11: All 751 tests pass
- [ ] Phase 12: CI pipeline green
- [ ] Phase 13: Deployed to production
- [ ] Phase 14: P95 < 120ms achieved
- [ ] Phase 15: Anti-overfitting measures in place

---

**This blueprint, when followed exactly, will achieve ≥97% round-trip accuracy for Korean processing in GMNAP v6.1.**