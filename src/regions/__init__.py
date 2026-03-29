"""
GMNAP Regional Processors - 43 Region Groups per v6.1 specs

Region Groups:
A1-A5: Anglo-Sphere, Western Europe, Nordic-Baltic, Oceania, Caribbean
B1-B3: East-Slavic, South-Slavic & Central Europe, Greek World
C1-C9: Turkic, Persian-Tajik, Arabic regions, Hebrew, Armenian, Georgian, Caucasus
D1-D5: South Asia regions (Hindi Belt, Dravidian, Bengali, Pakistan, Sinhala)
E1-E7: East Asia (Sinophone, Japan, Korea, Vietnam, SEA)
F1-F4: Sub-Saharan Africa regions
G1: Latin America & Iberian Caribbean
H1: Historical (≤1850)
R0: Residual Latin-ASCII
Z0: Quarantine

Each region implements clean→augment→validate→order_key operations
with script-specific linguistic rules.
"""

from .base import RegionRuleError, RegionSpec

__all__ = ["RegionSpec", "RegionRuleError"]
