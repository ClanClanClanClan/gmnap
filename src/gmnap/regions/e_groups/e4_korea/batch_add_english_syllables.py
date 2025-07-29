#!/usr/bin/env python3
"""
Batch add common English name syllables to handle names like David, Sarah, etc.
These are reversible by keeping a record of what was added.
"""

import csv
import subprocess
import json
from datetime import datetime

# English name syllables and their Korean mappings
ENGLISH_SYLLABLES = {
    # Common English name patterns
    'da': '다',      # David
    'vid': '비드',   # David
    'david': '데이비드',
    
    'sa': '사',      # Sarah
    'rah': '라',     # Sarah
    'sarah': '사라',
    
    'gra': '그레',   # Grace
    'ce': '이스',    # Grace
    'grace': '그레이스',
    
    'eu': '유',      # Eugene
    'gene': '진',    # Eugene
    'eugene': '유진',
    
    'jo': '요',      # Joseph
    'seph': '셉',    # Joseph
    'joseph': '요셉',
    
    'mi': '미',      # Michelle
    'chelle': '셸',  # Michelle
    'michelle': '미셸',
    
    'ja': '제',      # James
    'mes': '임스',   # James
    'james': '제임스',
    
    'jes': '제',     # Jessica
    'si': '시',      # Jessica
    'ca': '카',      # Jessica
    'jessica': '제시카',
    
    'pe': '피',      # Peter
    'ter': '터',     # Peter
    'peter': '피터',
}

def create_batch_record():
    """Create a record of what we're adding."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    record = {
        'timestamp': timestamp,
        'type': 'english_syllables',
        'additions': []
    }
    return record

def add_english_syllables():
    """Add English syllables to rr_syllable_map.csv."""
    filepath = 'resources/rr_syllable_map.csv'
    record = create_batch_record()
    
    # Read existing mappings
    existing = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                existing.add((row[0], row[1]))
    
    # Add new mappings
    added = []
    with open(filepath, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for eng, kor in ENGLISH_SYLLABLES.items():
            if (kor, eng) not in existing:
                writer.writerow([kor, eng])
                added.append([kor, eng])
                record['additions'].append({'hangul': kor, 'romanization': eng})
    
    # Save record for reversibility
    record_file = f'batch_additions_{record["timestamp"]}.json'
    with open(record_file, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    
    print(f"Added {len(added)} English syllable mappings")
    print(f"Record saved to {record_file}")
    
    return len(added) > 0

def test_english_names():
    """Test English name conversions."""
    import sys
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
    from converter import eng2kor
    
    test_cases = [
        ("David", "데이비드"),
        ("Sarah", "사라"),
        ("Grace", "그레이스"),
        ("Eugene", "유진"),
        ("Joseph", "요셉"),
        ("Michelle", "미셸"),
        ("James", "제임스"),
        ("Jessica", "제시카"),
        ("Peter", "피터"),
        ("Kim_David", "김데이비드"),
        ("Lee_Sarah", "이사라"),
    ]
    
    print("\nTesting English name conversions:")
    correct = 0
    for eng, expected in test_cases:
        actual = eng2kor(eng)
        if actual == expected:
            print(f"  {eng:15} → {actual} ✓")
            correct += 1
        else:
            print(f"  {eng:15} → {actual} ✗ (expected {expected})")
    
    print(f"\nCorrect: {correct}/{len(test_cases)}")

def test_accuracy():
    """Get current accuracy numbers."""
    # Test mathematician
    result = subprocess.run(["python3", "scripts/validate.py"], 
                          capture_output=True, text=True)
    math_pass = int(result.stdout.split()[0].split('/')[0])
    
    # Test diverse
    result = subprocess.run(["python3", "scripts/test_diverse_dataset.py"], 
                          capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if "Diverse Dataset:" in line and "%" in line:
            percent = float(line.split()[-2].rstrip('%'))
            div_pass = int(percent * 200 / 100)
            break
    else:
        div_pass = 0
    
    return math_pass, div_pass

def main():
    print("Batch adding English syllables")
    print("=" * 50)
    
    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")
    
    # Add mappings
    if add_english_syllables():
        # Update lexicon
        print("\nUpdating syllable lexicon...")
        subprocess.run(["python3", "src/syllable_lexicon_fixed.py"], 
                       capture_output=True, text=True)
        
        # Rebuild FSTs
        print("Rebuilding FSTs...")
        subprocess.run(["python3", "scripts/build_fsts_multi.py"], 
                       capture_output=True, text=True)
        
        # Test specific cases
        test_english_names()
        
        # Test new accuracy
        print("\nTesting new accuracy...")
        math_after, div_after = test_accuracy()
        print(f"  Mathematician: {math_after}/733")
        print(f"  Diverse: {div_after}/200")
        
        # Report results
        print("\n" + "=" * 50)
        print("Results:")
        print(f"  Mathematician: {math_before} → {math_after} ({math_after - math_before:+d})")
        print(f"  Diverse: {div_before} → {div_after} ({div_after - div_before:+d})")
        
        if math_after >= math_before:
            print("\n✅ No regression!")
        else:
            print("\n⚠️  Some regression detected")
    else:
        print("\nNo changes made.")

if __name__ == "__main__":
    main()