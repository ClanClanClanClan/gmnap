from rapidfuzz import fuzz
import sys
sys.path.append('src')

def roman_to_hangul(roman):
    """Convert romanized Korean to Hangul using V5 converter"""
    try:
        from v5.converter_with_backoff import convert_with_backoff
        
        # Handle complex names by converting parts
        if ',' in roman or ' ' in roman or '-' in roman:
            parts = roman.replace(',', '').split()
            converted_parts = []
            for part in parts:
                if '-' in part:
                    # Handle hyphenated names
                    subparts = part.split('-')
                    converted_subparts = []
                    for subpart in subparts:
                        result = convert_with_backoff(subpart.lower())
                        converted_subparts.append(result if result else subpart)
                    converted_parts.append('-'.join(converted_subparts))
                else:
                    result = convert_with_backoff(part.lower())
                    converted_parts.append(result if result else part)
            return ' '.join(converted_parts)
        else:
            # Simple name
            result = convert_with_backoff(roman.lower())
            return result if result else roman
    except Exception as e:
        print(f"Error in roman_to_hangul: {e}")
        return roman

def hangul_to_roman(hangul):
    """Convert Hangul to romanized Korean"""
    try:
        from v5.hangul_to_roman import hangul_to_roman as h2r
        return h2r(hangul)
    except:
        return "hangul"  # Fallback

def dice_coefficient(a, b):
    """Calculate Dice coefficient with NFC normalization"""
    import unicodedata
    
    # NFC normalize and casefold
    a_norm = unicodedata.normalize('NFC', a.casefold())
    b_norm = unicodedata.normalize('NFC', b.casefold())
    
    # Use token_sort_ratio as approximation of Dice coefficient
    similarity = fuzz.token_sort_ratio(a_norm, b_norm)
    return similarity / 100.0  # Convert to 0-1 range

def roundtrip_score(rr_name):
    """Calculate round-trip accuracy"""
    # Convert to Hangul
    hangul = roman_to_hangul(rr_name)
    
    # Convert back to romanization
    rr_reconstructed = hangul_to_roman(hangul)
    
    # Calculate Dice score
    return dice_coefficient(rr_name, rr_reconstructed)