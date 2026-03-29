import pytest

CJK = [
    ("张伟", "Zhang Wei"),
    ("王芳", "Wang Fang"),
    ("김민준", "Kim Min-jun"),
    ("佐藤", "Sato"),
]
SEA = [
    ("ສະບາຍດີ", "sabaidee"),
    ("សួស្តី", "suostei"),
    ("สวัสดี", "sawasdee"),
]  # Lao, Khmer, Thai (approx translits)


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_cjk_roundtrip_metric(dice):
    ok = 0
    for native, latin in CJK:
        generated = latin  # replace with system romaniser output when available
        score = dice(generated, latin)
        if score >= 0.97:
            ok += 1
    rate = ok / len(CJK)
    assert rate >= 0.97, f"Round-trip (CJK) {rate:.2%} below 97%"


@pytest.mark.paranoid
@pytest.mark.timeout(15)
def test_sea_roundtrip_metric(dice):
    ok = 0
    for native, latin in SEA:
        generated = latin  # replace with real pipeline roundtrip
        score = dice(generated, latin)
        if score >= 0.97:
            ok += 1
    rate = ok / len(SEA)
    assert rate >= 0.97, f"Round-trip (SEA) {rate:.2%} below 97%"
