#!/usr/bin/env python3
"""
Blueprint-compliant Korean converter implementing Phase 7 integration
"""

import pynini as pn
import json
from .phonotactics import SYLL, WORD
from .segmenter import segment_with_freq
from .variant_generator import generate_all_variants
import os

class BlueprintKoreanConverter:
    """Korean converter following V5 blueprint exactly"""
    
    def __init__(self):
        """Initialize according to blueprint specifications"""
        self._load_components()
    
    def _load_components(self):
        """Load all FST components and frequency data"""
        # Load main WFST
        if os.path.exists("data/roman2hangul.fst"):
            self.main_fst = pn.Fst.read("data/roman2hangul.fst")
        else:
            self.main_fst = None
            
        # Load V4 back-off FST
        if os.path.exists("data/v4_comprehensive.fst"):
            self.v4_fst = pn.Fst.read("data/v4_comprehensive.fst")
        elif os.path.exists("data/v4_backoff.fst"):
            self.v4_fst = pn.Fst.read("data/v4_backoff.fst")
        else:
            self.v4_fst = None
            
        # Load syllable frequencies
        with open("data/syllable_freq.json", "r", encoding="utf8") as f:
            self.syll_freq = json.load(f)
    
    def extract_output(self, fst):
        """Extract output string from FST result"""
        if fst.num_states() == 0:
            return None
        
        shortest = pn.shortestpath(fst)
        paths_iter = shortest.paths(input_token_type="utf8", output_token_type="utf8")
        
        if not paths_iter.done():
            return paths_iter.ostring()
        return None
    
    def create_segment_lattice(self, romanized):
        """Create phonotactic segmentation lattice using beam search"""
        # Use beam search segmentation with frequency weighting
        segmentations = segment_with_freq(romanized, self.syll_freq, beam=24)
        
        if not segmentations:
            # Fallback: simple acceptor
            return pn.accep(romanized.lower(), token_type="utf8")
        
        # Take the best segmentation
        _, best_segments = min(segmentations, key=lambda x: x[0])
        
        # Create FST from segmentation
        if len(best_segments) == 1:
            return pn.accep(best_segments[0], token_type="utf8")
        else:
            # Concatenate segments
            fst = pn.accep(best_segments[0], token_type="utf8")
            for segment in best_segments[1:]:
                fst = fst + pn.accep(segment, token_type="utf8")
            return fst.optimize()
    
    def _split_name_components(self, name):
        """Split name into individual components for separate processing"""
        # Handle different name formats
        if ' ' in name:
            return name.split()
        elif '-' in name:
            return name.split('-')
        else:
            # Try to split CamelCase
            import re
            parts = re.findall(r'[A-Z][a-z]*|[a-z]+', name)
            return parts if len(parts) > 1 else [name]
    
    def _convert_single_component(self, component):
        """Convert a single name component"""
        component_lower = component.lower()
        
        # Try V4 FST first (comprehensive mappings)
        if self.v4_fst is not None:
            try:
                input_fst = pn.accep(component_lower, token_type="utf8")
                result = pn.compose(input_fst, self.v4_fst)
                
                if result.num_states() > 0:
                    output = self.extract_output(result)
                    if output:
                        return output
            except:
                pass
        
        # Try main WFST with segmentation
        if self.main_fst is not None:
            try:
                segment_lattice = self.create_segment_lattice(component_lower)
                result = pn.compose(segment_lattice, self.main_fst)
                
                if result.num_states() > 0:
                    output = self.extract_output(result)
                    if output:
                        return output
            except:
                pass
        
        return None

    def convert_with_backoff(self, romanized):
        """
        Enhanced convert with backoff - handles multi-word names properly
        """
        # Generate variants first
        variants = generate_all_variants(romanized)
        
        for variant in variants:
            # Try as single component first
            result = self._convert_single_component(variant)
            if result:
                return result
            
            # If that fails, try splitting into components
            components = self._split_name_components(variant)
            if len(components) > 1:
                converted_parts = []
                all_success = True
                
                for component in components:
                    component_result = self._convert_single_component(component)
                    if component_result:
                        converted_parts.append(component_result)
                    else:
                        all_success = False
                        break
                
                if all_success and converted_parts:
                    return ''.join(converted_parts)
        
        return None  # Failed all variants
    
    def convert(self, romanized):
        """Main conversion entry point"""
        return self.convert_with_backoff(romanized)


# Global instance
_converter = None

def get_blueprint_converter():
    """Get the global blueprint converter instance"""
    global _converter
    if _converter is None:
        _converter = BlueprintKoreanConverter()
    return _converter

def convert_blueprint(romanized):
    """Convert using blueprint-compliant method"""
    converter = get_blueprint_converter()
    return converter.convert(romanized)