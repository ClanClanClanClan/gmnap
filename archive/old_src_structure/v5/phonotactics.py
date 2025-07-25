import pynini as pn

# Define vowel and consonant sets for RR
V_STRINGS = ["a","ae","ya","yae","eo","e","yeo","ye","o","wa","wae","oe","yo","u","wo","we","wi","yu","eu","ui","i"]
C_STRINGS = ["g","kk","n","d","tt","r","m","b","pp","s","ss","j","jj","ch","k","t","p","h","ng","ks","nj","nh","lk","lm","lp","ls","lt","lh","ps"]

# Create FSAs - use union of acceptors since string_set doesn't exist
V = pn.union(*[pn.accep(v, token_type="utf8") for v in V_STRINGS]).optimize()
C = pn.union(*[pn.accep(c, token_type="utf8") for c in C_STRINGS]).optimize()

# Korean syllable structure: (C)V(C)
SYLL = (C.ques + V + C.ques).optimize()
WORD = pn.closure(SYLL, 1).optimize()

# Export for use
SYLL.write("data/korean_syllable.fsa")