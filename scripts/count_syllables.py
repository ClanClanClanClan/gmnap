import re, sys, json

syll_pat = re.compile(r"[가-힣]")
freq = {}

for path in sys.argv[1:]:
    for line in open(path, "r", errors="ignore"):
        for ch in syll_pat.findall(line):
            freq[ch] = freq.get(ch, 0) + 1

json.dump(freq, open("data/syllable_freq.json", "w"))