#!/usr/bin/env python3
"""
Korean WFST-based segmenter using beam search.
Finds optimal syllable boundaries for compound Korean names.
"""

import pynini as pn
import heapq
import json
import math
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class WFSTSegmenter:
    """Segment romanized Korean names using WFST and beam search"""
    
    def __init__(self, beam_size=24):
        self.beam_size = beam_size
        self._load_resources()
    
    def _load_resources(self):
        """Load syllable FSA and frequency data"""
        # Load syllable FSA
        try:
            self.syllable_fsa = pn.Fst.read("data/korean_syllable.fsa")
            logger.info("Loaded syllable FSA")
        except:
            # Build if not found
            from .phonotactics import build_syllable_fsa
            self.syllable_fsa = build_syllable_fsa()
        
        # Load surname FSA
        try:
            self.surname_fsa = pn.Fst.read("data/korean_surname.fsa")
        except:
            from .phonotactics import build_surname_fsa
            self.surname_fsa = build_surname_fsa()
        
        # Load frequency data
        try:
            with open("data/syllable_freq.json", "r", encoding="utf8") as f:
                self.freq_data = json.load(f)
            self.total_freq = sum(self.freq_data.values())
            logger.info(f"Loaded frequencies for {len(self.freq_data)} syllables")
        except:
            self.freq_data = {}
            self.total_freq = 1
    
    def segment(self, text):
        """Segment text into Korean syllables using beam search"""
        text = text.lower().strip()
        if not text:
            return []
        
        # Check if it's a known surname
        if self._is_surname(text):
            return [text]
        
        # Use beam search for segmentation
        return self._beam_search(text)
    
    def _is_surname(self, text):
        """Check if text is a known surname"""
        try:
            input_fst = pn.accep(text)
            result = pn.compose(input_fst, self.surname_fsa)
            return result.num_states() > 0
        except:
            return False
    
    def _is_valid_syllable(self, text):
        """Check if text is a valid Korean syllable"""
        try:
            input_fst = pn.accep(text)
            result = pn.compose(input_fst, self.syllable_fsa)
            return result.num_states() > 0
        except:
            return False
    
    def _syllable_cost(self, syllable):
        """Calculate cost for a syllable (lower is better)"""
        # Length penalty (prefer 2-3 char syllables)
        length = len(syllable)
        if length == 2 or length == 3:
            length_cost = 0
        elif length == 1:
            length_cost = 0.5
        else:
            length_cost = length * 0.3
        
        # Frequency cost (if we have Korean mapping)
        # For now, use uniform cost
        freq_cost = 1.0
        
        return length_cost + freq_cost
    
    def _beam_search(self, text):
        """Beam search for optimal segmentation"""
        n = len(text)
        
        # Chart: position -> list of (cost, path) tuples
        chart = [[] for _ in range(n + 1)]
        chart[0] = [(0.0, [])]
        
        # Fill chart using dynamic programming with beam
        for i in range(n):
            if not chart[i]:  # No valid paths to this position
                continue
            
            # Try all possible syllable lengths (1-7 chars typical)
            candidates = []
            for j in range(i + 1, min(i + 8, n + 1)):
                syllable = text[i:j]
                
                # Check if valid syllable
                if self._is_valid_syllable(syllable):
                    syl_cost = self._syllable_cost(syllable)
                    
                    # Add to candidates from all paths at position i
                    for prev_cost, prev_path in chart[i]:
                        new_cost = prev_cost + syl_cost
                        new_path = prev_path + [syllable]
                        candidates.append((new_cost, new_path, j))
            
            # Distribute candidates to their target positions
            for cost, path, pos in candidates:
                heapq.heappush(chart[pos], (cost, path))
            
            # Prune to beam size at each position
            for j in range(i + 1, n + 1):
                if len(chart[j]) > self.beam_size:
                    chart[j] = heapq.nsmallest(self.beam_size, chart[j])
        
        # Return best complete path
        if chart[n]:
            best_cost, best_path = min(chart[n])
            return best_path
        
        # Fallback: character-by-character
        return list(text)
    
    def segment_name(self, name):
        """Segment a full name (may have spaces/hyphens)"""
        # Split on spaces and hyphens
        parts = name.replace('-', ' ').split()
        
        segmented_parts = []
        for part in parts:
            segments = self.segment(part)
            segmented_parts.extend(segments)
        
        return segmented_parts

def test_segmenter():
    """Test the segmenter with examples"""
    segmenter = WFSTSegmenter()
    
    test_cases = [
        "kimtaehyung",
        "parkjimin", 
        "jeonjungkook",
        "kimnamjoon",
        "junghoseok",
        "minyoongi",
        "kimseokjin",
        "leesangwook",
        "choiyongkyu",
        "kanghyunsuk",
        "hongjinseok",
        "baesangun",
        "baekhyeongchan"
    ]
    
    print("\nSegmentation results:")
    for name in test_cases:
        segments = segmenter.segment(name)
        print(f"{name:15} → {' '.join(segments)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_segmenter()