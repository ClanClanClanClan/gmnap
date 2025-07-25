#!/usr/bin/env python3
"""
Smart Korean converter that handles complex names
"""

import pynini as pn
import os
import re
from typing import Optional, List


class SmartKoreanConverter:
    """Smart converter that handles complex Korean names"""
    
    def __init__(self):
        """Initialize the smart converter"""
        self._load_fsts()
        self._load_comprehensive_mappings()
    
    def _load_fsts(self):
        """Load the FSTs"""
        try:
            if os.path.exists("data/roman2hangul.fst"):
                self.main_fst = pn.Fst.read("data/roman2hangul.fst")
            else:
                self.main_fst = None
        except:
            self.main_fst = None
        
        try:
            if os.path.exists("data/v4_comprehensive.fst"):
                self.v4_fst = pn.Fst.read("data/v4_comprehensive.fst")
            else:
                self.v4_fst = None
        except:
            self.v4_fst = None
    
    def _load_comprehensive_mappings(self):
        """Load the comprehensive mappings as fallback"""
        import json
        try:
            with open("data/v4_comprehensive_mappings.json", "r", encoding="utf-8") as f:
                self.mappings = json.load(f)
        except:
            self.mappings = {}
    
    def _extract_output(self, fst):
        """Extract output string from FST result"""
        if fst.num_states() == 0:
            return None
        
        shortest = pn.shortestpath(fst)
        paths_iter = shortest.paths(input_token_type="utf8", output_token_type="utf8")
        
        if not paths_iter.done():
            return paths_iter.ostring()
        return None
    
    def _convert_single_component(self, component: str) -> Optional[str]:
        """Convert a single component (surname or given name part)"""
        component_lower = component.lower()
        
        # Try V4 FST first (comprehensive mappings)
        if self.v4_fst is not None:
            try:
                input_fst = pn.accep(component_lower, token_type="utf8")
                result = pn.compose(input_fst, self.v4_fst)
                
                if result.num_states() > 0:
                    output = self._extract_output(result)
                    if output:
                        return output
            except:
                pass
        
        # Try direct mapping lookup
        if component_lower in self.mappings:
            return self.mappings[component_lower]
        
        # Try main FST if available
        if self.main_fst is not None:
            try:
                input_fst = pn.accep(component_lower, token_type="utf8")
                result = pn.compose(input_fst, self.main_fst)
                
                if result.num_states() > 0:
                    output = self._extract_output(result)
                    if output:
                        return output
            except:
                pass
        
        return None
    
    def _split_complex_name(self, name: str) -> List[str]:
        """Split a complex name into components"""
        # Handle space-separated names
        if ' ' in name:
            parts = []
            for segment in name.split():
                # Further split each segment if it's CamelCase
                parts.extend(self._split_camel_case(segment))
            return parts
        
        # Handle hyphenated names  
        if '-' in name:
            parts = []
            for segment in name.split('-'):
                # Further split each segment if it's CamelCase or has spaces
                if ' ' in segment:
                    for subseg in segment.split():
                        parts.extend(self._split_camel_case(subseg))
                else:
                    parts.extend(self._split_camel_case(segment))
            return parts
        
        # Handle CamelCase names
        return self._split_camel_case(name)
    
    def _split_camel_case(self, text: str) -> List[str]:
        """Split CamelCase text into components"""
        if not text:
            return []
        
        # Use regex to split on uppercase letters
        parts = re.findall(r'[A-Z][a-z]*|[a-z]+', text)
        return parts if parts else [text]
    
    def convert(self, romanized: str) -> Optional[str]:
        """
        Convert romanized Korean name to Hangul.
        
        Args:
            romanized: Romanized Korean name (e.g., "Kim Jong-Un", "AhnDaeHoon")
            
        Returns:
            Hangul conversion or None if failed
        """
        if not romanized:
            return None
        
        # First try as a single component
        single_result = self._convert_single_component(romanized)
        if single_result:
            return single_result
        
        # If that fails, try splitting and converting parts
        components = self._split_complex_name(romanized)
        
        if len(components) <= 1:
            return None  # Already tried single component
        
        converted_parts = []
        for component in components:
            converted = self._convert_single_component(component)
            if converted:
                converted_parts.append(converted)
            else:
                # If any part fails, the whole conversion fails
                return None
        
        # Join all converted parts
        return ''.join(converted_parts)


# Global instance for backward compatibility
_smart_converter = None

def get_smart_converter():
    """Get the global smart converter instance"""
    global _smart_converter
    if _smart_converter is None:
        _smart_converter = SmartKoreanConverter()
    return _smart_converter

def convert_with_smart_backoff(romanized: str) -> Optional[str]:
    """
    Convert romanized Korean to Hangul using smart segmentation.
    
    Args:
        romanized: Romanized Korean text
        
    Returns:
        Hangul conversion or None if failed
    """
    converter = get_smart_converter()
    return converter.convert(romanized)