from __future__ import annotations

from typing import Any, Dict, List


class MathGenealogyClient:
    """Disabled by default. Enable only if you have explicit permission.
    When enabled, implement a lawful client that abides by robots.txt and ToS.
    """

    def __init__(self, enabled: bool = False, allow_scrape: bool = False):
        self.enabled = enabled and allow_scrape

    async def get_advisors(self, name: str) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        # Placeholder to keep interface stable. Implement lawful data access here.
        return []
