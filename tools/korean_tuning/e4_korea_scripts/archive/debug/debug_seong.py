import sys

sys.path.append('src')
from converter import eng2kor, kor2eng

# Debug Seong vs Sung issue
print("Testing 성 romanization:")
kor = eng2kor("Seong")
print(f"eng2kor('Seong') = {kor}")

kor = eng2kor("Sung")  
print(f"eng2kor('Sung') = {kor}")

# Test full name
print("\nFull name test:")
kor = eng2kor("Oh, Seong-Joon")
print(f"eng2kor('Oh, Seong-Joon') = {kor}")

if kor:
    eng = kor2eng(kor)
    print(f"kor2eng('{kor}') = '{eng}' (without original)")
    
    eng2 = kor2eng(kor, "Oh, Seong-Joon")
    print(f"kor2eng('{kor}', 'Oh, Seong-Joon') = '{eng2}' (with original)")