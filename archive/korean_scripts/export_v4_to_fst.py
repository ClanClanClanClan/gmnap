import json
import pynini as pn
import sys

def export_v4_to_fst(v4_json_path, lambda_weight=3.0):
    """Convert V4 mappings to weighted FST"""
    v4_data = json.load(open(v4_json_path))
    
    # Build FST with penalty weight
    v4_fst = pn.Fst()
    
    for roman, hangul in v4_data.items():
        # Add path with λ penalty
        roman_fst = pn.accep(roman.lower(), token_type="utf8")
        hangul_fst = pn.accep(hangul, token_type="utf8")
        path = pn.cross(roman_fst, hangul_fst)
        
        # Apply weight using reweight for PyNini 2.1.6
        # Create weight vector of appropriate length
        weights = [pn.Weight('tropical', lambda_weight)] * path.num_states()
        path.reweight(weights)
        v4_fst = pn.union(v4_fst, path)
    
    v4_fst = v4_fst.optimize()
    v4_fst.write("data/v4_backoff.fst")
    return v4_fst

if __name__ == "__main__":
    export_v4_to_fst(sys.argv[1], float(sys.argv[2]))