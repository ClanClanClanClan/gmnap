"""Region processors for A-groups (Western/European heritage)."""

# Import all working A-group regions
from .a1_anglo_sphere import A1_AngloSphere
from .a2_western_europe import A2_WesternEurope
from .a3_nordic_baltic import A3NordicBalticProcessor as A3_NordicBaltic
from .a4_oceania import A4OceaniaProcessor as A4_Oceania
from .a5_caribbean import A5CaribbeanProcessor as A5_Caribbean

__all__ = ["A5_Caribbean", "A2_WesternEurope", "A1_AngloSphere", "A4_Oceania", "A3_NordicBaltic"]
