"""
GMNAP Tier-2 Authority Sources
Generated from universal template engine for rapid deployment.

Tier-2 sources provide supplementary authority data with moderate confidence.
"""

from .cern_cds import CERN_CDSFetcher
from .cnki import CNKIFetcher
from .ethos import EThOSFetcher
from .google_scholar import GoogleScholarFetcher
from .hal import HALFetcher
from .j_stage import JStageFetcher
from .jstor import JSTORFetcher
from .narcis import NARCISFetcher
from .proquest import ProQuestFetcher
from .scielo import SciELOFetcher
from .tel import TELFetcher
from .wikidata import WikidataFetcher

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
