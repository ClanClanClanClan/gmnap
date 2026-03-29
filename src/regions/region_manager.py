"""
V7-compatible RegionManager implementation.
"""

from pathlib import Path
from typing import Dict, Optional
from .base import RegionBase


class RegionManager:
    """
    Regional processor manager for GMNAP v7.0.
    Manages loading and accessing regional processors.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize RegionManager.

        Args:
            config_path: Path to configuration directory
        """
        self.config_path = config_path or Path("./config")
        self.regions: Dict[str, RegionBase] = {}
        self._loaded = False

    def get_region(self, code: str) -> RegionBase:
        """
        Get a region processor by code.

        Args:
            code: Region code (e.g., 'A1', 'E4')

        Returns:
            Region processor instance
        """
        # Try to import from manager module
        try:
            from .manager import get_region

            return get_region(code)
        except ImportError:
            pass

        # Check cache
        if code in self.regions:
            return self.regions[code]

        # Try to load dynamically
        region = self._load_region(code)
        if region:
            self.regions[code] = region
            return region

        # Fallback to base
        return RegionBase()

    def _load_region(self, code: str) -> Optional[RegionBase]:
        """
        Dynamically load a region processor.

        Args:
            code: Region code

        Returns:
            Region processor instance or None
        """
        # Map codes to modules
        region_map = {
            "A1": "regions_a1.RegionA1",
            "E1": "regions_e1.RegionE1",
            # Add more mappings as needed
        }

        if code not in region_map:
            return None

        try:
            module_path, class_name = region_map[code].rsplit(".", 1)
            module = __import__(f"src.regions.{module_path}", fromlist=[class_name])
            region_class = getattr(module, class_name)
            return region_class()
        except (ImportError, AttributeError):
            return None

    def list_regions(self) -> list:
        """
        List available region codes.

        Returns:
            List of region codes
        """
        return [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "B1",
            "B2",
            "B3",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "F1",
            "F2",
            "F3",
            "F4",
            "G1",
        ]
