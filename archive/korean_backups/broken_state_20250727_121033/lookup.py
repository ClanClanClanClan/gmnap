import csv, functools
@functools.lru_cache
def rom2han():
    return {r.lower():h for h,r in csv.reader(open("resources/rr_syllable_map.csv",encoding="utf8"))}