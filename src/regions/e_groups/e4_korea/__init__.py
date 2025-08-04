"""
E4 Korea Regional Processor - GMNAP v6.1

Handles Korean mathematician names per v6.1 specifications:
- ISO territories: KR, KP  
- Primary scripts: Hangul, Hanja
- Distinct features: Hyphen/space variation
- Linguistic rule 11: CJK Round-Trip ≥97% accuracy (Dice coefficient)
- Linguistic rule 13: Korean Hyphen/Space variant set, order_key collapsed

This module provides both v5 (legacy) and v6 (current) implementations
with automatic fallback for reliability.
"""

from .processor import E4KoreanProcessor
from .converter_v6 import KoreanConverterV6
from .converter_v7 import KoreanConverterV7

__all__ = ["E4KoreanProcessor", "KoreanConverterV6", "KoreanConverterV7"]