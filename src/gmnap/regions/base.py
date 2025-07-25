"""
Base classes for regional processing in GMNAP.
Implements the RegionSpec interface as defined in specs v6.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


class RegionRuleError(Exception):
    """Entry fails region-specific rule."""
    pass


@dataclass
class RegionSpec(ABC):
    """
    Region specification interface as defined in specs v6.
    
    All region implementations must inherit from this class and implement
    the mandatory hooks.
    """
    code: str
    yaml_files: List[str]
    scripts: List[str]
    mixed_scripts: bool = False
    canonical_order: Literal[
        "Family, Given", "Given Family",
        "Patronymic", "Mononym"
    ] = "Family, Given"
    romanisation_standards: List[str] = None
    
    def __post_init__(self):
        if self.romanisation_standards is None:
            self.romanisation_standards = []
        self.logger = logging.getLogger(f"regions.{self.code}")
    
    # Mandatory hooks
    @abstractmethod
    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean entry data according to regional rules.
        
        This method should:
        - Remove titles, honorifics
        - Normalize punctuation
        - Handle regional-specific formatting
        
        Args:
            entry: The entry dictionary to clean (modified in-place)
        
        Raises:
            RegionRuleError: If cleaning fails
        """
        pass
    
    @abstractmethod
    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with region-specific data.
        
        This method should:
        - Generate variants
        - Extract components (middle names, particles)
        - Add regional extras
        
        Args:
            entry: The entry dictionary to augment (modified in-place)
        
        Raises:
            RegionRuleError: If augmentation fails
        """
        pass
    
    @abstractmethod
    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry according to regional rules.
        
        This method should:
        - Check script validity
        - Validate name structure
        - Ensure required fields
        
        Args:
            entry: The entry dictionary to validate
        
        Raises:
            RegionRuleError: If validation fails
        """
        pass
    
    @abstractmethod
    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key for entry.
        
        Must be pure function - calling twice with same input
        must produce identical output.
        
        Args:
            entry: The entry dictionary
        
        Returns:
            Sort key string
        """
        pass
    
    # Optional bulk enrichment
    def batch_enrich(self, entries: List[Dict[str, Any]]) -> None:
        """
        Optional bulk enrichment for performance.
        
        Args:
            entries: List of entries to enrich
        """
        pass
    
    # Optional file-level hooks
    def on_file_load(self, data: Dict[str, Any]) -> None:
        """
        Hook called when YAML file is loaded.
        
        Args:
            data: The loaded YAML data
        """
        pass
    
    def before_write(self, data: Dict[str, Any]) -> None:
        """
        Hook called before writing YAML file.
        
        Args:
            data: The YAML data to write
        """
        pass
    
    def after_write(self, data: Dict[str, Any]) -> None:
        """
        Hook called after writing YAML file.
        
        Args:
            data: The written YAML data
        """
        pass


# Region code definitions from specs v6
REGION_CODES = {
    # A Groups - Western sphere
    "A1": "Core Anglo-Sphere",
    "A2": "Western Europe", 
    "A3": "Nordic-Baltic",
    "A4": "Oceania Island States",
    "A5": "Dutch/French Caribbean",
    
    # B Groups - Slavic/Central Europe
    "B1": "East-Slavic",
    "B2": "South-Slavic & Central Europe",
    "B3": "Greek World",
    
    # C Groups - Middle East/Caucasus
    "C1": "Greater-Turkic",
    "C2": "Persian-Tajik",
    "C3": "Arabic Levant-Nile",
    "C4": "Arabic Gulf",
    "C5": "Arabic Maghreb",
    "C6": "Hebrew & Diaspora",
    "C7": "Armenian",
    "C8": "Georgian",
    "C9": "Caucasus-Turkic",
    
    # D Groups - South Asia
    "D1": "South Asia - Hindi Belt",
    "D2": "South Asia - Dravidian",
    "D3": "South Asia - Bengali",
    "D4": "Pakistan & Urdu",
    "D5": "Sinhala",
    
    # E Groups - East Asia
    "E1": "Sinophone Mainland",
    "E2": "Sinophone Traditional",
    "E3": "Japan",
    "E4": "Korea",
    "E5": "Vietnam",
    "E6": "Mainland SEA",
    "E7": "Maritime SEA",
    
    # F Groups - Sub-Saharan Africa
    "F1": "SSA - Francophone",
    "F2": "SSA - Anglophone",
    "F3": "Horn of Africa",
    "F4": "Lusophone Africa",
    
    # G Groups - Latin America
    "G1": "Latin America & Iberian Caribbean",
    
    # H Groups - Historical
    "H1": "Historical (≤ 1850)",
    
    # Special
    "R0": "Residual Latin-ASCII",
    "Z0": "Quarantine"
}


# ISO territory mappings from specs
TERRITORY_TO_REGION = {
    # A1 - Core Anglo-Sphere
    "US": "A1", "GB": "A1", "CA": "A1", "AU": "A1", "NZ": "A1", "IE": "A1",
    "AG": "A1", "AI": "A1", "BB": "A1", "BM": "A1", "BS": "A1", "DM": "A1",
    "GD": "A1", "GY": "A1", "JM": "A1", "KN": "A1", "LC": "A1", "MS": "A1",
    "TC": "A1", "TT": "A1", "VC": "A1", "VG": "A1", "VI": "A1",
    "GU": "A1", "AS": "A1", "MP": "A1", "UM": "A1", "FK": "A1",
    
    # A2 - Western Europe
    "FR": "A2", "DE": "A2", "IT": "A2", "ES": "A2", "PT": "A2", "NL": "A2",
    "BE": "A2", "CH": "A2", "AT": "A2", "LU": "A2", "LI": "A2", "SM": "A2",
    "MC": "A2", "GI": "A2", "AD": "A2", "MT": "A2", "VA": "A2",
    
    # A3 - Nordic-Baltic
    "DK": "A3", "NO": "A3", "SE": "A3", "FI": "A3", "IS": "A3", "FO": "A3",
    "AX": "A3", "EE": "A3", "LV": "A3", "LT": "A3",
    
    # A4 - Oceania Island States
    "FJ": "A4", "PG": "A4", "SB": "A4", "VU": "A4", "WS": "A4", "TO": "A4",
    "KI": "A4", "TV": "A4", "NR": "A4", "CK": "A4", "NU": "A4", "PF": "A4",
    "NC": "A4",
    
    # A5 - Dutch/French Caribbean
    "CW": "A5", "SX": "A5", "BQ": "A5", "MQ": "A5", "GF": "A5", "GP": "A5",
    "RE": "A5", "YT": "A5", "PM": "A5",
    
    # B1 - East-Slavic
    "RU": "B1", "UA": "B1", "BY": "B1",
    
    # B2 - South-Slavic & Central Europe
    "BG": "B2", "RS": "B2", "ME": "B2", "HR": "B2", "SI": "B2", "BA": "B2",
    "MK": "B2", "PL": "B2", "CZ": "B2", "SK": "B2", "HU": "B2", "RO": "B2",
    "AL": "B2", "XK": "B2",
    
    # B3 - Greek World
    "GR": "B3", "CY": "B3",
    
    # C1 - Greater-Turkic
    "TR": "C1", "AZ": "C1", "UZ": "C1", "TM": "C1", "KG": "C1", "KZ": "C1",
    
    # C2 - Persian-Tajik
    "IR": "C2", "AF": "C2", "TJ": "C2",
    
    # C3 - Arabic Levant-Nile
    "IQ": "C3", "JO": "C3", "LB": "C3", "SY": "C3", "PS": "C3", "EG": "C3",
    "SD": "C3", "SS": "C3",
    
    # C4 - Arabic Gulf
    "SA": "C4", "KW": "C4", "AE": "C4", "QA": "C4", "OM": "C4", "BH": "C4",
    "YE": "C4",
    
    # C5 - Arabic Maghreb
    "MA": "C5", "DZ": "C5", "TN": "C5", "LY": "C5", "EH": "C5", "MR": "C5",
    
    # C6 - Hebrew & Diaspora
    "IL": "C6",
    
    # C7 - Armenian
    "AM": "C7",
    
    # C8 - Georgian
    "GE": "C8",
    
    # D1 - South Asia - Hindi Belt
    "IN": "D1", "NP": "D1", "BT": "D1",  # Note: IN needs sub-region detection
    
    # D3 - South Asia - Bengali
    "BD": "D3",
    
    # D4 - Pakistan & Urdu
    "PK": "D4",
    
    # D5 - Sinhala
    "LK": "D5",
    
    # E1 - Sinophone Mainland
    "CN": "E1",
    
    # E2 - Sinophone Traditional
    "TW": "E2", "HK": "E2", "MO": "E2",
    
    # E3 - Japan
    "JP": "E3",
    
    # E4 - Korea
    "KR": "E4", "KP": "E4",
    
    # E5 - Vietnam
    "VN": "E5",
    
    # E6 - Mainland SEA
    "TH": "E6", "KH": "E6", "LA": "E6",
    
    # E7 - Maritime SEA
    "ID": "E7", "MY": "E7", "SG": "E7", "BN": "E7", "PH": "E7", "TL": "E7",
    
    # F1 - SSA - Francophone
    "BJ": "F1", "BF": "F1", "CM": "F1", "CF": "F1", "CG": "F1", "CI": "F1",
    "DJ": "F1", "GA": "F1", "GN": "F1", "ML": "F1", "NE": "F1", "SN": "F1",
    "TG": "F1", "TD": "F1", "KM": "F1", "SC": "F1", "MG": "F1", "BI": "F1",
    
    # F2 - SSA - Anglophone
    "GH": "F2", "NG": "F2", "KE": "F2", "UG": "F2", "TZ": "F2", "ZW": "F2",
    "ZM": "F2", "MW": "F2", "GM": "F2", "LR": "F2", "SL": "F2", "BW": "F2",
    "LS": "F2", "NA": "F2", "RW": "F2", "SZ": "F2", "MU": "F2", "SS": "F2",
    
    # F3 - Horn of Africa
    "ET": "F3", "ER": "F3",
    
    # F4 - Lusophone Africa
    "AO": "F4", "MZ": "F4", "CV": "F4", "GW": "F4", "ST": "F4",
    
    # G1 - Latin America & Iberian Caribbean
    "AR": "G1", "BO": "G1", "BR": "G1", "CL": "G1", "CO": "G1", "CR": "G1",
    "CU": "G1", "DO": "G1", "EC": "G1", "GT": "G1", "GY": "G1", "HN": "G1",
    "HT": "G1", "MX": "G1", "NI": "G1", "PA": "G1", "PE": "G1", "PY": "G1",
    "SV": "G1", "SR": "G1", "UY": "G1", "VE": "G1", "PR": "G1",
}


def get_region_for_territory(territory_code: str) -> str:
    """
    Get region code for ISO territory.
    
    Args:
        territory_code: ISO 3166 2-letter code
        
    Returns:
        Region code (A1-H1, R0, Z0)
    """
    return TERRITORY_TO_REGION.get(territory_code.upper(), "R0")


def get_region_name(region_code: str) -> str:
    """
    Get human-readable name for region code.
    
    Args:
        region_code: Region code (e.g., "A1")
        
    Returns:
        Region name (e.g., "Core Anglo-Sphere")
    """
    return REGION_CODES.get(region_code, "Unknown Region")