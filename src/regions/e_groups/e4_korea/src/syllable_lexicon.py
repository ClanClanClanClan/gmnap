import csv

LEXICON = {
    row[1].lower() for row in csv.reader(open("resources/rr_syllable_map.csv", encoding="utf8"))
}
