"""
GMNAP v6.1 - Global Mathematician Name Authority Project

World-scale, script-aware knowledge base covering 43 region groups
across all continents following the v6.1 specifications.
"""

__version__ = "6.1.0"
__spec_version__ = "6.1"

from .core.pipeline import GMNAPPipeline
from .core.globalid import generate_global_id
from .core.database import GMNAPDatabase

__all__ = [
    "GMNAPPipeline", 
    "generate_global_id", 
    "GMNAPDatabase"
]