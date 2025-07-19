"""Regional processing modules for different linguistic groups."""

# Import all implemented regions
from .a_groups import A1_AngloSphere
from .b_groups import B1_EastSlavic
from .c_groups import C2_PersianTajik, C3_ArabicLevantNile
from .d_groups import D1_HindiBelt
from .e_groups import E1_SinophoneMainland, E3_Japan
from .g_groups import G1_LatinAmerica

__all__ = [
    "A1_AngloSphere",
    "B1_EastSlavic", 
    "C2_PersianTajik",
    "C3_ArabicLevantNile",
    "D1_HindiBelt",
    "E1_SinophoneMainland",
    "E3_Japan",
    "G1_LatinAmerica"
]