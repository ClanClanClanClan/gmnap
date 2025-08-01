"""
E-Groups: East Asian Regional Processors per GMNAP v6.1

E1: Sinophone Mainland (CN) - Han-Simplified, Pinyin vs Wade-Giles
E2: Sinophone Traditional (TW, HK, MO) - Han-Traditional, Cantonese romanisation  
E3: Japan (JP) - Kanji/Kana, Official order flip 2020
E4: Korea (KR, KP) - Hangul/Hanja, Hyphen/space variation ≥97% round-trip
E5: Vietnam (VN) - Latin with diacritics, Numeric tone variants
E6: Mainland SEA (TH, KH, LA) - Thai RTGS, Khmer UNGEGN, Lao MOICT 2019
E7: Maritime SEA (ID, MY, SG, BN, PH, TL) - Malay bin/binti, Indonesian mononyms

All E-groups implement CJK Round-Trip rule (Rule 11):
romanise+back-convert with ≥97% match using Dice coefficient after NFC casefold.
"""

from .e4_korea import E4KoreaProcessor

__all__ = ["E4KoreaProcessor"]