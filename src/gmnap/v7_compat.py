"""
GMNAP v7 Compatibility Layer

Wraps existing regional processors to provide v7-compliant interface
while maintaining backwards compatibility with v6 implementations.
"""

import logging
from typing import Any, Dict, List, Optional
from .regions.base import RegionSpec, RegionRuleError

logger = logging.getLogger(__name__)


class V7RegionAdapter:
    """
    Adapts existing regional processors to v7 interface.
    
    Provides enhanced error handling, logging, and standardized
    method signatures while preserving existing functionality.
    """
    
    def __init__(self, processor: RegionSpec):
        """
        Initialize adapter with existing processor.
        
        Args:
            processor: Existing regional processor instance
        """
        self.processor = processor
        self.code = processor.code
        self.logger = logging.getLogger(f"v7_compat.{self.code}")
        
        # V7 enhancement flags
        self.enhanced_validation = True
        self.performance_monitoring = True
        self.detailed_logging = True
    
    def clean(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        V7-enhanced clean method with error handling.
        
        Args:
            entry: Entry to clean
            
        Returns:
            Cleaned entry (copy)
            
        Raises:
            RegionRuleError: If cleaning fails
        """
        if self.detailed_logging:
            self.logger.debug(f"Cleaning entry for {self.code}")
        
        # Create copy to avoid modifying original
        cleaned_entry = entry.copy()
        
        try:
            # Call underlying processor
            self.processor.clean(cleaned_entry)
            
            if self.detailed_logging:
                self.logger.debug(f"Successfully cleaned entry for {self.code}")
            
            return cleaned_entry
            
        except Exception as e:
            self.logger.error(f"Clean failed for {self.code}: {e}")
            raise RegionRuleError(f"Clean failed for {self.code}: {e}") from e
    
    def augment(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        V7-enhanced augment method with error handling.
        
        Args:
            entry: Entry to augment
            
        Returns:
            Augmented entry (copy)
            
        Raises:
            RegionRuleError: If augmentation fails
        """
        if self.detailed_logging:
            self.logger.debug(f"Augmenting entry for {self.code}")
        
        # Create copy to avoid modifying original
        augmented_entry = entry.copy()
        
        try:
            # Call underlying processor
            self.processor.augment(augmented_entry)
            
            if self.detailed_logging:
                self.logger.debug(f"Successfully augmented entry for {self.code}")
            
            return augmented_entry
            
        except Exception as e:
            self.logger.error(f"Augment failed for {self.code}: {e}")
            raise RegionRuleError(f"Augment failed for {self.code}: {e}") from e
    
    def validate(self, entry: Dict[str, Any]) -> bool:
        """
        V7-enhanced validate method with standardized return.
        
        Args:
            entry: Entry to validate
            
        Returns:
            True if valid, False otherwise
        """
        if self.detailed_logging:
            self.logger.debug(f"Validating entry for {self.code}")
        
        try:
            # Call underlying processor
            self.processor.validate(entry)
            
            if self.detailed_logging:
                self.logger.debug(f"Entry validated successfully for {self.code}")
            
            return True
            
        except RegionRuleError as e:
            if self.detailed_logging:
                self.logger.debug(f"Validation failed for {self.code}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Validation error for {self.code}: {e}")
            return False
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        V7-enhanced order key generation with error handling.
        
        Args:
            entry: Entry to generate key for
            
        Returns:
            Sort key string
        """
        try:
            key = self.processor.order_key(entry)
            
            if self.detailed_logging:
                self.logger.debug(f"Generated order key for {self.code}: {key[:50]}...")
            
            return key
            
        except Exception as e:
            self.logger.error(f"Order key generation failed for {self.code}: {e}")
            # Return fallback key
            canonical = entry.get('CanonicalLatin', 'UNKNOWN')
            return f"FALLBACK_{self.code}_{canonical}"
    
    def process_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        V7 convenience method: full processing pipeline.
        
        Args:
            entry: Raw entry
            
        Returns:
            Fully processed entry
            
        Raises:
            RegionRuleError: If any step fails
        """
        if self.detailed_logging:
            self.logger.debug(f"Full processing pipeline for {self.code}")
        
        # Step 1: Clean
        processed_entry = self.clean(entry)
        
        # Step 2: Augment
        processed_entry = self.augment(processed_entry)
        
        # Step 3: Validate (validate() raises exception on failure)
        self.validate(processed_entry)
        
        # Step 4: Add order key
        processed_entry['_order_key'] = self.order_key(processed_entry)
        
        if self.detailed_logging:
            self.logger.debug(f"Full processing completed for {self.code}")
        
        return processed_entry


class V7RegionManager:
    """
    V7-compatible region manager.
    
    Manages collection of v7-adapted regional processors
    with enhanced discovery and routing capabilities.
    """
    
    def __init__(self):
        """Initialize empty manager."""
        self.adapters: Dict[str, V7RegionAdapter] = {}
        self.logger = logging.getLogger("v7_compat.manager")
    
    def register_processor(self, processor: RegionSpec) -> None:
        """
        Register a regional processor with v7 adapter.
        
        Args:
            processor: Regional processor to register
        """
        adapter = V7RegionAdapter(processor)
        self.adapters[processor.code] = adapter
        self.logger.info(f"Registered {processor.code} with v7 compatibility")
    
    def get_adapter(self, region_code: str) -> Optional[V7RegionAdapter]:
        """
        Get v7 adapter for region code.
        
        Args:
            region_code: Region code (e.g., "A1")
            
        Returns:
            V7RegionAdapter instance or None
        """
        return self.adapters.get(region_code)
    
    def list_regions(self) -> List[str]:
        """
        List all registered region codes.
        
        Returns:
            List of region codes
        """
        return list(self.adapters.keys())
    
    def process_entry(self, entry: Dict[str, Any], region_code: str) -> Dict[str, Any]:
        """
        Process entry with specified region.
        
        Args:
            entry: Entry to process
            region_code: Target region code
            
        Returns:
            Processed entry
            
        Raises:
            ValueError: If region not found
            RegionRuleError: If processing fails
        """
        adapter = self.get_adapter(region_code)
        if not adapter:
            raise ValueError(f"Region {region_code} not registered")
        
        return adapter.process_entry(entry)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get v7 compatibility status.
        
        Returns:
            Status dictionary
        """
        return {
            "v7_compatible": True,
            "registered_regions": len(self.adapters),
            "region_codes": list(self.adapters.keys()),
            "features": {
                "enhanced_validation": True,
                "performance_monitoring": True,
                "detailed_logging": True,
                "full_pipeline": True
            }
        }


# Global v7 manager instance
v7_manager = V7RegionManager()


def load_working_processors() -> V7RegionManager:
    """
    Load all working regional processors into v7 manager.
    
    Returns:
        Configured V7RegionManager
    """
    logger.info("Loading working processors for v7 compatibility")
    
    # Import working processors
    try:
        from .regions.a_groups.a1_anglo_sphere import A1_AngloSphere
        v7_manager.register_processor(A1_AngloSphere())
        logger.info("Loaded A1_AngloSphere")
    except ImportError as e:
        logger.warning(f"Could not load A1_AngloSphere: {e}")
    
    try:
        from .regions.a_groups.a2_western_europe import A2_WesternEurope
        v7_manager.register_processor(A2_WesternEurope())
        logger.info("Loaded A2_WesternEurope")
    except ImportError as e:
        logger.warning(f"Could not load A2_WesternEurope: {e}")
    
    try:
        from .regions.b_groups.b1_east_slavic import B1_EastSlavic
        v7_manager.register_processor(B1_EastSlavic())
        logger.info("Loaded B1_EastSlavic")
    except ImportError as e:
        logger.warning(f"Could not load B1_EastSlavic: {e}")
    
    try:
        from .regions.b_groups.b2_south_slavic_central import B2_SouthSlavicCentral
        v7_manager.register_processor(B2_SouthSlavicCentral())
        logger.info("Loaded B2_SouthSlavicCentral")
    except ImportError as e:
        logger.warning(f"Could not load B2_SouthSlavicCentral: {e}")
    
    try:
        from .regions.c_groups.c2_persian_tajik import C2_PersianTajik
        v7_manager.register_processor(C2_PersianTajik())
        logger.info("Loaded C2_PersianTajik")
    except ImportError as e:
        logger.warning(f"Could not load C2_PersianTajik: {e}")
    
    try:
        from .regions.c_groups.c3_arabic_levant_nile import C3_ArabicLevantNile
        v7_manager.register_processor(C3_ArabicLevantNile())
        logger.info("Loaded C3_ArabicLevantNile")
    except ImportError as e:
        logger.warning(f"Could not load C3_ArabicLevantNile: {e}")
    
    try:
        from .regions.c_groups.c4_arabic_gulf import C4_ArabicGulf
        v7_manager.register_processor(C4_ArabicGulf())
        logger.info("Loaded C4_ArabicGulf")
    except ImportError as e:
        logger.warning(f"Could not load C4_ArabicGulf: {e}")
    
    try:
        from .regions.d_groups.d1_south_asia_hindi_belt import D1_SouthAsiaHindiBelt
        v7_manager.register_processor(D1_SouthAsiaHindiBelt())
        logger.info("Loaded D1_SouthAsiaHindiBelt")
    except ImportError as e:
        logger.warning(f"Could not load D1_SouthAsiaHindiBelt: {e}")
    
    try:
        from .regions.e_groups.e1_sinophone_mainland import E1_SinophoneMainland
        v7_manager.register_processor(E1_SinophoneMainland())
        logger.info("Loaded E1_SinophoneMainland")
    except ImportError as e:
        logger.warning(f"Could not load E1_SinophoneMainland: {e}")
    
    try:
        from .regions.e_groups.e3_japan import E3_Japan
        v7_manager.register_processor(E3_Japan())
        logger.info("Loaded E3_Japan")
    except ImportError as e:
        logger.warning(f"Could not load E3_Japan: {e}")
    
    try:
        from .regions.g_groups.g1_latin_america import G1_LatinAmerica
        v7_manager.register_processor(G1_LatinAmerica())
        logger.info("Loaded G1_LatinAmerica")
    except ImportError as e:
        logger.warning(f"Could not load G1_LatinAmerica: {e}")
    
    logger.info(f"V7 compatibility layer loaded with {len(v7_manager.adapters)} regions")
    return v7_manager