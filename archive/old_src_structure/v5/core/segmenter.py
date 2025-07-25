#!/usr/bin/env python3
"""
Korean phonotactic segmentation for compound names.
Implements beam search to find optimal syllable boundaries.
"""

import re
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass
import heapq
import json

@dataclass
class SegmentationPath:
    """Represents a segmentation path with cost"""
    cost: float
    segments: List[str]
    position: int
    
    def __lt__(self, other):
        return self.cost < other.cost


class KoreanPhonemePatterns:
    """Korean phonotactic patterns for valid syllables"""
    
    # Revised Romanization patterns
    RR_INITIALS = {
        'g', 'n', 'd', 'r', 'm', 'b', 's', 'j', 'ch', 'k', 't', 'p', 'h',
        'kk', 'tt', 'pp', 'ss', 'jj',
        ''  # ㅇ (no sound initially)
    }
    
    RR_VOWELS = {
        'a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 
        'wae', 'oe', 'yo', 'u', 'wo', 'we', 'wi', 'yu', 'eu', 'ui', 'i'
    }
    
    RR_FINALS = {
        '', 'k', 'n', 't', 'l', 'm', 'p', 'ng',
        'ks', 'nj', 'nh', 'lk', 'lm', 'lp', 'ls', 'lt', 'lh', 'ps'
    }
    
    # Common name patterns
    COMMON_SURNAME_SYLLABLES = {
        'kim', 'lee', 'park', 'choi', 'jung', 'kang', 'jo', 'yoon', 'jang',
        'lim', 'han', 'oh', 'seo', 'shin', 'kwon', 'hwang', 'ahn', 'song',
        'jeon', 'hong', 'yu', 'ko', 'moon', 'yang', 'bae', 'baek', 'heo',
        'nam', 'sim', 'noh', 'ha', 'joo', 'koo', 'min', 'jin', 'cha'
    }
    
    # Alternative romanizations for common surnames
    SURNAME_VARIANTS = {
        'lee': ['lee', 'yi', 'rhee', 'li'],
        'park': ['park', 'pak', 'bak'],
        'choi': ['choi', 'choe', 'chwe'],
        'jung': ['jung', 'jeong', 'chung'],
        'kim': ['kim', 'gim'],
        'kang': ['kang', 'gang'],
        'yoon': ['yoon', 'yun', 'youn'],
        'seo': ['seo', 'suh', 'sur'],
        'oh': ['oh', 'o'],
        'jeon': ['jeon', 'jun', 'chun', 'cheon'],
        'yu': ['yu', 'yoo', 'ryu', 'ryoo'],
        'ko': ['ko', 'go', 'koh', 'goh'],
        'bae': ['bae', 'bai', 'pae', 'pai'],
        'ahn': ['ahn', 'an'],
    }


