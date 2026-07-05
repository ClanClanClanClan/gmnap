"""
GMNAP Tier-2 Authority Sources
Generated from universal template engine for rapid deployment.

Tier-2 sources provide supplementary authority data with moderate confidence.

R49 §2c: this package's __init__ was written aspirationally by the template
generator — it imported THREE modules that never existed (google_scholar,
hal, wikidata; HAL lives in tier1, Google Scholar is a ToS-deferred stub in
manager_tier01), so ``import src.authorities.tier2`` raised
ModuleNotFoundError and the roster-wide fetcher guard silently skipped the
whole package. Now imports exactly what exists.
"""

from .cern_cds import CERN_CDSFetcher
from .cnki import CNKIFetcher
from .dimensions import DimensionsFetcher
from .ethos import EThOSFetcher
from .j_stage import JStageFetcher
from .jstor import JSTORFetcher
from .mathscinet import MathSciNetHTMLFetcher
from .narcis import NARCISFetcher
from .proquest import ProQuestFetcher
from .scielo import SciELOFetcher
from .tel import TELFetcher

__all__ = [
    "CERN_CDSFetcher",
    "CNKIFetcher",
    "DimensionsFetcher",
    "EThOSFetcher",
    "JStageFetcher",
    "JSTORFetcher",
    "MathSciNetHTMLFetcher",
    "NARCISFetcher",
    "ProQuestFetcher",
    "SciELOFetcher",
    "TELFetcher",
]
