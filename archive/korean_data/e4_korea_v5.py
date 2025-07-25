from gmnap.core.base import BaseRegionHandler
from v5.core.pipeline import convert, roundtrip_score
from v5.converter_cached import optimized_convert
from v5.performance_metrics import monitor_performance, metrics
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
    
    @monitor_performance
    def latin_to_native(self, entry):
        """Convert Latin to Hangul using V5 system with performance monitoring"""
        latin = entry.get("CanonicalLatin", "")
        if not latin:
            return None
        
        # Clean and convert using optimized cached version
        clean_latin = self._clean_latin(latin)
        hangul = optimized_convert(clean_latin)
        
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