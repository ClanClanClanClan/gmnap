"""
GMNAP Tier-2 Authority Sources
Generated from universal template engine for rapid deployment.

Tier-2 sources provide supplementary authority data with moderate confidence.
"""

from .wikidata import WikidataFetcher
from .hal import HALFetcher
from .narcis import NARCISFetcher
from .scielo import SciELOFetcher
from .ethos import EThOSFetcher
from .cern_cds import CERN_CDSFetcher
from .google_scholar import GoogleScholarFetcher
from .cnki import CNKIFetcher
from .j_stage import JStageFetcher
from .jstor import JSTORFetcher
from .proquest import ProQuestFetcher
from .tel import TELFetcher

__all__ = [
    "WikidataFetcher",
    "HALFetcher",
    "NARCISFetcher",
    "SciELOFetcher",
    "EThOSFetcher",
    "CERN_CDSFetcher",
    "GoogleScholarFetcher",
    "CNKIFetcher",
    "JStageFetcher",
    "JSTORFetcher",
    "ProQuestFetcher",
    "TELFetcher",
]
