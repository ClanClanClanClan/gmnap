import unicodedata as ud, json, itertools, csv, pathlib

# 2.1 Enumerate all 11,172 Hangul syllables
BASE, LCOUNT, VCOUNT, TCOUNT = 0xAC00, 19, 21, 28

def decompose(syl):
    code = ord(syl) - BASE
    L = code // (VCOUNT * TCOUNT)
    V = (code % (VCOUNT * TCOUNT)) // TCOUNT
    T = code % TCOUNT
    return L, V, T

LEADS  = ["g","kk","n","d","tt","r","m","b","pp","s","ss","ng","j","jj","ch","k","t","p","h"]
VOWELS = ["a","ae","ya","yae","eo","e","yeo","ye","o","wa","wae","oe","yo","u","wo","we","wi","yu","eu","ui","i"]
TAILS  = ["","k","k","ks","n","nj","nh","t","l","lk","lm","lp","ls","lt","lp","lh","m","p","ps","t","t","ng","t","t","k","t","p","t"]

# 2.2 Build mapping rules for four systems
def rr(lead, vowel, tail):
    """Revised Romanization rules"""
    r = LEADS[lead] + VOWELS[vowel] + TAILS[tail]
    # Context-sensitive fixes
    if tail == 0 and r.endswith("k"):
        r = r[:-1] + "g"
    return r

def mr(lead, vowel, tail):
    """McCune-Reischauer rules"""
    # Implement MR-specific mappings
    mr_leads = ["k","kk","n","t","tt","r","m","p","pp","s","ss","","ch","tch","ch'","k'","t'","p'","h"]
    mr_vowels = ["a","ae","ya","yae","ŏ","e","yŏ","ye","o","wa","wae","oe","yo","u","wŏ","we","wi","yu","ŭ","ŭi","i"]
    return mr_leads[lead] + mr_vowels[vowel] + TAILS[tail]

def yale(lead, vowel, tail):
    """Yale romanization rules"""
    # Implement Yale-specific mappings
    yale_leads = ["k","kk","n","t","tt","l","m","p","pp","s","ss","","c","cc","ch","kh","th","ph","h"]
    yale_vowels = ["a","ay","ya","yay","e","ey","ye","yey","o","wa","way","oy","yo","wu","we","wey","wi","yu","u","uy","i"]
    return yale_leads[lead] + yale_vowels[vowel] + TAILS[tail]

def mltr(lead, vowel, tail):
    """MLTR (Ministry) rules"""
    # Similar to RR with minor variations
    return rr(lead, vowel, tail)  # Simplified for now

# Generate all mappings
rr_map = {}
mr_map = {}
yale_map = {}
mltr_map = {}

for idx in range(11172):
    syl = chr(BASE + idx)
    l, v, t = decompose(syl)
    rr_map[syl] = rr(l, v, t)
    mr_map[syl] = mr(l, v, t)
    yale_map[syl] = yale(l, v, t)
    mltr_map[syl] = mltr(l, v, t)

# Write CSV files
pathlib.Path("data/rr_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in rr_map.items()), encoding="utf8")
pathlib.Path("data/mr_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in mr_map.items()), encoding="utf8")
pathlib.Path("data/yale_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in yale_map.items()), encoding="utf8")
pathlib.Path("data/mltr_table.csv").write_text(
    "\n".join(f"{s},{r}" for s,r in mltr_map.items()), encoding="utf8")