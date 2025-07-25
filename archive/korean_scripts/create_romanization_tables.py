#!/usr/bin/env python3
"""
Create the required romanization CSV tables per blueprint Phase 2
"""

import csv
import os

def create_romanization_tables():
    """Create all 4 required romanization system tables"""
    print("=== CREATING ROMANIZATION TABLES (PHASE 2) ===\n")
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # 1. Revised Romanization (RR) - Official Korean Government System
    rr_data = [
        ['hangul', 'roman', 'notes'],
        ['가', 'ga', 'basic'],
        ['김', 'gim', 'surname'],
        ['김', 'kim', 'surname_variant'],
        ['이', 'i', 'surname'],
        ['이', 'lee', 'surname_variant'],
        ['이', 'yi', 'surname_variant'],
        ['박', 'bak', 'surname'],
        ['박', 'park', 'surname_variant'],
        ['최', 'choi', 'surname'],
        ['정', 'jeong', 'surname'],
        ['정', 'jung', 'surname_variant'],
        ['강', 'gang', 'surname'],
        ['강', 'kang', 'surname_variant'],
        ['조', 'jo', 'surname'],
        ['윤', 'yun', 'surname'],
        ['윤', 'yoon', 'surname_variant'],
        ['장', 'jang', 'surname'],
        ['장', 'chang', 'surname_variant'],
        ['임', 'im', 'surname'],
        ['임', 'lim', 'surname_variant'],
        ['한', 'han', 'surname'],
        ['오', 'o', 'surname'],
        ['서', 'seo', 'surname'],
        ['신', 'sin', 'surname'],
        ['권', 'gwon', 'surname'],
        ['황', 'hwang', 'surname'],
        ['안', 'an', 'surname'],
        ['송', 'song', 'surname'],
        ['홍', 'hong', 'surname'],
        ['전', 'jeon', 'surname'],
        ['고', 'go', 'surname'],
        ['문', 'mun', 'surname'],
        ['손', 'son', 'surname'],
        ['양', 'yang', 'surname'],
        ['배', 'bae', 'surname'],
        ['조', 'cho', 'surname_variant'],
        ['주', 'ju', 'surname'],
        ['백', 'baek', 'surname'],
        ['허', 'heo', 'surname'],
        ['유', 'yu', 'surname'],
        ['노', 'no', 'surname'],
        ['하', 'ha', 'surname'],
        ['김', 'gim', 'surname'],
        ['현', 'hyeon', 'given'],
        ['현', 'hyun', 'given_variant'],
        ['영', 'yeong', 'given'],
        ['영', 'young', 'given_variant'],
        ['수', 'su', 'given'],
        ['수', 'soo', 'given_variant'],
        ['민', 'min', 'given'],
        ['지', 'ji', 'given'],
        ['호', 'ho', 'given'],
        ['진', 'jin', 'given'],
        ['성', 'seong', 'given'],
        ['성', 'sung', 'given_variant'],
        ['준', 'jun', 'given'],
        ['준', 'joon', 'given_variant'],
        ['원', 'won', 'given'],
        ['용', 'yong', 'given'],
        ['일', 'il', 'given'],
        ['철', 'cheol', 'given'],
        ['철', 'chul', 'given_variant'],
        ['기', 'gi', 'given'],
        ['기', 'ki', 'given_variant'],
        ['태', 'tae', 'given'],
        ['범', 'beom', 'given'],
        ['범', 'bum', 'given_variant'],
        ['규', 'gyu', 'given'],
        ['규', 'kyu', 'given_variant']
    ]
    
    with open('data/revised_romanization.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rr_data)
    print("✅ Created data/revised_romanization.csv")
    
    # 2. McCune-Reischauer (MR) - Academic Standard
    mr_data = [
        ['hangul', 'roman', 'notes'],
        ['가', 'ka', 'basic'],
        ['김', "k'im", 'surname'],
        ['이', 'i', 'surname'], 
        ['박', "pak", 'surname'],
        ['최', "ch'oe", 'surname'],
        ['정', 'chŏng', 'surname'],
        ['강', 'kang', 'surname'],
        ['조', 'cho', 'surname'],
        ['윤', 'yun', 'surname'],
        ['장', 'chang', 'surname'],
        ['임', 'im', 'surname'],
        ['한', 'han', 'surname'],
        ['오', 'o', 'surname'],
        ['서', 'sŏ', 'surname'],
        ['신', 'sin', 'surname'],
        ['권', "kwŏn", 'surname'],
        ['황', 'hwang', 'surname'],
        ['안', 'an', 'surname'],
        ['송', 'song', 'surname'],
        ['홍', 'hong', 'surname'],
        ['현', 'hyŏn', 'given'],
        ['영', 'yŏng', 'given'], 
        ['수', 'su', 'given'],
        ['민', 'min', 'given'],
        ['지', 'chi', 'given'],
        ['호', 'ho', 'given'],
        ['진', 'chin', 'given'],
        ['성', 'sŏng', 'given'],
        ['준', 'chun', 'given'],
        ['원', 'wŏn', 'given'],
        ['용', 'yong', 'given'],
        ['일', 'il', 'given'],
        ['철', "ch'ŏl", 'given'],
        ['기', 'ki', 'given'],
        ['태', "t'ae", 'given'],
        ['범', 'pŏm', 'given'],
        ['규', 'kyu', 'given']
    ]
    
    with open('data/mccune_reischauer.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(mr_data)
    print("✅ Created data/mccune_reischauer.csv")
    
    # 3. Yale Romanization - Linguistic Standard
    yale_data = [
        ['hangul', 'roman', 'notes'],
        ['가', 'ka', 'basic'],
        ['김', 'kim', 'surname'],
        ['이', 'i', 'surname'],
        ['박', 'pak', 'surname'], 
        ['최', 'choy', 'surname'],
        ['정', 'ceng', 'surname'],
        ['강', 'kang', 'surname'],
        ['조', 'co', 'surname'],
        ['윤', 'yun', 'surname'],
        ['장', 'cang', 'surname'],
        ['임', 'im', 'surname'],
        ['한', 'han', 'surname'],
        ['오', 'o', 'surname'],
        ['서', 'se', 'surname'],
        ['신', 'sin', 'surname'],
        ['권', 'kwen', 'surname'],
        ['황', 'hwang', 'surname'],
        ['안', 'an', 'surname'],
        ['송', 'song', 'surname'],
        ['홍', 'hong', 'surname'],
        ['현', 'hyen', 'given'],
        ['영', 'yeng', 'given'],
        ['수', 'swu', 'given'],
        ['민', 'min', 'given'],
        ['지', 'ci', 'given'],
        ['호', 'ho', 'given'],
        ['진', 'cin', 'given'],
        ['성', 'seng', 'given'],
        ['준', 'cwun', 'given'],
        ['원', 'wen', 'given'],
        ['용', 'yong', 'given'],
        ['일', 'il', 'given'],
        ['철', 'chel', 'given'],
        ['기', 'ki', 'given'],
        ['태', 'thay', 'given'],
        ['범', 'pem', 'given'],
        ['규', 'kyu', 'given']
    ]
    
    with open('data/yale_romanization.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(yale_data)
    print("✅ Created data/yale_romanization.csv")
    
    # 4. MLTR (Multi-Lingual Text Representation) - ISO Standard
    mltr_data = [
        ['hangul', 'roman', 'notes'],
        ['가', 'ga', 'basic'],
        ['김', 'gim', 'surname'],
        ['이', 'i', 'surname'],
        ['박', 'bag', 'surname'],
        ['최', 'choe', 'surname'],
        ['정', 'jeong', 'surname'],
        ['강', 'gang', 'surname'],
        ['조', 'jo', 'surname'],
        ['윤', 'yun', 'surname'],
        ['장', 'jang', 'surname'],
        ['임', 'im', 'surname'],
        ['한', 'han', 'surname'],
        ['오', 'o', 'surname'],
        ['서', 'seo', 'surname'],
        ['신', 'sin', 'surname'],
        ['권', 'gweon', 'surname'],
        ['황', 'hwang', 'surname'],
        ['안', 'an', 'surname'],
        ['송', 'song', 'surname'],
        ['홍', 'hong', 'surname'],
        ['현', 'hyeon', 'given'],
        ['영', 'yeong', 'given'],
        ['수', 'su', 'given'],
        ['민', 'min', 'given'],
        ['지', 'ji', 'given'],
        ['호', 'ho', 'given'],
        ['진', 'jin', 'given'],
        ['성', 'seong', 'given'],
        ['준', 'jun', 'given'],
        ['원', 'weon', 'given'],
        ['용', 'yong', 'given'],
        ['일', 'il', 'given'],
        ['철', 'cheol', 'given'],
        ['기', 'gi', 'given'],
        ['태', 'tae', 'given'],
        ['범', 'beom', 'given'],
        ['규', 'gyu', 'given']
    ]
    
    with open('data/mltr_romanization.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(mltr_data)
    print("✅ Created data/mltr_romanization.csv")
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Revised Romanization: {len(rr_data)-1} entries")
    print(f"  ✅ McCune-Reischauer: {len(mr_data)-1} entries") 
    print(f"  ✅ Yale Romanization: {len(yale_data)-1} entries")
    print(f"  ✅ MLTR Standard: {len(mltr_data)-1} entries")
    print(f"\n🎉 Phase 2 romanization tables complete!")

if __name__ == "__main__":
    create_romanization_tables()