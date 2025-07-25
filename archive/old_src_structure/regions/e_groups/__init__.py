"""
E Groups - East Asian region implementations.
"""

from .e4_korea import E4_Korea

__all__ = ['E4_Korea']

# Auto-register
REGION_HANDLERS = {
    'E4': E4_Korea
}