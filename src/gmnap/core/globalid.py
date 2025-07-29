"""
GMNAP Global ID Generation

Implements GlobalID generation as specified in v6 specs:
"128-bit truncated SHA-256 (22 Base32 symbols) of {CanonicalNative, BirthYear?, DeathYear?}; 
if collision occurs append --1, --2, …"
"""

import hashlib
import base64
from typing import Optional, Dict, Any

def generate_global_id(
    canonical_native: str, 
    birth_year: Optional[int] = None, 
    death_year: Optional[int] = None
) -> str:
    """
    Generate GlobalID according to v6 specifications.
    
    Args:
        canonical_native: Authoritative form in the author's own script
        birth_year: Optional birth year
        death_year: Optional death year
        
    Returns:
        22-character Base32 GlobalID
    """
    # Build the input string for hashing
    components = [canonical_native]
    
    if birth_year is not None:
        components.append(str(birth_year))
    
    if death_year is not None:
        components.append(str(death_year))
    
    # Join components with a delimiter
    input_string = "|".join(components)
    
    # Generate SHA-256 hash
    hash_bytes = hashlib.sha256(input_string.encode('utf-8')).digest()
    
    # Truncate to 128 bits (16 bytes)
    truncated_hash = hash_bytes[:16]
    
    # Encode as Base32 and remove padding
    global_id = base64.b32encode(truncated_hash).decode('ascii').rstrip('=')
    
    # Should be exactly 22 characters for 128 bits encoded in Base32
    assert len(global_id) == 26, f"Expected 26 chars, got {len(global_id)}"
    
    # Take first 22 characters as specified
    return global_id[:22]


def generate_global_id_from_entry(entry: Dict[str, Any]) -> str:
    """
    Generate GlobalID from a complete entry dictionary.
    
    Args:
        entry: Entry dictionary with CanonicalNative and optional birth/death years
        
    Returns:
        22-character Base32 GlobalID
    """
    canonical_native = entry.get('CanonicalNative')
    if not canonical_native:
        raise ValueError("Entry must contain CanonicalNative field")
    
    birth_year = entry.get('BirthYear')
    death_year = entry.get('DeathYear')
    
    return generate_global_id(canonical_native, birth_year, death_year)


def handle_collision(base_id: str, collision_count: int) -> str:
    """
    Handle GlobalID collisions by appending --1, --2, etc.
    
    Args:
        base_id: Original 22-character GlobalID
        collision_count: Number of collisions encountered
        
    Returns:
        GlobalID with collision suffix
    """
    return f"{base_id}--{collision_count}"


def validate_global_id(global_id: str) -> bool:
    """
    Validate that a GlobalID follows the correct format.
    
    Args:
        global_id: GlobalID to validate
        
    Returns:
        True if valid format
    """
    # Check for collision suffix
    if '--' in global_id:
        base_id, suffix = global_id.split('--', 1)
        # Base should be 22 chars, suffix should be numeric
        if len(base_id) != 22 or not suffix.isdigit():
            return False
        global_id = base_id
    
    # Should be exactly 22 characters of Base32
    if len(global_id) != 22:
        return False
    
    # Should be valid Base32 characters
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567')
    return all(c in valid_chars for c in global_id)