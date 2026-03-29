import csv
import functools
import os


@functools.lru_cache
def rom2han():
    result = {}
    _base_dir = os.path.dirname(os.path.dirname(__file__))
    csv_path = os.path.join(_base_dir, "resources/rr_syllable_map.csv")
    for row in csv.reader(open(csv_path, encoding="utf8")):
        if len(row) >= 2 and not row[0].startswith("#"):
            h, r = row[0], row[1]
            result[r.lower()] = h
    return result
