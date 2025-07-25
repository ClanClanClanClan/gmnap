try:
    from rapidfuzz import fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    USE_RAPIDFUZZ = False

def roman_to_hangul(roman):
    """Convert romanized Korean to Hangul - placeholder"""
    # In real implementation, would use v5.converter_with_backoff
    return "한글"

def hangul_to_roman(hangul):
    """Convert Hangul to romanized Korean - placeholder"""
    # In real implementation, would use hangul_to_roman converter
    return "hangul"

def dice_coefficient(a, b):
    """Calculate Dice coefficient with NFC normalization"""
    import unicodedata
    
    # NFC normalize and casefold
    a_norm = unicodedata.normalize('NFC', a.casefold())
    b_norm = unicodedata.normalize('NFC', b.casefold())
    
    if USE_RAPIDFUZZ:
        # Use token_sort_ratio as approximation of Dice coefficient
        similarity = fuzz.token_sort_ratio(a_norm, b_norm)
        return similarity / 100.0  # Convert to 0-1 range
    else:
        # Manual Dice coefficient calculation
        # Convert strings to character bigrams
        def get_bigrams(s):
            return set(s[i:i+2] for i in range(len(s)-1)) if len(s) > 1 else {s}
        
        bigrams_a = get_bigrams(a_norm)
        bigrams_b = get_bigrams(b_norm)
        
        # Dice coefficient = 2 * |intersection| / (|A| + |B|)
        if len(bigrams_a) == 0 and len(bigrams_b) == 0:
            return 1.0
        
        intersection = len(bigrams_a & bigrams_b)
        dice = 2.0 * intersection / (len(bigrams_a) + len(bigrams_b))
        return dice

def roundtrip_score(rr_name):
    """Calculate round-trip accuracy"""
    # Convert to Hangul
    hangul = roman_to_hangul(rr_name)
    
    # Convert back to romanization
    rr_reconstructed = hangul_to_roman(hangul)
    
    # Calculate Dice score
    return dice_coefficient(rr_name, rr_reconstructed)

if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("kim", "kim"),
        ("lee", "li"),  
        ("park", "pak"),
        ("choi", "choe"),
    ]
    
    print("Testing Dice coefficient:")
    for a, b in test_cases:
        score = dice_coefficient(a, b)
        print(f"  {a} vs {b}: {score:.3f}")
    
    print("\nTesting round-trip accuracy:")
    for name in ["kim", "lee", "park", "jung"]:
        score = roundtrip_score(name)
        print(f"  {name}: {score:.3f}")