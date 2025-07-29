# Request for Help: Implementing Name-Level Beam Search Scorer

## Summary

I need help implementing a beam search solution to push Korean name conversion accuracy from 84.5% to 90-92% on the diverse dataset while maintaining 95-96% on the mathematician dataset. The current position-aware system has hit a hard ceiling due to fundamental limitations.

## Current Situation

### Accuracy Status
- **Mathematician Dataset**: 95.63% (701/733)
- **Diverse Dataset**: 84.50% (169/200)

### Key Problems
1. **Ambiguous syllables**: jung→정 vs 중, hun→훈 vs 헌 depend on context, not just position
2. **Compound tokens**: "Jin-Jung" splits to ["Jin", "Jung"], losing compound context
3. **English names**: Filtering breaks position indices
4. **Rare romanizations**: Each new mapping risks collisions

## Proposed Solution: Name-Level Beam Search

### Core Idea
Instead of deterministic per-token rules, generate multiple candidates and score complete name hypotheses.

### Algorithm
1. Generate 3-4 Hangul candidates per token (variant lookup + FST top-N)
2. Beam search with K=20 over token sequence
3. Score with three features:
   - FST arc weights (weight: 1.0)
   - Bigram frequency from Korean corpus (weight: 0.8)
   - Surname plausibility check (weight: -2.0 if invalid)

## What I Need Help With

### 1. Korean Bigram Language Model
I need a bigram frequency model from Korean text. Could you help me:
- Find or create bigram counts from a Korean corpus (Sejong corpus ideal)
- Format: `{("가", "나"): count, ...}`
- Save as `models/bigram_hangul.json`

If you don't have access to Korean corpus, we could:
- Use a smaller publicly available dataset
- Generate synthetic bigrams from the test datasets
- Use character transition probabilities from Korean Wikipedia

### 2. Implementation of `src/name_beam.py`

```python
import json
import heapq
from typing import List, Tuple, Dict
import pathlib

class NameBeamScorer:
    def __init__(self):
        # Load bigram model
        self.bigrams = json.load(open(pathlib.Path(__file__).parent.parent / "models" / "bigram_hangul.json"))
        # Load surname set
        self.surnames = set()
        with open(pathlib.Path(__file__).parent.parent / "resources" / "surnames.txt", encoding="utf8") as f:
            self.surnames = {line.strip() for line in f if line.strip()}
        
    def beam(self, tokens: List[str]) -> str:
        """
        Beam search over token sequence to find best Hangul string.
        
        Args:
            tokens: List of romanized tokens
        Returns:
            Best Hangul string
        """
        # TODO: Implementation needed
        pass
    
    def get_candidates(self, token: str) -> List[Tuple[str, float]]:
        """Get Hangul candidates for a token with scores."""
        # TODO: Call existing converter functions
        pass
    
    def score_name(self, hangul: str, fst_score: float) -> float:
        """Score a complete Hangul name."""
        # TODO: Implement 3-feature scoring
        pass
```

### 3. Tokenization Modification

Current tokenizer splits on hyphens. Need to modify to:
- Keep "Jung-Kook" as one token
- But still handle parts for variant lookup

### 4. Surname List

Need a comprehensive Korean surname list. The file should contain one surname per line:
```
김
이
박
최
정
...
```

### 5. Integration Questions

1. How to call existing FST from beam search to get top-N candidates?
2. How to preserve FST arc weights for scoring?
3. Should we cache candidate generation for common tokens?

## Implementation Steps

1. **Build bigram LM** (need Korean corpus)
2. **Create name_beam.py** with beam search logic
3. **Modify converter.py** to use beam for multi-token names
4. **Adjust tokenization** to handle compounds better
5. **Add regression gate** for simple names

## Specific Code Help Needed

### Getting FST N-Best Paths
```python
# Current code gets single best:
def _rr2han(rr): 
    return first_output(pn.accep(rr)@ROM2) or rom2han().get(rr)

# Need something like:
def get_nbest_candidates(rr, n=3):
    # How to get top-N paths with scores from PyNini FST?
    pass
```

### Bigram Scoring
```python
def bigram_score(hangul: str) -> float:
    """Calculate bigram log probability."""
    score = 0.0
    for i in range(len(hangul) - 1):
        bigram = (hangul[i], hangul[i+1])
        count = self.bigrams.get(bigram, 1)  # Smoothing
        score += log(count / total_bigrams)
    return score
```

## Expected Outcome

- Diverse dataset: 84.5% → 90-92%
- Mathematician dataset: maintained at 95-96%
- More robust handling of ambiguous cases

## Questions

1. Do you have access to Korean text corpus for bigram model?
2. Can you help implement the beam search algorithm?
3. Any concerns about the scoring weights or approach?
4. Should we handle 3-character names differently than 2-character names?

## Files to Create/Modify

1. `models/bigram_hangul.json` - Bigram frequency model
2. `src/name_beam.py` - Beam search implementation  
3. `src/converter.py` - Integration changes
4. `src/preprocess_fixed.py` - Tokenization tweaks
5. `resources/surnames.txt` - Korean surname list

Please help me implement this solution to break through the current accuracy ceiling!