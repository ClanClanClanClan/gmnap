#!/usr/bin/env python3
"""
Patch C: Implement loanword transliteration micro-pipe
Handles foreign (non-Korean) names with phonetic rules
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== PATCH C: LOANWORD TRANSLITERATION ===")
print("Adding phonetic mappings for foreign names...")

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

# Common English/foreign name syllables with Korean phonetic equivalents
# Based on standard Korean transliteration rules for foreign words
loanword_mappings = [
    # English consonant clusters
    ("브", "br", "-0.5"),  # Brian → 브라이언
    ("크", "cr", "-0.5"),  # Craig → 크레이그
    ("드", "dr", "-0.5"),  # Drew → 드류
    ("프", "fr", "-0.5"),  # Frank → 프랭크
    ("그", "gr", "-0.5"),  # Grace → 그레이스
    ("스", "st", "-0.5"),  # Steve → 스티브
    ("트", "tr", "-0.5"),  # Tracy → 트레이시
    # Common English name endings
    ("빗", "vid", "-0.3"),  # David → 데이빗
    ("빈", "vin", "-0.3"),  # Kevin → 케빈
    ("니", "ny", "-0.3"),  # Tiffany → 티파니
    ("시", "cy", "-0.3"),  # Nancy → 낸시
    ("리", "ry", "-0.3"),  # Mary → 메리
    ("디", "dy", "-0.3"),  # Wendy → 웬디
    # Vowel combinations
    ("에이", "ay", "-0.4"),  # Kay → 케이
    ("아이", "ai", "-0.4"),  # Kai → 카이
    ("오", "au", "-0.4"),  # Paul → 폴
    ("이", "ea", "-0.4"),  # Sean → 션
    ("우", "oo", "-0.4"),  # Moon → 문
    # Common foreign name components
    ("린다", "linda", "-0.2"),
    ("데이빗", "david", "-0.2"),
    ("그레이스", "grace", "-0.2"),
    ("마이클", "michael", "-0.2"),
    ("제니퍼", "jennifer", "-0.2"),
    ("케빈", "kevin", "-0.2"),
    ("제시카", "jessica", "-0.2"),
    ("스티븐", "steven", "-0.2"),
    ("앤드류", "andrew", "-0.2"),
    ("다니엘", "daniel", "-0.2"),
    # Single letter phonetics
    ("에이", "a", "0.5"),  # A → 에이 (when standalone)
    ("비", "b", "0.5"),  # B → 비
    ("시", "c", "0.5"),  # C → 시
    ("디", "d", "0.5"),  # D → 디
    ("이", "e", "0.5"),  # E → 이
    ("에프", "f", "0.5"),  # F → 에프
    ("지", "g", "0.5"),  # G → 지
    ("에이치", "h", "0.5"),  # H → 에이치
    ("제이", "j", "0.5"),  # J → 제이
    ("케이", "k", "0.5"),  # K → 케이
    ("엘", "l", "0.5"),  # L → 엘
    ("엠", "m", "0.5"),  # M → 엠
    ("엔", "n", "0.5"),  # N → 엔
    ("피", "p", "0.5"),  # P → 피
    ("큐", "q", "0.5"),  # Q → 큐
    ("알", "r", "0.5"),  # R → 알
    ("에스", "s", "0.5"),  # S → 에스
    ("티", "t", "0.5"),  # T → 티
    ("유", "u", "0.5"),  # U → 유
    ("브이", "v", "0.5"),  # V → 브이
    ("더블유", "w", "0.5"),  # W → 더블유
    ("엑스", "x", "0.5"),  # X → 엑스
    ("와이", "y", "0.5"),  # Y → 와이
    ("지", "z", "0.5"),  # Z → 지/제트
]

print(f"Current rows: {len(rows)}")

# Add loanword mappings
added_count = 0
existing_mappings = {(row[0], row[1]) for row in rows if len(row) >= 2}

for hangul, roman, weight in loanword_mappings:
    if (hangul, roman) not in existing_mappings:
        rows.append([hangul, roman, weight])
        print(f"  ADDED: {roman} → {hangul} (weight: {weight})")
        added_count += 1

print(f"\nTotal rows after loanwords: {len(rows)}")
print(f"Loanword mappings added: {added_count}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Patch C loanword mappings applied!")
print("\n=== EXPECTED IMPROVEMENTS ===")
print("1. Foreign names like David, Grace, Michael will transliterate correctly")
print("2. English initials (Kim J.) will map to Korean letters")
print("3. Mixed Korean-English names will handle both parts properly")
print("4. Better handling of consonant clusters (br, gr, st, etc.)")
print("\nTarget: +5 improvements according to expert guidance")