class KoreanSegmenter:
    """Segment romanized Korean names into syllables"""
    
    def __init__(self, beam_size: int = 24):
        self.beam_size = beam_size
        self.patterns = KoreanPhonemePatterns()
        self._load_syllable_costs()
        self._build_valid_syllables()
    
    def _load_syllable_costs(self):
        """Load syllable frequency costs"""
        try:
            with open("data/syllable_freq.json", "r", encoding="utf-8") as f:
                freq = json.load(f)
                total = sum(freq.values())
                # Convert to costs (negative log probability)
                self.syllable_costs = {}
                for syl, count in freq.items():
                    self.syllable_costs[syl] = -math.log((count + 1) / (total + len(freq)))
        except:
            self.syllable_costs = {}
    
    def _build_valid_syllables(self):
        """Build set of valid Korean syllable patterns in romanization"""
        self.valid_patterns = set()
        
        # Add all combinations of initial + vowel + final
        for initial in self.patterns.RR_INITIALS:
            for vowel in self.patterns.RR_VOWELS:
                for final in self.patterns.RR_FINALS:
                    syllable = initial + vowel + final
                    self.valid_patterns.add(syllable)
        
        # Add common surname patterns and variants
        for surname_list in self.patterns.SURNAME_VARIANTS.values():
            self.valid_patterns.update(surname_list)
        
        self.valid_patterns.update(self.patterns.COMMON_SURNAME_SYLLABLES)
    
    def is_valid_syllable(self, text: str) -> bool:
        """Check if text could be a valid Korean syllable"""
        text_lower = text.lower()
        
        # Check if it's a known pattern
        if text_lower in self.valid_patterns:
            return True
        
        # Check if it matches CV(C) pattern
        # This is a simplified check - full implementation would be more sophisticated
        if len(text) < 1 or len(text) > 7:  # Korean syllables in romanization are typically 1-7 chars
            return False
        
        # Check against patterns using regex
        # Initial consonant (optional for ㅇ), vowel (required), final consonant (optional)
        pattern = r'^([gndlmbsjchktpk]?[gndlmbsjchktpk]?)([aeiouwyü]+)([ktnlmpng]?[sjhg]?)$'
        return bool(re.match(pattern, text_lower))
    
    def get_syllable_cost(self, syllable: str) -> float:
        """Get cost for a syllable (lower is better)"""
        # Length-based cost
        base_cost = len(syllable) * 0.5
        
        # Prefer known surnames
        if syllable.lower() in self.patterns.COMMON_SURNAME_SYLLABLES:
            base_cost -= 2.0
        
        # Add frequency-based cost if available
        # (Would need reverse lookup from romanization to Hangul)
        
        return base_cost
    
    def segment(self, text: str) -> List[List[str]]:
        """
        Segment romanized Korean text into syllables using beam search.
        
        Args:
            text: Romanized Korean text (e.g., "kimtaehyung")
            
        Returns:
            List of segmentation options, best first
        """
        text = text.lower().strip()
        if not text:
            return [[]]
        
        # Initialize beam search
        n = len(text)
        chart = [[] for _ in range(n + 1)]
        chart[0] = [SegmentationPath(0.0, [], 0)]
        
        # Dynamic programming with beam search
        for i in range(n):
            if not chart[i]:
                continue
            
            # Try all possible syllable lengths
            for j in range(i + 1, min(i + 8, n + 1)):  # Max syllable length 7
                syllable = text[i:j]
                
                if self.is_valid_syllable(syllable):
                    syllable_cost = self.get_syllable_cost(syllable)
                    
                    # Add this syllable to all paths ending at position i
                    for path in chart[i]:
                        new_cost = path.cost + syllable_cost
                        new_segments = path.segments + [syllable]
                        new_path = SegmentationPath(new_cost, new_segments, j)
                        
                        heapq.heappush(chart[j], new_path)
            
            # Keep only top beam_size paths at each position
            if len(chart[i + 1]) > self.beam_size:
                chart[i + 1] = heapq.nsmallest(self.beam_size, chart[i + 1])
        
        # Extract final segmentations
        final_paths = chart[n]
        if not final_paths:
            # Fallback: character-by-character
            return [[char for char in text]]
        
        # Return all found segmentations, best first
        results = []
        for path in sorted(final_paths, key=lambda p: p.cost):
            results.append(path.segments)
        
        return results
    
    def segment_name(self, name: str) -> Tuple[List[str], float]:
        """
        Segment a Korean name and return best segmentation with confidence.
        
        Args:
            name: Romanized Korean name
            
        Returns:
            Tuple of (syllables, confidence)
        """
        # Handle already segmented names (with spaces or hyphens)
        if ' ' in name or '-' in name:
            parts = re.split(r'[\s\-]+', name)
            return parts, 1.0
        
        # Get segmentation options
        segmentations = self.segment(name)
        
        if not segmentations:
            return [name], 0.0
        
        best = segmentations[0]
        
        # Calculate confidence based on segmentation quality
        confidence = 1.0
        
        # Reduce confidence for unusual patterns
        for syllable in best:
            if len(syllable) > 5:  # Very long syllable
                confidence *= 0.8
            if syllable not in self.valid_patterns:
                confidence *= 0.9
        
        # Boost confidence for known surname patterns
        if best and best[0].lower() in self.patterns.COMMON_SURNAME_SYLLABLES:
            confidence = min(confidence * 1.2, 1.0)
        
        return best, confidence


# Convenience functions
def create_segmenter(beam_size: int = 24) -> KoreanSegmenter:
    """Create a Korean segmenter with specified beam size"""
    return KoreanSegmenter(beam_size)


def segment_korean_name(name: str, beam_size: int = 24) -> List[str]:
    """Segment a romanized Korean name into syllables"""
    segmenter = create_segmenter(beam_size)
    syllables, _ = segmenter.segment_name(name)
    return syllables


# Example usage and testing
if __name__ == "__main__":
    import math
    
    segmenter = KoreanSegmenter()
    
    # Test cases
    test_names = [
        "kimtaehyung",
        "parkjimin", 
        "jeonggukjeon",
        "songkangho",
        "kimsoohyun",
        "leeminho",
        "choiyujin",
        "kanghaneul",
        "kim",
        "lee",
        "park"
    ]
    
    print("Korean Name Segmentation Tests:")
    print("=" * 60)
    
    for name in test_names:
        segmentations = segmenter.segment(name)
        best, confidence = segmenter.segment_name(name)
        
        print(f"\nInput: '{name}'")
        print(f"Best segmentation: {' | '.join(best)} (confidence: {confidence:.2f})")
        
        if len(segmentations) > 1:
            print("Alternative segmentations:")
            for i, seg in enumerate(segmentations[1:4], 1):  # Show top 3 alternatives
                print(f"  {i}. {' | '.join(seg)}")
    
    print("\n" + "=" * 60)
    print("Testing surname detection:")
    
    for surname in ["kim", "lee", "park", "choi", "jung"]:
        is_valid = segmenter.is_valid_syllable(surname)
        cost = segmenter.get_syllable_cost(surname)
        print(f"  {surname}: valid={is_valid}, cost={cost:.2f}")

def segment_with_freq(romanized_name, beam=24):
    """Segment Korean name using frequency-based costs"""
    segmenter = KoreanSegmenter(beam_size=beam)
    results = segmenter.segment(romanized_name)
    if results:
        return results[0]  # Return best segmentation
    return [romanized_name]  # Fallback