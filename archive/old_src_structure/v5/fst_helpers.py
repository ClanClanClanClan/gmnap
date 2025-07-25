import pynini as pn, json, math

TOK = "utf8"

def load_map(csv_path):
    """Load romanization map as FST"""
    pairs = []
    for line in open(csv_path, encoding="utf8"):
        k, v = line.rstrip().split(",", 1)
        pairs.append((v, k))  # roman → Hangul
    return pn.string_map(pairs, input_token_type=TOK, output_token_type=TOK).optimize()

# Load all romanization systems
RR_FST   = load_map("data/rr_table.csv")
MR_FST   = load_map("data/mr_table.csv")
YALE_FST = load_map("data/yale_table.csv")
MLTR_FST = load_map("data/mltr_table.csv")

# Basic union
ROMAN2HANGUL = (RR_FST | MR_FST | YALE_FST | MLTR_FST).optimize()

# 3.2 Add frequency weights
syll_freq = json.load(open("data/syllable_freq.json"))
total = sum(syll_freq.values())

def weight(hangul):
    """Calculate -log frequency weight"""
    return -math.log((syll_freq.get(hangul, 1)) / total)

# Build weighted FST
# For now, use the basic union without frequency weights
# The frequency weighting requires more complex FST manipulation
ROMAN2HANGUL = (RR_FST | MR_FST | YALE_FST | MLTR_FST).optimize()

# TODO: Add frequency weights in a later optimization phase
# This would require creating individual weighted paths for each mapping

# Save for later use
ROMAN2HANGUL.write("data/roman2hangul.fst")