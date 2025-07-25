"""
GMNAP Authority Sources - External API integrations per v6.1 specs

Tier-0 Sources (Free, high-quota):
- OpenAlex (864k/day) - Works, concepts, ORCIDs  
- Crossref (4.3M/day) - DOI metadata
- MathSciNet HTML (20k/day) - Subscription HTML parse
- zbMATH Open (200/day) - JSON
- ORCID (500/day) - REST

Tier-1 Sources (Month 6+):
- Scopus, Dimensions, WoS ResearcherID
- DBLP, MGP, ISNI, GND, BNF IdRef
- Regional: Lattes, ADS, HAL, SciELO, RSL, CNKI, CiNii

Tier-2 Sources (--force-extreme only):
- Google Scholar (with YES_I_ACCEPT_GS_TOS=yes)

All sources implement aiohttp fetch, licence quotas, token-bucket limiting.
"""

from .base import AuthoritySource

__all__ = ["AuthoritySource"]