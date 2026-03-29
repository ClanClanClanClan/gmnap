#!/usr/bin/env python3
"""
Remove conflicting incorrect mappings as per plan step 2
"""
import csv
from pathlib import Path

E4_ROOT = Path(__file__).parent.parent

# Incorrect mappings to remove (these conflict with correct names)
incorrect_mappings = [
    ("붐", "bum"),  # Should be 범,bum
    ("숭", "sung"),  # Should be 성,sung
    ("중", "jung"),  # Should be 정,jung
    ("창", "chang"),  # Should be 장,chang
    ("초", "cho"),  # Should be 조,cho
    ("숩", "sup"),  # Should be 섭,sup
    ("춘", "chun"),  # Should be 전,chun
    ("출", "chul"),  # Should be 철,chul
    ("큐", "kyu"),  # Should be 규,kyu
    ("숲", "sup"),  # Should be 섭,sup
    ("큥", "kyung"),  # Should be 경,kyung
    ("킴", "kim"),  # Should be 김,kim
    ("흉", "hyung"),  # Should be 형,hyung
    ("봌", "bok"),  # Should be 복,bok
    ("흌", "hyuk"),  # Should be 혁,hyuk
    ("휵", "hyuk"),  # Should be 혁,hyuk
    ("휶", "hyuk"),  # Should be 혁,hyuk
    ("선", "sun"),  # Should be 선,seon (sun = 순)
    ("캉", "kang"),  # Should be 강,kang
    ("퀀", "kwon"),  # Should be 권,kwon
    ("쾈", "kwak"),  # Should be 곽,kwak
    ("뷴", "byun"),  # Should be 변,byun
    ("파잌", "paik"),  # Should be 백,paik
    ("바잌", "baik"),  # Should be 백,baik
    ("충", "chung"),  # Should be 정,chung
    ("움", "um"),  # Should be 엄,um
    ("코", "ko"),  # Should be 고,ko
    ("콱", "kwak"),  # Should be 곽,kwak
    ("요우", "you"),  # Should be 유,you
    ("고오", "koo"),  # Should be 구,koo
    ("팡", "pang"),  # Should be 방,pang
    ("퍀", "paek"),  # Should be 백,paek
    ("팍", "pak"),  # Should be 박,pak
    ("콩", "kong"),  # Should be 공,kong
    ("뫀", "mok"),  # Should be 목,mok
    ("곽", "gwak"),  # Should keep only 곽,kwak
    ("쿠", "ku"),  # Should be 구,ku
    ("청", "chung"),  # Should keep only 정,chung for surname
    ("콲", "kwak"),  # Should be 곽,kwak
    ("신", "sin"),  # Should keep only shin in variant_map.csv
    ("팎", "pak"),  # Should be 박,pak
    ("밖", "bak"),  # Should be 박,bak
    ("퀘온", "kweon"),  # Should be 권,kweon
    ("뵨", "byon"),  # Should be 변,byon
    ("리", "ri"),  # Should be 이,ri
    ("주네", "june"),  # Should be 준,june
]


def main():
    syllable_map_path = E4_ROOT / "resources" / "rr_syllable_map.csv"
    temp_path = syllable_map_path.with_suffix(".tmp")

    removed = 0
    kept = 0

    with open(syllable_map_path, encoding="utf8") as f_in:
        with open(temp_path, "w", encoding="utf8") as f_out:
            writer = csv.writer(f_out)

            for row in csv.reader(f_in):
                if len(row) >= 2:
                    hangul, roman = row[0], row[1]
                    if (hangul, roman) in incorrect_mappings:
                        removed += 1
                        print(f"Removing incorrect: {hangul},{roman}")
                    else:
                        writer.writerow(row)
                        kept += 1
                else:
                    writer.writerow(row)

    # Replace original file
    temp_path.replace(syllable_map_path)

    print(f"✓ Removed {removed} incorrect mappings")
    print(f"✓ Kept {kept} mappings")


if __name__ == "__main__":
    main()
